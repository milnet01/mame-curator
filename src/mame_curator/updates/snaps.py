"""Download + extract progettoSnaps snap pack into ``data/snaps/snap/``.

Per ``docs/specs/P10.md`` § "1. progettoSnaps — local pack model" and
§ "``mame-curator refresh-snaps`` CLI".

Snap is the only kind progettoSnaps actively publishes (verified
2026-05-18). The pack URL pattern is
``https://www.progettosnaps.net/snapshots/packs/full_sets/pS_snap_fullset_<NNN>.zip``
where ``<NNN>`` is the MAME version (e.g. ``287`` for MAME 0.287).
Discovery scrapes the Snapshots index page for the highest ``<NNN>``;
``--url`` overrides discovery for pinned older versions or upstream
URL drift.

The downloader uses ``mame_curator.downloads.download`` (P07 ✅) with
the body cap raised to 600 MB (snap pack is ~498 MB; the default 100 MB
cap is sized for INIs).
"""

from __future__ import annotations

import logging
import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

import httpx

from mame_curator.downloads import ManualFallback, download

logger = logging.getLogger(__name__)

INDEX_URL = "https://www.progettosnaps.net/snapshots"

# Capture group 1 = the URL (relative or absolute); group 2 = the NNN.
# Both relative (``href="/snapshots/..."``) and absolute
# (``href="https://www.progettosnaps.net/snapshots/..."``) shapes appear
# on the live index page side-by-side, so the prefix is optional.
PACK_URL_PATTERN = re.compile(
    r'href="((?:https?://www\.progettosnaps\.net)?'
    r"/snapshots/packs/full_sets/pS_snap_fullset_(\d+)\.zip)\""
)

# Pack body cap. Snap pack at MAME 0.287 is ~498 MB; headroom for the
# next several releases keeps the cap stable.
SNAP_PACK_MAX_BYTES = 600 * 1024 * 1024

# Default destination root; the actual files land under ``<dest>/snap/``.
DEFAULT_DEST = Path("./data/snaps")


@dataclass(frozen=True)
class SnapsRefreshReport:
    """Outcome of one ``refresh_snaps`` invocation."""

    downloaded: bool
    """True if a fresh pack was fetched + extracted."""

    pack_url: str
    """The URL we ended up fetching (post-discovery or --url override)."""

    files_extracted: int
    """Count of PNG entries that landed on disk."""

    files_skipped: int
    """PNG entries that existed already and ``force=False`` left untouched."""

    error: str | None = None
    """Populated on disk-space gate failure or download failure. A corrupt
    pack at extract raises (``BadZipFile`` / ``OSError``) rather than
    populating this field."""


async def discover_snap_pack_url(
    *,
    client: httpx.AsyncClient,
    index_url: str = INDEX_URL,
) -> str:
    """Return the highest-MAME-version snap-pack URL listed on the index.

    Raises ``ValueError`` if no candidate URLs are found (upstream
    restructured) — callers should fall back to ``--url`` or surface
    the error to the user.
    """
    response = await client.get(index_url)
    response.raise_for_status()
    candidates: list[tuple[int, str]] = []
    for match in PACK_URL_PATTERN.finditer(response.text):
        url, nnn = match.group(1), int(match.group(2))
        if url.startswith("/"):
            url = "https://www.progettosnaps.net" + url
        candidates.append((nnn, url))
    if not candidates:
        raise ValueError(
            f"discover_snap_pack_url: no pS_snap_fullset_<NNN>.zip links found at "
            f"{index_url!r} — upstream may have restructured. Pass --url to override."
        )
    candidates.sort(key=lambda pair: pair[0], reverse=True)
    return candidates[0][1]


async def refresh_snaps(
    *,
    dest_dir: Path,
    client: httpx.AsyncClient,
    url: str | None = None,
    force: bool = False,
) -> SnapsRefreshReport:
    """Download the snap pack and extract PNGs into ``dest_dir/snap/``.

    Discovery is skipped when ``url`` is provided. The disk-space gate
    checks ``dest_dir``'s filesystem reports at least 2x the pack's
    declared content-length free before issuing the GET.

    Returns a ``SnapsRefreshReport``. The destination directory is
    created if missing; existing files are preserved unless ``force=True``.
    """
    pack_url = url if url is not None else await discover_snap_pack_url(client=client)

    declared_size = await _head_content_length(client, pack_url)
    if declared_size is not None:
        usage = shutil.disk_usage(dest_dir if dest_dir.exists() else dest_dir.parent)
        required = declared_size * 2
        if usage.free < required:
            error = (
                f"refresh_snaps: not enough disk space at {dest_dir!s} - "
                f"need ~{required // (1024 * 1024)} MiB free (2x pack size), "
                f"got {usage.free // (1024 * 1024)} MiB"
            )
            logger.warning(error)
            return SnapsRefreshReport(
                downloaded=False,
                pack_url=pack_url,
                files_extracted=0,
                files_skipped=0,
                error=error,
            )

    snap_dir = dest_dir / "snap"
    snap_dir.mkdir(parents=True, exist_ok=True)

    pack_path = dest_dir / "pS_snap_fullset.zip"
    result = await download(
        url=pack_url,
        dest=pack_path,
        client=client,
        max_bytes=SNAP_PACK_MAX_BYTES,
    )
    if isinstance(result, ManualFallback):
        error = f"refresh_snaps: download failed: {result.reason}"
        logger.warning(error)
        return SnapsRefreshReport(
            downloaded=False,
            pack_url=pack_url,
            files_extracted=0,
            files_skipped=0,
            error=error,
        )

    extracted, skipped = _extract_pack(pack_path, snap_dir, force=force)
    return SnapsRefreshReport(
        downloaded=True,
        pack_url=pack_url,
        files_extracted=extracted,
        files_skipped=skipped,
    )


async def _head_content_length(client: httpx.AsyncClient, url: str) -> int | None:
    """Return the declared content-length of ``url`` via HEAD, or ``None``."""
    try:
        response = await client.head(url)
    except httpx.HTTPError as exc:
        logger.info("refresh_snaps: HEAD probe failed for %s: %s", url, exc)
        return None
    declared = response.headers.get("content-length")
    if declared is None:
        return None
    try:
        return int(declared)
    except ValueError:
        return None


def _extract_pack(pack_path: Path, snap_dir: Path, *, force: bool) -> tuple[int, int]:
    """Extract ``*.png`` entries from ``pack_path`` flat into ``snap_dir``.

    Subdirectory paths inside the ZIP are ignored — the documented
    upstream layout is flat ``<short_name>.png`` at the archive root.
    Non-PNG entries (READMEs, manifests) are skipped silently.

    Returns ``(extracted, skipped)``.
    """
    extracted = 0
    skipped = 0
    with zipfile.ZipFile(pack_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename
            # Flat layout only: skip entries with a directory component.
            if "/" in name or "\\" in name:
                continue
            if not name.lower().endswith(".png"):
                continue
            dest = snap_dir / name
            if dest.exists() and not force:
                skipped += 1
                continue
            with zf.open(info) as src, dest.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            extracted += 1
    return extracted, skipped

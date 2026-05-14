"""Lazy-fetch disk cache for media URLs.

Per ``docs/specs/P05.md`` § Public API:

- ``cache_path_for`` is pure (no I/O).
- ``fetch_with_cache`` returns the on-disk path if cached; otherwise downloads
  via the caller-supplied ``httpx.AsyncClient`` and writes atomically.
- 404 is the no-image sentinel (returns ``None``); no negative caching.
- Other upstream errors raise ``MediaFetchError``.
"""

from __future__ import annotations

import contextlib
import hashlib
import logging
import os
from pathlib import Path
from urllib.parse import urlparse

import httpx

from mame_curator._atomic import fsync_parent_dir

logger = logging.getLogger(__name__)

# FP27 B4: 16 MiB default cap. Libretro-thumbnails images at the
# typical 90th percentile are ~500 KiB; 16 MiB leaves ~30x headroom
# for fanart while putting a hard ceiling on accidental OOMs from a
# misconfigured or malicious upstream.
DEFAULT_MAX_BYTES = 16 * 1024 * 1024

_ALLOWED_URL_SCHEMES = frozenset({"http", "https"})


class MediaError(Exception):
    """Base class for media subsystem errors."""


class MediaFetchError(MediaError):
    """Upstream non-200 (other than 404) or network failure."""


def cache_path_for(url: str, cache_dir: Path) -> Path:
    """Return ``cache_dir / f"{sha256(url).hexdigest()}{ext}"``.

    ``ext`` is the URL path's suffix (``.png`` for libretro thumbnails). URLs
    with no path suffix produce a bare-hex filename. Pure function — no I/O,
    no directory creation.
    """
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    ext = Path(urlparse(url).path).suffix
    return cache_dir / f"{digest}{ext}"


async def fetch_with_cache(
    url: str,
    cache_dir: Path,
    *,
    client: httpx.AsyncClient,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> Path | None:
    """Return cached path if present; otherwise download, cache, return path.

    404 returns ``None`` (sentinel; no negative caching). Other upstream
    failures raise ``MediaFetchError`` with the underlying ``httpx.HTTPError``
    chained via ``__cause__`` when applicable.

    Concurrent calls for the same URL are safe: the write uses a unique
    ``.tmp`` sibling + ``os.replace`` so the cache file is never torn.
    The wasted second download is acceptable at single-user scale.

    FP27 B4: rejects non-http(s) schemes (``file://``, ``data:``, etc.)
    before any network call; caps the body at ``max_bytes`` (default
    16 MiB) — both abort with ``MediaFetchError``; streams chunks
    straight to ``.tmp`` instead of buffering ``resp.content``.
    Mirrors the streaming-cap pattern from ``downloads.py`` (same
    ``BodyTooLarge: …`` log-line prefix; control flow differs because
    media has no mirror list — failures raise immediately).
    """
    # FP27 B4: scheme check first, before any I/O. file:// / data: /
    # ftp: URLs would otherwise be processed by httpx and might leak
    # filesystem-path semantics.
    scheme = urlparse(url).scheme
    if scheme not in _ALLOWED_URL_SCHEMES:
        raise MediaFetchError(f"unsupported scheme: {scheme!r} for {url!r}")

    path = cache_path_for(url, cache_dir)
    # FP10 A4: TOCTOU-safe — cache writes are append-only via the
    # atomic-replace below (no delete path); a concurrent rename
    # produces a new inode whose bytes any reader after this exists()
    # check sees correctly under POSIX.
    if path.exists():
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    aborted = False
    total = 0
    try:
        async with client.stream("GET", url) as resp:
            if resp.status_code == 404:
                return None
            if resp.status_code != 200:
                raise MediaFetchError(f"upstream {resp.status_code} for {url!r}")
            tmp_handle = tmp.open("wb")
            try:
                async for chunk in resp.aiter_bytes(chunk_size=64 * 1024):
                    total += len(chunk)
                    if total > max_bytes:
                        msg = f"BodyTooLarge: {url}: streamed {total} bytes exceeds cap {max_bytes}"
                        logger.warning("media/cache: %s", msg)
                        aborted = True
                        raise MediaFetchError(msg)
                    tmp_handle.write(chunk)
                tmp_handle.flush()
                os.fsync(tmp_handle.fileno())
            finally:
                tmp_handle.close()
    except httpx.HTTPError as exc:
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)
        raise MediaFetchError(f"network error for {url!r}: {exc}") from exc
    except MediaFetchError:
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)
        raise

    if aborted:
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)
        return None  # unreachable; the raise above fires first
    if total == 0:
        # FP10 A2: raw.githubusercontent.com rate-limit interstitials and CDN
        # edge cases occasionally return 200 + Content-Length: 0. Caching that
        # poisons the slot; treat as a fetch error instead.
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)
        raise MediaFetchError(f"empty body for {url!r}")
    os.replace(tmp, path)
    fsync_parent_dir(path)
    return path

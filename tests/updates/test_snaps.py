"""Tests for ``mame_curator.updates.snaps`` (P10 chunk 3a).

Per ``docs/specs/P10.md`` § "1. progettoSnaps — local pack model" and
§ "`mame-curator refresh-snaps` CLI". Snap is the only kind progettoSnaps
maintains upstream (verified 2026-05-18); chunk 3a downloads the
versioned ZIP pack and extracts ``<name>.png`` entries into
``data/snaps/snap/``.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import httpx
import pytest
import respx


@pytest.fixture(autouse=True)
def _no_sleep(no_sleep: None) -> None:
    pass


_INDEX_BODY = """
<html><body>
<a href="/snapshots/packs/full_sets/pS_snap_fullset_278.zip">0.278</a>
<a href="/snapshots/packs/full_sets/pS_snap_fullset_287.zip">0.287</a>
<a href="https://www.progettosnaps.net/snapshots/packs/full_sets/pS_snap_fullset_282.zip">0.282</a>
<a href="/snapshots/packs/pS_artpreview_upd_287.zip">unrelated</a>
</body></html>
""".strip()


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    """Build an in-memory ZIP archive carrying ``entries``."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _mount_pack(mock: respx.MockRouter, url: str, body: bytes) -> None:
    """Mount both the HEAD-probe and GET routes for a pack URL."""
    headers = {"content-length": str(len(body))}
    mock.head(url).mock(return_value=httpx.Response(200, headers=headers))
    mock.get(url).mock(return_value=httpx.Response(200, content=body, headers=headers))


async def test_refresh_snaps_discovery_picks_highest_mame_version() -> None:
    """``discover_snap_pack_url`` parses the index and returns the highest NNN URL."""
    from mame_curator.updates.snaps import INDEX_URL, discover_snap_pack_url

    with respx.mock(assert_all_called=True) as mock:
        mock.get(INDEX_URL).mock(return_value=httpx.Response(200, text=_INDEX_BODY))
        async with httpx.AsyncClient() as client:
            url = await discover_snap_pack_url(client=client)

    # 287 wins over 282 and 278; the artpreview href is correctly ignored
    # (different filename stem). Discovery normalises to the canonical
    # absolute URL form (the index mixes relative + absolute hrefs).
    assert url == "https://www.progettosnaps.net/snapshots/packs/full_sets/pS_snap_fullset_287.zip"


async def test_refresh_snaps_downloads_pack_via_downloads_primitive(
    tmp_path: Path,
) -> None:
    """``refresh_snaps`` discovers the URL, hits it, and reports success."""
    from mame_curator.updates.snaps import INDEX_URL, refresh_snaps

    pack_url = "https://www.progettosnaps.net/snapshots/packs/full_sets/pS_snap_fullset_287.zip"
    pack_body = _zip_bytes({"pacman.png": b"\x89PNG\r\n\x1a\nfake"})

    with respx.mock(assert_all_called=True) as mock:
        mock.get(INDEX_URL).mock(return_value=httpx.Response(200, text=_INDEX_BODY))
        _mount_pack(mock, pack_url, pack_body)
        async with httpx.AsyncClient() as client:
            report = await refresh_snaps(dest_dir=tmp_path, client=client)

    assert report.downloaded is True
    assert report.pack_url == pack_url
    assert report.error is None
    assert (tmp_path / "snap" / "pacman.png").exists()
    assert report.files_extracted == 1


async def test_refresh_snaps_extracts_zip_into_snap_dir(tmp_path: Path) -> None:
    """The ZIP's ``<name>.png`` entries land flat under ``<dest>/snap/``."""
    from mame_curator.updates.snaps import refresh_snaps

    pack_url = "https://example.test/pS_snap_fullset_999.zip"
    pack_body = _zip_bytes(
        {
            "pacman.png": b"pac",
            "dkong.png": b"dk",
            "galaga.png": b"gal",
        }
    )

    with respx.mock(assert_all_called=True) as mock:
        _mount_pack(mock, pack_url, pack_body)
        async with httpx.AsyncClient() as client:
            report = await refresh_snaps(dest_dir=tmp_path, url=pack_url, client=client)

    assert report.files_extracted == 3
    for name in ("pacman.png", "dkong.png", "galaga.png"):
        assert (tmp_path / "snap" / name).read_bytes() in {b"pac", b"dk", b"gal"}


async def test_refresh_snaps_verifies_disk_space_before_download(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If ``shutil.disk_usage`` reports < 2x pack size free, the CLI refuses."""
    import shutil
    from collections import namedtuple

    from mame_curator.updates.snaps import refresh_snaps

    pack_url = "https://example.test/pS_snap_fullset_999.zip"
    pack_body = _zip_bytes({"pacman.png": b"pac"})

    Usage = namedtuple("Usage", "total used free")
    monkeypatch.setattr(shutil, "disk_usage", lambda _p: Usage(total=10_000_000, used=0, free=100))

    # The HEAD request lets refresh-snaps preflight content-length; do not
    # let the actual GET fire (assert_all_called=False — the GET mock is
    # there only as a tripwire if the disk-space gate fails to refuse).
    with respx.mock(assert_all_called=False) as mock:
        head_route = mock.head(pack_url).mock(
            return_value=httpx.Response(
                200,
                headers={"content-length": str(10_000_000)},
            )
        )
        get_route = mock.get(pack_url).mock(return_value=httpx.Response(200, content=pack_body))
        async with httpx.AsyncClient() as client:
            report = await refresh_snaps(dest_dir=tmp_path, url=pack_url, client=client)

    assert report.downloaded is False
    assert report.error is not None
    assert "disk space" in report.error.lower()
    assert head_route.called  # HEAD probe happened
    assert not get_route.called  # but the GET was aborted by the gate


async def test_refresh_snaps_refuses_overwrite_without_force(tmp_path: Path) -> None:
    """Pre-existing ``<dest>/snap/pacman.png`` is preserved unless ``--force``."""
    from mame_curator.updates.snaps import refresh_snaps

    snap_dir = tmp_path / "snap"
    snap_dir.mkdir()
    (snap_dir / "pacman.png").write_bytes(b"existing")

    pack_url = "https://example.test/pS_snap_fullset_999.zip"
    pack_body = _zip_bytes({"pacman.png": b"newer"})

    with respx.mock(assert_all_called=True) as mock:
        _mount_pack(mock, pack_url, pack_body)
        async with httpx.AsyncClient() as client:
            report = await refresh_snaps(dest_dir=tmp_path, url=pack_url, client=client)

    assert (snap_dir / "pacman.png").read_bytes() == b"existing"
    assert report.files_extracted == 0
    assert report.files_skipped == 1


async def test_refresh_snaps_force_overwrites_existing_files(tmp_path: Path) -> None:
    """``force=True`` overwrites pre-existing entries."""
    from mame_curator.updates.snaps import refresh_snaps

    snap_dir = tmp_path / "snap"
    snap_dir.mkdir()
    (snap_dir / "pacman.png").write_bytes(b"existing")

    pack_url = "https://example.test/pS_snap_fullset_999.zip"
    pack_body = _zip_bytes({"pacman.png": b"newer"})

    with respx.mock(assert_all_called=True) as mock:
        _mount_pack(mock, pack_url, pack_body)
        async with httpx.AsyncClient() as client:
            report = await refresh_snaps(dest_dir=tmp_path, url=pack_url, client=client, force=True)

    assert (snap_dir / "pacman.png").read_bytes() == b"newer"
    assert report.files_extracted == 1
    assert report.files_skipped == 0


async def test_refresh_snaps_url_override_skips_discovery(tmp_path: Path) -> None:
    """Passing ``url=`` skips the index scrape entirely."""
    from mame_curator.updates.snaps import INDEX_URL, refresh_snaps

    pack_url = "https://example.test/pS_snap_fullset_999.zip"
    pack_body = _zip_bytes({"pacman.png": b"pac"})

    with respx.mock(assert_all_called=False) as mock:
        index_route = mock.get(INDEX_URL).mock(return_value=httpx.Response(200, text=_INDEX_BODY))
        _mount_pack(mock, pack_url, pack_body)
        async with httpx.AsyncClient() as client:
            report = await refresh_snaps(dest_dir=tmp_path, url=pack_url, client=client)

    assert report.downloaded is True
    assert report.pack_url == pack_url
    assert not index_route.called, "url= override must skip discovery"


async def test_refresh_snaps_extraction_skips_non_png_entries(tmp_path: Path) -> None:
    """Non-PNG ZIP entries are ignored — only ``*.png`` lands in ``snap/``."""
    from mame_curator.updates.snaps import refresh_snaps

    pack_url = "https://example.test/pS_snap_fullset_999.zip"
    pack_body = _zip_bytes(
        {
            "pacman.png": b"pac",
            "readme.txt": b"readme body",
            "subdir/dkong.png": b"dk",  # subdirectory paths are ignored too
        }
    )

    with respx.mock(assert_all_called=True) as mock:
        _mount_pack(mock, pack_url, pack_body)
        async with httpx.AsyncClient() as client:
            report = await refresh_snaps(dest_dir=tmp_path, url=pack_url, client=client)

    assert (tmp_path / "snap" / "pacman.png").exists()
    assert not (tmp_path / "snap" / "readme.txt").exists()
    # Sub-paths in the ZIP are NOT honored — flat layout only, matching
    # the documented upstream pack structure.
    assert not (tmp_path / "snap" / "subdir" / "dkong.png").exists()
    assert not (tmp_path / "snap" / "dkong.png").exists()
    assert report.files_extracted == 1


def test_pack_url_pattern_matches_pinned_filename() -> None:
    """``PACK_URL_PATTERN`` recognises the canonical pinned filename shape.

    Regression-lock: if a future spec edit drifts the regex, this test
    catches it before the next live discovery breaks.
    """
    from mame_curator.updates.snaps import PACK_URL_PATTERN

    match = PACK_URL_PATTERN.search('href="/snapshots/packs/full_sets/pS_snap_fullset_287.zip"')
    assert match is not None
    assert match.group(2) == "287"

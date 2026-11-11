"""mame-curator-1225 — unpacking the progettoSnaps pack.

CR-04-3: an entry named like ``C:evil.png`` leaves ``snap/`` on Windows.
CR-04-4: the pack must fit in the free space before anything is unpacked.
Each entry is already cut at its declared size by ``zipfile`` itself.
"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from mame_curator.updates import snaps


def _pack(tmp_path: Path, entries: dict[str, bytes]) -> Path:
    path = tmp_path / "pack.zip"
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return path


def test_an_entry_with_a_drive_is_skipped(tmp_path: Path) -> None:
    snap_dir = tmp_path / "snap"
    snap_dir.mkdir()
    pack = _pack(tmp_path, {"C:evil.png": b"\x89PNG", "pacman.png": b"\x89PNG"})
    extracted, _ = snaps._extract_pack(pack, snap_dir, force=False)
    assert extracted == 1
    assert sorted(p.name for p in snap_dir.iterdir()) == ["pacman.png"]


def test_a_pack_larger_than_the_free_space_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    snap_dir = tmp_path / "snap"
    snap_dir.mkdir()
    pack = _pack(tmp_path, {"pacman.png": b"\x89PNG" * 100})
    monkeypatch.setattr(shutil, "disk_usage", lambda p: SimpleNamespace(free=10))
    with pytest.raises(snaps.SnapPackTooLargeError):
        snaps._extract_pack(pack, snap_dir, force=False)
    assert list(snap_dir.iterdir()) == []


async def test_refresh_reports_a_pack_too_large_to_unpack(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import httpx
    import respx

    pack_url = "https://example.test/pS_snap_fullset_999.zip"
    body = (_pack(tmp_path, {"pacman.png": b"\x89PNG"})).read_bytes()

    def _refuse(*args: object, **kwargs: object) -> tuple[int, int]:
        raise snaps.SnapPackTooLargeError("the snaps need 9 bytes and x has 1 free")

    monkeypatch.setattr(snaps, "_extract_pack", _refuse)
    headers = {"content-length": str(len(body))}
    with respx.mock(assert_all_called=True) as mock:
        mock.head(pack_url).mock(return_value=httpx.Response(200, headers=headers))
        mock.get(pack_url).mock(return_value=httpx.Response(200, content=body, headers=headers))
        async with httpx.AsyncClient() as client:
            report = await snaps.refresh_snaps(dest_dir=tmp_path / "d", url=pack_url, client=client)
    assert report.error is not None and "not enough disk space" in report.error
    assert report.files_extracted == 0

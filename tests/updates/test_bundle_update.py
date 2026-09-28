"""mame-curator-1010 spec §4.4, INV-9 — a bundle update writes only a verified file."""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

import httpx
import pytest

from mame_curator.updates.app import (
    ReleaseAsset,
    ReleaseInfo,
    UpdateError,
    bundle_target,
    download_bundle,
)

NAME = "MAME_Curator-1.4.0-x86_64.AppImage"
BODY = b"new bundle bytes"


def _release(sha: str | None, name: str = NAME) -> ReleaseInfo:
    return ReleaseInfo(
        version="1.4.0",
        tag="v1.4.0",
        notes_markdown="",
        html_url="https://example.test/r",
        assets=(ReleaseAsset(name=name, url="https://example.test/asset", sha256=sha),),
    )


def _client(status: int = 200) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(status, content=BODY))
    )


def _run(release: ReleaseInfo, folder: Path, status: int = 200) -> Path:
    return asyncio.run(download_bundle(release, name=NAME, folder=folder, client=_client(status)))


def test_verified_download_lands_executable(tmp_path: Path) -> None:
    dest = _run(_release(hashlib.sha256(BODY).hexdigest()), tmp_path)
    assert dest == tmp_path / NAME
    assert dest.read_bytes() == BODY
    assert dest.stat().st_mode & 0o111
    assert sorted(p.name for p in tmp_path.iterdir()) == [NAME]


@pytest.mark.parametrize(
    ("release", "status", "code"),
    [
        (_release("00" * 32), 200, "update_digest_mismatch"),
        (_release(None), 200, "update_unverifiable"),
        (_release("00" * 32, name="other.exe"), 200, "update_no_asset"),
        (_release(hashlib.sha256(BODY).hexdigest()), 404, "update_download_failed"),
    ],
)
def test_failures_leave_no_file(
    tmp_path: Path, release: ReleaseInfo, status: int, code: str
) -> None:
    with pytest.raises(UpdateError) as err:
        _run(release, tmp_path, status)
    assert err.value.code == code
    assert list(tmp_path.iterdir()) == []


def test_bundle_target_per_platform(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("APPIMAGE", str(tmp_path / "MAME_Curator-1.3.0-x86_64.AppImage"))
    assert bundle_target("1.4.0", system="Linux") == (NAME, tmp_path)
    name, _ = bundle_target("1.4.0", system="Windows")
    assert name == "MAME_Curator-1.4.0-x86_64.exe"
    name, folder = bundle_target("1.4.0", system="Darwin", machine="arm64")
    assert name == "MAME_Curator-1.4.0-arm64.dmg"
    assert folder == Path.home() / "Downloads"

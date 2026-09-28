"""mame-curator-1010 spec §4.1-§4.2 — install kind, release check, version order."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx
import pytest

import mame_curator.updates.app as app_mod
from mame_curator.updates.app import UpdateCheckError, install_kind, is_newer, latest_release


def test_install_kind(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """INV-1 — bundle when frozen (even beside a .git), git with .git, else package."""
    monkeypatch.setattr(app_mod, "bundle_root", lambda: tmp_path)
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert install_kind() == "package"
    (tmp_path / ".git").mkdir()
    assert install_kind() == "git"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert install_kind() == "bundle"


def test_is_newer() -> None:
    """INV-2 — numeric order; a pre-release is never newer."""
    assert is_newer("1.10.0", "1.9.0")
    assert is_newer("1.4.0", "1.3.0")
    assert not is_newer("1.3.0", "1.3.0")
    assert not is_newer("1.2.9", "1.3.0")
    assert not is_newer("1.4.0-rc.1", "1.3.0")
    assert not is_newer("garbage", "1.3.0")


def _client(handler: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=handler)


RELEASE = {
    "tag_name": "v1.4.0",
    "body": "## Added\n- things",
    "html_url": "https://github.com/milnet01/mame-curator/releases/tag/v1.4.0",
    "assets": [
        {
            "name": "MAME_Curator-1.4.0-x86_64.AppImage",
            "browser_download_url": "https://example.test/a",
            "digest": "sha256:" + "ab" * 32,
        },
        {"name": "no-digest.exe", "browser_download_url": "https://example.test/b"},
    ],
}


def test_latest_release_parses_the_api_answer() -> None:
    transport = httpx.MockTransport(lambda r: httpx.Response(200, content=json.dumps(RELEASE)))
    info = asyncio.run(latest_release(_client(transport)))
    assert (info.version, info.tag) == ("1.4.0", "v1.4.0")
    assert info.assets[0].sha256 == "ab" * 32
    assert info.assets[1].sha256 is None


@pytest.mark.parametrize(
    "respond",
    [
        lambda r: httpx.Response(403, content=b"rate limited"),
        lambda r: httpx.Response(200, content=b"not json"),
        lambda r: httpx.Response(200, content=b"{}"),
        lambda r: httpx.Response(200, content=b"[]"),
        lambda r: httpx.Response(
            200, content=b'{"tag_name": "v1", "html_url": "x", "assets": [1]}'
        ),
    ],
)
def test_latest_release_failures_are_typed(respond: object) -> None:
    transport = httpx.MockTransport(respond)  # type: ignore[arg-type]
    with pytest.raises(UpdateCheckError):
        asyncio.run(latest_release(_client(transport)))


def test_network_error_is_typed() -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    with pytest.raises(UpdateCheckError):
        asyncio.run(latest_release(_client(httpx.MockTransport(boom))))

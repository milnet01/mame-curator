"""Tests for ``mame_curator.downloads`` — sha256-verified atomic HTTP get.

Per long-form roadmap Phase 7 step 3 (KEEP). Used by P07 INI refresh and
P08 setup wizard. Tests use respx (project convention — see
``tests/media/test_cache.py``) and monkeypatch ``asyncio.sleep`` so the
retry-backoff path runs instantly.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from mame_curator.downloads import ManualFallback, download


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace ``asyncio.sleep`` so retry-path tests don't actually wait."""

    async def _instant(_seconds: float, *args: Any, **kwargs: Any) -> None:
        return None

    monkeypatch.setattr("mame_curator.downloads.asyncio.sleep", _instant)


@pytest.mark.asyncio
async def test_download_writes_to_dest_with_correct_bytes(tmp_path: Path) -> None:
    """Happy path: 200 OK → file appears at dest, bytes match."""
    body = b"Hello, world!"
    url = "https://example.com/file.ini"
    dest = tmp_path / "file.ini"

    with respx.mock(assert_all_called=True) as mock:
        mock.get(url).mock(return_value=httpx.Response(200, content=body))
        async with httpx.AsyncClient() as client:
            result = await download(url=url, dest=dest, client=client)

    assert result == dest
    assert dest.read_bytes() == body


@pytest.mark.asyncio
async def test_download_verifies_sha256_match(tmp_path: Path) -> None:
    """Correct sha256 is accepted; file written."""
    body = b"verified content"
    sha = hashlib.sha256(body).hexdigest()
    url = "https://example.com/x.ini"
    dest = tmp_path / "x.ini"

    with respx.mock(assert_all_called=True) as mock:
        mock.get(url).mock(return_value=httpx.Response(200, content=body))
        async with httpx.AsyncClient() as client:
            result = await download(url=url, dest=dest, client=client, sha256=sha)

    assert result == dest
    assert dest.read_bytes() == body


@pytest.mark.asyncio
async def test_download_rejects_sha256_mismatch_and_does_not_write(
    tmp_path: Path,
) -> None:
    """Wrong sha256 → ManualFallback, dest is untouched."""
    body = b"wrong content"
    expected_sha = "0" * 64
    url = "https://example.com/y.ini"
    dest = tmp_path / "y.ini"

    with respx.mock(assert_all_called=True) as mock:
        mock.get(url).mock(return_value=httpx.Response(200, content=body))
        async with httpx.AsyncClient() as client:
            result = await download(url=url, dest=dest, client=client, sha256=expected_sha)

    assert isinstance(result, ManualFallback)
    assert result.url == url
    assert "ChecksumMismatch" in result.reason
    assert not dest.exists(), "checksum-failed download must not touch dest"


@pytest.mark.asyncio
async def test_download_retries_on_http_error_then_succeeds(tmp_path: Path) -> None:
    """First call returns 503; retry succeeds."""
    body = b"eventually OK"
    url = "https://example.com/retry.ini"
    dest = tmp_path / "retry.ini"

    with respx.mock(assert_all_called=True) as mock:
        mock.get(url).mock(
            side_effect=[
                httpx.Response(503),
                httpx.Response(200, content=body),
            ]
        )
        async with httpx.AsyncClient() as client:
            result = await download(url=url, dest=dest, client=client, max_attempts=2)

    assert result == dest
    assert dest.read_bytes() == body


@pytest.mark.asyncio
async def test_download_falls_back_to_mirror(tmp_path: Path) -> None:
    """Primary URL exhausts retries → mirror URL succeeds."""
    body = b"from mirror"
    primary = "https://example.com/primary.ini"
    mirror = "https://example.org/mirror.ini"
    dest = tmp_path / "z.ini"

    with respx.mock(assert_all_called=True) as mock:
        mock.get(primary).mock(return_value=httpx.Response(503))
        mock.get(mirror).mock(return_value=httpx.Response(200, content=body))
        async with httpx.AsyncClient() as client:
            result = await download(
                url=primary,
                dest=dest,
                client=client,
                mirrors=[mirror],
                max_attempts=2,
            )

    assert result == dest
    assert dest.read_bytes() == body


@pytest.mark.asyncio
async def test_download_returns_manual_fallback_on_total_failure(
    tmp_path: Path,
) -> None:
    """All URLs + retries fail → ManualFallback with the primary URL."""
    url = "https://example.com/never.ini"
    dest = tmp_path / "never.ini"

    with respx.mock(assert_all_called=True) as mock:
        mock.get(url).mock(return_value=httpx.Response(503))
        async with httpx.AsyncClient() as client:
            result = await download(url=url, dest=dest, client=client, max_attempts=2)

    assert isinstance(result, ManualFallback)
    assert result.url == url
    assert not dest.exists()


@pytest.mark.asyncio
async def test_download_checksum_mismatch_falls_through_to_mirror(
    tmp_path: Path,
) -> None:
    """Primary serves wrong-sha content; mirror serves the right one."""
    primary = "https://example.com/wrong.ini"
    mirror = "https://example.org/right.ini"
    body = b"correct"
    sha = hashlib.sha256(body).hexdigest()
    dest = tmp_path / "ok.ini"

    with respx.mock(assert_all_called=True) as mock:
        mock.get(primary).mock(return_value=httpx.Response(200, content=b"wrong"))
        mock.get(mirror).mock(return_value=httpx.Response(200, content=body))
        async with httpx.AsyncClient() as client:
            result = await download(
                url=primary,
                dest=dest,
                client=client,
                sha256=sha,
                mirrors=[mirror],
            )

    assert result == dest
    assert dest.read_bytes() == body

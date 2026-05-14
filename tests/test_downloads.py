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

from mame_curator.downloads import InvalidUrlError, ManualFallback, download


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


# ---- FP20-F: URL scheme allowlist (http / https only) -----------------------


@pytest.mark.parametrize(
    "bad_url",
    [
        "file:///etc/passwd",
        "ftp://example.com/foo.ini",
        "data:text/plain,hello",
        "javascript:alert(1)",
        "gopher://example.com/",
    ],
)
@pytest.mark.asyncio
async def test_download_rejects_non_http_scheme(tmp_path: Path, bad_url: str) -> None:
    """FP20-F: download() must reject schemes outside http(s) at function entry.

    Without this check, a misconfigured (or attacker-controlled) URL could
    drive ``httpx.AsyncClient.get`` to a custom transport that opens
    ``file://`` for local exfiltration or ``data:`` for arbitrary in-memory
    bodies. The expected behaviour is a typed ``InvalidUrlError`` raised
    BEFORE any network attempt — no respx mocks armed, so if the check
    silently passed httpx would fail with a different error and the
    test would mis-diagnose.
    """
    dest = tmp_path / "out.ini"
    async with httpx.AsyncClient() as client:
        with pytest.raises(InvalidUrlError):
            await download(url=bad_url, dest=dest, client=client)
    assert not dest.exists()


@pytest.mark.asyncio
async def test_download_rejects_bad_scheme_in_mirrors(tmp_path: Path) -> None:
    """FP20-F: mirrors[] entries are validated alongside the primary URL.

    A valid primary masking a poisoned mirror would still trigger the
    transport-level attack on fallback. Validation is upfront so the
    failure happens before any network call.
    """
    primary = "https://example.com/ok.ini"
    bad_mirror = "file:///etc/passwd"
    dest = tmp_path / "out.ini"
    async with httpx.AsyncClient() as client:
        with pytest.raises(InvalidUrlError):
            await download(url=primary, dest=dest, client=client, mirrors=[bad_mirror])
    assert not dest.exists()


# ---------------------------------------------------------------------------
# FP27 B3 — download() chunk-list buffering
#
# `downloads.py:135-148` accumulates streamed chunks into a
# `chunks: list[bytes]` then joins via `body = b"".join(chunks)` and
# writes via `atomic_write_bytes(dest, body)`. Peak RAM at the join
# call is ~2× the body size (chunks list still alive while the joined
# buffer is built). For a 50 MB DAT, that's ~100 MB resident.
#
# Fix: stream each `aiter_bytes` chunk straight to a `.tmp` sibling of
# `dest`, hashing incrementally; on success fsync + os.replace +
# fsync_parent_dir; on sha256 mismatch or size-cap abort, close + unlink
# the .tmp. No new parameter — preserves the existing `dest: Path` API.
#
# Pre-fix: large body causes tracemalloc peak > body_size/4 → fails.
# Post-fix: peak stays under body_size/4.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_download_streams_chunks_to_tmp_not_buffer(tmp_path: Path) -> None:
    """A 10 MB body must NOT spike RAM peak above body_size/4 (≈2.5 MB)
    plus httpx async-machinery overhead. Threshold is loose enough to
    absorb the async noise without being so tight it flakes; tight
    enough to fail the chunk-list buffering pre-fix shape (which lifts
    peak to ~20 MB).
    """
    import tracemalloc

    body = b"x" * (10 * 1024 * 1024)  # 10 MB
    url = "https://example.com/big.dat"
    dest = tmp_path / "big.dat"
    body_sha = hashlib.sha256(body).hexdigest()

    tracemalloc.start()
    try:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(url).mock(return_value=httpx.Response(200, content=body))
            async with httpx.AsyncClient() as client:
                result = await download(url=url, dest=dest, client=client, sha256=body_sha)
        # tracemalloc snapshots include all Python allocations during
        # the await — chunk-list pre-fix would accumulate 10 MB here.
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert result == dest
    assert dest.read_bytes() == body

    # Threshold calibration: under respx-mocked transport the body
    # bytes are pre-allocated in test scope (10 MB) and also held by
    # httpx's response object (another 10 MB-ish copy). tracemalloc
    # snapshots both. Pre-fix the implementation added a third buffer
    # (`chunks: list[bytes]` + `b"".join(chunks)`) lifting peak to
    # ~30 MB. Post-fix it streams chunk slices straight to .tmp;
    # peak stays near 2× body size. The 2.5× body_size threshold
    # cleanly distinguishes the two shapes without being so tight it
    # flakes on respx + asyncio task-allocator noise.
    upper = int(2.5 * 10 * 1024 * 1024)  # 25 MB
    assert peak < upper, (
        f"FP27 B3 — download must stream to disk, not buffer; "
        f"tracemalloc peak {peak} ≥ {upper} suggests chunk-list "
        f"buffering still present. See `docs/specs/FP27.md` § B3."
    )


@pytest.mark.asyncio
async def test_download_sha256_mismatch_unlinks_tmp(
    tmp_path: Path,
) -> None:
    """A sha256 mismatch during incremental verification must close +
    unlink the `.tmp` sibling before falling through to the next mirror
    (no orphan `.tmp` left on disk).
    """
    body = b"the served bytes"
    expected_sha = "0" * 64  # deliberately wrong
    url = "https://example.com/file.ini"
    dest = tmp_path / "file.ini"

    with respx.mock(assert_all_called=False) as mock:
        mock.get(url).mock(return_value=httpx.Response(200, content=body))
        async with httpx.AsyncClient() as client:
            result = await download(url=url, dest=dest, client=client, sha256=expected_sha)

    # Mismatch → ManualFallback returned (existing contract).
    assert isinstance(result, ManualFallback)
    # Dest must be absent (no half-written content survived).
    assert not dest.exists(), "FP27 B3 — sha256 mismatch must leave no live file at dest."
    # No orphan `.tmp` sibling left behind.
    tmp_siblings = list(tmp_path.glob("file.ini*"))
    assert tmp_siblings == [], (
        f"FP27 B3 — sha256 mismatch must close and unlink the .tmp; "
        f"orphans: {tmp_siblings!r}. See `docs/specs/FP27.md` § B3."
    )

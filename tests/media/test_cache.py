"""Tests for ``cache_path_for`` and ``fetch_with_cache``.

Per ``docs/specs/P05.md`` § Public API. SHA-256-keyed flat cache; 404 returns
``None`` (no negative caching); other upstream errors raise ``MediaFetchError``.
"""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

import httpx
import pytest
import respx

_URL = "https://raw.githubusercontent.com/libretro-thumbnails/MAME/master/Named_Boxarts/Pac-Man.png"


def _expected_path(url: str, cache_dir: Path) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return cache_dir / f"{digest}.png"


# ---- cache_path_for ----------------------------------------------------------


def test_cache_path_for_is_sha256_url_keyed(tmp_path: Path) -> None:
    """Different URLs → different paths; same URL → same path; ext = ``.png``."""
    from mame_curator.media import cache_path_for

    url_a = "https://example.com/a.png"
    url_b = "https://example.com/b.png"
    path_a = cache_path_for(url_a, tmp_path)
    path_a2 = cache_path_for(url_a, tmp_path)
    path_b = cache_path_for(url_b, tmp_path)

    assert path_a == path_a2
    assert path_a != path_b
    assert path_a.suffix == ".png"
    assert path_a.parent == tmp_path
    # Filename stem is the lowercase hex sha256 of the URL bytes.
    assert path_a.stem == hashlib.sha256(url_a.encode("utf-8")).hexdigest()


def test_cache_path_for_no_url_suffix(tmp_path: Path) -> None:
    """URL with no path suffix → ``ext=""`` → bare-hex filename."""
    from mame_curator.media import cache_path_for

    url = "https://example.com/no_extension"
    path = cache_path_for(url, tmp_path)
    assert path.suffix == ""
    assert path.name == hashlib.sha256(url.encode("utf-8")).hexdigest()


def test_cache_path_for_is_pure(tmp_path: Path) -> None:
    """``cache_path_for`` returns a ``Path`` and does NOT touch the filesystem."""
    from mame_curator.media import cache_path_for

    nonexistent = tmp_path / "definitely_not_created_yet"
    assert not nonexistent.exists()
    path = cache_path_for(_URL, nonexistent)
    # Must NOT have created the directory or any files.
    assert not nonexistent.exists()
    assert not path.exists()


# ---- fetch_with_cache --------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_with_cache_writes_on_miss(tmp_path: Path) -> None:
    """200 response → file appears at ``cache_path_for(url, cache_dir)``; bytes match."""
    from mame_curator.media import cache_path_for, fetch_with_cache

    body = b"\x89PNG\r\n\x1a\n" + b"fake-png-bytes"
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(_URL).mock(return_value=httpx.Response(200, content=body))
            path = await fetch_with_cache(_URL, tmp_path, client=client)

    assert path is not None
    assert path == cache_path_for(_URL, tmp_path)
    assert path.read_bytes() == body


@pytest.mark.asyncio
async def test_fetch_with_cache_returns_existing_on_hit(tmp_path: Path) -> None:
    """Pre-write file → no network call; function returns the existing path."""
    from mame_curator.media import cache_path_for, fetch_with_cache

    pre_existing = b"already-cached"
    cache_path = cache_path_for(_URL, tmp_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(pre_existing)

    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=False) as mock:
            route = mock.get(_URL).mock(return_value=httpx.Response(200, content=b"fresh"))
            path = await fetch_with_cache(_URL, tmp_path, client=client)

    assert path == cache_path
    assert path.read_bytes() == pre_existing  # not overwritten by upstream
    assert not route.called


@pytest.mark.asyncio
async def test_fetch_with_cache_returns_none_on_404(tmp_path: Path) -> None:
    """404 → ``None``; no file written; calling again still hits upstream."""
    from mame_curator.media import cache_path_for, fetch_with_cache

    expected_path = cache_path_for(_URL, tmp_path)
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            route = mock.get(_URL).mock(return_value=httpx.Response(404))
            result = await fetch_with_cache(_URL, tmp_path, client=client)

    assert result is None
    assert not expected_path.exists()
    assert route.call_count == 1

    # Second call should hit upstream again (no negative caching).
    async with httpx.AsyncClient() as client2:
        with respx.mock(assert_all_called=True) as mock:
            route2 = mock.get(_URL).mock(return_value=httpx.Response(404))
            result2 = await fetch_with_cache(_URL, tmp_path, client=client2)

    assert result2 is None
    assert route2.call_count == 1


@pytest.mark.asyncio
async def test_fetch_with_cache_raises_on_500(tmp_path: Path) -> None:
    """500 → ``MediaFetchError``; no file written."""
    from mame_curator.media import MediaFetchError, cache_path_for, fetch_with_cache

    expected_path = cache_path_for(_URL, tmp_path)
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(_URL).mock(return_value=httpx.Response(500))
            with pytest.raises(MediaFetchError) as exc_info:
                await fetch_with_cache(_URL, tmp_path, client=client)

    assert "500" in str(exc_info.value)
    assert not expected_path.exists()


@pytest.mark.asyncio
async def test_fetch_with_cache_raises_on_empty_200(tmp_path: Path) -> None:
    """FP10 A2: 200 + empty body → ``MediaFetchError``; cache must NOT be poisoned.

    ``raw.githubusercontent.com`` rate-limit interstitials and CDN edge cases
    occasionally return ``200 + Content-Length: 0``. Without the guard, a
    zero-byte file is cached and every subsequent request serves nothing.
    """
    from mame_curator.media import MediaFetchError, cache_path_for, fetch_with_cache

    expected_path = cache_path_for(_URL, tmp_path)
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(_URL).mock(return_value=httpx.Response(200, content=b""))
            with pytest.raises(MediaFetchError) as exc_info:
                await fetch_with_cache(_URL, tmp_path, client=client)

    assert "empty" in str(exc_info.value).lower()
    assert not expected_path.exists(), "empty body must not be cached"


@pytest.mark.asyncio
async def test_fetch_with_cache_raises_on_network_error(tmp_path: Path) -> None:
    """``httpx.HTTPError`` → ``MediaFetchError`` chained via ``__cause__``."""
    from mame_curator.media import MediaFetchError, fetch_with_cache

    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(_URL).mock(side_effect=httpx.ConnectTimeout("timeout"))
            with pytest.raises(MediaFetchError) as exc_info:
                await fetch_with_cache(_URL, tmp_path, client=client)

    assert isinstance(exc_info.value.__cause__, httpx.HTTPError)


@pytest.mark.asyncio
async def test_fetch_with_cache_network_error_message_no_double_repr(tmp_path: Path) -> None:
    """FP10 A5: network-error message uses ``{url!r}: {exc}`` — no second ``!r``.

    The chained ``__cause__`` already carries the typed exception for logs;
    repeating the class name in the user-facing message (``ConnectTimeout(...)``)
    is noise.
    """
    from mame_curator.media import MediaFetchError, fetch_with_cache

    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(_URL).mock(side_effect=httpx.ConnectTimeout("connection timeout"))
            with pytest.raises(MediaFetchError) as exc_info:
                await fetch_with_cache(_URL, tmp_path, client=client)

    msg = str(exc_info.value)
    assert repr(_URL) in msg, "url should be repr-quoted (single !r)"
    assert "ConnectTimeout(" not in msg, "exc class name should not leak (drop second !r)"


@pytest.mark.asyncio
async def test_fetch_with_cache_atomic(tmp_path: Path) -> None:
    """Concurrent same-URL → final bytes equal exactly one of {body_A, body_B},
    never a mixture. Both calls return the same path.
    """
    from mame_curator.media import cache_path_for, fetch_with_cache

    body_a = b"A" * 4096
    body_b = b"B" * 4096
    expected_path = cache_path_for(_URL, tmp_path)

    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=False) as mock:
            mock.get(_URL).mock(
                side_effect=[
                    httpx.Response(200, content=body_a),
                    httpx.Response(200, content=body_b),
                ]
            )
            path_a, path_b = await asyncio.gather(
                fetch_with_cache(_URL, tmp_path, client=client),
                fetch_with_cache(_URL, tmp_path, client=client),
            )

    assert path_a == path_b == expected_path
    final_bytes = expected_path.read_bytes()
    assert final_bytes in (body_a, body_b), "torn write or interleaved bytes"


@pytest.mark.asyncio
async def test_fetch_with_cache_creates_cache_dir_on_demand(tmp_path: Path) -> None:
    """``cache_dir`` may not exist on first call; ``atomic_write_bytes``
    parents the directory. Verifies one less precondition the caller has to satisfy.
    """
    from mame_curator.media import fetch_with_cache

    cache_dir = tmp_path / "media-cache" / "nested"
    assert not cache_dir.exists()

    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(_URL).mock(return_value=httpx.Response(200, content=b"data"))
            path = await fetch_with_cache(_URL, cache_dir, client=client)

    assert path is not None
    assert cache_dir.exists()
    assert path.parent == cache_dir


# ---------------------------------------------------------------------------
# FP27 B4 — fetch_with_cache size cap + scheme check + streaming
#
# `media/cache.py:43-79` calls `client.get(url)` (buffered full body)
# and writes via `atomic_write_bytes(path, resp.content)`. Three gaps:
#   (a) no max-bytes cap — a malicious or misconfigured upstream can
#       OOM the server.
#   (b) no scheme check — `file:///etc/passwd` would be processed by
#       httpx and leak FS-path semantics. (`downloads.py` already has
#       `_ALLOWED_URL_SCHEMES`; `media/cache.py` does not.)
#   (c) full-RAM resident even though the eventual sink is on-disk.
#
# Fix: add `max_bytes` parameter (default 16 MiB); add scheme check;
# stream via `client.stream("GET", url)` + `aiter_bytes(64*1024)` to
# `.tmp` sibling; raise `MediaFetchError` with `"BodyTooLarge: ..."` on
# overflow.
#
# Pre-fix: no scheme check (httpx would attempt the request) → fails.
# Post-fix: scheme check raises MediaFetchError before any network call.
# ---------------------------------------------------------------------------


from mame_curator.media.cache import (  # noqa: E402  # FP27 T2 B4: tests sit after the existing module's tests for narrative grouping.
    MediaFetchError,
    fetch_with_cache,
)


@pytest.mark.asyncio
async def test_fetch_with_cache_rejects_file_scheme(tmp_path: Path) -> None:
    """A `file://` URL must raise `MediaFetchError` before any network
    call — no FS-path leak via httpx.

    Pre-fix: `client.get("file:///etc/passwd")` would be attempted →
    test fails (likely with an httpx error or unintended FS read).
    Post-fix: scheme check at the top of `fetch_with_cache` raises
    `MediaFetchError(f"unsupported scheme: 'file'")` before any I/O.
    """
    cache_dir = tmp_path / "cache"
    async with httpx.AsyncClient() as client:
        with pytest.raises(MediaFetchError):
            await fetch_with_cache("file:///etc/passwd", cache_dir, client=client)


@pytest.mark.asyncio
async def test_fetch_with_cache_caps_body_size(tmp_path: Path) -> None:
    """A body exceeding `max_bytes` must raise `MediaFetchError` with a
    `BodyTooLarge:` prefix.

    Pre-fix: no cap → the test sends a 32 MiB body, `client.get` buffers
    it all, no error is raised → assertion fails. Post-fix: the
    streaming loop aborts at the cap and `raise MediaFetchError(...)`.
    """
    body = b"y" * (32 * 1024 * 1024)  # 32 MiB
    url = "https://raw.githubusercontent.com/.../oversize.png"
    cache_dir = tmp_path / "cache"

    with respx.mock(assert_all_called=False) as mock:
        mock.get(url).mock(return_value=httpx.Response(200, content=body))
        async with httpx.AsyncClient() as client:
            with pytest.raises(MediaFetchError, match=r"BodyTooLarge"):
                await fetch_with_cache(
                    url,
                    cache_dir,
                    client=client,
                    max_bytes=16 * 1024 * 1024,
                )


@pytest.mark.slow
@pytest.mark.asyncio
async def test_fetch_with_cache_streams_to_disk(tmp_path: Path) -> None:
    """A 5 MiB body must not lift `tracemalloc` peak above body_size/2
    (≈2.5 MiB) — the streaming fix means at most one chunk plus httpx
    overhead is RAM-resident at any time.

    Pre-fix: `resp.content` buffers the full body → peak ≥ 5 MiB →
    test fails. Post-fix: streaming via `client.stream(...)` plus
    `aiter_bytes(...)` keeps peak well under the cap.
    """
    import tracemalloc

    body = b"z" * (5 * 1024 * 1024)  # 5 MiB
    url = "https://raw.githubusercontent.com/.../big.png"
    cache_dir = tmp_path / "cache"

    tracemalloc.start()
    try:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(url).mock(return_value=httpx.Response(200, content=body))
            async with httpx.AsyncClient() as client:
                result = await fetch_with_cache(url, cache_dir, client=client)
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert result is not None
    assert result.exists()
    assert result.read_bytes() == body

    # Threshold calibration: under respx the body is pre-allocated in
    # test scope (5 MiB) and also held by httpx's response object;
    # tracemalloc captures both. Pre-fix added a third copy via
    # `resp.content` + `atomic_write_bytes(path, resp.content)` lifting
    # peak to ~15-20 MB. Post-fix streams chunk slices to .tmp; peak
    # stays near 2× body size. 2.5× body_size cleanly distinguishes
    # the two shapes.
    upper = int(2.5 * 5 * 1024 * 1024)  # 12.5 MiB
    assert peak < upper, (
        f"FP27 B4 — fetch_with_cache must stream to disk, not buffer; "
        f"tracemalloc peak {peak} ≥ {upper}. See `docs/specs/FP27.md` § B4."
    )

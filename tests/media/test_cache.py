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

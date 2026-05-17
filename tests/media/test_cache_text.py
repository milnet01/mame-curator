"""Tests for ``fetch_text_with_cache`` and ``DEFAULT_TEXT_MAX_BYTES``.

Per ``docs/specs/P10.md`` § Public API — parallel to P05's
``fetch_with_cache`` but for text / JSON bodies, returning ``str``.
Same SHA-256-keyed cache; same atomic-write protocol; same 404
sentinel; UTF-8 decode failure raises ``MediaFetchError``.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import httpx
import pytest
import respx

_URL = "https://example.com/api/lookup.json"


def _expected_path(url: str, cache_dir: Path) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    ext = Path(url).suffix
    return cache_dir / f"{digest}{ext}"


def test_default_text_max_bytes_is_public_constant() -> None:
    """``DEFAULT_TEXT_MAX_BYTES`` is re-exported from media.__init__."""
    from mame_curator.media import DEFAULT_TEXT_MAX_BYTES

    assert DEFAULT_TEXT_MAX_BYTES == 256 * 1024


@pytest.mark.asyncio
async def test_fetch_text_with_cache_writes_on_miss(tmp_path: Path) -> None:
    """Mocked 200 → file appears at ``cache_path_for(url, cache_dir)``;
    returned string equals upstream body."""
    from mame_curator.media import fetch_text_with_cache

    body = '{"hello": "world"}'
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(_URL).mock(return_value=httpx.Response(200, text=body))
            result = await fetch_text_with_cache(_URL, tmp_path, client=client)

    assert result == body
    assert _expected_path(_URL, tmp_path).read_text(encoding="utf-8") == body


@pytest.mark.asyncio
async def test_fetch_text_with_cache_returns_existing_on_hit(tmp_path: Path) -> None:
    """Pre-write file → no network call; function returns cached body."""
    from mame_curator.media import fetch_text_with_cache

    cached = '{"cached": true}'
    _expected_path(_URL, tmp_path).write_text(cached, encoding="utf-8")

    unused = httpx.Response(200, text="should-not-be-served")
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=False) as mock:
            route = mock.get(_URL).mock(return_value=unused)
            result = await fetch_text_with_cache(_URL, tmp_path, client=client)
            assert not route.called, "Cache hit must not touch upstream"

    assert result == cached


@pytest.mark.asyncio
async def test_fetch_text_with_cache_returns_none_on_404(tmp_path: Path) -> None:
    """Mocked 404 → returns None; no file written; negative result not cached."""
    from mame_curator.media import fetch_text_with_cache

    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(_URL).mock(return_value=httpx.Response(404))
            result = await fetch_text_with_cache(_URL, tmp_path, client=client)

    assert result is None
    assert not _expected_path(_URL, tmp_path).exists()


@pytest.mark.asyncio
async def test_fetch_text_with_cache_raises_on_500(tmp_path: Path) -> None:
    """Mocked 500 → MediaFetchError; no file written."""
    from mame_curator.media import MediaFetchError, fetch_text_with_cache

    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(_URL).mock(return_value=httpx.Response(500))
            with pytest.raises(MediaFetchError) as exc_info:
                await fetch_text_with_cache(_URL, tmp_path, client=client)

    assert "500" in str(exc_info.value)
    assert not _expected_path(_URL, tmp_path).exists()


@pytest.mark.asyncio
async def test_fetch_text_with_cache_raises_on_empty_200(tmp_path: Path) -> None:
    """Mocked 200 + empty body → MediaFetchError; no cache slot."""
    from mame_curator.media import MediaFetchError, fetch_text_with_cache

    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(_URL).mock(return_value=httpx.Response(200, content=b""))
            with pytest.raises(MediaFetchError, match="empty body"):
                await fetch_text_with_cache(_URL, tmp_path, client=client)

    assert not _expected_path(_URL, tmp_path).exists()


@pytest.mark.asyncio
async def test_fetch_text_with_cache_raises_on_oversize(tmp_path: Path) -> None:
    """Body larger than max_bytes → MediaFetchError, no .tmp left behind."""
    from mame_curator.media import MediaFetchError, fetch_text_with_cache

    huge = "x" * 1024
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(_URL).mock(return_value=httpx.Response(200, text=huge))
            with pytest.raises(MediaFetchError, match="BodyTooLarge"):
                await fetch_text_with_cache(_URL, tmp_path, client=client, max_bytes=512)

    # No final cache file
    assert not _expected_path(_URL, tmp_path).exists()
    # No .tmp leftover
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.asyncio
async def test_fetch_text_with_cache_raises_on_bad_utf8(tmp_path: Path) -> None:
    """200 with non-UTF-8 bytes → MediaFetchError; no cache slot."""
    from mame_curator.media import MediaFetchError, fetch_text_with_cache

    invalid = b"\xff\xfe\x00bad"
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(_URL).mock(return_value=httpx.Response(200, content=invalid))
            with pytest.raises(MediaFetchError, match="decode"):
                await fetch_text_with_cache(_URL, tmp_path, client=client)

    assert not _expected_path(_URL, tmp_path).exists()


@pytest.mark.asyncio
async def test_fetch_text_with_cache_raises_on_network_error(tmp_path: Path) -> None:
    """httpx network error → MediaFetchError chained via __cause__."""
    from mame_curator.media import MediaFetchError, fetch_text_with_cache

    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(_URL).mock(side_effect=httpx.ConnectError("boom"))
            with pytest.raises(MediaFetchError) as exc_info:
                await fetch_text_with_cache(_URL, tmp_path, client=client)

    assert exc_info.value.__cause__ is not None
    assert isinstance(exc_info.value.__cause__, httpx.HTTPError)

"""mame-curator-1235: the picture cache, made reliable (2026-11-11 review).

Each test names the finding it locks.
"""

from __future__ import annotations

import errno
import json
from pathlib import Path

import httpx
import pytest
import respx

from mame_curator.media import TokenBucket, cache_path_for
from mame_curator.parser.models import Machine

_PIC = "https://example.com/pictures/pacman.png"
_TEXT = "https://example.com/api/pacman.json"


def _spent_bucket() -> TokenBucket:
    """A bucket with nothing left in it, and no refill within a test."""
    bucket = TokenBucket(rate=1e-9, capacity=1)
    assert bucket.acquire()
    return bucket


def _pacman() -> Machine:
    return Machine(name="pacman", description="Pac-Man", runnable=True)


# ---- CR-03-4, CR-03-5: the picture writer -----------------------------------


@pytest.mark.asyncio
async def test_picture_write_leaves_another_writers_tmp_alone(tmp_path: Path) -> None:
    """CR-03-4: a fixed `.tmp` name lets two fetches of one URL tear each other."""
    from mame_curator.media import fetch_with_cache

    slot = cache_path_for(_PIC, tmp_path)
    other = slot.with_suffix(slot.suffix + ".tmp")
    other.write_bytes(b"another fetch, half written")
    async with httpx.AsyncClient() as client:
        with respx.mock() as mock:
            mock.get(_PIC).mock(
                return_value=httpx.Response(
                    200, content=b"\x89PNG data", headers={"content-type": "image/png"}
                )
            )
            path = await fetch_with_cache(_PIC, tmp_path, client=client)

    assert path is not None and path.read_bytes() == b"\x89PNG data"
    assert other.read_bytes() == b"another fetch, half written"


@pytest.mark.asyncio
async def test_a_full_disk_is_a_media_error_and_leaves_no_tmp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CR-03-5: an OSError escaped untyped and left the `.tmp` behind."""
    from mame_curator.media import MediaFetchError, fetch_with_cache

    def disk_full(_fd: int) -> None:
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr("mame_curator.media.cache.os.fsync", disk_full)
    async with httpx.AsyncClient() as client:
        with respx.mock() as mock:
            mock.get(_PIC).mock(
                return_value=httpx.Response(
                    200, content=b"\x89PNG data", headers={"content-type": "image/png"}
                )
            )
            with pytest.raises(MediaFetchError):
                await fetch_with_cache(_PIC, tmp_path, client=client)

    assert list(tmp_path.glob("*.tmp")) == []
    assert not cache_path_for(_PIC, tmp_path).exists()


# ---- CR-03-10: a text-cache hit that cannot be read --------------------------


@pytest.mark.asyncio
async def test_an_undecodable_text_slot_is_a_media_error_and_is_dropped(tmp_path: Path) -> None:
    """CR-03-10: a bad slot escaped untyped, so /wiki answered 500."""
    from mame_curator.media import MediaFetchError, fetch_text_with_cache

    slot = cache_path_for(_TEXT, tmp_path)
    slot.write_bytes(b"\xff\xfe not utf-8")
    async with httpx.AsyncClient() as client:
        with pytest.raises(MediaFetchError):
            await fetch_text_with_cache(_TEXT, tmp_path, client=client)

    assert not slot.exists()


# ---- CR-03-6: a lookup answered from disk spends no token --------------------


@pytest.mark.asyncio
async def test_arcadedb_cached_lookup_spends_no_token(tmp_path: Path) -> None:
    """CR-03-6: cached art stopped showing once the bucket ran dry."""
    from mame_curator.media.sources import ArcadeDBSource

    source = ArcadeDBSource(limiter=_spent_bucket(), cache_dir=tmp_path)
    url = source._scraper_url(_pacman())
    cache_path_for(url, tmp_path).write_text('{"release":0,"result":[]}', encoding="utf-8")
    async with httpx.AsyncClient() as client:
        await source.prepare(_pacman(), client=client)  # no MediaRateLimited


def _cache_game_page(cache_dir: Path) -> None:
    from mame_curator.media.wikipedia_titles import _WIKIPEDIA_REST_SUMMARY_BASE, candidate_titles

    title = candidate_titles(_pacman())[0]
    from urllib.parse import quote

    page = {
        "type": "standard",
        "title": title,
        "description": "1980 video game",
        "extract": "Pac-Man is a maze game.",
        "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Pac-Man"}},
        "thumbnail": {"source": "https://upload.wikimedia.org/pacman.png"},
    }
    url = f"{_WIKIPEDIA_REST_SUMMARY_BASE}/{quote(title)}"
    cache_path_for(url, cache_dir).write_text(json.dumps(page), encoding="utf-8")


@pytest.mark.asyncio
async def test_wikipedia_image_cached_lookup_spends_no_token(tmp_path: Path) -> None:
    """CR-03-6: the same holds for the Wikipedia picture."""
    from mame_curator.media.wikipedia_image import WikipediaImageSource

    _cache_game_page(tmp_path)
    source = WikipediaImageSource(limiter=_spent_bucket(), cache_dir=tmp_path)
    async with httpx.AsyncClient() as client:
        await source.prepare(_pacman(), client=client)  # no MediaRateLimited


@pytest.mark.asyncio
async def test_wikipedia_extract_cached_lookup_spends_no_token(tmp_path: Path) -> None:
    """CR-03-6: and for the About paragraph, which shares the Wikipedia budget."""
    from mame_curator.media.wikipedia import resolve_wikipedia_extract

    _cache_game_page(tmp_path)
    async with httpx.AsyncClient() as client:
        extract = await resolve_wikipedia_extract(
            _pacman(), cache_dir=tmp_path, client=client, limiter=_spent_bucket()
        )
    assert extract is not None


@pytest.mark.asyncio
async def test_a_lookup_that_needs_the_network_still_spends_its_token(tmp_path: Path) -> None:
    """CR-03-6: the budget still holds for real requests."""
    from mame_curator.media import MediaRateLimited
    from mame_curator.media.sources import ArcadeDBSource

    source = ArcadeDBSource(limiter=_spent_bucket(), cache_dir=tmp_path)
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=False), pytest.raises(MediaRateLimited):
            await source.prepare(_pacman(), client=client)

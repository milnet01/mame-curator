"""mame-curator-1079 — MobyGames cover lookup and JSON-body caching.

Built from the published API shape, as Skyscraper's working parser
(src/mobygames.cpp) uses it, because no key is available here: a title
search returns ``games[]`` with ``game_id`` and ``platforms[]``
(``platform_id``, ``platform_name``); ``/v1/games/{id}/platforms/{pid}/covers``
returns ``cover_groups[].covers[]`` with ``scan_of`` and ``image``. Unverified
against the live service. The responses below are constructed in that shape.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from mame_curator.media import MediaFetchError, MobyGamesSource, SourceDisabledFlag
from tests.media.conftest import _machine, _make_unbounded_limiter

KEY = "secret-key-123"
SEARCH = {
    "games": [
        {
            "game_id": 1,
            "title": "Pac-Man",
            "platforms": [{"platform_id": 50, "platform_name": "Atari 2600"}],
        },
        {
            "game_id": 2,
            "title": "Pac-Man",
            "platforms": [{"platform_id": 143, "platform_name": "Arcade"}],
        },
    ]
}
COVERS = {
    "cover_groups": [
        {
            "countries": ["United States"],
            "covers": [
                {"scan_of": "Back Cover", "image": "https://cdn.mobygames.com/back.jpg"},
                {"scan_of": "Front Cover", "image": "https://cdn.mobygames.com/front.jpg"},
            ],
        }
    ]
}


def _source(cache_dir: Path, monkeypatch: pytest.MonkeyPatch) -> MobyGamesSource:
    monkeypatch.setenv("MOBYGAMES_API_KEY", KEY)
    return MobyGamesSource(
        limiter=_make_unbounded_limiter(),
        cache_dir=cache_dir,
        disabled_flag=SourceDisabledFlag(),
        secrets_dir=cache_dir / "none",
    )


async def _prepare(src: MobyGamesSource, search: object, covers: object) -> int:
    """Run ``prepare`` against mocked endpoints; return how many requests it made.

    Counted inside the block: respx clears its recorded calls on exit."""
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=False) as mock:
            mock.get(host="api.mobygames.com", path="/v1/games").mock(
                return_value=httpx.Response(200, json=search)
            )
            mock.get(host="api.mobygames.com", path="/v1/games/2/platforms/143/covers").mock(
                return_value=httpx.Response(200, json=covers)
            )
            try:
                await src.prepare(_machine(), client=client)
            finally:
                calls: int = mock.calls.call_count
    return calls


@pytest.mark.asyncio
async def test_front_cover_of_the_arcade_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = _source(tmp_path, monkeypatch)
    await _prepare(src, SEARCH, COVERS)
    assert src.url_for(_machine(), "boxart") == "https://cdn.mobygames.com/front.jpg"


@pytest.mark.asyncio
async def test_no_arcade_version_means_no_cover(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = _source(tmp_path, monkeypatch)
    search = {"games": [SEARCH["games"][0]]}
    calls = await _prepare(src, search, COVERS)
    assert src.url_for(_machine(), "boxart") is None
    assert calls == 1  # the covers endpoint was never asked


@pytest.mark.asyncio
async def test_second_lookup_is_served_from_disk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _prepare(_source(tmp_path, monkeypatch), SEARCH, COVERS)
    again = _source(tmp_path, monkeypatch)
    calls = await _prepare(again, SEARCH, COVERS)
    assert calls == 0
    assert again.url_for(_machine(), "boxart") == "https://cdn.mobygames.com/front.jpg"


@pytest.mark.asyncio
async def test_malformed_body_is_not_cached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = _source(tmp_path, monkeypatch)
    with pytest.raises(MediaFetchError):
        await _prepare(src, ["not", "an", "object"], COVERS)
    calls = await _prepare(_source(tmp_path, monkeypatch), SEARCH, COVERS)
    assert calls == 2  # nothing poisoned was served from disk


@pytest.mark.asyncio
async def test_cache_never_holds_the_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    await _prepare(_source(tmp_path, monkeypatch), SEARCH, COVERS)
    cached = [p for p in tmp_path.rglob("*") if p.is_file()]
    assert cached, "nothing was cached"
    for path in cached:
        assert KEY not in path.name
        assert KEY not in path.read_text(encoding="utf-8")

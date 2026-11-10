"""mame-curator-1146 — ``media/candidates.py``: the picture guide's listing.

Per ``docs/specs/mame-curator-1146-picture-choice.md`` §4.3 and INV-6, INV-7,
INV-8 and INV-13. Fake sources count ``prepare`` calls; ``fetch_with_cache``
is replaced with a URL → file map, so nothing reaches the network.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import httpx
import pytest

from mame_curator.media import Kind, MediaSource, MediaSourceRegistry
from mame_curator.media import resolve as resolve_mod
from mame_curator.media.cache import MediaFetchError
from mame_curator.media.candidates import (
    LIMITED_SOURCES,
    CandidateList,
    list_candidates,
    resolve_image_found,
    resolve_pair,
)
from mame_curator.media.rate_limit import MediaRateLimited
from mame_curator.parser.models import Machine
from tests.media.conftest import _machine

_ALL: frozenset[Kind] = frozenset({"boxart", "title", "snap"})


class _Fake:
    """A source answering ``http://<name>.test/<kind>`` for the kinds it has."""

    def __init__(
        self,
        name: str,
        *,
        kinds: frozenset[Kind] = _ALL,
        has: frozenset[Kind] | None = None,
        prepare_exc: Exception | None = None,
        url: str | None = None,
    ) -> None:
        self.name = name
        self.license_compatible = True
        self.kinds = kinds
        self.disabled_reason: str | None = None
        self._has = kinds if has is None else has
        self._prepare_exc = prepare_exc
        self._url = url
        self.prepare_calls = 0

    async def prepare(self, machine: Machine, *, client: httpx.AsyncClient) -> None:
        self.prepare_calls += 1
        if self._prepare_exc is not None:
            raise self._prepare_exc

    def url_for(self, machine: Machine, kind: Kind) -> str | None:
        if self._url is not None:
            return self._url
        return f"http://{self.name}.test/{kind}" if kind in self._has else None


def _registry(*sources: _Fake) -> MediaSourceRegistry:
    available = cast("dict[str, MediaSource]", {s.name: s for s in sources})
    return MediaSourceRegistry(tuple(s.name for s in sources), available)


def _serve(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, files: dict[str, bytes]) -> None:
    """Every URL in ``files`` answers with its bytes; any other URL is a 404."""
    paths: dict[str, Path] = {}
    for i, (url, data) in enumerate(files.items()):
        p = tmp_path / f"img{i}.png"
        p.write_bytes(data)
        paths[url] = p

    async def _fake(url: str, cache_dir: Path, *, client: httpx.AsyncClient) -> Path | None:
        return paths.get(url)

    monkeypatch.setattr(resolve_mod, "fetch_with_cache", _fake)


async def _list(
    registry: MediaSourceRegistry, tmp_path: Path, *, ask_limited: bool
) -> CandidateList:
    async with httpx.AsyncClient() as client:
        return await list_candidates(
            _machine(),
            registry=registry,
            ask_limited=ask_limited,
            cache_dir=tmp_path,
            client=client,
        )


def test_limited_sources_are_the_three_with_rate_limits() -> None:
    assert frozenset({"arcadeDB", "wikipediaImage", "mobyGames"}) == LIMITED_SOURCES


@pytest.mark.asyncio
async def test_default_listing_asks_no_limited_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """INV-6: a free source holding boxart; the limited counts stay 0."""
    free = _Fake("libretro")
    arcade = _Fake("arcadeDB")
    wiki = _Fake("wikipediaImage", kinds=frozenset({"boxart"}))
    _serve(monkeypatch, tmp_path, {"http://libretro.test/boxart": b"A"})
    result = await _list(_registry(free, arcade, wiki), tmp_path, ask_limited=False)
    assert arcade.prepare_calls == 0
    assert wiki.prepare_calls == 0
    assert [(f.source, f.kind) for f in result.found] == [("libretro", "boxart")]
    assert result.not_asked == ("arcadeDB", "wikipediaImage")
    assert result.not_answered == ()


@pytest.mark.asyncio
async def test_further_asks_each_limited_source_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """INV-6: ask_limited=True asks every limited source; one prepare per source."""
    arcade = _Fake("arcadeDB")
    wiki = _Fake("wikipediaImage", kinds=frozenset({"boxart"}))
    free = _Fake("libretro")
    _serve(
        monkeypatch,
        tmp_path,
        {
            "http://arcadeDB.test/boxart": b"1",
            "http://arcadeDB.test/title": b"2",
            "http://arcadeDB.test/snap": b"3",
            "http://wikipediaImage.test/boxart": b"4",
        },
    )
    result = await _list(_registry(arcade, wiki, free), tmp_path, ask_limited=True)
    assert arcade.prepare_calls == 1
    assert wiki.prepare_calls == 1
    assert free.prepare_calls == 1
    assert [(f.source, f.kind) for f in result.found] == [
        ("arcadeDB", "boxart"),
        ("wikipediaImage", "boxart"),
        ("arcadeDB", "title"),
        ("arcadeDB", "snap"),
    ]
    assert result.not_asked == ()


@pytest.mark.asyncio
async def test_equal_bytes_listed_once_earliest_kept(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """INV-7: two sources serving the same bytes give one candidate."""
    first = _Fake("first", kinds=frozenset({"boxart"}))
    second = _Fake("second", kinds=frozenset({"boxart"}))
    _serve(
        monkeypatch,
        tmp_path,
        {"http://first.test/boxart": b"same", "http://second.test/boxart": b"same"},
    )
    result = await _list(_registry(first, second), tmp_path, ask_limited=False)
    assert [(f.source, f.kind) for f in result.found] == [("first", "boxart")]


@pytest.mark.asyncio
async def test_a_source_that_raises_is_named_and_the_listing_goes_on(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """INV-8: one rate-limited, one failing, one answering → both named, answer listed.

    The failing source is not asked again for a later kind.
    """
    limited = _Fake("limited", prepare_exc=MediaRateLimited("empty"))
    broken = _Fake("broken", prepare_exc=MediaFetchError("down"))
    good = _Fake("good", kinds=frozenset({"snap"}))
    _serve(monkeypatch, tmp_path, {"http://good.test/snap": b"S"})
    result = await _list(_registry(limited, broken, good), tmp_path, ask_limited=False)
    assert result.not_answered == ("limited", "broken")
    assert [(f.source, f.kind) for f in result.found] == [("good", "snap")]
    assert limited.prepare_calls == 1
    assert broken.prepare_calls == 1


@pytest.mark.asyncio
async def test_a_fetch_error_is_named_in_not_answered(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """INV-8: a fetch that fails after prepare also names its source."""
    src = _Fake("flaky", kinds=frozenset({"boxart"}))

    async def _boom(url: str, cache_dir: Path, *, client: httpx.AsyncClient) -> Path | None:
        raise MediaFetchError("502")

    monkeypatch.setattr(resolve_mod, "fetch_with_cache", _boom)
    result = await _list(_registry(src), tmp_path, ask_limited=False)
    assert result.not_answered == ("flaky",)
    assert result.found == ()


@pytest.mark.asyncio
async def test_resolve_pair_refuses_file_url_from_a_network_source(tmp_path: Path) -> None:
    """INV-13: a network source answering file:///etc/passwd gives None."""
    hostile = _Fake("libretro", url="file:///etc/passwd")
    async with httpx.AsyncClient() as client:
        got = await resolve_pair(
            _machine(),
            "libretro",
            "boxart",
            registry=_registry(hostile),
            cache_dir=tmp_path,
            client=client,
        )
    assert got is None


@pytest.mark.asyncio
async def test_resolve_pair_serves_a_local_source_file(tmp_path: Path) -> None:
    """A local source may answer file://; a source outside the chain is None."""
    img = tmp_path / "pacman.png"
    img.write_bytes(b"local")
    local = _Fake("esde", url=img.as_uri())
    registry = _registry(local)
    async with httpx.AsyncClient() as client:
        got = await resolve_pair(
            _machine(), "esde", "title", registry=registry, cache_dir=tmp_path, client=client
        )
        missing = await resolve_pair(
            _machine(), "nosuch", "title", registry=registry, cache_dir=tmp_path, client=client
        )
    assert got == img
    assert missing is None


@pytest.mark.asyncio
async def test_resolve_pair_raises_for_the_caller(tmp_path: Path) -> None:
    """resolve_pair raises MediaRateLimited; callers decide."""
    src = _Fake("arcadeDB", prepare_exc=MediaRateLimited("empty"))
    async with httpx.AsyncClient() as client:
        with pytest.raises(MediaRateLimited):
            await resolve_pair(
                _machine(),
                "arcadeDB",
                "boxart",
                registry=_registry(src),
                cache_dir=tmp_path,
                client=client,
            )


@pytest.mark.asyncio
async def test_resolve_image_found_names_the_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """resolve_image_found reports which source answered, after one that missed."""
    miss = _Fake("miss", has=frozenset())
    hit = _Fake("hit")
    _serve(monkeypatch, tmp_path, {"http://hit.test/boxart": b"H"})
    async with httpx.AsyncClient() as client:
        found = await resolve_image_found(
            _machine(), "boxart", registry=_registry(miss, hit), cache_dir=tmp_path, client=client
        )
    assert found is not None
    assert (found.source, found.kind) == ("hit", "boxart")
    assert found.path.read_bytes() == b"H"

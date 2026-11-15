"""mame-curator-1143 — a game with no picture is remembered for seven days.

Contract: ``src/mame_curator/media/spec.md`` § Remembered misses. Fake
sources count ``prepare`` calls; ``fetch_with_cache`` is replaced with a URL
→ file map, so nothing reaches the network.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import cast

import httpx
import pytest

from mame_curator.media import Kind, MediaSource, MediaSourceRegistry
from mame_curator.media import resolve as resolve_mod
from mame_curator.media.cache import MediaFetchError
from mame_curator.media.misses import (
    MISS_DAYS,
    forget_misses,
    miss_marker,
    resolve_image_remembered,
)
from mame_curator.media.rate_limit import MediaRateLimited
from tests.media.conftest import _machine

_ALL: frozenset[Kind] = frozenset({"boxart", "title", "snap"})


class _Fake:
    """A source answering ``http://<name>.test/<kind>`` for the kinds it has."""

    def __init__(
        self,
        name: str,
        *,
        has: frozenset[Kind] = frozenset(),
        prepare_exc: Exception | None = None,
    ) -> None:
        self.name = name
        self.license_compatible = True
        self.kinds = _ALL
        self.disabled_reason: str | None = None
        self.has = has
        self.prepare_exc = prepare_exc
        self.prepare_calls = 0

    async def prepare(self, machine: object, *, client: httpx.AsyncClient) -> None:
        self.prepare_calls += 1
        if self.prepare_exc is not None:
            raise self.prepare_exc

    def url_for(self, machine: object, kind: Kind) -> str | None:
        return f"http://{self.name}.test/{kind}" if kind in self.has else None


@pytest.fixture(autouse=True)
def _fetch_from_disk(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    served = tmp_path / "served"
    served.mkdir()

    async def _fetch(url: str, cache_dir: Path, *, client: httpx.AsyncClient) -> Path:
        path = served / (url.removeprefix("http://").replace("/", "-") + ".png")
        path.write_bytes(url.encode())
        return path

    monkeypatch.setattr(resolve_mod, "fetch_with_cache", _fetch)


def _registry(*fakes: _Fake) -> MediaSourceRegistry:
    available = cast("dict[str, MediaSource]", {f.name: f for f in fakes})
    return MediaSourceRegistry(tuple(available), available)


async def _resolve(
    registry: MediaSourceRegistry, cache_dir: Path, *, settings: str = "s1", kind: Kind = "boxart"
) -> Path | None:
    async with httpx.AsyncClient() as client:
        return await resolve_image_remembered(
            _machine(),
            kind,
            registry=registry,
            cache_dir=cache_dir,
            client=client,
            settings=settings,
        )


def _age(marker: Path, days: float) -> None:
    then = time.time() - days * 86400
    os.utime(marker, (then, then))


async def test_a_clean_miss_is_remembered_and_not_asked_again(tmp_path: Path) -> None:
    """The second view asks no source: the miss is remembered."""
    libretro = _Fake("libretro")
    registry = _registry(libretro)
    assert await _resolve(registry, tmp_path) is None
    assert await _resolve(registry, tmp_path) is None
    assert libretro.prepare_calls == 1
    assert miss_marker(tmp_path, "pacman", "boxart").is_file()


async def test_a_remembered_miss_is_asked_again_after_seven_days(tmp_path: Path) -> None:
    libretro = _Fake("libretro")
    registry = _registry(libretro)
    await _resolve(registry, tmp_path)
    _age(miss_marker(tmp_path, "pacman", "boxart"), MISS_DAYS + 0.01)
    await _resolve(registry, tmp_path)
    assert libretro.prepare_calls == 2


async def test_a_miss_younger_than_seven_days_still_holds(tmp_path: Path) -> None:
    libretro = _Fake("libretro")
    registry = _registry(libretro)
    await _resolve(registry, tmp_path)
    _age(miss_marker(tmp_path, "pacman", "boxart"), MISS_DAYS - 0.01)
    await _resolve(registry, tmp_path)
    assert libretro.prepare_calls == 1


@pytest.mark.parametrize(
    "exc", [MediaRateLimited("busy"), MediaFetchError("down")], ids=["rate-limited", "failed"]
)
async def test_a_miss_with_a_source_that_did_not_answer_is_not_remembered(
    tmp_path: Path, exc: Exception
) -> None:
    """A busy or failing source may hold a picture, so the miss is not final."""
    registry = _registry(_Fake("libretro"), _Fake("arcadeDB", prepare_exc=exc))
    assert await _resolve(registry, tmp_path) is None
    assert not miss_marker(tmp_path, "pacman", "boxart").exists()


async def test_changed_picture_settings_ask_again(tmp_path: Path) -> None:
    """A new folder or source may hold the picture the old ones did not."""
    libretro = _Fake("libretro")
    registry = _registry(libretro)
    await _resolve(registry, tmp_path, settings="s1")
    await _resolve(registry, tmp_path, settings="s2")
    assert libretro.prepare_calls == 2


async def test_a_new_source_in_the_chain_asks_again(tmp_path: Path) -> None:
    libretro = _Fake("libretro")
    await _resolve(_registry(libretro), tmp_path)
    esde = _Fake("esde", has=frozenset({"boxart"}))
    path = await _resolve(_registry(esde, libretro), tmp_path)
    assert path is not None
    assert esde.prepare_calls == 1


async def test_a_found_picture_writes_no_miss(tmp_path: Path) -> None:
    registry = _registry(_Fake("libretro", has=frozenset({"boxart"})))
    assert await _resolve(registry, tmp_path) is not None
    assert not miss_marker(tmp_path, "pacman", "boxart").exists()


async def test_each_kind_is_remembered_on_its_own(tmp_path: Path) -> None:
    libretro = _Fake("libretro", has=frozenset({"snap"}))
    registry = _registry(libretro)
    assert await _resolve(registry, tmp_path, kind="boxart") is None
    assert await _resolve(registry, tmp_path, kind="snap") is not None


async def test_forget_misses_asks_again_at_once(tmp_path: Path) -> None:
    """The "Look for a picture again" button's backend half."""
    libretro = _Fake("libretro")
    registry = _registry(libretro)
    await _resolve(registry, tmp_path, kind="boxart")
    await _resolve(registry, tmp_path, kind="snap")
    forget_misses(tmp_path, "pacman")
    assert not miss_marker(tmp_path, "pacman", "boxart").exists()
    assert not miss_marker(tmp_path, "pacman", "snap").exists()
    await _resolve(registry, tmp_path)
    assert libretro.prepare_calls == 3


def test_forget_misses_with_none_stored_does_nothing(tmp_path: Path) -> None:
    forget_misses(tmp_path, "pacman")
    assert not (tmp_path / "misses").exists()


async def test_an_unwritable_miss_folder_still_answers(tmp_path: Path) -> None:
    """A miss that cannot be saved is asked again, never an error."""
    (tmp_path / "misses").write_text("a file where the folder would go")
    libretro = _Fake("libretro")
    registry = _registry(libretro)
    assert await _resolve(registry, tmp_path) is None
    assert await _resolve(registry, tmp_path) is None
    assert libretro.prepare_calls == 2


def test_the_marker_name_does_not_carry_the_game_name(tmp_path: Path) -> None:
    """A name with a path separator cannot leave the misses folder."""
    marker = miss_marker(tmp_path, "../../etc/x", "boxart")
    assert marker.parent == tmp_path / "misses" / "boxart"

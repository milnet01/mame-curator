"""mame-curator-1143 — the picture proxy remembers a miss; the retry route forgets it.

Contract: ``src/mame_curator/api/spec.md`` § Media proxy and
``src/mame_curator/media/spec.md`` § Remembered misses. The registry is
replaced with fake sources; ``fetch_with_cache`` reads files from a URL map,
so nothing reaches the network.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import httpx
import pytest

from mame_curator.api.state import replace_world
from mame_curator.media import Kind, MediaSource, MediaSourceRegistry
from mame_curator.media import resolve as resolve_mod
from mame_curator.media.rate_limit import MediaRateLimited
from mame_curator.parser.models import Machine

_SOURCES = ["esde", "libretro"]
_ALL: frozenset[Kind] = frozenset({"boxart", "title", "snap"})


class _Fake:
    def __init__(self, name: str) -> None:
        self.name = name
        self.license_compatible = True
        self.kinds = _ALL
        self.disabled_reason: str | None = None
        self.has: frozenset[Kind] = frozenset()
        self.prepare_exc: Exception | None = None
        self.prepare_calls = 0

    async def prepare(self, machine: Machine, *, client: httpx.AsyncClient) -> None:
        self.prepare_calls += 1
        if self.prepare_exc is not None:
            raise self.prepare_exc

    def url_for(self, machine: Machine, kind: Kind) -> str | None:
        return f"http://{self.name}.test/{kind}/{machine.name}" if kind in self.has else None


@pytest.fixture
def fakes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, _Fake]:
    found = {name: _Fake(name) for name in _SOURCES}
    served = tmp_path / "served"
    served.mkdir()

    def _registry(request: Any, world: Any) -> MediaSourceRegistry:
        available = cast("dict[str, MediaSource]", dict(found))
        return MediaSourceRegistry(world.config.media.sources, available)

    async def _fetch(url: str, cache_dir: Path, *, client: httpx.AsyncClient) -> Path:
        path = served / (url.removeprefix("http://").replace("/", "-") + ".png")
        path.write_bytes(url.encode())
        return path

    from mame_curator.api.routes import media as media_routes

    monkeypatch.setattr(media_routes, "request_registry", _registry)
    monkeypatch.setattr(resolve_mod, "fetch_with_cache", _fetch)
    return found


pytestmark = pytest.mark.parametrize("configured_media_sources", [_SOURCES], indirect=True)


def test_a_missing_picture_is_asked_once_across_views(client: Any, fakes: dict[str, _Fake]) -> None:
    assert client.get("/media/pacman/boxart").status_code == 404
    assert client.get("/media/pacman/boxart").status_code == 404
    assert fakes["esde"].prepare_calls == 1


def test_the_other_kinds_are_remembered_too(client: Any, fakes: dict[str, _Fake]) -> None:
    client.get("/media/pacman/snap")
    client.get("/media/pacman/snap")
    assert fakes["esde"].prepare_calls == 1


def test_a_rate_limited_source_is_asked_again(client: Any, fakes: dict[str, _Fake]) -> None:
    fakes["libretro"].prepare_exc = MediaRateLimited("busy")
    client.get("/media/pacman/boxart")
    client.get("/media/pacman/boxart")
    assert fakes["esde"].prepare_calls == 2


def test_changed_picture_settings_ask_again(client: Any, fakes: dict[str, _Fake]) -> None:
    client.get("/media/pacman/boxart")
    world = client.app.state.world
    media = world.config.media.model_copy(update={"esde_media_dir": Path("/elsewhere")})
    config = world.config.model_copy(update={"media": media})
    client.app.state.world = replace_world(base=world, config=config)
    client.get("/media/pacman/boxart")
    assert fakes["esde"].prepare_calls == 2


def test_retry_finds_a_picture_that_arrived(client: Any, fakes: dict[str, _Fake]) -> None:
    """The button: a remembered miss is forgotten and the sources asked now."""
    client.get("/media/pacman/boxart")
    fakes["esde"].has = frozenset({"boxart"})
    response = client.post("/api/media/pacman/retry")
    assert response.status_code == 200
    assert response.json() == {"short_name": "pacman", "found": True}
    assert client.get("/media/pacman/boxart").status_code == 200


def test_retry_with_still_no_picture_says_so(client: Any, fakes: dict[str, _Fake]) -> None:
    client.get("/media/pacman/boxart")
    response = client.post("/api/media/pacman/retry")
    assert response.json() == {"short_name": "pacman", "found": False}
    assert fakes["esde"].prepare_calls == 2


def test_retry_forgets_every_kind(client: Any, fakes: dict[str, _Fake]) -> None:
    client.get("/media/pacman/snap")
    client.post("/api/media/pacman/retry")
    client.get("/media/pacman/snap")
    # One snap view, the retry's boxart look, the snap view after.
    assert fakes["esde"].prepare_calls == 3


def test_retry_on_an_unknown_game_is_404(client: Any, fakes: dict[str, _Fake]) -> None:
    response = client.post("/api/media/nosuchgame/retry")
    assert response.status_code == 404
    assert response.json()["code"] == "game_not_found"


def test_a_source_query_is_never_remembered(client: Any, fakes: dict[str, _Fake]) -> None:
    """The picture guide asks one source; its misses stay live."""
    client.get("/media/pacman/boxart?source=esde")
    client.get("/media/pacman/boxart?source=esde")
    assert fakes["esde"].prepare_calls == 2

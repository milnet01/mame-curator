"""mame-curator-1146 — the stored picture choice, its address, and its routes.

Per ``docs/specs/mame-curator-1146-picture-choice.md`` INV-1 to INV-7, INV-9
and INV-13. The media registry is replaced with fake sources named after real
ones; ``fetch_with_cache`` reads files from a URL map, so nothing reaches the
network.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

import httpx
import pytest
from fastapi.testclient import TestClient

from mame_curator.api.state import build_world, replace_world
from mame_curator.media import Kind, MediaSource, MediaSourceRegistry
from mame_curator.media import resolve as resolve_mod
from mame_curator.media.rate_limit import MediaRateLimited
from mame_curator.parser.models import Machine

_SOURCES = ["esde", "retroarchThumbnails", "arcadeDB", "libretro"]
_IMMUTABLE = "public, max-age=2592000, immutable"
_ALL: frozenset[Kind] = frozenset({"boxart", "title", "snap"})


class _Fake:
    """A source answering ``http://<name>.test/<kind>/<game>`` for its kinds."""

    def __init__(
        self,
        name: str,
        *,
        kinds: frozenset[Kind] = _ALL,
        has: frozenset[Kind] | None = None,
        prepare_exc: Exception | None = None,
    ) -> None:
        self.name = name
        self.license_compatible = True
        self.kinds = kinds
        self.disabled_reason: str | None = None
        self.has = kinds if has is None else has
        self.prepare_exc = prepare_exc
        self.prepare_calls = 0

    async def prepare(self, machine: Machine, *, client: httpx.AsyncClient) -> None:
        self.prepare_calls += 1
        if self.prepare_exc is not None:
            raise self.prepare_exc

    def url_for(self, machine: Machine, kind: Kind) -> str | None:
        return f"http://{self.name}.test/{kind}/{machine.name}" if kind in self.has else None


def _bytes(source: str, kind: str, game: str = "pacman") -> bytes:
    return f"{source}-{kind}-{game}".encode()


@pytest.fixture
def fakes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, _Fake]:
    """Fake sources behind the media registry; every URL serves its own bytes."""
    found = {
        "esde": _Fake("esde"),
        "retroarchThumbnails": _Fake("retroarchThumbnails"),
        "arcadeDB": _Fake("arcadeDB"),
        "libretro": _Fake("libretro", has=frozenset()),
        "wikipediaImage": _Fake("wikipediaImage", kinds=frozenset({"boxart"})),
    }
    served = tmp_path / "served"
    served.mkdir()

    def _registry(request: Any, world: Any) -> MediaSourceRegistry:
        available = cast("dict[str, MediaSource]", dict(found))
        return MediaSourceRegistry(world.config.media.sources, available)

    async def _fetch(url: str, cache_dir: Path, *, client: httpx.AsyncClient) -> Path | None:
        source, kind, game = url.removeprefix("http://").replace(".test", "").split("/")
        path = served / f"{source}-{kind}-{game}.png"
        path.write_bytes(_bytes(source, kind, game))
        return path

    from mame_curator.api.routes import media as media_routes

    monkeypatch.setattr(media_routes, "request_registry", _registry)
    monkeypatch.setattr(resolve_mod, "fetch_with_cache", _fetch)
    return found


pytestmark = pytest.mark.parametrize("configured_media_sources", [_SOURCES], indirect=True)


def _pictures_file(config_file: Path) -> Path:
    return config_file.parent / "data" / "pictures.json"


def _choose(client: Any, source: str, kind: str, name: str = "pacman") -> Any:
    return client.put(f"/api/games/{name}/picture", json={"source": source, "kind": kind})


def _set_sources(client: Any, sources: tuple[str, ...]) -> None:
    world = client.app.state.world
    media = world.config.media.model_copy(update={"sources": sources})
    config = world.config.model_copy(update={"media": media})
    client.app.state.world = replace_world(base=world, config=config)


def _card(client: Any, name: str = "pacman") -> dict[str, Any]:
    items = client.get(f"/api/games/{name}/alternatives").json()["items"]
    return cast("dict[str, Any]", next(c for c in items if c["short_name"] == name))


# --- INV-1: the stored choice -------------------------------------------------


def test_save_writes_the_file_snapshots_the_old_one_and_survives_a_restart(
    client: Any, fakes: dict[str, _Fake], config_file: Path
) -> None:
    path = _pictures_file(config_file)
    first = _choose(client, "esde", "snap")
    assert first.status_code == 200, first.text
    assert first.json() == {"short_name": "pacman", "chosen": {"source": "esde", "kind": "snap"}}
    old_bytes = path.read_bytes()

    assert _choose(client, "retroarchThumbnails", "title").status_code == 200
    assert json.loads(path.read_text()) == {
        "pictures": {"pacman": {"source": "retroarchThumbnails", "kind": "title"}}
    }
    snapshots = config_file.parent / "data" / "snapshots"
    held = [p.read_bytes() for p in snapshots.glob("*/pictures.json")]
    assert old_bytes in held

    client.app.state.world = build_world(config_file)
    assert _card(client)["picture"] == {"source": "retroarchThumbnails", "kind": "title"}
    listed = client.get("/api/games").json()["items"]
    assert next(c for c in listed if c["short_name"] == "pacman")["picture"] == {
        "source": "retroarchThumbnails",
        "kind": "title",
    }


# --- INV-2: a bad file is no choices -----------------------------------------


@pytest.mark.parametrize(
    "content",
    [b"\xff\xfe not utf-8", b"not json", b'{"pictures": {"pacman": {"source": "esde"}}}', None],
    ids=["undecodable", "not-json", "invalid", "unreadable"],
)
def test_a_bad_pictures_file_loads_as_no_choices_and_is_left_alone(
    config_file: Path,
    fake_home: Path,
    caplog: pytest.LogCaptureFixture,
    content: bytes | None,
) -> None:
    from mame_curator.api import create_app

    path = _pictures_file(config_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    if content is None:
        path.mkdir()  # a folder where the file should be: reading it raises
    else:
        path.write_bytes(content)
    caplog.set_level(logging.WARNING, logger="mame_curator.api.pictures")
    with TestClient(create_app(config_file)) as client:
        assert client.get("/api/games").status_code == 200
        assert _card(client)["picture"] is None
    warnings = [r for r in caplog.records if r.name == "mame_curator.api.pictures"]
    assert len(warnings) == 1
    assert str(path) in warnings[0].getMessage()
    if content is not None:
        assert path.read_bytes() == content


# --- INV-3: the chosen picture and its cache header --------------------------


@pytest.fixture
def chosen(client: Any, fakes: dict[str, _Fake]) -> Iterator[Any]:
    """pacman's choice is (retroarchThumbnails, title); esde, first, has a boxart."""
    assert _choose(client, "retroarchThumbnails", "title").status_code == 200
    yield client


def test_the_chosen_pair_is_served_and_cached_when_v_names_it(chosen: Any) -> None:
    reply = chosen.get("/media/pacman/boxart?v=retroarchThumbnails.title")
    assert reply.status_code == 200
    assert reply.content == _bytes("retroarchThumbnails", "title")
    assert reply.headers["cache-control"] == _IMMUTABLE


@pytest.mark.parametrize("query", ["", "?v=esde.boxart"])
def test_the_chosen_pair_under_another_address_is_not_cached(chosen: Any, query: str) -> None:
    reply = chosen.get(f"/media/pacman/boxart{query}")
    assert reply.content == _bytes("retroarchThumbnails", "title")
    assert reply.headers["cache-control"] == "no-store"


def test_a_chosen_source_removed_from_media_sources_falls_back(chosen: Any) -> None:
    _set_sources(chosen, ("esde", "arcadeDB", "libretro"))
    reply = chosen.get("/media/pacman/boxart?v=retroarchThumbnails.title")
    assert reply.content == _bytes("esde", "boxart")
    assert reply.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("failure", ["rate-limited", "no-candidate"])
def test_a_chosen_pair_that_does_not_resolve_falls_back(
    chosen: Any, fakes: dict[str, _Fake], failure: str
) -> None:
    if failure == "rate-limited":
        fakes["retroarchThumbnails"].prepare_exc = MediaRateLimited("empty")
    else:
        fakes["retroarchThumbnails"].has = frozenset()
    reply = chosen.get("/media/pacman/boxart?v=retroarchThumbnails.title")
    assert reply.content == _bytes("esde", "boxart")
    assert reply.headers["cache-control"] == "no-store"


def test_v_without_a_choice_is_not_cached_and_plain_is(
    client: Any, fakes: dict[str, _Fake]
) -> None:
    named = client.get("/media/pacman/boxart?v=retroarchThumbnails.title")
    assert named.content == _bytes("esde", "boxart")
    assert named.headers["cache-control"] == "no-store"
    plain = client.get("/media/pacman/boxart")
    assert plain.headers["cache-control"] == _IMMUTABLE


# --- INV-4: only the game's boxart address changes ---------------------------


def test_a_choice_changes_only_that_games_boxart(client: Any, fakes: dict[str, _Fake]) -> None:
    addresses = [
        "/media/pacman/title",
        "/media/pacman/snap",
        "/media/pacmanf/boxart",
        "/media/pacman/boxart?source=esde",
    ]
    before = [client.get(a).content for a in addresses]
    assert _choose(client, "retroarchThumbnails", "title").status_code == 200
    after = [client.get(a).content for a in addresses]
    assert after == before


# --- INV-5: ?source= serves one pair only ------------------------------------


def test_source_that_misses_is_404_not_the_chain(client: Any, fakes: dict[str, _Fake]) -> None:
    fakes["retroarchThumbnails"].has = frozenset({"title"})
    reply = client.get("/media/pacman/boxart?source=retroarchThumbnails")
    assert reply.status_code == 404
    assert reply.json()["code"] == "media_upstream_not_found"


def test_source_that_is_rate_limited_is_404(client: Any, fakes: dict[str, _Fake]) -> None:
    fakes["retroarchThumbnails"].prepare_exc = MediaRateLimited("empty")
    reply = client.get("/media/pacman/boxart?source=retroarchThumbnails")
    assert reply.status_code == 404
    assert reply.json()["code"] == "media_upstream_not_found"


@pytest.mark.parametrize(
    "address", ["/media/pacman/boxart?source=nosuch", "/media/pacman/title?source=wikipediaImage"]
)
def test_source_outside_the_chain_is_422(
    client: Any, fakes: dict[str, _Fake], address: str
) -> None:
    reply = client.get(address)
    assert reply.status_code == 422
    assert reply.json()["code"] == "media_source_unknown"


def test_source_that_answers_is_served_and_cached(client: Any, fakes: dict[str, _Fake]) -> None:
    reply = client.get("/media/pacman/snap?source=arcadeDB")
    assert reply.content == _bytes("arcadeDB", "snap")
    assert reply.headers["cache-control"] == _IMMUTABLE


# --- INV-6, INV-7: the candidates route --------------------------------------


def _candidates(client: Any, further: bool = False) -> dict[str, Any]:
    reply = client.get(f"/api/games/pacman/picture/candidates?further={str(further).lower()}")
    assert reply.status_code == 200, reply.text
    return cast("dict[str, Any]", reply.json())


def test_candidates_ask_no_limited_source_when_a_free_one_has_boxart(
    client: Any, fakes: dict[str, _Fake]
) -> None:
    body = _candidates(client)
    assert fakes["arcadeDB"].prepare_calls == 0
    assert body["not_asked"] == ["arcadeDB"]
    assert body["chosen"] is None
    assert body["chosen_found"] is True
    pairs = [(c["source"], c["kind"], c["in_use"]) for c in body["candidates"]]
    assert pairs[0] == ("esde", "boxart", True)
    assert [p for p in pairs if p[2]] == [pairs[0]]
    assert len({(p[0], p[1]) for p in pairs}) == len(pairs), "listed once"


def test_candidates_list_the_in_use_limited_picture_first(
    client: Any, fakes: dict[str, _Fake]
) -> None:
    """The boxart walk reaches arcadeDB only because the free sources miss."""
    fakes["esde"].has = frozenset({"title"})
    fakes["retroarchThumbnails"].has = frozenset({"snap"})
    body = _candidates(client)
    assert fakes["arcadeDB"].prepare_calls == 1
    pairs = [(c["source"], c["kind"], c["in_use"]) for c in body["candidates"]]
    assert pairs == [
        ("arcadeDB", "boxart", True),
        ("esde", "title", False),
        ("retroarchThumbnails", "snap", False),
    ]


def test_a_stored_limited_choice_costs_one_prepare(client: Any, fakes: dict[str, _Fake]) -> None:
    assert _choose(client, "arcadeDB", "title").status_code == 200
    body = _candidates(client)
    assert fakes["arcadeDB"].prepare_calls == 1
    assert body["chosen"] == {"source": "arcadeDB", "kind": "title"}
    assert body["candidates"][0] == {"source": "arcadeDB", "kind": "title", "in_use": True}


def test_further_asks_the_limited_sources(client: Any, fakes: dict[str, _Fake]) -> None:
    body = _candidates(client, further=True)
    assert fakes["arcadeDB"].prepare_calls == 1
    assert body["not_asked"] == []
    sources = {c["source"] for c in body["candidates"]}
    assert "arcadeDB" in sources


def test_a_choice_that_does_not_resolve_says_so(client: Any, fakes: dict[str, _Fake]) -> None:
    assert _choose(client, "retroarchThumbnails", "title").status_code == 200
    fakes["retroarchThumbnails"].prepare_exc = MediaRateLimited("empty")
    body = _candidates(client)
    assert body["chosen_found"] is False
    assert body["not_answered"] == ["retroarchThumbnails"]
    assert body["candidates"][0] == {"source": "esde", "kind": "boxart", "in_use": True}


# --- INV-9, INV-13: save and clear -------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        {"source": "nosuch", "kind": "boxart"},
        {"source": "wikipediaImage", "kind": "snap"},
        {"source": "../../etc", "kind": "boxart"},
    ],
)
def test_save_refuses_a_source_the_card_could_not_serve(
    client: Any, fakes: dict[str, _Fake], config_file: Path, body: dict[str, str]
) -> None:
    reply = client.put("/api/games/pacman/picture", json=body)
    assert reply.status_code == 422
    assert reply.json()["code"] == "media_source_unknown"
    assert not _pictures_file(config_file).exists()


def test_save_fetches_nothing(client: Any, fakes: dict[str, _Fake]) -> None:
    fakes["arcadeDB"].prepare_exc = MediaRateLimited("empty")
    assert _choose(client, "arcadeDB", "snap").status_code == 200
    assert fakes["arcadeDB"].prepare_calls == 0


def test_clear_is_safe_to_repeat(client: Any, fakes: dict[str, _Fake], config_file: Path) -> None:
    assert _choose(client, "esde", "title").status_code == 200
    for _ in range(2):
        reply = client.delete("/api/games/pacman/picture")
        assert reply.status_code == 200
        assert reply.json() == {"short_name": "pacman", "chosen": None}
    assert json.loads(_pictures_file(config_file).read_text()) == {"pictures": {}}
    assert _card(client)["picture"] is None


def test_clear_with_no_choice_writes_nothing(
    client: Any, fakes: dict[str, _Fake], config_file: Path
) -> None:
    assert client.delete("/api/games/pacman/picture").json()["chosen"] is None
    assert not _pictures_file(config_file).exists()


@pytest.mark.parametrize(
    ("method", "address"),
    [
        ("get", "/api/games/nosuch/picture/candidates"),
        ("put", "/api/games/nosuch/picture"),
        ("delete", "/api/games/nosuch/picture"),
    ],
)
def test_an_unknown_game_is_404(
    client: Any, fakes: dict[str, _Fake], method: str, address: str
) -> None:
    kwargs = {"json": {"source": "esde", "kind": "boxart"}} if method == "put" else {}
    reply = getattr(client, method)(address, **kwargs)
    assert reply.status_code == 404
    assert reply.json()["code"] == "game_not_found"

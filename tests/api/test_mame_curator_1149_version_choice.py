"""mame-curator-1149: choosing a version takes effect, or says it did not."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient


def _winners(client: Any) -> list[str]:
    return [card["short_name"] for card in client.get("/api/games").json()["items"]]


def _saved(config_file: Path) -> dict[str, str]:
    saved: dict[str, str] = yaml.safe_load((config_file.parent / "overrides.yaml").read_text())[
        "overrides"
    ]
    return saved


@pytest.fixture
def old_file_client(config_file: Path, fake_home: Path) -> Iterator[Any]:
    """A server started on a file an earlier release wrote."""
    from mame_curator.api import create_app

    (config_file.parent / "overrides.yaml").write_text(
        "overrides:\n  pacman: pacmanf\n  pacmanf: pacman\n  ghost: nothing\n"
    )
    with TestClient(create_app(config_file)) as client:
        yield client


@pytest.mark.parametrize("name", ["pacman", "pacmanf"])
def test_alternatives_name_the_real_parent(client: Any, name: str) -> None:
    assert client.get(f"/api/games/{name}/alternatives").json()["parent"] == "pacman"


def test_a_second_choice_through_the_real_parent_changes_the_winner(client: Any) -> None:
    assert client.post("/api/overrides", json={"parent": "pacman", "winner": "pacmanf"}).is_success
    assert "pacmanf" in _winners(client)
    assert client.post("/api/overrides", json={"parent": "pacman", "winner": "pacman"}).is_success
    assert "pacman" in _winners(client)
    assert "pacmanf" not in _winners(client)


@pytest.mark.parametrize(
    ("parent", "winner"),
    [
        ("pacmanf", "pacman"),  # the old panel's request: a clone as the key
        ("ghost", "pacman"),  # no such family
        ("pacman", "neogeo"),  # another family's game
        ("pacman", "ghost"),  # not in the game list
    ],
)
def test_a_choice_that_would_not_take_is_refused_and_not_saved(
    client: Any, config_file: Path, parent: str, winner: str
) -> None:
    before = _winners(client)
    reply = client.post("/api/overrides", json={"parent": parent, "winner": winner})
    assert reply.status_code == 422
    assert reply.json()["code"] == "override_rejected"
    assert _winners(client) == before
    assert not (config_file.parent / "overrides.yaml").exists()


def test_an_old_clone_keyed_choice_applies_after_an_upgrade(
    config_file: Path, fake_home: Path
) -> None:
    from mame_curator.api import create_app

    (config_file.parent / "overrides.yaml").write_text("overrides:\n  pacmanf: pacmanf\n")
    with TestClient(create_app(config_file)) as client:
        assert "pacmanf" in _winners(client)
        assert client.get("/api/games/pacmanf").json()["override"] == "pacmanf"
        assert "overridden" in client.get("/api/games/pacmanf").json()["badges"]
        assert client.get("/api/games/pacmanf/alternatives").json()["parent"] == "pacman"


def test_the_old_file_is_untouched_until_the_next_save_then_takes_the_new_form(
    old_file_client: Any, config_file: Path
) -> None:
    assert _saved(config_file) == {"pacman": "pacmanf", "pacmanf": "pacman", "ghost": "nothing"}
    reply = old_file_client.post("/api/overrides", json={"parent": "pacman", "winner": "pacmanf"})
    assert reply.status_code == 200
    assert _saved(config_file) == {"pacman": "pacmanf", "ghost": "nothing"}


def test_warnings_about_another_saved_choice_do_not_refuse_this_one(old_file_client: Any) -> None:
    """The reply still carries them, and the frontend says so instead of success."""
    assert "pacman" in _winners(old_file_client)
    reply = old_file_client.post("/api/overrides", json={"parent": "pacman", "winner": "pacmanf"})
    assert reply.status_code == 200
    assert reply.json()["warnings"] == ["override key 'ghost' is not a known parent; ignored"]
    assert "pacmanf" in _winners(old_file_client)


def test_a_backup_holding_an_old_clone_key_still_applies(client: Any) -> None:
    bundle = client.post("/api/config/export").json()
    bundle["overrides"] = {"overrides": {"pacmanf": "pacmanf"}}
    assert client.post("/api/config/import", json=bundle).status_code == 200
    assert "pacmanf" in _winners(client)


def test_a_snapshot_holding_an_old_clone_key_still_applies(client: Any, config_file: Path) -> None:
    (config_file.parent / "overrides.yaml").write_text("overrides:\n  pacmanf: pacmanf\n")
    # A save snapshots the file it replaces, so this snapshot holds the old form.
    client.post("/api/overrides", json={"parent": "pacman", "winner": "pacman"})
    snapshots = client.get("/api/config/snapshots").json()["items"]
    assert client.post(f"/api/config/snapshots/{snapshots[0]['id']}/restore").status_code == 200
    assert "pacmanf" in _winners(client)

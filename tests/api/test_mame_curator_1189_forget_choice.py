"""mame-curator-1189: a saved choice that cannot be used can be forgotten."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient

_GHOST_WARNING = "override key 'ghost' is not a known parent; ignored"


@pytest.fixture
def old_choice_client(config_file: Path, fake_home: Path) -> Iterator[Any]:
    """A server whose saved choices hold one that cannot be used."""
    from mame_curator.api import create_app

    (config_file.parent / "overrides.yaml").write_text(
        "overrides:\n  pacman: pacmanf\n  ghost: nothing\n"
    )
    with TestClient(create_app(config_file)) as client:
        yield client


def _saved(config_file: Path) -> dict[str, str]:
    saved: dict[str, str] = yaml.safe_load((config_file.parent / "overrides.yaml").read_text())[
        "overrides"
    ]
    return saved


def test_a_choice_reply_names_the_saved_choices_that_cannot_be_used(
    old_choice_client: Any,
) -> None:
    reply = old_choice_client.post("/api/overrides", json={"parent": "pacman", "winner": "pacman"})
    assert reply.status_code == 200
    assert reply.json()["warnings"] == [_GHOST_WARNING]
    assert reply.json()["unusable"] == ["ghost"]


def test_forgetting_the_unusable_choice_ends_the_warning(
    old_choice_client: Any, config_file: Path
) -> None:
    reply = old_choice_client.delete("/api/overrides/ghost")
    assert reply.status_code == 200
    assert reply.json() == {"entries": {"pacman": "pacmanf"}, "warnings": [], "unusable": []}
    assert _saved(config_file) == {"pacman": "pacmanf"}
    later = old_choice_client.post("/api/overrides", json={"parent": "pacman", "winner": "pacman"})
    assert later.json()["warnings"] == []
    assert later.json()["unusable"] == []


def test_forgetting_one_choice_still_names_the_others_that_cannot_be_used(
    old_choice_client: Any,
) -> None:
    reply = old_choice_client.delete("/api/overrides/pacman")
    assert reply.status_code == 200
    assert reply.json()["warnings"] == [_GHOST_WARNING]
    assert reply.json()["unusable"] == ["ghost"]

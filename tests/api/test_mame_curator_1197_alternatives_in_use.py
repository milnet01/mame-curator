"""mame-curator-1197 — the alternatives reply says which version is in use.

The version guide at ``/fix/:shortName`` took the address's game as the one
in use. That holds from a Library card and is wrong for an address naming
another version. ``in_use`` is the family's current winner: the picker's
choice, or a saved choice of version.
"""

from __future__ import annotations

from typing import Any

import pytest


def _in_use(client: Any, name: str) -> object:
    response = client.get(f"/api/games/{name}/alternatives")
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    assert "in_use" in body
    return body["in_use"]


@pytest.mark.parametrize("name", ["pacman", "pacmanf"])
def test_every_version_of_a_family_names_the_same_one_in_use(client: Any, name: str) -> None:
    assert _in_use(client, name) == "pacman"


@pytest.mark.parametrize("name", ["pacman", "pacmanf"])
def test_a_saved_choice_of_version_is_the_one_in_use(client: Any, name: str) -> None:
    assert client.post("/api/overrides", json={"parent": "pacman", "winner": "pacmanf"}).is_success

    assert _in_use(client, name) == "pacmanf"

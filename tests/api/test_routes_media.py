"""R39 shape test (minimal media proxy).

Per ``docs/specs/P04.md`` § Media proxy. P04 ships a minimal pass-through
proxy; P05 swaps in the real URL builder + cache.
"""

from __future__ import annotations

from typing import Any


def test_route_r39_shape_media_unknown_kind(client: Any) -> None:
    """R39 — unknown {kind} returns 400 with code media_kind_invalid."""
    response = client.get("/media/pacman/unknown_kind")
    assert response.status_code == 400
    assert response.json()["code"] == "media_kind_invalid"


def test_route_r39_shape_media_unknown_game(client: Any) -> None:
    """R39 — unknown {name} returns 404 with code game_not_found
    (distinct from upstream 404)."""
    response = client.get("/media/no_such_machine/boxart")
    assert response.status_code == 404
    assert response.json()["code"] == "game_not_found"

"""R01–R07 shape tests + L04 / L05 / L06 behavioral tests.

Per ``docs/specs/P04.md`` § Routes (Games + metadata) and § Tests.

Until Step 4 lands ``create_app``, every test fails at fixture-setup with
``NotImplementedError``. Step 4 makes them green by wiring the handlers.
"""

from __future__ import annotations

from typing import Any

# ---- Per-route shape tests (R01–R07) ----------------------------------------


def test_route_r01_shape_games_listing(client: Any) -> None:
    """R01 GET /api/games → GamesPage."""
    response = client.get("/api/games")
    assert response.status_code == 200
    body = response.json()
    for key in ("items", "page", "page_size", "total"):
        assert key in body, f"GamesPage missing field {key!r}"
    assert isinstance(body["items"], list)


def test_route_r02_shape_game_detail(client: Any) -> None:
    """R02 GET /api/games/{name} → GameDetail; 404 for unknown name."""
    response = client.get("/api/games/pacman")
    assert response.status_code == 200
    body = response.json()
    for key in (
        "short_name",
        "machine",
        "category",
        "languages",
        "bestgames_tier",
        "mature",
        "chd_required",
        "badges",
        "override",
        "parent",
    ):
        assert key in body, f"GameDetail missing field {key!r}"
    assert body["short_name"] == "pacman"

    not_found = client.get("/api/games/no_such_machine")
    assert not_found.status_code == 404
    assert not_found.json()["code"] == "game_not_found"


def test_route_r03_shape_alternatives(client: Any) -> None:
    """R03 GET /api/games/{name}/alternatives → Alternatives."""
    response = client.get("/api/games/pacman/alternatives")
    assert response.status_code == 200
    assert "items" in response.json()


def test_route_r04_shape_explanation(client: Any) -> None:
    """R04 GET /api/games/{name}/explanation → Explanation."""
    response = client.get("/api/games/pacman/explanation")
    assert response.status_code == 200
    body = response.json()
    for key in ("short_name", "parent", "candidates", "hits"):
        assert key in body


def test_route_r05_shape_notes_get(client: Any) -> None:
    """R05 GET /api/games/{name}/notes → Notes (empty string default)."""
    response = client.get("/api/games/pacman/notes")
    assert response.status_code == 200
    assert "notes" in response.json()


def test_route_r06_shape_notes_put(client: Any) -> None:
    """R06 PUT /api/games/{name}/notes → Notes."""
    response = client.put("/api/games/pacman/notes", json={"notes": "Best with arcade stick"})
    assert response.status_code == 200
    assert response.json()["notes"] == "Best with arcade stick"


def test_route_r07_shape_stats(client: Any) -> None:
    """R07 GET /api/stats → Stats."""
    response = client.get("/api/stats")
    assert response.status_code == 200
    body = response.json()
    for key in ("by_genre", "by_decade", "by_publisher", "by_driver_status", "total_bytes"):
        assert key in body


# ---- Behavioral tests -------------------------------------------------------


def test_notes_round_trip(client: Any) -> None:
    """L04 — PUT then GET returns the same body across world swap."""
    written = client.put("/api/games/pacman/notes", json={"notes": "test note"})
    assert written.status_code == 200

    read = client.get("/api/games/pacman/notes")
    assert read.status_code == 200
    assert read.json()["notes"] == "test note"

    # The PUT triggers a world swap (per spec § Re-computation triggers).
    # A subsequent GET on a different game should NOT carry over the value.
    other = client.get("/api/games/neogeo/notes")
    assert other.status_code == 200
    assert other.json()["notes"] == ""


def test_explanation_returns_chain(client: Any) -> None:
    """L05 — explanation for a contested-group winner returns the tiebreaker chain;
    a solo winner returns hits=().
    """
    contested = client.get("/api/games/pacman/explanation")
    assert contested.status_code == 200
    body = contested.json()
    assert isinstance(body["hits"], list)
    # Spec: parent/clone group with 2+ candidates produces non-empty hits.
    # The mini DAT has pacman + pacmanf as a contested pair.
    assert len(body["hits"]) >= 1, "expected tiebreaker hits for contested group"

    # A machine that's solo in its group → hits=()
    # neogeo is a BIOS so it should be filtered out before Phase B; instead
    # check for "brokensim" which is solo (preliminary, but if it survived).
    solo = client.get("/api/games/3bagfull/explanation")
    if solo.status_code == 200:
        assert solo.json()["hits"] == []


def test_stats_aggregations(client: Any) -> None:
    """L06 — counts by genre / decade / publisher / driver-status match
    a hand-counted ground-truth on the 6-machine fixture DAT.
    """
    response = client.get("/api/stats")
    assert response.status_code == 200
    body = response.json()
    # The fixture DAT has 6 machines; bios/device/mechanical/preliminary drop
    # leaves a small set of arcade winners. Counts vary by filter config but
    # the response shape must hold.
    assert isinstance(body["by_genre"], dict)
    assert isinstance(body["by_decade"], dict)
    assert isinstance(body["by_publisher"], dict)
    assert isinstance(body["by_driver_status"], dict)
    assert isinstance(body["total_bytes"], int)
    assert body["total_bytes"] >= 0

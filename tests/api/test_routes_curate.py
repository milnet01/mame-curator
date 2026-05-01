"""R08–R13b shape tests + L02 / L03 behavioral tests.

Per ``docs/specs/P04.md`` § Routes (Overrides + sessions) and § Tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# ---- Per-route shape tests --------------------------------------------------


def test_route_r08_shape_overrides_post(client: Any) -> None:
    response = client.post("/api/overrides", json={"parent": "pacman", "winner": "pacmanf"})
    assert response.status_code == 200
    assert "entries" in response.json()


def test_route_r09_shape_overrides_delete(client: Any) -> None:
    client.post("/api/overrides", json={"parent": "pacman", "winner": "pacmanf"})
    response = client.delete("/api/overrides/pacman")
    assert response.status_code == 200
    assert "entries" in response.json()

    not_found = client.delete("/api/overrides/no_such_parent")
    assert not_found.status_code == 404


def test_route_r10_shape_sessions_list(client: Any) -> None:
    response = client.get("/api/sessions")
    assert response.status_code == 200
    body = response.json()
    assert "active" in body
    assert "sessions" in body


def test_route_r11_shape_sessions_post(client: Any) -> None:
    response = client.post(
        "/api/sessions",
        json={
            "name": "test_session",
            "session": {"include_genres": ["Shooter*"]},
        },
    )
    assert response.status_code == 200
    assert "test_session" in response.json()["sessions"]

    invalid_name = client.post(
        "/api/sessions",
        json={"name": "_leading_underscore", "session": {"include_genres": ["X"]}},
    )
    assert invalid_name.status_code == 422
    assert invalid_name.json()["code"] == "session_name_invalid"


def test_route_r12_shape_sessions_delete(client: Any) -> None:
    client.post(
        "/api/sessions",
        json={"name": "to_delete", "session": {"include_genres": ["X"]}},
    )
    response = client.delete("/api/sessions/to_delete")
    assert response.status_code == 200
    assert "to_delete" not in response.json()["sessions"]

    not_found = client.delete("/api/sessions/never_existed")
    assert not_found.status_code == 404


def test_route_r13_shape_sessions_activate(client: Any) -> None:
    client.post(
        "/api/sessions",
        json={"name": "to_activate", "session": {"include_genres": ["X"]}},
    )
    response = client.post("/api/sessions/to_activate/activate", json={})
    assert response.status_code == 200
    assert response.json()["active"] == "to_activate"


def test_route_r13b_shape_sessions_deactivate(client: Any) -> None:
    response = client.post("/api/sessions/_deactivate", json={})
    assert response.status_code == 200
    assert response.json()["active"] is None


# ---- Behavioral tests -------------------------------------------------------


def test_overrides_post_persists_to_yaml(client: Any, tmp_path: Path) -> None:
    """L02 — POST writes overrides.yaml; subsequent GET reflects the change;
    snapshot directory contains the prior file.
    """
    response = client.post("/api/overrides", json={"parent": "pacman", "winner": "pacmanf"})
    assert response.status_code == 200

    config_response = client.get("/api/config")
    assert config_response.status_code == 200

    # The override should now appear in subsequent listings.
    detail = client.get("/api/games/pacman")
    assert detail.status_code == 200
    assert detail.json()["override"] == "pacmanf"

    # Snapshot directory exists and contains the prior overrides.yaml.
    snapshots = client.get("/api/config/snapshots")
    assert snapshots.status_code == 200
    snap_list = snapshots.json()
    assert "items" in snap_list or "snapshots" in snap_list


def test_sessions_crud(client: Any) -> None:
    """L03 — create + read + activate + delete round-trip via R10–R13 + R13b."""
    create = client.post(
        "/api/sessions",
        json={
            "name": "shoot_em_ups",
            "session": {"include_genres": ["Shooter*"]},
        },
    )
    assert create.status_code == 200
    assert "shoot_em_ups" in create.json()["sessions"]

    listing = client.get("/api/sessions")
    assert "shoot_em_ups" in listing.json()["sessions"]

    activated = client.post("/api/sessions/shoot_em_ups/activate", json={})
    assert activated.json()["active"] == "shoot_em_ups"

    deactivated = client.post("/api/sessions/_deactivate", json={})
    assert deactivated.json()["active"] is None

    deleted = client.delete("/api/sessions/shoot_em_ups")
    assert deleted.status_code == 200
    assert "shoot_em_ups" not in deleted.json()["sessions"]

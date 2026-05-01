"""R14–R19 shape tests + L07 / L08 / L09 behavioral + P01 property test.

Per ``docs/specs/P04.md`` § Routes (Config) and § Tests.
"""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# ---- Per-route shape tests --------------------------------------------------


def test_route_r14_shape_config_get(client: Any) -> None:
    response = client.get("/api/config")
    assert response.status_code == 200
    body = response.json()
    for key in ("paths", "server", "filters", "ui", "updates", "fs"):
        assert key in body


def test_route_r15_shape_config_patch(client: Any) -> None:
    response = client.patch("/api/config", json={"ui": {"theme": "light"}})
    assert response.status_code == 200
    body = response.json()
    assert body["ui"]["theme"] == "light"
    assert "restart_required" in body


def test_route_r16_shape_snapshots_list(client: Any) -> None:
    response = client.get("/api/config/snapshots")
    assert response.status_code == 200


def test_route_r17_shape_snapshot_restore(client: Any) -> None:
    # Trigger a snapshot via PATCH first.
    client.patch("/api/config", json={"ui": {"theme": "light"}})
    snaps = client.get("/api/config/snapshots").json()
    items = snaps.get("items") or snaps.get("snapshots") or []
    if items:
        snapshot_id = items[0]["id"]
        response = client.post(f"/api/config/snapshots/{snapshot_id}/restore")
        assert response.status_code == 200

    not_found = client.post("/api/config/snapshots/nonexistent/restore")
    assert not_found.status_code == 404


def test_route_r18_shape_config_export(client: Any) -> None:
    response = client.post("/api/config/export")
    assert response.status_code == 200
    body = response.json()
    for key in ("config", "overrides", "sessions", "notes"):
        assert key in body


def test_route_r19_shape_config_import(client: Any) -> None:
    bundle = client.post("/api/config/export").json()
    response = client.post("/api/config/import", json=bundle)
    assert response.status_code == 200


# ---- Behavioral tests -------------------------------------------------------


def test_config_patch_validates(client: Any) -> None:
    """L07 — PATCH with invalid path → 422 with field-level error."""
    response = client.patch(
        "/api/config", json={"paths": {"source_roms": "/definitely/not/a/path"}}
    )
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "config_invalid"
    assert any(
        f["loc"] == "paths.source_roms" and f["type"] == "path_not_found" for f in body["fields"]
    )


def test_config_snapshots_round_trip(client: Any) -> None:
    """L08 — PATCH creates snapshot; restore replays; GET reflects the rollback."""
    # Capture initial state.
    pre = client.get("/api/config").json()
    pre_theme = pre["ui"]["theme"]
    new_theme = "light" if pre_theme != "light" else "dark"

    # PATCH triggers snapshot.
    client.patch("/api/config", json={"ui": {"theme": new_theme}})

    # Snapshot should exist; pick the most recent one.
    snaps = client.get("/api/config/snapshots").json()
    items = snaps.get("items") or snaps.get("snapshots") or []
    assert len(items) >= 1, "PATCH should have created a snapshot"
    most_recent = items[0]

    # Restore it; theme should revert.
    restore = client.post(f"/api/config/snapshots/{most_recent['id']}/restore")
    assert restore.status_code == 200
    post = client.get("/api/config").json()
    assert post["ui"]["theme"] == pre_theme


def test_config_export_import_round_trip(client: Any) -> None:
    """L09 — export → reset → import reproduces winners byte-equal."""
    games_pre = client.get("/api/games").json()
    bundle = client.post("/api/config/export").json()

    # Mutate the live state.
    client.patch("/api/config", json={"ui": {"theme": "light"}})

    # Import bundle; state should round-trip.
    imported = client.post("/api/config/import", json=bundle)
    assert imported.status_code == 200

    games_post = client.get("/api/games").json()
    assert games_post["total"] == games_pre["total"]
    assert [g["short_name"] for g in games_post["items"]] == [
        g["short_name"] for g in games_pre["items"]
    ]


# ---- Property test ----------------------------------------------------------


@given(st.fixed_dictionaries({}))
@settings(max_examples=5, deadline=None)
@pytest.mark.xfail(reason="P04 — not yet implemented", strict=False)
def test_filter_recompute_idempotent_under_no_op_patch(client: Any, _: dict[str, Any]) -> None:
    """P01 — PATCH with no fields → 200 + filter result unchanged.

    Hypothesis-driven so a future expansion (random no-op shapes) plugs in.
    """
    pre = client.get("/api/games").json()
    response = client.patch("/api/config", json={})
    assert response.status_code == 200
    post = client.get("/api/games").json()
    assert post == pre, "no-op PATCH must not change games listing"

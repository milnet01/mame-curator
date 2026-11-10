"""R18 / R19 shape tests + L09 behavioral: Backup export and import.

Per ``docs/specs/P04-http-api.md`` § Routes (Config). Moved from
``test_routes_config.py`` with the routes to ``routes/backup.py``
(mame-curator-1146 §2 item 6).
"""

from __future__ import annotations

from typing import Any


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


def test_backup_carries_drop_multigame(client: Any) -> None:
    """mame-curator-1216: the switch is config, so Backup keeps and restores it."""
    filters = client.get("/api/config").json()["filters"]
    assert filters["drop_multigame"] is False
    saved = client.patch("/api/config", json={"filters": {**filters, "drop_multigame": True}})
    assert saved.json()["filters"]["drop_multigame"] is True

    bundle = client.post("/api/config/export").json()
    assert bundle["config"]["filters"]["drop_multigame"] is True

    client.patch("/api/config", json={"filters": {**filters, "drop_multigame": False}})
    assert client.post("/api/config/import", json=bundle).status_code == 200
    assert client.get("/api/config").json()["filters"]["drop_multigame"] is True


def test_backup_carries_keep_languages(client: Any) -> None:
    """mame-curator-1217: the chosen languages are config, so Backup keeps them."""
    filters = client.get("/api/config").json()["filters"]
    assert filters["keep_languages"] == []
    english = {**filters, "keep_languages": ["English"]}
    saved = client.patch("/api/config", json={"filters": english})
    assert saved.json()["filters"]["keep_languages"] == ["English"]

    bundle = client.post("/api/config/export").json()
    assert bundle["config"]["filters"]["keep_languages"] == ["English"]

    client.patch("/api/config", json={"filters": {**filters, "keep_languages": []}})
    assert client.post("/api/config/import", json=bundle).status_code == 200
    assert client.get("/api/config").json()["filters"]["keep_languages"] == ["English"]

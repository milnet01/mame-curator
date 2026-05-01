"""R35 (setup-check) + R36 (updates-check) shape tests.

Per ``docs/specs/P04.md`` § Stub endpoints.
"""

from __future__ import annotations

from typing import Any


def test_route_r35_shape_setup_check(client: Any) -> None:
    response = client.get("/api/setup/check")
    assert response.status_code == 200
    body = response.json()
    for key in ("config_present", "paths", "reference_files"):
        assert key in body
    for path_key in ("source_roms", "source_dat", "dest_roms"):
        assert path_key in body["paths"]


def test_route_r36_shape_updates_check(client: Any) -> None:
    response = client.get("/api/updates/check")
    assert response.status_code == 200
    body = response.json()
    assert "app" in body
    assert "ini" in body
    assert body["ini"] == [], "P04 stub: ini list always empty"

    app = body["app"]
    assert "current_version" in app
    assert app["latest_version"] is None, "P04 stub: latest_version always null"
    assert app["update_available"] is False

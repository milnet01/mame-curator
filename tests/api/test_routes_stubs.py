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


def test_setup_check_cloneof_map_size_and_listxml_status(client: Any) -> None:
    """P15 § 4.3.1: /api/setup/check exposes cloneof_map_size and the
    raw listxml status under reference_files.

    FP24-BB: the derived ``listxml_available`` boolean was removed —
    the ListxmlBanner re-derives `file missing` vs `parsed empty`
    from the raw fields so it can pick a different body for each.
    cloneof_map_size is the literal len(world.cloneof_map).

    The api_listxml fixture maps pacmanf → pacman, so cloneof_map_size
    >= 1 and reference_files.listxml.exists is True.
    """
    resp = client.get("/api/setup/check")
    assert resp.status_code == 200
    body = resp.json()
    assert "listxml_available" not in body
    assert body["cloneof_map_size"] >= 1
    assert body["reference_files"]["listxml"]["exists"] is True

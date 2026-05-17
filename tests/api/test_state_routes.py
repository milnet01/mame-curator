"""P14 — GET/POST/DELETE /api/state route tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def _state_yaml(config_file: Path) -> Path:
    return config_file.parent / "data" / "state.yaml"


def _activity_log(config_file: Path) -> Path:
    return config_file.parent / "data" / "activity.jsonl"


def _activity_lines(config_file: Path) -> list[dict[str, Any]]:
    log = _activity_log(config_file)
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line]


# ---- POST happy + write effects --------------------------------------------


def test_post_state_persists_to_disk(client: Any, config_file: Path) -> None:
    """state.yaml on disk reflects the entry after POST."""
    response = client.post("/api/state", json={"short_name": "pacman", "state": "reviewed"})
    assert response.status_code == 200
    assert response.json() == {"entries": {"pacman": "reviewed"}}
    on_disk = yaml.safe_load(_state_yaml(config_file).read_text(encoding="utf-8"))
    assert on_disk == {"state": {"pacman": "reviewed"}}


def test_post_state_recomputes_world(client: Any, app: Any) -> None:
    """world.review_state reflects the new entry after POST."""
    client.post("/api/state", json={"short_name": "pacman", "state": "skipped"})
    world = app.state.world
    assert world.review_state.entries["pacman"].value == "skipped"


def test_post_state_appends_activity_event(client: Any, config_file: Path) -> None:
    """INV-5 — every mutation appends exactly one review_state activity line."""
    client.post("/api/state", json={"short_name": "pacman", "state": "reviewed"})
    lines = [
        line for line in _activity_lines(config_file) if line.get("event_type") == "review_state"
    ]
    assert len(lines) == 1
    event = lines[0]
    assert event["session_id"] == ""
    assert event["summary"] == "marked pacman as reviewed"
    assert event["details"]["short_name"] == "pacman"
    assert event["details"]["state"] == "reviewed"
    assert event["details"]["previous"] == "pending"


# ---- POST error paths ------------------------------------------------------


def test_post_pending_returns_422(client: Any) -> None:
    """INV-8 — `pending` is rejected by the Pydantic enum before the handler."""
    response = client.post("/api/state", json={"short_name": "pacman", "state": "pending"})
    assert response.status_code == 422


def test_post_unknown_short_name_returns_404_game_not_found(client: Any) -> None:
    """INV-8 — unknown short_name → 404 with code game_not_found."""
    response = client.post("/api/state", json={"short_name": "no_such_game", "state": "reviewed"})
    assert response.status_code == 404
    assert response.json()["code"] == "game_not_found"


def test_post_invalid_state_value_returns_422(client: Any) -> None:
    """INV-8 — invalid `state` value → 422."""
    response = client.post("/api/state", json={"short_name": "pacman", "state": "approved"})
    assert response.status_code == 422


def test_post_same_value_is_no_op(client: Any, config_file: Path) -> None:
    """INV-13 — same-value re-post is a no-op (no second activity line)."""
    client.post("/api/state", json={"short_name": "pacman", "state": "reviewed"})
    yaml_path = _state_yaml(config_file)
    yaml_mtime_before = yaml_path.stat().st_mtime_ns
    log_before = len(_activity_lines(config_file))

    response = client.post("/api/state", json={"short_name": "pacman", "state": "reviewed"})
    assert response.status_code == 200

    assert yaml_path.stat().st_mtime_ns == yaml_mtime_before
    assert len(_activity_lines(config_file)) == log_before


# ---- DELETE ----------------------------------------------------------------


def test_delete_state_clears_entry(client: Any, config_file: Path) -> None:
    """DELETE removes the entry from the sparse store."""
    client.post("/api/state", json={"short_name": "pacman", "state": "reviewed"})
    response = client.delete("/api/state/pacman")
    assert response.status_code == 200
    assert response.json() == {"entries": {}}
    on_disk = yaml.safe_load(_state_yaml(config_file).read_text(encoding="utf-8"))
    assert on_disk == {"state": {}}


def test_delete_state_idempotent_on_missing_entry(client: Any, config_file: Path) -> None:
    """INV-13 — DELETE on a game already at pending is a no-op.

    No file write (mtime unchanged) AND no activity event.
    """
    yaml_path = _state_yaml(config_file)
    # No state.yaml yet -- assert via missing file before & after.
    assert not yaml_path.exists()
    activity_before = len(_activity_lines(config_file))

    response = client.delete("/api/state/pacman")
    assert response.status_code == 200
    assert response.json() == {"entries": {}}

    assert not yaml_path.exists()
    assert len(_activity_lines(config_file)) == activity_before


def test_delete_unknown_short_name_returns_404(client: Any) -> None:
    """Unknown short_name → 404 game_not_found (same as POST)."""
    response = client.delete("/api/state/no_such_game")
    assert response.status_code == 404
    assert response.json()["code"] == "game_not_found"


# ---- GET -------------------------------------------------------------------


def test_get_state_returns_full_map(client: Any) -> None:
    """GET /api/state returns the full entries dict."""
    response = client.get("/api/state")
    assert response.status_code == 200
    assert response.json() == {"entries": {}}

    client.post("/api/state", json={"short_name": "pacman", "state": "needs-decision"})
    response = client.get("/api/state")
    assert response.json() == {"entries": {"pacman": "needs-decision"}}

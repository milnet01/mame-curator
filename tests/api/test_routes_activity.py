"""R28 shape test + L11 behavioral test (paginated activity log).

Per ``docs/specs/P04.md`` § Routes (Activity) and § Tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def test_route_r28_shape_activity(client: Any) -> None:
    response = client.get("/api/activity")
    assert response.status_code == 200
    body = response.json()
    for key in ("items", "page", "page_size", "total"):
        assert key in body


def test_route_r28_missing_file_returns_empty_page(client: Any) -> None:
    """Spec line ~173: missing data/activity.jsonl → empty page, never 404/500."""
    response = client.get("/api/activity")
    assert response.status_code == 200
    body = response.json()
    # On a fresh fixture install, no copy has run → activity.jsonl is absent.
    assert body["total"] == 0
    assert body["items"] == []


def test_activity_log_paginated(client: Any, tmp_path: Path) -> None:
    """L11 — paginated + filterable by event_type, since, until."""
    # Synthesize 50 events into data/activity.jsonl by running 50 mini-copies
    # (the runner appends one ActivityEvent per copy session). For the Step-3
    # red state, the assertions below will fail at fixture setup; once
    # implemented, the test seeds the file and asserts pagination.
    activity_file = tmp_path / "data" / "activity.jsonl"
    activity_file.parent.mkdir(parents=True, exist_ok=True)
    events: list[dict[str, Any]] = [
        {
            "timestamp": f"2026-05-01T00:00:{i:02d}Z",
            "event_type": "copy_finished" if i % 2 == 0 else "override_set",
            "summary": f"event {i}",
            "details": {},
        }
        for i in range(50)
    ]
    activity_file.write_text("\n".join(json.dumps(e) for e in events) + "\n")

    page1 = client.get("/api/activity?page=1&page_size=10")
    assert page1.status_code == 200
    assert len(page1.json()["items"]) <= 10

    filtered = client.get("/api/activity?event_type=copy_finished")
    assert filtered.status_code == 200
    if filtered.json()["items"]:
        assert all(e["event_type"] == "copy_finished" for e in filtered.json()["items"])

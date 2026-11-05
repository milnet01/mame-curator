"""mame-curator-1158: a page can find the copy that is still running.

## Invariants

- **INV-1** `GET /api/copy/current` answers `null` when no copy is in flight,
  both before any copy and after the last one ended. *Tests:*
  `test_current_is_null_before_any_copy`, `test_current_reports_a_paused_copy`.
- **INV-2** While a copy is in flight it answers that job's `JobStatus`, and
  its `state` is the controller's: `paused` after a pause, `running` after a
  resume. *Test:* `test_current_reports_a_paused_copy`.

## Rationale

A user who left the Library or the guide by the top menu or browser Back
lost the copy window, and with it Pause, Resume and Stop. A copy left paused
then refused every new copy. The pages need a plain read of the in-flight
job to reconnect to it; the status stream also replays a finished job, so it
cannot answer "is one still running?".
"""

from __future__ import annotations

import threading
import time
from typing import Any

import pytest

from mame_curator.copy import runner as runner_module
from mame_curator.copy.executor import copy_one

_TIMEOUT = 10.0


def test_current_is_null_before_any_copy(client: Any) -> None:
    """INV-1."""
    response = client.get("/api/copy/current")
    assert response.status_code == 200, response.text
    assert response.json() is None


def test_current_reports_a_paused_copy(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """INV-1, INV-2."""
    release = threading.Event()

    def held_copy_one(*args: Any, **kwargs: Any) -> Any:
        release.wait(_TIMEOUT)
        return copy_one(*args, **kwargs)

    monkeypatch.setattr(runner_module, "copy_one", held_copy_one)
    start = client.post(
        "/api/copy/start",
        json={"selected_names": ["pacman", "3bagfull"], "conflict_strategy": "OVERWRITE"},
    )
    assert start.status_code == 200, start.text
    job_id = start.json()["job_id"]
    try:
        assert client.post("/api/copy/pause").status_code == 200

        paused = client.get("/api/copy/current")
        assert paused.status_code == 200, paused.text
        body = paused.json()
        assert isinstance(body, dict), body
        assert body["job_id"] == job_id
        assert body["state"] == "paused"
        assert body["files_total"] == 2

        assert client.post("/api/copy/resume").status_code == 200
        assert client.get("/api/copy/current").json()["state"] == "running"
    finally:
        release.set()

    deadline = time.monotonic() + _TIMEOUT
    while client.app.state.job.current is not None:
        if time.monotonic() > deadline:
            pytest.fail("the copy never finished")
        time.sleep(0.02)
    assert client.get("/api/copy/current").json() is None

"""mame-curator-1157: a copy that crashes leaves a record the user can find.

## Invariants

- **INV-1** When the copy worker crashes after the copy started (an
  unexpected exception, not the user's Stop), the activity log gains one
  `copy_aborted` entry for the same `session_id` as its `copy_started`
  entry. Its summary says the copy stopped because of an error and carries
  the error's first line. *Test:* `test_crash_mid_copy_records_activity_and_report`.
- **INV-2** The same crash writes the copy's report, with status `ERROR`,
  the files copied before the crash in `succeeded`, and the error's first
  line in `warnings`. *Test:* `test_crash_mid_copy_records_activity_and_report`.
- **INV-3** When the record itself cannot be written (the activity log is
  unwritable), the job still ends: the manager goes idle, the stream ends
  with `job_aborted`, and the report is still written. *Test:*
  `test_crash_with_unwritable_activity_log_still_ends_the_job`.
- **INV-4** A crash before the copy started still adds a `copy_aborted`
  entry naming the error, so the Activity page the crash alert points to
  is not silent. *Test:* `test_crash_before_start_records_activity`.

## Rationale

Before the fix, `JobManager`'s worker caught the exception and emitted
`job_aborted` only: no report, no activity entry. The UI says the copy
crashed and points to Activity, which showed only that the copy started.
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any

import pytest

from mame_curator.copy import runner as runner_module
from mame_curator.copy.executor import copy_one

_TIMEOUT = 10.0


def _wait_idle(client: Any) -> None:
    jobs = client.app.state.job
    deadline = time.monotonic() + _TIMEOUT
    while jobs.current is not None:
        if time.monotonic() > deadline:
            pytest.fail("the crashed copy job never ended")
        time.sleep(0.02)


def _activity(client: Any) -> list[dict[str, Any]]:
    log = client.app.state.world.data_dir / "activity.jsonl"
    if not log.is_file():
        return []
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line]


def _crash_on_second_file(monkeypatch: pytest.MonkeyPatch, before_raise: Any = None) -> None:
    calls = {"n": 0}

    def flaky(*args: Any, **kwargs: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 1:
            return copy_one(*args, **kwargs)
        if before_raise is not None:
            before_raise()
        raise RuntimeError("disk exploded\nsecond line of detail")

    monkeypatch.setattr(runner_module, "copy_one", flaky)


def _start(client: Any) -> str:
    response = client.post(
        "/api/copy/start",
        json={"selected_names": ["pacman", "3bagfull"], "conflict_strategy": "OVERWRITE"},
    )
    assert response.status_code == 200, response.text
    return str(response.json()["job_id"])


def test_crash_mid_copy_records_activity_and_report(
    client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INV-1, INV-2."""
    _crash_on_second_file(monkeypatch)
    job_id = _start(client)
    _wait_idle(client)

    events = _activity(client)
    started = [e for e in events if e["event_type"] == "copy_started"]
    aborted = [e for e in events if e["event_type"] == "copy_aborted"]
    assert len(started) == 1, events
    assert len(aborted) == 1, f"expected one copy_aborted entry, saw {events!r}"
    entry = aborted[0]
    assert entry["session_id"] == started[0]["session_id"]
    assert "stopped because of an error" in entry["summary"]
    assert "disk exploded" in entry["summary"]
    assert "second line" not in entry["summary"]
    assert entry["details"]["reason"] == "ERROR"

    response = client.get(f"/api/copy/history/{job_id}/report")
    assert response.status_code == 200, f"no report written for the crashed copy: {response.text}"
    report = response.json()
    assert report["status"] == "ERROR"
    assert report["session_id"] == started[0]["session_id"]
    assert [o["short_name"] for o in report["succeeded"]] == ["3bagfull"]
    assert any("disk exploded" in w for w in report["warnings"]), report["warnings"]

    listing = client.get("/api/copy/history").json()
    assert [item["status"] for item in listing["items"]] == ["ERROR"]


def test_crash_with_unwritable_activity_log_still_ends_the_job(
    client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INV-3."""
    log: Path = client.app.state.world.data_dir / "activity.jsonl"

    def break_the_log() -> None:
        # A directory where the log file was: every append now fails.
        log.unlink()
        log.mkdir()

    _crash_on_second_file(monkeypatch, before_raise=break_the_log)
    job_id = _start(client)
    _wait_idle(client)

    last = client.app.state.job.replayable
    assert last is not None
    assert last.lifecycle_history[-1].event == "job_aborted"
    response = client.get(f"/api/copy/history/{job_id}/report")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ERROR"
    shutil.rmtree(log)


def test_crash_before_start_records_activity(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """INV-4."""

    def broken_preflight(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("preflight fell over")

    monkeypatch.setattr(runner_module, "preflight", broken_preflight)
    _start(client)
    _wait_idle(client)

    events = _activity(client)
    assert [e["event_type"] for e in events] == ["copy_aborted"], events
    assert "stopped because of an error" in events[0]["summary"]
    assert "preflight fell over" in events[0]["summary"]

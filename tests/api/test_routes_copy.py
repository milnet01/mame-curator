"""R20–R27 shape tests + L10 behavioral test (pause/resume/abort).

Per ``docs/specs/P04.md`` § Routes (Copy) and § Tests.
"""

from __future__ import annotations

from typing import Any

import pytest

# ---- Per-route shape tests --------------------------------------------------


def test_route_r20_shape_dry_run(client: Any) -> None:
    response = client.post(
        "/api/copy/dry-run",
        json={"selected_names": ["pacman"], "conflict_strategy": "CANCEL"},
    )
    assert response.status_code == 200
    body = response.json()
    # DryRunReport schema (schemas_copy.py) — both fields are required.
    assert "counts" in body, body
    assert "summary" in body, body


def test_route_r21_shape_start(client: Any) -> None:
    response = client.post(
        "/api/copy/start",
        json={"selected_names": ["pacman"], "conflict_strategy": "OVERWRITE"},
    )
    # Either accepted (202/200 with job_id) or 409 if a job is already running.
    assert response.status_code in (200, 409)
    if response.status_code == 200:
        assert "job_id" in response.json()


@pytest.mark.parametrize(
    ("endpoint", "json_body"),
    [
        ("/api/copy/pause", None),
        ("/api/copy/resume", None),
        ("/api/copy/abort", {"recycle_partial": False}),
    ],
    ids=["r22-pause", "r23-resume", "r24-abort"],
)
def test_route_r22_r24_action_job_not_found(
    client: Any, endpoint: str, json_body: dict[str, Any] | None
) -> None:
    """R22/R23/R24 — pause / resume / abort all 404 with code ``job_not_found``
    when no job is running (fresh client → no current job)."""
    response = client.post(endpoint, json=json_body)
    assert response.status_code == 404, response.text
    assert response.json()["code"] == "job_not_found"


def test_route_r25_shape_status_no_job(client: Any) -> None:
    """R25 GET /api/copy/status — 404 when no active job."""
    response = client.get("/api/copy/status")
    assert response.status_code == 404


def test_route_r26_shape_history(client: Any) -> None:
    response = client.get("/api/copy/history")
    assert response.status_code == 200
    body = response.json()
    # HistoryListing schema (schemas_copy.py) — all four fields required.
    for key in ("items", "page", "page_size", "total"):
        assert key in body, f"missing {key!r} in {body!r}"


def test_route_r27_shape_history_report_not_found(client: Any) -> None:
    response = client.get("/api/copy/history/no_such_job_id/report")
    assert response.status_code == 404


# ---- Behavioral test (L10) --------------------------------------------------


def test_pause_resume_abort_copy(client: Any) -> None:
    """L10 — route-level pause → resume → abort lifecycle contract.

    Deterministic-by-branch. The fixture ``.zip`` files complete in
    microseconds, so a control call may catch the live job (200) or arrive
    after the worker finished (404) — a genuine race we cannot eliminate
    without a slow fixture. This test stays non-vacuous on *both* branches:
    on 200 it asserts the transitional ``state`` the endpoint promises, on
    404 it asserts the typed ``job_not_found`` code. A regression (wrong
    state, wrong/absent error code, or a 500) is caught whoever wins the
    race; previously both branches accepted any 200/404 and asserted
    nothing (mame-curator-1052).

    The deterministic *behavioural* contract for pause/resume/cancel lives
    in ``tests/copy/test_controller.py`` (the state machine) and
    ``tests/copy/test_runner_lifecycle.py::test_pause_holds_at_file_boundary``
    (the worker honours the gate). ``test_sse.py`` covers the happy-path SSE
    event sequence only — it does NOT drive pause/resume — so these
    endpoints are smoke-tested here and nowhere else.
    """
    # Start a copy of two winners (more files → a slightly wider race window).
    start = client.post(
        "/api/copy/start",
        json={"selected_names": ["pacman", "neogeo"], "conflict_strategy": "OVERWRITE"},
    )
    assert start.status_code == 200
    assert "job_id" in start.json()

    # Pause: 200 → JobStatus carries the "paused" override; 404 → the worker
    # already finished, which must surface as the typed job_not_found code.
    pause = client.post("/api/copy/pause")
    assert pause.status_code in (200, 404), pause.text
    if pause.status_code == 200:
        assert pause.json()["state"] == "paused", pause.text
    else:
        assert pause.json()["code"] == "job_not_found", pause.text

    # Resume: 200 → "running" override; 404 → already done. (The test name
    # promised a resume step the old body never made — closed here.)
    resume = client.post("/api/copy/resume")
    assert resume.status_code in (200, 404), resume.text
    if resume.status_code == 200:
        assert resume.json()["state"] == "running", resume.text
    else:
        assert resume.json()["code"] == "job_not_found", resume.text

    # Abort with recycle: 200 → "terminating" override; 404 → already done.
    # NB: the original test attempted ``client.get("/api/copy/status")`` to
    # probe job state synchronously, but that endpoint returns a streaming
    # SSE response the sync TestClient blocks on indefinitely — so state is
    # asserted via the action endpoints' own JobStatus bodies, not /status.
    abort = client.post("/api/copy/abort", json={"recycle_partial": True})
    assert abort.status_code in (200, 404), abort.text
    if abort.status_code == 200:
        assert abort.json()["state"] == "terminating", abort.text
    else:
        assert abort.json()["code"] == "job_not_found", abort.text

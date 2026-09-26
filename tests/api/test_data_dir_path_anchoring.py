"""Regression tests for mame-curator-1105 (server data-dir path anchoring).

## Invariants

- **INV-1** A copy started through the API appends its activity-log
  events (`copy_started`, then `copy_finished` / `copy_aborted`) to
  `world.data_dir / "activity.jsonl"` — never to a `data/activity.jsonl`
  resolved against the server process's current working directory, and
  creates nothing under `<cwd>/data/`. *Test:*
  `test_copy_writes_activity_log_under_data_dir_not_cwd`.
- **INV-2** A copy through the API that recycles a replaced destination
  file (APPEND conflict strategy + a `REPLACE_AND_RECYCLE` append
  decision) moves the recycled file under `world.data_dir / "recycle"`
  — never under a cwd-relative `data/recycle`. *Test:*
  `test_copy_recycles_replaced_file_under_data_dir_not_cwd`.
- **INV-3** `PUT /api/media/sources/mobyGames/secret` writes the
  MobyGames key dotfile under `world.data_dir / "secrets"` — never
  under a cwd-relative `data/secrets`. *Test:*
  `test_save_mobygames_key_writes_under_data_dir_not_cwd`.

## Rationale

mame-curator-1105: `copy/runner.py::run_copy` passes
`log_path=Path("data/activity.jsonl")` (matching `copy/activity.py`'s
own default) on every `append_activity` call, `copy/recyclebin.py
::recycle_file` defaults `recycle_root=Path("data/recycle")`, and
`media/mobygames.py::mobygames_key_path` defaults
`secrets_dir=Path("data/secrets")`. All three resolve against the
*server process's current working directory*, not against the
config's data dir (`config_path.parent / "data"`, exposed as
`WorldState.data_dir` — see `api/state.py`). Observed 2026-09-26: a
server started with an absolute `--config` from `frontend/` wrote
`frontend/data/activity.jsonl` instead of the intended data dir.
`api/routes/activity.py` and `api/routes/curate.py` already read/write
via `world.data_dir / "activity.jsonl"`, and `JobManager`'s history
store is already `world.data_dir / "copy-history"` (`api/app.py`) — so
the natural anchor, and the one the eventual fix should move every
default onto, is `world.data_dir`.

## Scope

In scope: the three cwd-relative defaults named in the roadmap item,
exercised at the black-box HTTP seam (`POST /api/copy/start` for
activity + recycle, `PUT /api/media/sources/{name}/secret` for the
MobyGames key), with the test process's cwd `monkeypatch.chdir`'d to a
directory distinct from the config's, so a cwd-relative write is
filesystem-distinguishable from the correct one.

Out of scope: fixing the production defaults (this pass locks the
regression down *before* the fix lands — see `EXPECTED RUN DIRECTION`
below); the CLI's own invocations of these same functions (`cli/` is a
different seam and isn't named in the roadmap item); `media.snaps_dir`,
which already has an explicit config override exercised elsewhere
(the `configured_snaps_dir` fixture in `tests/api/conftest.py`).

## Regression history

Live at HEAD (`dacb6e1`, 2026-09-26) as roadmap item mame-curator-1105.
Not yet fixed as of this test's authoring — `copy/runner.py`,
`copy/activity.py`, `copy/recyclebin.py` and `media/mobygames.py` all
still default their log/root/secrets path to a project-relative
`Path("data/...")` rather than accepting or threading `world.data_dir`.

EXPECTED RUN DIRECTION: the defect is LIVE. Every test below must FAIL
at its assertion against the unfixed tree (never at fixture setup, an
import error, or a missing parameter) — see each test's own
``Why this exists`` line for which assertion is expected to fail and
why.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest


def _wait_for_report(client: Any, job_id: str, timeout: float = 5.0) -> dict[str, Any]:
    """Poll ``GET /api/copy/history/{job_id}/report`` until the job persists.

    ``JobManager._on_worker_done`` (``api/jobs.py``) writes
    ``report.json`` to ``world.data_dir / "copy-history" / job_id`` —
    a call site already anchored on ``world.data_dir`` and therefore
    unaffected by mame-curator-1105 — so polling it is a reliable,
    bug-independent way to know the worker thread has finished without
    resorting to the streaming SSE endpoint (which the sync
    ``TestClient`` cannot consume without blocking; see
    ``test_routes_copy.py``'s ``test_pause_resume_abort_copy`` note).
    """
    deadline = time.monotonic() + timeout
    last_status: int | None = None
    while time.monotonic() < deadline:
        response = client.get(f"/api/copy/history/{job_id}/report")
        last_status = response.status_code
        if response.status_code == 200:
            return dict(response.json())
        time.sleep(0.02)
    pytest.fail(
        f"copy job {job_id!r} did not finish within {timeout}s "
        f"(last GET /report status: {last_status})"
    )


def test_copy_writes_activity_log_under_data_dir_not_cwd(
    client: Any,
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """INV-1.

    Why this exists: mame-curator-1105 — ``run_copy``'s ``append_activity``
    calls all pass the cwd-relative default ``Path("data/activity.jsonl")``,
    so on the unfixed tree the log lands under the monkeypatched cwd
    (``<cwd>/data/activity.jsonl``) instead of ``world.data_dir /
    "activity.jsonl"``, and the first assertion below fails.
    """
    world = client.app.state.world
    other_cwd = tmp_path_factory.mktemp("cwd-t1")
    monkeypatch.chdir(other_cwd)

    start = client.post(
        "/api/copy/start",
        json={"selected_names": ["pacman"], "conflict_strategy": "OVERWRITE"},
    )
    assert start.status_code == 200, start.text
    job_id = start.json()["job_id"]
    report = _wait_for_report(client, job_id)

    expected_log = world.data_dir / "activity.jsonl"
    wrong_log = other_cwd / "data" / "activity.jsonl"

    assert expected_log.exists(), (
        f"expected activity log at {expected_log!s}, but it does not exist "
        f"(cwd was {other_cwd!s}; report={report!r})"
    )
    lines = [
        json.loads(line)
        for line in expected_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    event_types = {e["event_type"] for e in lines}
    assert "copy_started" in event_types, (
        f"expected a copy_started event in {expected_log!s}, saw {event_types!r}"
    )
    assert event_types & {"copy_finished", "copy_aborted"}, (
        f"expected a terminal copy event in {expected_log!s}, saw {event_types!r}"
    )
    assert not wrong_log.exists(), (
        f"activity log leaked to cwd-relative path {wrong_log!s} "
        f"(process cwd was {other_cwd!s}, expected only {expected_log!s})"
    )
    assert not (other_cwd / "data").exists(), (
        f"a cwd-relative data/ directory was created at {other_cwd / 'data'!s}"
    )


def test_copy_recycles_replaced_file_under_data_dir_not_cwd(
    client: Any,
    dest_dir: Path,
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """INV-2.

    Why this exists: mame-curator-1105 — ``run_copy``'s
    ``REPLACE_AND_RECYCLE`` branch calls ``recycle_file`` without a
    ``recycle_root`` argument, so it falls back to the cwd-relative
    default ``Path("data/recycle")``. On the unfixed tree the replaced
    zip lands under the monkeypatched cwd instead of ``world.data_dir /
    "recycle"``, and the "expected a recycled pacman.zip" assertion
    below fails.
    """
    world = client.app.state.world
    other_cwd = tmp_path_factory.mktemp("cwd-t2")

    old_pacman = dest_dir / "pacman.zip"
    old_pacman.write_bytes(b"OLD PACMAN CONTENT - pre-replace")

    monkeypatch.chdir(other_cwd)

    start = client.post(
        "/api/copy/start",
        json={
            "selected_names": ["pacmanf"],
            "conflict_strategy": "APPEND",
            "append_decisions": {"pacmanf": {"kind": "REPLACE_AND_RECYCLE", "replaces": "pacman"}},
        },
    )
    assert start.status_code == 200, start.text
    job_id = start.json()["job_id"]
    report = _wait_for_report(client, job_id)
    assert report["recycled"], f"expected a recycled entry, got report={report!r}"

    expected_recycle_root = world.data_dir / "recycle"
    wrong_recycle_root = other_cwd / "data" / "recycle"

    recycled_hits = (
        list(expected_recycle_root.rglob("pacman.zip")) if expected_recycle_root.exists() else []
    )
    assert recycled_hits, (
        f"expected a recycled pacman.zip under {expected_recycle_root!s}, "
        f"found none (cwd was {other_cwd!s}; report.recycled={report['recycled']!r})"
    )
    assert recycled_hits[0].read_bytes() == b"OLD PACMAN CONTENT - pre-replace", (
        f"file at {recycled_hits[0]!s} does not hold the pre-replace content"
    )
    assert not wrong_recycle_root.exists(), (
        f"recycled file leaked to cwd-relative path {wrong_recycle_root!s} "
        f"(process cwd was {other_cwd!s}, expected only {expected_recycle_root!s})"
    )


def test_save_mobygames_key_writes_under_data_dir_not_cwd(
    client: Any,
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """INV-3.

    Why this exists: mame-curator-1105 — the secret-write route
    (``api/routes/media.py::media_source_secret``) calls
    ``mobygames_key_path()`` with no argument, so it falls back to the
    cwd-relative default ``Path("data/secrets")``. On the unfixed tree
    the key dotfile lands under the monkeypatched cwd instead of
    ``world.data_dir / "secrets"``, and the "expected MobyGames key"
    assertion below fails.
    """
    world = client.app.state.world
    other_cwd = tmp_path_factory.mktemp("cwd-t3")
    monkeypatch.chdir(other_cwd)

    response = client.put(
        "/api/media/sources/mobyGames/secret",
        json={"secret": "abc123-secret"},
    )
    assert response.status_code == 204, response.text

    expected_keyfile = world.data_dir / "secrets" / "mobygames.key"
    wrong_keyfile = other_cwd / "data" / "secrets" / "mobygames.key"

    assert expected_keyfile.exists(), (
        f"expected MobyGames key at {expected_keyfile!s}, but it does not exist "
        f"(cwd was {other_cwd!s})"
    )
    assert expected_keyfile.read_text(encoding="utf-8") == "abc123-secret"
    assert not wrong_keyfile.exists(), (
        f"MobyGames key leaked to cwd-relative path {wrong_keyfile!s} "
        f"(process cwd was {other_cwd!s}, expected only {expected_keyfile!s})"
    )

    # Read side: the MobyGames source must find the saved key from the same
    # data dir, so the readiness endpoint reports it enabled even though the
    # process cwd holds no key. Clear the env-var route so only the file counts.
    monkeypatch.delenv("MOBYGAMES_API_KEY", raising=False)
    rows = client.get("/api/media/sources").json()["sources"]
    moby = next(r for r in rows if r["name"] == "mobyGames")
    assert moby["enabled"], f"mobyGames not enabled after saving its key: {moby}"

"""mame-curator-1144 — the stream must report a pause no progress tick will.

``run_copy`` holds at ``wait_if_paused()`` before each file. A pause landing
before the worker's first tick, or after a file's last one, blocks the worker
with no tick left to report it, so the client must learn from the manager.

The gate holds the worker before ``run_copy`` starts, which makes "the pause
lands before any tick" deterministic. ``run_copy`` itself is the real one.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest

from mame_curator.api import jobs as jobs_module
from mame_curator.api.jobs import JobManager
from mame_curator.copy import run_copy


@pytest.fixture
def gate(monkeypatch: pytest.MonkeyPatch) -> threading.Event:
    """Holds the copy worker until set, so no tick can happen before a test acts."""
    released = threading.Event()

    def gated_run_copy(*args: Any, **kwargs: Any) -> Any:
        released.wait(timeout=10)
        return run_copy(*args, **kwargs)

    monkeypatch.setattr(jobs_module, "run_copy", gated_run_copy)
    return released


async def _started_client(app: Any) -> AsyncIterator[httpx.AsyncClient]:
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            start = await client.post(
                "/api/copy/start",
                json={"selected_names": ["pacman"], "conflict_strategy": "OVERWRITE"},
            )
            assert start.status_code == 200, start.text
            yield client


def _control_events(jobs: JobManager) -> list[str]:
    job = jobs.replayable
    assert job is not None
    return [e.event for e in job.lifecycle_history if e.event in ("paused", "resumed")]


async def _wait_until_retired(jobs: JobManager) -> None:
    for _ in range(500):
        if jobs.current is None:
            return
        await asyncio.sleep(0.01)
    raise AssertionError("copy job did not finish in time")


def test_pause_before_any_tick_reaches_the_stream(app: Any, gate: threading.Event) -> None:
    """Settles the review's jobs.py claim: the worker holds and the stream says so."""

    async def _drive() -> None:
        async for client in _started_client(app):
            pause = await client.post("/api/copy/pause")
            assert pause.status_code == 200, pause.text
            gate.set()

            jobs: JobManager = app.state.job
            job = jobs.current
            assert job is not None
            await asyncio.sleep(0.2)

            # Really held at the boundary: alive, and nothing has started.
            assert job.thread.is_alive()
            seen = [e.event for e in job.lifecycle_history]
            assert "file_started" not in seen
            assert _control_events(jobs) == ["paused"], (
                f"worker is held with no paused event, so the client has no Resume: {seen}"
            )

            resume = await client.post("/api/copy/resume")
            assert resume.status_code == 200, resume.text
            await _wait_until_retired(jobs)
            assert _control_events(jobs) == ["paused", "resumed"]

    asyncio.run(_drive())


def test_resume_before_any_tick_reaches_the_stream(app: Any, gate: threading.Event) -> None:
    """A Resume with no tick to follow it must not leave the client on Paused."""

    async def _drive() -> None:
        async for client in _started_client(app):
            await client.post("/api/copy/pause")
            await client.post("/api/copy/resume")
            jobs: JobManager = app.state.job
            assert _control_events(jobs) == ["paused", "resumed"]
            gate.set()
            await _wait_until_retired(jobs)

    asyncio.run(_drive())


def test_repeated_pause_and_resume_report_one_transition_each(
    app: Any, gate: threading.Event
) -> None:
    async def _drive() -> None:
        async for client in _started_client(app):
            await client.post("/api/copy/resume")
            jobs: JobManager = app.state.job
            assert _control_events(jobs) == [], "a resume of a running copy is no transition"

            await client.post("/api/copy/pause")
            await client.post("/api/copy/pause")
            assert _control_events(jobs) == ["paused"]

            await client.post("/api/copy/resume")
            await client.post("/api/copy/resume")
            assert _control_events(jobs) == ["paused", "resumed"]
            gate.set()
            await _wait_until_retired(jobs)

    asyncio.run(_drive())


def test_pause_after_abort_reports_nothing(app: Any, gate: threading.Event) -> None:
    """A cancel is sticky: the controller refuses the pause, so no event may claim it."""

    async def _drive() -> None:
        async for client in _started_client(app):
            await client.post("/api/copy/abort", json={"recycle_partial": False})
            await client.post("/api/copy/pause")
            jobs: JobManager = app.state.job
            assert _control_events(jobs) == []
            gate.set()
            await _wait_until_retired(jobs)

    asyncio.run(_drive())

"""mame-curator-1145 review, Group 4, and mame-curator-1159: what JobManager tells a client."""

from __future__ import annotations

import asyncio
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from mame_curator.api import jobs as jobs_module
from mame_curator.api.jobs import Job, JobManager
from mame_curator.api.schemas import JobEvent
from mame_curator.copy import ConflictStrategy, CopyController, CopyPlan

# A hang must end the test, not the suite.
_NO_HANG_SECONDS = 20
_PAST_THE_QUEUE = jobs_module._QUEUE_SIZE + 500


def _job(tmp_path: Path, *, state: Any = "running") -> Job:
    plan = CopyPlan(
        winners=(),
        machines={},
        bios_chain={},
        chd_required=frozenset(),
        source_dir=tmp_path,
        dest_dir=tmp_path,
        conflict_strategy=ConflictStrategy.OVERWRITE,
        append_decisions={},
    )
    return Job(
        id="20260101T000000Z-00000000",
        plan=plan,
        started_at=datetime.now(UTC),
        controller=CopyController(),
        thread=threading.Thread(target=lambda: None),
        files_total=0,
        bytes_total=0,
        state=state,
    )


def _stored(count: int) -> list[JobEvent]:
    start = datetime.now(UTC)
    return [
        JobEvent(event="file_finished", payload={"n": i}, ts=start + timedelta(microseconds=i))
        for i in range(count)
    ]


def _manager(tmp_path: Path, job: Job, *, live: bool) -> JobManager:
    manager = JobManager(tmp_path, loop=asyncio.get_running_loop())
    if live:
        manager._current = job
    else:
        manager._last = job
    return manager


@pytest.mark.asyncio
async def test_replay_of_a_finished_job_past_the_queue_size_ends(tmp_path: Path) -> None:
    job = _job(tmp_path, state="finished")
    job.lifecycle_history = _stored(_PAST_THE_QUEUE)
    manager = _manager(tmp_path, job, live=False)

    async def collect() -> list[JobEvent]:
        return [ev async for ev in manager.events()]

    seen = await asyncio.wait_for(collect(), timeout=_NO_HANG_SECONDS)

    assert [ev.payload["n"] for ev in seen] == list(range(_PAST_THE_QUEUE))


@pytest.mark.asyncio
async def test_replay_of_a_live_job_past_the_queue_size_goes_on_to_live_events(
    tmp_path: Path,
) -> None:
    job = _job(tmp_path)
    job.lifecycle_history = _stored(_PAST_THE_QUEUE)
    manager = _manager(tmp_path, job, live=True)
    seen: list[JobEvent] = []
    replayed = asyncio.Event()

    async def collect() -> None:
        async for ev in manager.events():
            seen.append(ev)
            if len(seen) == _PAST_THE_QUEUE:
                replayed.set()

    task = asyncio.create_task(collect())
    await asyncio.wait_for(replayed.wait(), timeout=_NO_HANG_SECONDS)
    live = JobEvent(event="file_finished", payload={"n": "live"}, ts=datetime.now(UTC))
    manager._emit(live)
    manager._emit(JobEvent(event="job_finished", payload={}, ts=datetime.now(UTC)))
    await asyncio.wait_for(task, timeout=_NO_HANG_SECONDS)

    assert [ev.event for ev in seen[-2:]] == ["file_finished", "job_finished"]
    assert seen[-2].payload["n"] == "live"
    assert len(seen) == _PAST_THE_QUEUE + 2
    assert job.subscribers == []


@pytest.mark.asyncio
async def test_a_stored_terminal_event_ends_the_replay_of_a_live_job(tmp_path: Path) -> None:
    """The job finished after subscribing only in history: the stream must not wait on."""
    job = _job(tmp_path)
    job.lifecycle_history = [
        *_stored(3),
        JobEvent(event="job_aborted", payload={}, ts=datetime.now(UTC) + timedelta(seconds=1)),
    ]
    manager = _manager(tmp_path, job, live=True)

    async def collect() -> list[JobEvent]:
        return [ev async for ev in manager.events()]

    seen = await asyncio.wait_for(collect(), timeout=_NO_HANG_SECONDS)

    assert seen[-1].event == "job_aborted"
    assert job.subscribers == []


@pytest.mark.asyncio
async def test_a_client_leaving_during_replay_is_unsubscribed(tmp_path: Path) -> None:
    job = _job(tmp_path)
    job.lifecycle_history = _stored(5)
    manager = _manager(tmp_path, job, live=True)

    stream = manager.events()
    await asyncio.wait_for(anext(stream), timeout=_NO_HANG_SECONDS)
    assert len(job.subscribers) == 1
    await stream.aclose()  # type: ignore[attr-defined]  # an async generator, typed as AsyncIterator.

    assert job.subscribers == []


# --- the replies (mame-curator-1159) ---------------------------------------------


@pytest.mark.asyncio
async def test_pause_and_resume_report_the_state_they_reached(tmp_path: Path) -> None:
    manager = _manager(tmp_path, _job(tmp_path), live=True)

    assert (await manager.pause()).state == "paused"
    assert (await manager.resume()).state == "running"


@pytest.mark.asyncio
async def test_pause_and_resume_after_a_cancel_say_terminating(tmp_path: Path) -> None:
    job = _job(tmp_path)
    manager = _manager(tmp_path, job, live=True)
    job.controller.cancel(recycle_partial=False)

    assert (await manager.pause()).state == "terminating"
    assert (await manager.resume()).state == "terminating"


# --- bytes_done -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_bytes_done_counts_the_whole_job(tmp_path: Path) -> None:
    job = _job(tmp_path)
    manager = _manager(tmp_path, job, live=True)
    now = datetime.now(UTC)

    def tick(short: str, done: int, total: int) -> None:
        payload = {"short_name": short, "bytes_done": done, "bytes_total": total}
        manager._emit(JobEvent(event="file_progress", payload=payload, ts=now))

    tick("a", 500, 1000)
    tick("a", 1000, 1000)
    manager._emit(JobEvent(event="file_finished", payload={"bytes": 1000}, ts=now))
    tick("b", 200, 300)

    assert job.bytes_done == 1200

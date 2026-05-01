"""JobManager — singleton owning the in-flight copy job + SSE event stream.

Bridges sync ``run_copy`` → async event consumers via a worker thread plus
a ``_ProgressSynthesizer`` that schedules events on the FastAPI event loop
through ``loop.call_soon_threadsafe``. See ``docs/specs/P04.md`` §
JobManager + SSE contract.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import secrets
import threading
from asyncio import AbstractEventLoop
from collections import deque
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from mame_curator._atomic import atomic_write_bytes
from mame_curator.api.errors import (
    JobAlreadyRunningError,
    JobNotFoundError,
    PlaylistConflictCancelledError,
)
from mame_curator.api.schemas import JobEvent, JobStatus
from mame_curator.copy import (
    ConflictStrategy,
    CopyController,
    CopyControlState,
    CopyPlan,
    CopyReport,
    CopyReportStatus,
    resolve_bios_dependencies,
    run_copy,
)

if TYPE_CHECKING:
    from mame_curator.api.state import WorldState

logger = logging.getLogger(__name__)

_QUEUE_SIZE = 4096
_TERMINAL_EVENTS = ("job_finished", "job_aborted")
# FP09 B3 + Cluster R H1: history is split across two stores so that
# subscriber replay never loses a lifecycle event (job_started, file_started,
# file_finished, paused, resumed, bios_warning, terminal). file_progress
# events are bounded; lifecycle events are unbounded but small (~3N+5 for an
# N-file copy ≈ 30k events / 2 MB on a 10k-file run). Replay merges the two
# stores by timestamp.
_PROGRESS_CAP = 200_000


def _new_job_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ-") + secrets.token_hex(4)


@dataclass
class Job:
    """In-flight copy job — singleton on ``app.state.job.current``."""

    id: str
    plan: CopyPlan
    started_at: datetime
    controller: CopyController
    thread: threading.Thread
    files_total: int
    bytes_total: int
    files_done: int = 0
    bytes_done: int = 0
    state: str = "running"
    # FP09 Cluster R H1: split lifecycle vs progress storage. Lifecycle is
    # unbounded but small; progress is bounded with drop-oldest. See
    # `_replay_history()` for the merge.
    lifecycle_history: list[JobEvent] = field(default_factory=list)
    progress_history: deque[JobEvent] = field(default_factory=lambda: deque(maxlen=_PROGRESS_CAP))
    subscribers: list[asyncio.Queue[JobEvent | None]] = field(default_factory=list)


class _ProgressSynthesizer:
    """Worker-thread on_progress callback; converts ticks into JobEvents."""

    def __init__(
        self,
        loop: AbstractEventLoop,
        sink: JobManager,
        controller: CopyController,
    ) -> None:
        """Build a synthesizer bound to ``loop`` for thread-safe event dispatch."""
        self._loop = loop
        self._sink = sink
        self._controller = controller
        self._seen: set[str] = set()
        self._was_paused = False

    def __call__(self, short: str, bytes_done: int, bytes_total: int) -> None:
        ts = datetime.now(UTC)
        if short not in self._seen:
            self._seen.add(short)
            self._dispatch(
                JobEvent(
                    event="file_started",
                    payload={"short_name": short, "bytes_total": bytes_total},
                    ts=ts,
                )
            )
        self._dispatch(
            JobEvent(
                event="file_progress",
                payload={
                    "short_name": short,
                    "bytes_done": bytes_done,
                    "bytes_total": bytes_total,
                },
                ts=ts,
            )
        )
        if bytes_done == bytes_total:
            self._dispatch(
                JobEvent(
                    event="file_finished",
                    payload={"short_name": short, "bytes": bytes_total},
                    ts=ts,
                )
            )

        is_paused = self._controller.state == CopyControlState.PAUSED
        if is_paused != self._was_paused:
            self._dispatch(
                JobEvent(
                    event="paused" if is_paused else "resumed",
                    payload={"at": ts.isoformat()},
                    ts=ts,
                )
            )
            self._was_paused = is_paused

    def _dispatch(self, event: JobEvent) -> None:
        self._loop.call_soon_threadsafe(self._sink._emit, event)


class JobManager:
    """Singleton: owns ``app.state.job``."""

    def __init__(self, history_dir: Path) -> None:
        """Initialize the manager. ``history_dir`` is where job reports persist."""
        self._history_dir = history_dir
        self._lock = asyncio.Lock()
        self._current: Job | None = None
        self._loop: AbstractEventLoop | None = None

    @property
    def current(self) -> Job | None:
        """The in-flight Job, or None when idle."""
        return self._current

    async def start(self, plan: CopyPlan, world: WorldState) -> Job:
        """Spawn the worker thread + initial events. Raises if a job is running."""
        async with self._lock:
            if self._current is not None:
                raise JobAlreadyRunningError("a copy job is already running")
            self._loop = asyncio.get_running_loop()

            # Resolve BIOS deps + replay warnings before the worker thread starts.
            bios_set, bios_warnings = resolve_bios_dependencies(
                plan.winners, dict(world.bios_chain)
            )

            files_total = len(plan.winners) + len(bios_set)
            bytes_total = _sum_input_sizes(plan, bios_set)

            controller = CopyController()
            job_id = _new_job_id()
            started_at = datetime.now(UTC)

            synth = _ProgressSynthesizer(self._loop, self, controller)

            def worker() -> None:
                try:
                    report = run_copy(plan, controller=controller, on_progress=synth)
                except Exception as exc:  # pragma: no cover - defense in depth
                    logger.exception("copy worker crashed")
                    self._loop and self._loop.call_soon_threadsafe(self._on_worker_error, str(exc))
                    return
                if self._loop is None:
                    return
                self._loop.call_soon_threadsafe(self._on_worker_done, report)

            thread = threading.Thread(target=worker, name=f"copy-{job_id}", daemon=True)
            job = Job(
                id=job_id,
                plan=plan,
                started_at=started_at,
                controller=controller,
                thread=thread,
                files_total=files_total,
                bytes_total=bytes_total,
            )
            self._current = job

            # Emit initial events on the loop thread before the worker spawns.
            self._emit(
                JobEvent(
                    event="job_started",
                    payload={
                        "job_id": job_id,
                        "total_files": files_total,
                        "total_bytes": bytes_total,
                        "started_at": started_at.isoformat(),
                    },
                    ts=started_at,
                )
            )
            for warn in bios_warnings:
                self._emit(
                    JobEvent(
                        event="bios_warning",
                        payload={"name": warn.name, "kind": warn.kind},
                        ts=started_at,
                    )
                )

            thread.start()
            return job

    async def pause(self) -> JobStatus:
        """Pause the in-flight job at the next file boundary."""
        job = self._require_job()
        job.controller.pause()
        await asyncio.sleep(0.05)
        return self._status(job, override_state="paused")

    async def resume(self) -> JobStatus:
        """Resume a paused job."""
        job = self._require_job()
        job.controller.resume()
        await asyncio.sleep(0.05)
        return self._status(job, override_state="running")

    async def abort(self, *, recycle_partial: bool) -> JobStatus:
        """Cancel the in-flight job, optionally recycling already-copied files."""
        job = self._require_job()
        job.controller.cancel(recycle_partial=recycle_partial)
        await asyncio.sleep(0.05)
        return self._status(job, override_state="terminating")

    def status(self) -> JobStatus:
        """Return the current ``JobStatus`` snapshot."""
        job = self._require_job()
        return self._status(job)

    def events(self) -> AsyncIterator[JobEvent]:
        """Subscribe; replay history first, then live events until terminal."""
        return self._events_iterator()

    # ------------------------------------------------------------------ internals

    def _require_job(self) -> Job:
        if self._current is None:
            raise JobNotFoundError("no active copy job")
        return self._current

    def _status(self, job: Job, *, override_state: str | None = None) -> JobStatus:
        return JobStatus(
            job_id=job.id,
            state=override_state or job.state,  # type: ignore[arg-type]
            started_at=job.started_at,
            files_done=job.files_done,
            files_total=job.files_total,
            bytes_done=job.bytes_done,
            bytes_total=job.bytes_total,
        )

    def _emit(self, event: JobEvent) -> None:
        """Loop-thread: append to history, fan out to subscribers."""
        if self._current is None:
            return
        # FP09 Cluster R H1: lifecycle goes to the unbounded list so a
        # subscriber that connects late always sees `job_started` etc.;
        # `file_progress` goes to the bounded deque (drop-oldest under
        # pressure).
        if event.event == "file_progress":
            self._current.progress_history.append(event)
            payload = event.payload
            self._current.bytes_done = max(
                self._current.bytes_done, int(payload.get("bytes_done", 0))
            )
        else:
            self._current.lifecycle_history.append(event)
            if event.event == "file_finished":
                self._current.files_done += 1
        for q in list(self._current.subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                if event.event == "file_progress":
                    continue
                with contextlib.suppress(asyncio.QueueEmpty):
                    q.get_nowait()
                with contextlib.suppress(asyncio.QueueFull):
                    q.put_nowait(event)

    def _on_worker_done(self, report: CopyReport) -> None:
        job = self._current
        if job is None:
            return
        # Persist report.
        report_dir = self._history_dir / job.id
        try:
            report_dir.mkdir(parents=True, exist_ok=True)
            atomic_write_bytes(
                report_dir / "report.json",
                report.model_dump_json(indent=2).encode("utf-8"),
            )
        except OSError:
            logger.exception("failed to persist copy report for job %r", job.id)

        terminal: JobEvent
        if report.status in (CopyReportStatus.OK, CopyReportStatus.PARTIAL_FAILURE):
            job.state = "finished"
            terminal = JobEvent(
                event="job_finished",
                payload={
                    "job_id": job.id,
                    "status": report.status.value,
                    "report_path": str(report_dir / "report.json"),
                },
                ts=datetime.now(UTC),
            )
        else:
            job.state = "aborted"
            recycled = len(report.recycled)
            terminal = JobEvent(
                event="job_aborted",
                payload={
                    "job_id": job.id,
                    "reason": report.status.value,
                    "recycled_count": recycled,
                },
                ts=datetime.now(UTC),
            )
            if report.status == CopyReportStatus.CANCELLED_PLAYLIST_CONFLICT:
                # Pre-emit handler raises; this branch only fires if start()
                # routed past the synchronous check.
                pass
        self._emit(terminal)
        self._close_subscribers()
        self._current = None

    def _on_worker_error(self, message: str) -> None:
        job = self._current
        if job is None:
            return
        job.state = "aborted"
        # FP09 A1: `message` flows from `str(exc)` of the worker exception;
        # repr-quote so a control byte in the exception message can't break
        # the FP06-FP08 single-line `detail` invariant when the SSE consumer
        # ultimately renders this payload.
        ev = JobEvent(
            event="job_aborted",
            payload={"job_id": job.id, "reason": repr(message), "recycled_count": 0},
            ts=datetime.now(UTC),
        )
        self._emit(ev)
        self._close_subscribers()
        self._current = None

    def _close_subscribers(self) -> None:
        if self._current is None:
            return
        for q in list(self._current.subscribers):
            with contextlib.suppress(asyncio.QueueFull):
                q.put_nowait(None)

    async def _events_iterator(self) -> AsyncIterator[JobEvent]:
        if self._current is None:
            raise JobNotFoundError("no active copy job")
        job = self._current
        q: asyncio.Queue[JobEvent | None] = asyncio.Queue(maxsize=_QUEUE_SIZE)
        # Replay history (lifecycle + progress merged by ts), then register so
        # live events queue afterwards. Cluster R H1: lifecycle is unbounded;
        # progress is bounded and may have evicted oldest ticks under pressure.
        import heapq

        merged = heapq.merge(job.lifecycle_history, job.progress_history, key=lambda ev: ev.ts)
        for ev in merged:
            await q.put(ev)
        # If the job already terminated while we were replaying, push sentinel.
        if job.state in ("finished", "aborted"):
            await q.put(None)
        else:
            job.subscribers.append(q)
        try:
            while True:
                next_ev: JobEvent | None = await q.get()
                if next_ev is None:
                    return
                yield next_ev
                if next_ev.event in _TERMINAL_EVENTS:
                    return
        finally:
            with contextlib.suppress(ValueError):
                if job.subscribers and q in job.subscribers:
                    job.subscribers.remove(q)


def _sum_input_sizes(plan: CopyPlan, bios_set: frozenset[str]) -> int:
    total = 0
    for short in (*plan.winners, *bios_set):
        src = plan.source_dir / f"{short}.zip"
        try:
            total += src.stat().st_size
        except OSError:
            continue
    return total


def check_playlist_conflict(plan: CopyPlan) -> None:
    """Pre-flight: raise PlaylistConflictCancelledError if CANCEL would abort."""
    if plan.conflict_strategy is not ConflictStrategy.CANCEL:
        return
    if not (plan.dest_dir / "mame.lpl").exists():
        return
    # Only raise if not idempotent — let run_copy handle the no-op case.
    all_present = all((plan.dest_dir / f"{w}.zip").exists() for w in plan.winners)
    if not all_present:
        raise PlaylistConflictCancelledError(
            f"existing playlist at {str(plan.dest_dir)!r}; "
            "use APPEND or OVERWRITE conflict strategy"
        )

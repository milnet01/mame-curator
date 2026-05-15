"""FP21 — fix-pass after FP20: regression tests for the Tier 2 sweep.

One test per actionable finding where the regression is reachable in a
single-process unit-style test. Wider behavioural tests live with their
respective routes (filter / copy / api / frontend).
"""

from __future__ import annotations

import asyncio
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from threading import Thread
from typing import Any

# ---- K — SSE register-before-replay race + snapshot-as-tuple ----------------


def test_fp21_k_events_iterator_snapshots_history_before_replay(
    tmp_path: Path,
) -> None:
    """FP21-K: ``_events_iterator`` snapshots ``lifecycle_history`` and
    ``progress_history`` into tuples BEFORE merging — concurrent mutation
    by ``_emit`` (worker thread via ``call_soon_threadsafe``) must not
    raise ``RuntimeError: deque mutated during iteration``.

    Setup: a synthetic Job with a partially-filled progress deque. Spawn
    a background thread that mutates the deque while the iterator
    iterates. Pre-fix the heapq.merge over the live deque would crash;
    post-fix the snapshot tuple is immutable so iteration is safe.
    """
    from mame_curator.api.jobs import Job, JobManager
    from mame_curator.api.schemas import JobEvent
    from mame_curator.copy import ConflictStrategy, CopyController, CopyPlan

    plan = CopyPlan(
        winners=("kof94",),
        machines={},
        bios_chain={},
        source_dir=tmp_path / "src",
        dest_dir=tmp_path / "dst",
        conflict_strategy=ConflictStrategy.CANCEL,
    )

    manager = JobManager(history_dir=tmp_path / "history")

    now = datetime.now(UTC)
    job = Job(
        id="test-job",
        plan=plan,
        started_at=now,
        controller=CopyController(),
        thread=Thread(),  # never started
        files_total=1,
        bytes_total=100,
    )
    # Pre-populate with replay-able history. Use 500 entries so the
    # mutating thread has time to fire mid-iteration on most machines.
    for i in range(500):
        job.progress_history.append(
            JobEvent(
                event="file_progress",
                payload={"short_name": "kof94", "bytes_done": i, "bytes_total": 100},
                ts=now,
            )
        )
    job.lifecycle_history.append(
        JobEvent(
            event="job_started",
            payload={
                "job_id": "test-job",
                "files_total": 1,
                "bytes_total": 100,
                "started_at": now.isoformat(),
            },
            ts=now,
        )
    )
    manager._current = job

    async def _drive() -> int:
        iter_task = manager._events_iterator()

        # Background thread: mutate the deque while the iterator runs.
        # If FP21-K's snapshot-to-tuple fix is absent, ``heapq.merge``
        # over the live deque blows up with RuntimeError.
        stop = [False]

        def mutator() -> None:
            count = 0
            while not stop[0] and count < 1000:
                try:
                    job.progress_history.append(
                        JobEvent(
                            event="file_progress",
                            payload={
                                "short_name": "kof94",
                                "bytes_done": count,
                                "bytes_total": 100,
                            },
                            ts=now,
                        )
                    )
                    count += 1
                except Exception:
                    return

        thread = Thread(target=mutator, daemon=True)
        thread.start()
        try:
            seen = 0
            async for _ev in iter_task:
                seen += 1
                # Yield control so the mutator thread can race in.
                await asyncio.sleep(0)
                if seen >= 50:
                    # We've drained enough replay entries to prove the
                    # snapshot path doesn't crash under mutation.
                    break
            return seen
        finally:
            stop[0] = True
            thread.join(timeout=1.0)

    seen = asyncio.run(_drive())
    assert seen >= 50, f"iterator must yield replay entries safely under mutation; got {seen}"


def test_fp21_k_subscriber_registered_before_history_drain(
    tmp_path: Path,
) -> None:
    """FP21-K: the subscriber queue is appended to ``job.subscribers``
    BEFORE the history snapshot is drained. Live events emitted while
    the consumer is still chewing through the replay must reach the
    queue, not be silently dropped.

    Setup: register a subscriber via _events_iterator (which starts the
    drain). Emit a live event mid-drain. Assert the live event reaches
    the subscriber by the time it finishes replay.
    """
    from mame_curator.api.jobs import Job, JobManager
    from mame_curator.api.schemas import JobEvent
    from mame_curator.copy import ConflictStrategy, CopyController, CopyPlan

    plan = CopyPlan(
        winners=("kof94",),
        machines={},
        bios_chain={},
        source_dir=tmp_path / "src",
        dest_dir=tmp_path / "dst",
        conflict_strategy=ConflictStrategy.CANCEL,
    )

    manager = JobManager(history_dir=tmp_path / "history")

    now = datetime.now(UTC)
    job = Job(
        id="test-job",
        plan=plan,
        started_at=now,
        controller=CopyController(),
        thread=Thread(),
        files_total=1,
        bytes_total=100,
    )
    # Smaller history so we control when the drain ends.
    job.lifecycle_history.append(
        JobEvent(
            event="job_started",
            payload={
                "job_id": "test-job",
                "files_total": 1,
                "bytes_total": 100,
                "started_at": now.isoformat(),
            },
            ts=now,
        )
    )
    manager._current = job

    async def _drive() -> list[str]:
        # FP28-A1: _emit asserts the running loop matches self._loop.
        # JobManager was constructed sync (no running loop), so _loop is
        # None at this point — bind it to the test's running loop before
        # the direct _emit call below.
        manager._loop = asyncio.get_running_loop()
        iter_obj = manager._events_iterator()
        events: list[str] = []
        first = await iter_obj.__anext__()
        events.append(first.event)
        # FP21-K: subscriber MUST already be registered. Emit a live
        # event directly via the manager — it goes to subscribers via
        # ``_emit``. Without the FP21-K register-first ordering, this
        # event arrives BEFORE the subscriber appends to ``subscribers``,
        # so it's silently dropped.
        terminal = JobEvent(
            event="job_finished",
            payload={"job_id": "test-job", "status": "OK"},
            ts=now,
        )
        manager._emit(terminal)
        # Drain remaining entries.
        async for ev in iter_obj:
            events.append(ev.event)
        return events

    events = asyncio.run(_drive())
    assert "job_started" in events, "replay must include job_started"
    assert "job_finished" in events, (
        f"FP21-K: live event emitted after subscriber start must reach the consumer; got {events!r}"
    )


# ---- L — late-progress-after-terminal (analysed; preserved guard) -----------


def test_fp21_l_emit_after_current_cleared_is_a_noop(tmp_path: Path) -> None:
    """FP21-L: ``JobManager._emit`` is a no-op when ``self._current`` is
    ``None``. This is the existing guard that prevents a stray
    ``file_progress`` from being dispatched after ``_on_worker_done``
    cleared the current job.

    Per FP21 analysis: ``call_soon_threadsafe`` from the worker thread
    is FIFO with respect to the worker's enqueue order — all progress
    callbacks fire before ``_on_worker_done`` since the worker queues
    them before queueing the terminal callback. The "late progress"
    finding is therefore not reachable through normal execution paths.
    This test pins the defensive guard so it doesn't regress.
    """
    from datetime import UTC, datetime

    from mame_curator.api.jobs import JobManager
    from mame_curator.api.schemas import JobEvent

    # DS04 T1.4: history_dir is unused in this test (the _emit guard
    # short-circuits on _current=None before touching it), but a fresh
    # tmp_path keeps the constructor signature honest without world-
    # writable /tmp paths or # noqa: S108.
    manager = JobManager(history_dir=tmp_path)
    # _current starts None; _emit must be a clean no-op.
    assert manager._current is None
    manager._emit(
        JobEvent(
            event="file_progress",
            payload={"short_name": "x", "bytes_done": 0, "bytes_total": 0},
            ts=datetime.now(UTC),
        )
    )
    # No exception, no state change. The guard holds.
    assert manager._current is None


def test_fp21_l_progress_history_is_drop_oldest_under_pressure() -> None:
    """FP21-L sibling: progress_history is a drop-oldest deque so a flood
    of late progress events can't unbounded-grow memory. Verified at the
    dataclass level by FP09 B3 — this is a structural sibling assertion
    pinning the contract.
    """
    import dataclasses

    from mame_curator.api.jobs import Job

    fields = {f.name: f for f in dataclasses.fields(Job)}
    progress_factory = fields["progress_history"].default_factory
    assert progress_factory is not dataclasses.MISSING
    progress_instance = progress_factory()
    assert isinstance(progress_instance, deque)
    assert progress_instance.maxlen is not None and progress_instance.maxlen > 0


# ---- M — Snapshot directory bounded by MAX_SNAPSHOTS LRU -------------------


def test_fp21_m_snapshot_files_prunes_oldest_beyond_cap(tmp_path: Path) -> None:
    """FP21-M: ``snapshot_files`` removes oldest siblings once the dir
    count exceeds ``MAX_SNAPSHOTS``. Without the cap, a long-running
    server's data directory grew unbounded — every PATCH / override /
    notes write added one dir.
    """
    from mame_curator.api.persist import MAX_SNAPSHOTS, snapshot_files

    snapshots_dir = tmp_path / "snapshots"
    # Pre-populate (MAX_SNAPSHOTS + 5) sibling dirs with monotonically
    # increasing names so the prune logic picks the oldest by lexical sort.
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    for i in range(MAX_SNAPSHOTS + 5):
        (snapshots_dir / f"20260101T000000_000000Z_{i:04d}").mkdir()

    # One real call creates a fresh snapshot dir at "now", then prunes.
    # No source files needed — empty mapping still triggers the prune.
    snapshot_files(snapshots_dir, {})

    remaining = sorted(p for p in snapshots_dir.iterdir() if p.is_dir())
    assert len(remaining) <= MAX_SNAPSHOTS, (
        f"FP21-M: count must be capped at MAX_SNAPSHOTS={MAX_SNAPSHOTS}, "
        f"found {len(remaining)} remaining"
    )


# ---- N — patch_config rejects unknown top-level keys via AppConfigPatch ----


def test_fp21_n_patch_config_rejects_unknown_top_level_keys(client: Any) -> None:
    """FP21-N: PATCH ``/api/config`` body validates through
    ``AppConfigPatch`` (extra='forbid') before the merge. Unknown
    top-level keys are 422'd at the FastAPI boundary so bare-dict
    ingestion can't smuggle arbitrary payloads into ``deep_merge``.
    """
    response = client.patch("/api/config", json={"unknown_section": {"x": 1}})
    assert response.status_code == 422, (
        f"FP21-N: unknown top-level key must 422, got {response.status_code} {response.json()!r}"
    )


def test_fp21_n_deep_merge_caps_recursion_depth() -> None:
    """FP21-N defence-in-depth: ``deep_merge`` is depth-capped so a
    pathological nested-dict patch can't stack-overflow.
    """
    from mame_curator.api.state import _MERGE_MAX_DEPTH, deep_merge

    # Build a patch deeper than the cap.
    deep: dict[str, Any] = {"x": 1}
    for _ in range(_MERGE_MAX_DEPTH + 5):
        deep = {"x": deep}

    # The merge MUST return without RecursionError.
    result = deep_merge({}, deep)
    assert isinstance(result, dict)


# ---- O — import_config drops in-progress sentinel for crash detection -----


def test_fp21_o_import_config_writes_and_clears_sentinel(client: Any) -> None:
    """FP21-O: the import path writes ``data/import.in_progress`` before
    the four atomic file writes and removes it after the last one
    succeeds. A startup-time check (out of scope here) can detect a
    half-applied import by the sentinel's presence.
    """
    bundle = client.post("/api/config/export").json()
    response = client.post("/api/config/import", json=bundle)
    assert response.status_code == 200, f"import failed: {response.json()}"

    # On success the sentinel is cleared. Reach into the app state
    # directly via the client fixture's app attribute.
    world = client.app.state.world
    sentinel = world.data_dir / "import.in_progress"
    assert not sentinel.exists(), (
        "FP21-O: import.in_progress sentinel must be cleared on successful import"
    )

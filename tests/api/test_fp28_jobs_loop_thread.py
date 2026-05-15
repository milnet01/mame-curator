"""FP28 A1 — `JobManager._emit` must raise when called off the manager's loop thread.

`api/jobs.py:282` `_emit` mutates `self._current.lifecycle_history` (L297) and
iterates `self._current.subscribers` (L300) without any synchronisation. The
docstring at L283 pins a "Loop-thread" invariant but there is no runtime
check; a non-loop-thread caller would silently corrupt state.

A1 adds a loop-thread comparator at the top of `_emit`:

    running_loop = asyncio.get_running_loop()
    if running_loop is not self._loop:
        raise RuntimeError("JobManager._emit must run on the manager's loop thread")

The comparator uses `raise RuntimeError(...)` not `assert` so `python -O`
cannot strip it. `self._loop` already exists as an attribute at
`api/jobs.py:154` (initialised to `None` in `__init__`, assigned inside
`start()` at L166); A1's fix hoists the assignment up to `__init__` so the
comparator has a non-None target before any `_emit` call.

Pre-fix: no comparator → no RuntimeError → ``pytest.raises(RuntimeError)`` fails.
Post-fix: comparator raises (or `asyncio.get_running_loop()` raises from the
off-loop thread, which is also RuntimeError) → test passes.

See ``docs/specs/FP28.md`` § A1.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mame_curator.api.jobs import JobManager


@pytest.mark.asyncio
async def test_job_manager_emit_raises_off_loop_thread(tmp_path: Path) -> None:
    manager = JobManager(history_dir=tmp_path)
    # Post-fix `__init__` will set `self._loop` to the running loop; simulate
    # that here so the test's intent (off-thread call detection) is what
    # actually fails pre-fix rather than a NoneType comparator.
    manager._loop = asyncio.get_running_loop()
    # Bypass the early `if self._current is None: return` guard so `_emit`
    # actually reaches the lock-thread check. A MagicMock with the relevant
    # attributes is enough — we never inspect them.
    manager._current = MagicMock()
    manager._current.subscribers = []

    fake_event = MagicMock()
    fake_event.event = "job_started"

    def _call_emit_off_thread() -> None:
        manager._emit(fake_event)

    loop = asyncio.get_running_loop()
    with pytest.raises(RuntimeError):
        await loop.run_in_executor(None, _call_emit_off_thread)

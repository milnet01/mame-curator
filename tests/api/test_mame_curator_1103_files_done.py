"""mame-curator-1103 B1 — ``file_finished`` events must carry ``files_done``.

Investigation note (verbatim): "useCopySession never counts done files.
file_progress carries no files_done, and the hook ignores file_finished."
User decision: "count a skipped file as processed, so the counter reaches
its total and the finish screen lists what was skipped."

The frontend (``useCopySession.ts``) only reads ``files_done`` off
``file_progress`` payloads and silently drops ``file_finished`` events
entirely (see the ``case 'file_finished': default: return prev`` fallthrough).
For the counter to ever reach its total — including for a skipped file,
which never produces a ``file_progress`` tick — each ``file_finished``
event emitted by ``_ProgressSynthesizer`` (``api/jobs.py``) must itself
carry a running ``files_done`` count (1, 2, 3, ... in emission order).

Pre-fix: ``_ProgressSynthesizer.__call__`` builds the ``file_finished``
payload as ``{"short_name": short, "bytes": bytes_total}`` — no
``files_done`` key at all, so this test's assertion fails at the first
`in` check as reliably as at the value check.

Regression history: reported 2026-09-26 as mame-curator-1103; no fix is
in the tree at the time this test was written.
"""

from __future__ import annotations

import asyncio
from typing import cast

from mame_curator.api.jobs import JobManager, _ProgressSynthesizer
from mame_curator.api.schemas import JobEvent
from mame_curator.copy import CopyController


class _RecordingSink:
    """Stand-in for ``JobManager`` — only the ``_emit`` seam is exercised."""

    def __init__(self) -> None:
        self.events: list[JobEvent] = []

    def _emit(self, event: JobEvent) -> None:
        self.events.append(event)


async def test_file_finished_payload_carries_running_files_done_count() -> None:
    """Each file_finished event's files_done is the 1-based running count."""
    loop = asyncio.get_running_loop()
    sink = _RecordingSink()
    controller = CopyController()
    # _RecordingSink duck-types JobManager's only seam _ProgressSynthesizer
    # calls (`_emit`); a real JobManager needs a running Job + history_dir
    # this test has no use for.
    synth = _ProgressSynthesizer(loop, cast(JobManager, sink), controller)

    # Three distinct files, each finishing in one tick (done == total).
    synth("pacman", 100, 100)
    synth("dkong", 50, 50)
    synth("galaga", 75, 75)
    # _ProgressSynthesizer dispatches via call_soon_threadsafe; yield to the
    # loop so the scheduled _emit callbacks actually run before we inspect
    # `sink.events`.
    await asyncio.sleep(0)

    finished = [e for e in sink.events if e.event == "file_finished"]
    assert len(finished) == 3, f"expected 3 file_finished events, got {len(finished)}"

    for i, event in enumerate(finished, start=1):
        assert "files_done" in event.payload, (
            f"file_finished #{i} (short_name={event.payload.get('short_name')!r}) "
            f"payload is missing 'files_done'; got keys={sorted(event.payload.keys())}"
        )
        assert event.payload["files_done"] == i, (
            f"file_finished #{i} (short_name={event.payload.get('short_name')!r}): "
            f"expected files_done == {i}, got {event.payload['files_done']!r}"
        )

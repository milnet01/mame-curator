"""How a copy job counts its progress: the totals up front, and the per-file events."""

from __future__ import annotations

from asyncio import AbstractEventLoop
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from mame_curator.api.schemas import JobEvent
from mame_curator.copy import CopyPlan

if TYPE_CHECKING:
    from mame_curator.api.jobs import JobManager


class ProgressSynthesizer:
    """Worker-thread on_progress callback; converts ticks into JobEvents."""

    def __init__(self, loop: AbstractEventLoop, sink: JobManager) -> None:
        """Build a synthesizer bound to ``loop`` for thread-safe event dispatch."""
        self._loop = loop
        self._sink = sink
        self._seen: set[str] = set()
        # mame-curator-1103: job-wide count carried on each file_finished,
        # so a client (or a reconnect replay) reads the count, not a tally.
        self._files_done = 0

    def __call__(self, short: str, bytes_done: int, bytes_total: int) -> None:
        """Turn one tick into `file_started` (first tick), `file_progress`, `file_finished`."""
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
            self._files_done += 1
            self._dispatch(
                JobEvent(
                    event="file_finished",
                    payload={
                        "short_name": short,
                        "bytes": bytes_total,
                        "files_done": self._files_done,
                    },
                    ts=ts,
                )
            )

    def _dispatch(self, event: JobEvent) -> None:
        self._loop.call_soon_threadsafe(self._sink._emit, event)


def sum_input_sizes(plan: CopyPlan, bios_set: frozenset[str]) -> int:
    """Total size of the source zips a job will copy; a missing one counts as 0."""
    total = 0
    for short in (*plan.winners, *bios_set):
        src = plan.source_dir / f"{short}.zip"
        try:
            total += src.stat().st_size
        except OSError:
            continue
    return total

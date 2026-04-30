"""Activity log: append-only newline-delimited JSON at `data/activity.jsonl`.

Atomic at the per-line level via O_APPEND (POSIX guarantees writes
≤ PIPE_BUF (4 KiB on Linux) don't interleave). Each line is one
`ActivityEvent`.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from pathlib import Path

from pydantic import ValidationError

from mame_curator.copy.types import ActivityEvent

logger = logging.getLogger(__name__)


def append_activity(
    event: ActivityEvent,
    log_path: Path = Path("data/activity.jsonl"),
) -> None:
    """Append one event line to the activity log; creates parent dir if missing."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(event.model_dump_json() + "\n")


def read_activity(
    log_path: Path = Path("data/activity.jsonl"),
) -> Iterator[ActivityEvent]:
    """Stream events newest-first; corrupt lines logged + skipped."""
    if not log_path.exists():
        return
    lines = log_path.read_text(encoding="utf-8").splitlines()
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            yield ActivityEvent.model_validate_json(line)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning("skipping corrupt activity line: %s", exc)

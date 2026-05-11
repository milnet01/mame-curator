"""Activity log: append-only newline-delimited JSON at `data/activity.jsonl`.

FP20-B: each append goes through ``os.open(O_WRONLY|O_APPEND|O_CREAT)``
+ a single ``os.write(fd, line_bytes)`` call. POSIX guarantees a single
``write()`` syscall on an O_APPEND fd is atomic regardless of size on
local filesystems, so concurrent appenders never interleave. Python's
``BufferedWriter.write`` may split a logical write across multiple
syscalls when the buffer fills (8 KiB default), breaking the atomicity
claim for large events; bypassing the buffer keeps the contract sound.
"""

from __future__ import annotations

import json
import logging
import os
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
    line_bytes = (event.model_dump_json() + "\n").encode("utf-8")
    fd = os.open(log_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, line_bytes)
    finally:
        os.close(fd)


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

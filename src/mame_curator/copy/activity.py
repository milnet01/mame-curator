"""Activity log: append-only newline-delimited JSON at `data/activity.jsonl`.

FP20-B: each append goes through ``os.open(O_WRONLY|O_APPEND|O_CREAT)``
+ a single ``os.write(fd, line_bytes)`` call. POSIX guarantees a single
``write()`` syscall on an O_APPEND fd is atomic regardless of size on
local filesystems, so concurrent appenders never interleave. Python's
``BufferedWriter.write`` may split a logical write across multiple
syscalls when the buffer fills (8 KiB default), breaking the atomicity
claim for large events; bypassing the buffer keeps the contract sound.

FP25-B durability + typed errors:

- After the write completes, a best-effort ``os.fsync`` flushes the page
  cache. Some filesystems (tmpfs, some containers, some networked
  mounts) reject fsync; the ``OSError`` is suppressed because power-cut
  durability is defense-in-depth, not a hard contract.
- POSIX permits ``os.write`` to return a value smaller than the input
  length (signal-interrupted on EINTR, ENOSPC partway through). Local
  filesystems under CPython virtually never trigger this — CPython
  auto-retries on EINTR and most kernels write the full buffer in one
  go — but the writer now loops until every byte has been written
  rather than truncating the line silently. Multi-writer concurrency:
  a short write on a regular file is rare enough on local filesystems
  that the spec's atomic-line claim holds in practice; the loop only
  matters for the single-writer correctness case.
- Every ``OSError`` raised in the open / write path wraps in
  ``ActivityLogError`` (a ``CopyError`` subclass) so the CLI/API
  boundary still catches it per the ``copy/spec.md`` typed-error
  envelope.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
from collections.abc import Iterator
from pathlib import Path

from pydantic import ValidationError

from mame_curator.copy.errors import ActivityLogError
from mame_curator.copy.types import ActivityEvent

logger = logging.getLogger(__name__)


def append_activity(
    event: ActivityEvent,
    log_path: Path = Path("data/activity.jsonl"),
) -> None:
    """Append one event line to the activity log; creates parent dir if missing."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    line_bytes = (event.model_dump_json() + "\n").encode("utf-8")
    try:
        fd = os.open(log_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    except OSError as exc:
        raise ActivityLogError("failed to open activity log for append", path=log_path) from exc
    try:
        view = line_bytes
        while view:
            try:
                written = os.write(fd, view)
            except OSError as exc:
                raise ActivityLogError("failed to write activity event", path=log_path) from exc
            if written == 0:
                # Spec-permitted but kernel-unusual: 0-byte write with no
                # error is undefined. Bail rather than spin.
                raise ActivityLogError("activity log write returned 0 bytes", path=log_path)
            view = view[written:]
        # FP25-B: best-effort fsync. Some filesystems (tmpfs, some
        # containers, some networked mounts) reject fsync. Power-cut
        # durability is defense-in-depth — suppress OSError so the
        # successful write isn't followed by a spurious error to the
        # caller. Mirrors the ``_atomic.py`` suppress pattern.
        with contextlib.suppress(OSError):
            os.fsync(fd)
    finally:
        with contextlib.suppress(OSError):
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

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
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from mame_curator._atomic import fsync_parent_dir
from mame_curator.copy.errors import ActivityLogError
from mame_curator.copy.types import (
    ActivityEvent,
    ActivityEventType,
    CopyAbortedDetails,
    CopyReportStatus,
)

logger = logging.getLogger(__name__)


def append_activity(
    event: ActivityEvent,
    log_path: Path = Path("data/activity.jsonl"),
) -> None:
    """Append one event line to the activity log; creates parent dir if missing."""
    # FP26-B: wrap the mkdir in the ActivityLogError envelope so an
    # EACCES on `data/` (or any OSError class — EROFS, ENOSPC for inode
    # allocation, ENOTDIR if a sibling file occupies the parent name)
    # surfaces as the typed CopyError subclass instead of escaping the
    # CLI's catch boundary. The FP25-B audit (L2-H1) caught the gap.
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ActivityLogError(
            "failed to prepare activity log directory", path=log_path.parent
        ) from exc
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
    # FP26-F: parent-dir fsync, best-effort. The file fsync above
    # flushes the file content but does NOT make the dirent durable
    # on the very first append (O_CREAT just brought the entry into
    # the page cache). One more best-effort call closes the lacuna at
    # near-zero cost. Re-uses the helper from ``_atomic.py`` (Rule of
    # Three honoured — atomic_write_text + atomic_write_bytes already
    # rely on it).
    fsync_parent_dir(log_path)


_ERROR_MESSAGE_CAP = 200


def short_error_message(exc: BaseException) -> str:
    """The error's first line, capped; the exception's type name when it has no text."""
    lines = str(exc).strip().splitlines()
    text = lines[0].strip() if lines else ""
    if not text:
        return type(exc).__name__
    if len(text) > _ERROR_MESSAGE_CAP:
        return text[: _ERROR_MESSAGE_CAP - 1] + "…"
    return text


def record_copy_error(
    exc: BaseException,
    *,
    session_id: str,
    recycled_count: int = 0,
    log_path: Path,
) -> None:
    """Append a `copy_aborted` event for a copy an error stopped. Never raises.

    mame-curator-1157: this runs while an exception is already propagating,
    so a failure here is logged and dropped rather than replacing that error.
    """
    try:
        append_activity(
            ActivityEvent(
                timestamp=datetime.now(UTC),
                event_type=ActivityEventType.COPY_ABORTED,
                summary=f"copy stopped because of an error: {short_error_message(exc)}",
                session_id=session_id,
                details=CopyAbortedDetails(
                    reason=CopyReportStatus.ERROR.value, recycled_count=recycled_count
                ),
            ),
            log_path=log_path,
        )
    except Exception:
        logger.exception("could not record the copy error in the activity log")


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

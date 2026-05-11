"""FP25-E: concurrent-write property test for the activity log.

The existing ``test_activity_log_append_uses_single_os_write``
(``tests/copy/test_activity.py``) asserts that ``append_activity`` issues
**exactly one** ``os.write`` syscall — a necessary condition for the
POSIX O_APPEND atomicity claim in ``copy/spec.md``, but not sufficient.

FP25-E adds the sufficient-condition test: fork two child processes,
each appending N × 6 KiB lines, and assert every resulting JSONL line
parses cleanly. 6 KiB is comfortably above Linux's legacy PIPE_BUF
(4 KiB) so this exercises the contract that O_APPEND atomicity holds
for arbitrarily large writes on regular files (not just pipe/FIFO
boundaries).

Gated on ``sys.platform == "linux"`` (FP26-D): Windows has no POSIX
O_APPEND atomicity guarantee — the NTFS equivalent is a separate
contract the project does not claim. macOS's `mp.get_context("fork")`
is unsafe after CoreFoundation initialisation (the project's CI
matrix runs `macos-latest` without setting
`OBJC_DISABLE_INITIALIZE_FORK_SAFETY`), so the test would either hang
on the 30 s join timeout or fail with a non-zero exitcode. Linux-only
keeps the contract pinned where it's load-bearing.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from mame_curator.copy import append_activity
from mame_curator.copy.types import (
    ActivityEvent,
    ActivityEventType,
    ConflictStrategy,
    CopyStartedDetails,
    PlanSummary,
)

# FP26-D: gate strictly on linux; macOS fork is unsafe post-CoreFoundation.
_FORK_SAFE = sys.platform == "linux"


def _make_big_event(session_id: str, summary_size: int = 6 * 1024) -> ActivityEvent:
    """Construct an event whose JSON serialisation is ≳ ``summary_size`` bytes."""
    return ActivityEvent(
        timestamp=datetime(2026, 5, 11, 12, 0, 0, tzinfo=UTC),
        event_type=ActivityEventType.COPY_STARTED,
        summary="A" * summary_size,
        session_id=session_id,
        details=CopyStartedDetails(
            plan_summary=PlanSummary(
                winners_count=1,
                bios_count=0,
                conflict_strategy=ConflictStrategy.APPEND,
                source_dir=Path("/s"),
                dest_dir=Path("/d"),
            ),
            conflict_strategy=ConflictStrategy.APPEND,
        ),
    )


def _child_appender(log_path: str, session_id: str, count: int) -> None:
    """Child entry-point: append ``count`` events to ``log_path``."""
    for _ in range(count):
        append_activity(_make_big_event(session_id), log_path=Path(log_path))


@pytest.mark.skipif(
    not _FORK_SAFE,
    reason="POSIX O_APPEND atomicity + fork-safe mp.get_context — linux only",
)
def test_fp25_e_concurrent_appenders_never_interleave(tmp_path: Path) -> None:
    """Two child processes each appending 6 KiB events produce parseable lines.

    Without the FP20-B single-``os.write`` fix, the BufferedWriter would
    split a 6 KiB line into two 8 KiB-buffer-aligned syscalls and child A's
    second half would interleave with child B's first half, producing a
    JSON-corrupt line. With FP20-B's single-write contract and POSIX
    O_APPEND atomicity, every line on disk is a complete event.
    """
    log_path = tmp_path / "activity.jsonl"
    per_child = 20
    expected_total = 2 * per_child

    # FP26-D: ``mp.get_context("fork")`` returns a ``ForkContext`` on
    # Linux but mypy on Windows sees the union'd ``BaseContext`` (no
    # ``Process`` attribute) — the test is skipif-gated above, so the
    # call is unreachable on Windows, but mypy still type-checks it.
    # Suppress with attr-defined; the skipif gate is the runtime guard.
    ctx = mp.get_context("fork")
    # The Windows-mypy-only attr-defined suppression below also carries
    # unused-ignore so the Linux gate doesn't flag the suppression as
    # unused; on Linux mypy sees the narrow ForkContext (Process is
    # available) so the attr-defined ignore is logically dead there.
    p1 = ctx.Process(  # type: ignore[attr-defined,unused-ignore]
        target=_child_appender, args=(str(log_path), "child-a", per_child)
    )
    p2 = ctx.Process(  # type: ignore[attr-defined,unused-ignore]
        target=_child_appender, args=(str(log_path), "child-b", per_child)
    )
    p1.start()
    p2.start()
    p1.join(timeout=30)
    p2.join(timeout=30)

    assert p1.exitcode == 0, f"child-a failed: exitcode={p1.exitcode}"
    assert p2.exitcode == 0, f"child-b failed: exitcode={p2.exitcode}"

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == expected_total, f"expected {expected_total} lines, got {len(lines)}"

    session_counts = {"child-a": 0, "child-b": 0}
    for i, line in enumerate(lines):
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            pytest.fail(
                f"line {i} is not valid JSON — interleaving leaked: "
                f"{exc}; first 200 bytes: {line[:200]!r}"
            )
        session_id = parsed["session_id"]
        assert session_id in session_counts, (
            f"line {i} has unexpected session_id {session_id!r} — "
            "indicates byte-level corruption between writers"
        )
        session_counts[session_id] += 1

    assert session_counts == {"child-a": per_child, "child-b": per_child}, (
        f"per-child line counts mismatch: {session_counts}"
    )

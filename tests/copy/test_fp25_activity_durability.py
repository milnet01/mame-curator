"""FP25-B: activity-log durability + typed errors.

The pre-FP25-B ``append_activity`` writer:

- ignored the return value of ``os.write`` — POSIX permits a regular-file
  write to return *fewer* bytes than the input length (signal-interrupted,
  ENOSPC partway through);
- did no ``fsync`` — the page-cache flush is at the kernel's discretion,
  so a power loss between ``write()`` returning and the kernel flushing
  silently drops the most-recent record(s);
- propagated raw ``OSError`` instead of wrapping in ``ActivityLogError``
  per the ``copy/spec.md`` typed-error envelope.

FP25-B closes all three. The atomic-line claim (single ``os.write`` on an
O_APPEND fd) is preserved in the happy path — the new loop only iterates
when the kernel returns short, which on local filesystems never happens
under normal load.
"""

from __future__ import annotations

import json
import os as os_mod
from datetime import UTC, datetime
from pathlib import Path

import pytest

from mame_curator.copy import append_activity
from mame_curator.copy.errors import ActivityLogError, CopyError
from mame_curator.copy.types import (
    ActivityEvent,
    ActivityEventType,
    ConflictStrategy,
    CopyStartedDetails,
    PlanSummary,
)


def _event() -> ActivityEvent:
    return ActivityEvent(
        timestamp=datetime(2026, 5, 11, 12, 0, 0, tzinfo=UTC),
        event_type=ActivityEventType.COPY_STARTED,
        summary="fp25-b durability event",
        session_id="01HZZ",
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


def test_fp25_b_activitylogerror_is_copyerror_subclass() -> None:
    """``ActivityLogError`` must inherit from ``CopyError`` for the CLI envelope."""
    assert issubclass(ActivityLogError, CopyError)


def test_fp25_b_short_write_loop_completes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A short ``os.write`` is followed by a second write of the remainder.

    POSIX permits regular-file writes to return fewer bytes than the input
    length (signal-interrupted, ENOSPC partway). The pre-FP25-B writer
    ignored this — the on-disk line would be truncated and the next
    reader's ``json.loads`` would fail. The fix loops until every byte
    has been written.
    """
    log_path = tmp_path / "activity.jsonl"
    line_bytes = (_event().model_dump_json() + "\n").encode("utf-8")
    real_write = os_mod.write
    calls: list[int] = []

    def short_first_write(fd: int, data: bytes) -> int:
        # Only short-write OUR fd (skip any tmp_path bookkeeping fd).
        if len(data) == len(line_bytes) and not calls:
            calls.append(len(data))
            half = len(data) // 2
            return real_write(fd, data[:half])
        calls.append(len(data))
        return real_write(fd, data)

    monkeypatch.setattr(os_mod, "write", short_first_write)
    append_activity(_event(), log_path=log_path)

    on_disk = log_path.read_text(encoding="utf-8").splitlines()
    assert len(on_disk) == 1, f"expected one full line, got: {on_disk!r}"
    parsed = json.loads(on_disk[0])
    assert parsed["session_id"] == "01HZZ"
    # First call was short; second call wrote the remainder.
    assert len(calls) >= 2, f"loop must retry after short write, got calls={calls}"


def test_fp25_b_fsync_issued_best_effort(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``os.fsync`` is called on the append fd before close (best-effort)."""
    log_path = tmp_path / "activity.jsonl"
    fsync_calls: list[int] = []
    real_fsync = os_mod.fsync

    def tracking_fsync(fd: int) -> None:
        fsync_calls.append(fd)
        real_fsync(fd)

    monkeypatch.setattr(os_mod, "fsync", tracking_fsync)
    append_activity(_event(), log_path=log_path)

    assert len(fsync_calls) >= 1, "fsync must be issued after append (best-effort)"


def test_fp25_b_fsync_oserror_suppressed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``OSError`` on fsync is suppressed — tmpfs and some networked mounts reject it.

    The page-cache flush is best-effort: a failing fsync MUST NOT abort
    the append (the write itself succeeded; durability is defense-in-
    depth). Mirrors the ``_atomic.py`` ``contextlib.suppress(OSError)``
    pattern used by ``atomic_write_text``.
    """
    log_path = tmp_path / "activity.jsonl"

    def failing_fsync(fd: int) -> None:
        raise OSError("simulated tmpfs fsync rejection")

    monkeypatch.setattr(os_mod, "fsync", failing_fsync)
    # Must not raise.
    append_activity(_event(), log_path=log_path)

    parsed = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert parsed["session_id"] == "01HZZ"


def test_fp25_b_oserror_on_write_wrapped_as_activitylogerror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Raw ``OSError`` from ``os.write`` propagates as ``ActivityLogError``.

    Per ``copy/spec.md`` § Errors envelope: every error path inside the
    copy module surfaces as a ``CopyError`` subclass so the CLI's catch
    boundary holds. Bare ``OSError`` from the activity-log writer would
    escape that envelope.
    """
    log_path = tmp_path / "activity.jsonl"
    line_bytes = (_event().model_dump_json() + "\n").encode("utf-8")

    def failing_write(fd: int, data: bytes) -> int:
        if len(data) == len(line_bytes):
            raise OSError("simulated ENOSPC")
        return os_mod.write(fd, data)

    monkeypatch.setattr(os_mod, "write", failing_write)

    with pytest.raises(ActivityLogError) as exc_info:
        append_activity(_event(), log_path=log_path)
    assert isinstance(exc_info.value, CopyError)
    assert exc_info.value.path == log_path


def test_fp26_b_oserror_on_mkdir_wrapped_as_activitylogerror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FP26-B: ``OSError`` from the parent-dir ``mkdir`` also wraps as
    ``ActivityLogError``.

    The FP25-B closing review (L2-H1) caught that the pre-FP26-B writer
    let ``log_path.parent.mkdir(...)`` raise raw ``OSError`` on EACCES
    / EROFS / ENOSPC for inode allocation / ENOTDIR. The CLI / API's
    ``CopyError`` boundary would not catch the bare OSError. Now it
    wraps in the typed envelope alongside the open / write paths.
    """
    log_path = tmp_path / "no_perm" / "activity.jsonl"

    real_mkdir = Path.mkdir

    def failing_mkdir(self: Path, *args: object, **kwargs: object) -> None:
        if self == log_path.parent:
            raise OSError("simulated EACCES on parent dir")
        real_mkdir(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "mkdir", failing_mkdir)

    with pytest.raises(ActivityLogError) as exc_info:
        append_activity(_event(), log_path=log_path)
    assert isinstance(exc_info.value, CopyError)
    assert exc_info.value.path == log_path.parent


def test_fp26_h_zero_byte_write_raises_activitylogerror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FP26-H: a 0-byte ``os.write`` return with no OSError raises
    ``ActivityLogError`` rather than spinning forever.

    POSIX permits ``os.write(fd, data)`` to return 0 with no error in
    rare conditions (some pseudo-filesystems, hypothetical kernel
    bugs); without the explicit "written == 0" branch in FP25-B's
    loop, the writer would spin on `view = view[0:]` forever. Test
    forces the branch via a monkey-patched ``os.write`` that always
    returns 0.
    """
    log_path = tmp_path / "activity.jsonl"

    def zero_write(fd: int, data: bytes) -> int:
        return 0

    monkeypatch.setattr(os_mod, "write", zero_write)

    with pytest.raises(ActivityLogError) as exc_info:
        append_activity(_event(), log_path=log_path)
    assert "0 bytes" in str(exc_info.value)


def test_fp25_b_oserror_on_open_wrapped_as_activitylogerror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Raw ``OSError`` from ``os.open`` also wraps as ``ActivityLogError``."""
    log_path = tmp_path / "activity.jsonl"
    real_open = os_mod.open

    def failing_open(
        path: str | bytes | os_mod.PathLike[str] | os_mod.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        # Fail on OUR target only — pytest internals open many fds.
        if str(path) == str(log_path):
            raise OSError("simulated EACCES")
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os_mod, "open", failing_open)

    with pytest.raises(ActivityLogError) as exc_info:
        append_activity(_event(), log_path=log_path)
    assert isinstance(exc_info.value, CopyError)

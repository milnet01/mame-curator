"""Tests for `copy_one` atomic copy primitive."""

from __future__ import annotations

from pathlib import Path

import pytest

from mame_curator.copy import copy_one
from mame_curator.copy.errors import CopyExecutionError
from mame_curator.copy.types import CopyOutcomeStatus


def test_copy_succeeded_writes_dest_with_correct_bytes(source_dir: Path, dest_dir: Path) -> None:
    src = source_dir / "kof94.zip"
    dst = dest_dir / "kof94.zip"
    outcome = copy_one(src, dst, short_name="kof94", role="winner")
    assert outcome.status is CopyOutcomeStatus.SUCCEEDED
    assert dst.read_bytes() == src.read_bytes()
    assert outcome.bytes == src.stat().st_size


def test_copy_atomic_uses_tmp_then_replace(
    source_dir: Path, dest_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Failure during copy step leaves no .tmp behind; original dst untouched."""
    src = source_dir / "kof94.zip"
    dst = dest_dir / "kof94.zip"
    # Create an existing dst with different content.
    dst.write_bytes(b"OLD CONTENT")
    original_size = dst.stat().st_size

    # Make shutil.copy2 raise mid-copy.
    import shutil as _shutil

    from mame_curator.copy import executor

    def boom(src_arg: object, tmp_arg: object) -> None:
        # Simulate a partial write of the .tmp first
        tmp = Path(str(tmp_arg))
        tmp.write_bytes(b"PARTIAL")
        raise OSError("simulated mid-copy failure")

    monkeypatch.setattr(_shutil, "copy2", boom)
    monkeypatch.setattr(executor, "shutil", _shutil)

    with pytest.raises(CopyExecutionError):
        copy_one(src, dst, short_name="kof94", role="winner")

    # Original dst still has its old content (atomic — never half-written).
    assert dst.read_bytes() == b"OLD CONTENT"
    assert dst.stat().st_size == original_size
    # No .tmp left behind.
    assert not (dst.with_suffix(".zip.tmp")).exists()
    assert not list(dest_dir.glob("*.tmp"))


def test_copy_idempotent_skipped_when_size_and_mtime_match(
    source_dir: Path, dest_dir: Path
) -> None:
    """Re-copying the same file is a no-op when dest size+mtime match."""
    src = source_dir / "kof94.zip"
    dst = dest_dir / "kof94.zip"

    first = copy_one(src, dst, short_name="kof94", role="winner")
    assert first.status is CopyOutcomeStatus.SUCCEEDED

    second = copy_one(src, dst, short_name="kof94", role="winner")
    assert second.status is CopyOutcomeStatus.SKIPPED_IDEMPOTENT
    assert second.bytes == 0


def test_copy_idempotency_breaks_when_size_differs(source_dir: Path, dest_dir: Path) -> None:
    """Different size at dst → not skipped."""
    src = source_dir / "kof94.zip"
    dst = dest_dir / "kof94.zip"
    # Write a different-sized dst.
    dst.write_bytes(b"different-size")
    outcome = copy_one(src, dst, short_name="kof94", role="winner")
    assert outcome.status is CopyOutcomeStatus.SUCCEEDED


def test_copy_preserves_mtime(source_dir: Path, dest_dir: Path) -> None:
    """shutil.copy2 preserves source mtime."""
    src = source_dir / "kof94.zip"
    dst = dest_dir / "kof94.zip"
    src_mtime = src.stat().st_mtime
    copy_one(src, dst, short_name="kof94", role="winner")
    assert abs(dst.stat().st_mtime - src_mtime) < 1.0


def test_copy_progress_callback_emits_chunks(source_dir: Path, dest_dir: Path) -> None:
    """progress callback is invoked at least once for a real copy."""
    # Make a larger source so chunked copy emits multiple progress events.
    src = source_dir / "big.zip"
    src.write_bytes(b"X" * (3 * 1024 * 1024))  # 3 MiB
    dst = dest_dir / "big.zip"

    events: list[tuple[int, int]] = []

    def cb(done: int, total: int) -> None:
        events.append((done, total))

    copy_one(src, dst, short_name="big", role="winner", progress=cb)
    assert events
    # Final event should report bytes_done == total.
    assert events[-1][0] == events[-1][1]
    assert events[-1][1] == src.stat().st_size


def test_copy_outcome_records_short_name_and_role(source_dir: Path, dest_dir: Path) -> None:
    src = source_dir / "neogeo.zip"
    dst = dest_dir / "neogeo.zip"
    outcome = copy_one(src, dst, short_name="neogeo", role="bios")
    assert outcome.short_name == "neogeo"
    assert outcome.role == "bios"


# FP05 — C3 test below


def test_copy_one_exdev_raises_typed_error(
    source_dir: Path, dest_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C3 — `os.replace` raising EXDEV (cross-filesystem rename) inside
    `copy_one` must surface as `CopyExecutionError` so the runner can
    catch it via the typed-error contract. The existing `except OSError`
    branch in `copy_one` already wraps OSError → CopyExecutionError;
    this test pins that EXDEV stays inside the typed family across the
    FP05 C3 changes (which add an explicit EXDEV-aware error path)."""
    import errno
    import os

    src = source_dir / "kof94.zip"
    dst = dest_dir / "kof94.zip"

    def _exdev(*_args: object, **_kwargs: object) -> None:
        raise OSError(errno.EXDEV, "Invalid cross-device link")

    monkeypatch.setattr(os, "replace", _exdev)

    with pytest.raises(CopyExecutionError):
        copy_one(src, dst, short_name="kof94", role="winner")

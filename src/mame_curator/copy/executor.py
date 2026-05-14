"""Atomic copy primitive: `.tmp` + `os.replace` with mtime preservation."""

from __future__ import annotations

import contextlib
import os
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from mame_curator._atomic import fsync_parent_dir
from mame_curator.copy.errors import CopyExecutionError
from mame_curator.copy.types import CopyOutcome, CopyOutcomeStatus

_CHUNK = 1024 * 1024  # 1 MiB


def _is_idempotent(src: Path, dst: Path) -> bool:
    if not dst.exists():
        return False
    s = src.stat()
    d = dst.stat()
    return s.st_size == d.st_size and abs(s.st_mtime - d.st_mtime) < 1.0


def _chunked_copy(src: Path, tmp: Path, total: int, progress: Callable[[int, int], None]) -> None:
    done = 0
    with src.open("rb") as fin, tmp.open("wb") as fout:
        while True:
            chunk = fin.read(_CHUNK)
            if not chunk:
                break
            fout.write(chunk)
            done += len(chunk)
            progress(done, total)
        # FP27 B1: fsync the tmp's bytes to disk BEFORE the implicit
        # close (which is itself before os.replace at the caller).
        # Without this, a power cut within the kernel writeback window
        # (~30s default `dirty_expire_centisecs`) after os.replace
        # returned leaves dst pointing at an inode whose bytes never
        # reached the platter → zero-byte / truncated dst on reboot.
        fout.flush()
        os.fsync(fout.fileno())
    # Preserve mtime + permissions like shutil.copy2.
    shutil.copystat(src, tmp)


def copy_one(
    src: Path,
    dst: Path,
    *,
    short_name: str,
    role: Literal["winner", "bios"],
    progress: Callable[[int, int], None] | None = None,
) -> CopyOutcome:
    """Atomically copy `src` to `dst`; idempotent on size+mtime; chunked progress."""
    if _is_idempotent(src, dst):
        return CopyOutcome(
            short_name=short_name,
            role=role,
            status=CopyOutcomeStatus.SKIPPED_IDEMPOTENT,
            src=src,
            dst=dst,
            bytes=0,
        )

    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    # FP21-G: source can disappear between an upstream existence check
    # and this ``stat`` (TOCTOU). Return the SKIPPED variant instead of
    # raising ``FileNotFoundError`` — the runner already has typed
    # handling for "missing source"; "failed mid-copy" was the wrong
    # bucket for this case.
    try:
        total = src.stat().st_size
    except FileNotFoundError:
        return CopyOutcome(
            short_name=short_name,
            role=role,
            status=CopyOutcomeStatus.SKIPPED_MISSING_SOURCE,
            src=src,
            dst=dst,
            bytes=0,
        )
    # try/finally over try/except so KeyboardInterrupt, MemoryError, and any
    # other BaseException also trigger tmp cleanup. The OSError branch wraps
    # into CopyExecutionError; everything else propagates with the .tmp gone.
    completed = False
    try:
        try:
            # FP27 B1: both write paths now funnel through `_chunked_copy`
            # so the fsync-before-close + parent-dir fsync sequence covers
            # the no-progress branch too. The progress callback collapses
            # to a no-op for the no-progress case.
            _chunked_copy(
                src,
                tmp,
                total,
                progress if progress is not None else lambda _done, _total: None,
            )
            os.replace(tmp, dst)
            # FP27 B1: fsync the parent dir so the rename hits the
            # journal — same protocol as `mame_curator._atomic`.
            fsync_parent_dir(dst)
            completed = True
        except OSError as exc:
            raise CopyExecutionError(f"copy failed: {exc}", path=src) from exc
    finally:
        if not completed:
            with contextlib.suppress(OSError):
                tmp.unlink(missing_ok=True)

    return CopyOutcome(
        short_name=short_name,
        role=role,
        status=CopyOutcomeStatus.SUCCEEDED,
        src=src,
        dst=dst,
        bytes=total,
    )

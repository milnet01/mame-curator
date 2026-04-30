"""Atomic copy primitive: `.tmp` + `os.replace` with mtime preservation."""

from __future__ import annotations

import contextlib
import os
import shutil
from collections.abc import Callable
from pathlib import Path

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
    # Preserve mtime + permissions like shutil.copy2.
    shutil.copystat(src, tmp)


def copy_one(
    src: Path,
    dst: Path,
    *,
    short_name: str,
    role: str,
    progress: Callable[[int, int], None] | None = None,
) -> CopyOutcome:
    """Atomically copy `src` to `dst`; idempotent on size+mtime; chunked progress."""
    if _is_idempotent(src, dst):
        return CopyOutcome(
            short_name=short_name,
            role=role,  # type: ignore[arg-type]
            status=CopyOutcomeStatus.SKIPPED_IDEMPOTENT,
            src=src,
            dst=dst,
            bytes=0,
        )

    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    total = src.stat().st_size
    try:
        if progress is not None:
            _chunked_copy(src, tmp, total, progress)
        else:
            shutil.copy2(src, tmp)
        os.replace(tmp, dst)
    except OSError as exc:
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)
        raise CopyExecutionError(f"copy failed: {exc}", path=src) from exc

    return CopyOutcome(
        short_name=short_name,
        role=role,  # type: ignore[arg-type]
        status=CopyOutcomeStatus.SUCCEEDED,
        src=src,
        dst=dst,
        bytes=total,
    )

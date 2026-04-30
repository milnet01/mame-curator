"""Preflight: validate a CopyPlan against source/destination filesystems."""

from __future__ import annotations

import shutil
from pathlib import Path

from mame_curator.copy.types import CopyPlan, PreflightResult


def _can_create_dir(target: Path) -> bool:
    if target.exists():
        return target.is_dir()
    # Walk up to first existing ancestor; check it's a writable dir.
    for parent in [target, *target.parents]:
        if parent.exists():
            return parent.is_dir()
    return False


def _is_idempotent(src: Path, dst: Path) -> bool:
    if not dst.exists():
        return False
    s = src.stat()
    d = dst.stat()
    return s.st_size == d.st_size and abs(s.st_mtime - d.st_mtime) < 1.0


def preflight(plan: CopyPlan) -> PreflightResult:
    """Check source/destination filesystems; return PreflightResult (never raises)."""
    missing: list[str] = []
    already: list[str] = []
    for short in plan.winners:
        src = plan.source_dir / f"{short}.zip"
        if not src.exists():
            missing.append(short)
            continue
        dst = plan.dest_dir / f"{short}.zip"
        if _is_idempotent(src, dst):
            already.append(short)

    dest_writable = _can_create_dir(plan.dest_dir)
    existing_playlist = (plan.dest_dir / "mame.lpl").exists()

    free_space_gap = 0
    if dest_writable:
        try:
            total_needed = sum(
                (plan.source_dir / f"{w}.zip").stat().st_size
                for w in plan.winners
                if (plan.source_dir / f"{w}.zip").exists()
            )
            anchor = plan.dest_dir if plan.dest_dir.exists() else plan.dest_dir.parent
            if anchor.exists():
                stat = shutil.disk_usage(anchor)
                free_space_gap = stat.free - total_needed
        except OSError:
            free_space_gap = 0

    return PreflightResult(
        missing_source=tuple(sorted(missing)),
        dest_writable=dest_writable,
        free_space_gap_bytes=free_space_gap,
        existing_playlist=existing_playlist,
        already_copied=tuple(sorted(already)),
    )

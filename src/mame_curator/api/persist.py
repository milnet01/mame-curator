"""Atomic-write + snapshot helpers shared across config / overrides / sessions / notes routes.

Per ``docs/specs/P04.md`` § Atomic-write protocol.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import shutil
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from mame_curator._atomic import atomic_write_bytes
from mame_curator.api.errors import SnapshotNotFoundError

logger = logging.getLogger(__name__)


# FP21-M: cap on the number of snapshot directories kept on disk. Every
# PATCH / override / session / notes / grant / import creates a new
# snapshot dir; without an LRU bound a long-running server fills the
# data directory indefinitely. ``200`` covers roughly six months of
# moderate use (1 mutation per day) and keeps disk usage trivial.
MAX_SNAPSHOTS = 200


def snapshot_files(snapshots_dir: Path, files: Mapping[str, Path]) -> str:
    """Snapshot any files that currently exist into a new timestamped directory.

    Returns the snapshot id (timestamp string). Files that don't exist are
    skipped (e.g. first PATCH before any user-side overrides.yaml exists).

    FP21-M: after creating the new snapshot dir, prune oldest siblings
    that exceed ``MAX_SNAPSHOTS``. Best-effort — a stat / rmtree failure
    is logged but doesn't fail the snapshot itself.
    """
    snap_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S_%fZ")
    snap_dir = snapshots_dir / snap_id
    snap_dir.mkdir(parents=True, exist_ok=True)
    for name, src in files.items():
        if not src.exists():
            continue
        try:
            data = src.read_bytes()
        except OSError:
            logger.exception("snapshot read failed for %r", str(src))
            continue
        atomic_write_bytes(snap_dir / name, data)
    _prune_old_snapshots(snapshots_dir)
    return snap_id


def _prune_old_snapshots(snapshots_dir: Path) -> None:
    """FP21-M: enforce ``MAX_SNAPSHOTS`` cap by removing oldest siblings."""
    try:
        all_dirs = [p for p in snapshots_dir.iterdir() if p.is_dir()]
    except OSError:
        return
    if len(all_dirs) <= MAX_SNAPSHOTS:
        return
    # Sort oldest-first by name (timestamp prefix is monotonic).
    all_dirs.sort(key=lambda p: p.name)
    overflow = len(all_dirs) - MAX_SNAPSHOTS
    for victim in all_dirs[:overflow]:
        try:
            shutil.rmtree(victim)
        except OSError:
            logger.exception("snapshot prune failed for %r", str(victim))


def list_snapshots(snapshots_dir: Path) -> list[dict[str, Any]]:
    """List snapshot directories, newest-first."""
    if not snapshots_dir.exists():
        return []
    items: list[dict[str, Any]] = []
    for child in sorted(snapshots_dir.iterdir(), reverse=True):
        if not child.is_dir():
            continue
        try:
            mtime = datetime.fromtimestamp(child.stat().st_mtime, tz=UTC)
        except OSError:
            continue
        files = tuple(sorted(p.name for p in child.iterdir() if p.is_file()))
        items.append({"id": child.name, "ts": mtime, "files": files})
    return items


def restore_snapshot(snapshots_dir: Path, snap_id: str, targets: Mapping[str, Path]) -> None:
    """Copy the named files from ``snapshots_dir/<id>/`` back to their targets.

    Files absent from the snapshot are deleted from the live targets so the
    restore reverts cleanly to the snapshot state.

    FP27 B2: stage-then-promote. The previous per-iteration shape
    (``atomic_write_bytes(dst, ...)`` then ``dst.unlink()``) read from
    snap_dir and wrote to the live target in the same pass — a crash
    mid-loop with N files left k restored and (M-k) unlinked, a
    half-restored state. Now the snapshot bytes are first read into a
    sibling staging directory; only after every stage-write succeeds
    do the live-target promotes (``os.replace``) and absent-file
    unlinks run. Mid-stage failures leave the live targets untouched.
    A mid-promote failure can still produce a half-restored end state
    (per-file ``os.replace`` is the POSIX atomic unit), but the
    read-from-snapshot step is front-loaded so the snapshot dir can
    vanish after staging without losing data.
    """
    snap_dir = snapshots_dir / snap_id
    if not snap_dir.exists() or not snap_dir.is_dir():
        raise SnapshotNotFoundError(f"snapshot id not found: {snap_id!r}")

    # Stage every snapshot file into a sibling staging dir. The stage
    # writes use the existing atomic-write helper, so a crash inside
    # the stage step leaves no half-written staging file behind.
    staging_dir = snap_dir / "_restore_staging"
    staging_dir.mkdir(parents=True, exist_ok=True)
    stage_paths: dict[str, Path] = {}  # name → staging path
    unlink_names: list[str] = []
    try:
        for name, _dst in targets.items():
            src = snap_dir / name
            if src.exists():
                stage_path = staging_dir / name
                atomic_write_bytes(stage_path, src.read_bytes())
                stage_paths[name] = stage_path
            else:
                unlink_names.append(name)

        # Promote: replace live targets, then unlink absentees. The
        # order within each phase is best-effort; once we're here,
        # every stage write succeeded and the bytes are safely on disk.
        for name, stage_path in stage_paths.items():
            os.replace(stage_path, targets[name])
        for name in unlink_names:
            dst = targets[name]
            if dst.exists():
                try:
                    dst.unlink()
                except OSError:
                    logger.exception("failed to remove %r during restore", str(dst))
    finally:
        # Clean up the staging dir whether we succeeded or aborted.
        # Any staging files still present (mid-failure) are orphans
        # the next restore call would step on; remove them now.
        with contextlib.suppress(OSError):
            shutil.rmtree(staging_dir)


def write_yaml_atomic(path: Path, data: Mapping[str, Any]) -> None:
    """Atomically write a YAML file (Path values stringified, keys sorted)."""
    text = yaml.safe_dump(_jsonify(dict(data)), sort_keys=True, default_flow_style=False)
    atomic_write_bytes(path, text.encode("utf-8"))


def write_json_atomic(path: Path, data: Mapping[str, Any]) -> None:
    """Atomically write a JSON file (Path values stringified, keys sorted)."""
    text = json.dumps(_jsonify(dict(data)), indent=2, sort_keys=True)
    atomic_write_bytes(path, text.encode("utf-8"))


def _jsonify(obj: Any) -> Any:
    """Best-effort JSON/YAML-serialisable conversion (Path → str, etc.)."""
    if isinstance(obj, dict):
        return {str(k): _jsonify(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonify(v) for v in obj]
    if isinstance(obj, Path):
        return str(obj)
    if hasattr(obj, "value"):  # StrEnum
        try:
            return obj.value
        except AttributeError:
            return str(obj)
    return obj

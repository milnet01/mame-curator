"""Atomic-write + snapshot helpers shared across config / overrides / sessions / notes routes.

Per ``docs/specs/P04.md`` § Atomic-write protocol.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from mame_curator._atomic import atomic_write_bytes
from mame_curator.api.errors import SnapshotNotFoundError

logger = logging.getLogger(__name__)


def snapshot_files(snapshots_dir: Path, files: Mapping[str, Path]) -> str:
    """Snapshot any files that currently exist into a new timestamped directory.

    Returns the snapshot id (timestamp string). Files that don't exist are
    skipped (e.g. first PATCH before any user-side overrides.yaml exists).
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
    return snap_id


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
    """
    snap_dir = snapshots_dir / snap_id
    if not snap_dir.exists() or not snap_dir.is_dir():
        raise SnapshotNotFoundError(f"snapshot id not found: {snap_id!r}")
    for name, dst in targets.items():
        src = snap_dir / name
        if src.exists():
            atomic_write_bytes(dst, src.read_bytes())
        elif dst.exists():
            try:
                dst.unlink()
            except OSError:
                logger.exception("failed to remove %r during restore", str(dst))


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

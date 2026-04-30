"""Project-internal recycle bin at `data/recycle/`.

NOT the OS recycle bin (no send2trash dependency). 30-day retention
is project-owned per design § 6.4.
"""

from __future__ import annotations

import json
import shutil
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from mame_curator.copy.errors import RecycleError


def recycle_file(
    path: Path,
    *,
    reason: str,
    session_id: str,
    recycle_root: Path = Path("data/recycle"),
) -> Path:
    """Move `path` into `recycle_root/<session_id>/`; write manifest."""
    if not path.exists():
        raise RecycleError("source path does not exist", path=path)

    now = datetime.now(UTC)
    base = recycle_root / session_id
    # Same session, same filename (pathological — recycling identical paths
    # twice in one session): walk a `-1`, `-2`, ... counter on the parent
    # directory. Different sessions never share a directory because
    # session_id is unique per copy run (timestamp + random suffix).
    target_dir = base
    counter = 0
    while (target_dir / path.name).exists():
        counter += 1
        target_dir = base.with_name(f"{base.name}-{counter}")
    target_dir.mkdir(parents=True, exist_ok=True)

    target = target_dir / path.name
    try:
        shutil.move(str(path), str(target))
    except OSError as exc:
        raise RecycleError(f"failed to move to recycle: {exc}", path=path) from exc

    manifest = target_dir / "manifest.json"
    payload = {
        "recycled_at": now.isoformat(),
        "reason": reason,
        "session_id": session_id,
        "original_path": str(path),
    }
    manifest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target


def purge_recycle(
    *,
    older_than: timedelta = timedelta(days=30),
    recycle_root: Path = Path("data/recycle"),
) -> tuple[int, int]:
    """Remove recycle subdirs older than `older_than`; return (dirs_purged, bytes_freed)."""
    if not recycle_root.exists():
        return (0, 0)

    cutoff = time.time() - older_than.total_seconds()
    dirs_purged = 0
    bytes_freed = 0
    for sub in sorted(recycle_root.iterdir()):
        if not sub.is_dir():
            continue
        if sub.stat().st_mtime > cutoff:
            continue
        # Sum sizes before removal.
        for child in sub.rglob("*"):
            if child.is_file():
                bytes_freed += child.stat().st_size
        shutil.rmtree(sub)
        dirs_purged += 1
    return (dirs_purged, bytes_freed)

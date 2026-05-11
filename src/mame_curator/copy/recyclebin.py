"""Project-internal recycle bin at `data/recycle/`.

NOT the OS recycle bin (no send2trash dependency). 30-day retention
is project-owned per design § 6.4.
"""

from __future__ import annotations

import contextlib
import json
import logging
import shutil
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from mame_curator._atomic import atomic_write_text
from mame_curator.copy.errors import RecycleError

logger = logging.getLogger(__name__)


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
    # FP25-C: remember whether target_dir was created by this call so we
    # can rm it on rollback without disturbing a sibling session's dir.
    target_dir_existed = target_dir.exists()
    target_dir.mkdir(parents=True, exist_ok=True)

    target = target_dir / path.name
    try:
        shutil.move(str(path), str(target))
    except OSError as exc:
        if not target_dir_existed:
            with contextlib.suppress(OSError):
                target_dir.rmdir()
        raise RecycleError(f"failed to move to recycle: {exc}", path=path) from exc

    manifest = target_dir / "manifest.json"
    payload = {
        "recycled_at": now.isoformat(),
        "reason": reason,
        "session_id": session_id,
        "original_path": str(path),
    }
    # FP20-B: atomic_write_text via tmp+rename so a crash mid-write
    # leaves the prior manifest intact (or no manifest at all) — never
    # a half-written file. Rule-of-three honoured: copy/playlist.py and
    # cli/__init__.py already use the same helper.
    # FP25-C: on manifest-write failure, roll the move back so the
    # filesystem is in its pre-call state and wrap the OSError in
    # RecycleError. The raw-OSError escape bypassed the typed-error
    # envelope established at the move step above.
    try:
        atomic_write_text(manifest, json.dumps(payload, indent=2))
    except OSError as exc:
        try:
            shutil.move(str(target), str(path))
        except OSError as rollback_exc:
            logger.warning(
                "FP25-C: recycle manifest write failed AND rollback failed; "
                "file remains at %s without manifest. rollback error: %s",
                target,
                rollback_exc,
            )
        else:
            if not target_dir_existed:
                with contextlib.suppress(OSError):
                    target_dir.rmdir()
        raise RecycleError(f"failed to write recycle manifest: {exc}", path=manifest) from exc
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

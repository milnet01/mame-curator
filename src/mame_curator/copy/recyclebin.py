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
from mame_curator.copy.activity import append_activity
from mame_curator.copy.errors import ActivityLogError, RecycleError
from mame_curator.copy.types import (
    ActivityEvent,
    ActivityEventType,
    FileRecycledDetails,
    RecyclePurgedDetails,
)

logger = logging.getLogger(__name__)


def recycle_file(
    path: Path,
    *,
    reason: str,
    session_id: str,
    recycle_root: Path = Path("data/recycle"),
) -> Path:
    """Move `path` into `recycle_root/<session_id>/`; write a per-file manifest.

    FP21-D: per-file ``<basename>.manifest.json`` (was a single
    ``manifest.json`` per dir, which multiple files in the same session
    silently overwrote). The manifest is written **before** the move so
    a failure during the manifest step leaves the source file untouched
    — no rollback path needed. If the manifest write succeeds and the
    move then fails, the manifest is unlinked so the recycle directory
    doesn't accumulate metadata for files that aren't there.
    """
    if not path.exists():
        raise RecycleError("source path does not exist", path=path)

    now = datetime.now(UTC)
    base = recycle_root / session_id
    # Same session, same filename (pathological — recycling identical paths
    # twice in one session): walk a `-1`, `-2`, ... counter on the parent
    # directory. Different basenames share the same dir per FP21-D (each
    # gets its own `<basename>.manifest.json`).
    target_dir = base
    counter = 0
    while (target_dir / path.name).exists():
        counter += 1
        target_dir = base.with_name(f"{base.name}-{counter}")
    # Remember whether target_dir was created by this call so we can
    # rm it on cleanup without disturbing a sibling session's dir.
    target_dir_existed = target_dir.exists()
    target_dir.mkdir(parents=True, exist_ok=True)

    target = target_dir / path.name
    # FP21-D: per-file manifest name. Two recycle_file calls with
    # different basenames coexist; the FP02 counter-on-collision rule
    # still applies for the (rare) same-basename-twice case.
    manifest = target_dir / f"{path.name}.manifest.json"
    payload = {
        "recycled_at": now.isoformat(),
        "reason": reason,
        "session_id": session_id,
        "original_path": str(path),
    }

    # FP21-D: write manifest first. If this fails the source file is
    # untouched (never moved), so there is no rollback to perform — the
    # filesystem is in the same state as before the call. atomic_write_text
    # itself is tmp+rename+fsync (FP20-B) so a crash mid-write leaves no
    # half-written manifest either.
    try:
        atomic_write_text(manifest, json.dumps(payload, indent=2))
    except OSError as exc:
        if not target_dir_existed:
            with contextlib.suppress(OSError):
                target_dir.rmdir()
        raise RecycleError(
            f"failed to write recycle manifest: {exc}",
            path=manifest,
        ) from exc

    # FP21-D: move after manifest is durable. On move failure, unlink
    # the manifest so the recycle tree doesn't accumulate metadata for
    # files that don't exist. The source file remains at its original
    # location either way.
    try:
        shutil.move(str(path), str(target))
    except OSError as exc:
        with contextlib.suppress(OSError):
            manifest.unlink()
        if not target_dir_existed:
            with contextlib.suppress(OSError):
                target_dir.rmdir()
        raise RecycleError(f"failed to move to recycle: {exc}", path=path) from exc

    # FP27 A3: append a FILE_RECYCLED activity event so the Activity UI
    # tab can show the audit trail promised at copy/spec.md:266. Activity
    # log lives at `<recycle_root>.parent / "activity.jsonl"` — under the
    # default `data/recycle/`, that's `data/activity.jsonl` (matches the
    # canonical path append_activity defaults to). Append failures log
    # but don't roll back the recycle: the FS state is the primary
    # contract; missing audit-trail bytes are a soft failure.
    event = ActivityEvent(
        timestamp=now,
        event_type=ActivityEventType.FILE_RECYCLED,
        summary=f"recycled {path.name}",
        session_id=session_id,
        details=FileRecycledDetails(path=str(path), reason=reason),
    )
    try:
        append_activity(event, log_path=recycle_root.parent / "activity.jsonl")
    except ActivityLogError:
        logger.exception("recycle_file: failed to append FILE_RECYCLED event")
    return target


def _latest_recycled_at(sub: Path) -> datetime | None:
    """Return the max ``recycled_at`` across all manifests in ``sub``.

    Supports both the FP21-D per-file ``<basename>.manifest.json`` shape
    and the legacy single ``manifest.json`` shape so a recycle tree
    written before the upgrade still purges correctly. Returns ``None``
    when no readable manifest is present (corrupt JSON, permission
    denied, no matching file at all); ``purge_recycle`` then falls back
    to directory mtime.
    """
    latest: datetime | None = None
    for manifest_path in sub.glob("*.manifest.json"):
        ts = _read_recycled_at(manifest_path)
        if ts is None:
            continue
        if latest is None or ts > latest:
            latest = ts
    legacy = sub / "manifest.json"
    if legacy.exists():
        ts = _read_recycled_at(legacy)
        if ts is not None and (latest is None or ts > latest):
            latest = ts
    return latest


def _read_recycled_at(manifest_path: Path) -> datetime | None:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    ts_str = payload.get("recycled_at") if isinstance(payload, dict) else None
    if not isinstance(ts_str, str):
        return None
    try:
        return datetime.fromisoformat(ts_str)
    except ValueError:
        return None


def purge_recycle(
    *,
    older_than: timedelta = timedelta(days=30),
    recycle_root: Path = Path("data/recycle"),
) -> tuple[int, int]:
    """Remove recycle subdirs older than `older_than`; return (dirs_purged, bytes_freed).

    FP21-F: eligibility is keyed to the latest ``recycled_at`` across
    the dir's manifests (not the dir's mtime, which advances on every
    new file added). Falls back to dir mtime when no readable manifest
    is present. ``bytes_freed`` is accumulated **after** a successful
    ``shutil.rmtree`` so a partial-failure mid-purge doesn't over-report.
    """
    if not recycle_root.exists():
        return (0, 0)

    cutoff = datetime.now(UTC) - older_than
    cutoff_epoch = time.time() - older_than.total_seconds()
    dirs_purged = 0
    bytes_freed = 0
    for sub in sorted(recycle_root.iterdir()):
        if not sub.is_dir():
            continue
        latest_dt = _latest_recycled_at(sub)
        if latest_dt is not None:
            if latest_dt > cutoff:
                continue
        else:
            try:
                if sub.stat().st_mtime > cutoff_epoch:
                    continue
            except OSError:
                continue
        # Sum sizes before removal so a partial failure doesn't leave
        # bytes_freed referencing already-deleted children. The
        # accumulation only commits to the return total if rmtree
        # succeeds.
        sub_bytes = 0
        try:
            for child in sub.rglob("*"):
                if child.is_file():
                    try:
                        sub_bytes += child.stat().st_size
                    except OSError:
                        continue
            shutil.rmtree(sub)
        except OSError:
            logger.exception("purge_recycle: failed to remove %r", str(sub))
            continue
        bytes_freed += sub_bytes
        dirs_purged += 1

    # FP27 A3: append a RECYCLE_PURGED activity event so the Activity UI
    # tab can report retention-policy actions. Uses the sentinel
    # session_id `_purge` (system-scoped action; not bound to any copy
    # session). Append failures log but don't disturb the return value.
    if dirs_purged > 0 or bytes_freed > 0:
        event = ActivityEvent(
            timestamp=datetime.now(UTC),
            event_type=ActivityEventType.RECYCLE_PURGED,
            summary=f"purged {dirs_purged} recycle dirs ({bytes_freed} bytes)",
            session_id="_purge",
            details=RecyclePurgedDetails(dirs_purged=dirs_purged, bytes_freed=bytes_freed),
        )
        try:
            append_activity(event, log_path=recycle_root.parent / "activity.jsonl")
        except ActivityLogError:
            logger.exception("purge_recycle: failed to append RECYCLE_PURGED event")
    return (dirs_purged, bytes_freed)

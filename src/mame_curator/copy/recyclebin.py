"""Project-internal recycle bin at `data/recycle/`.

NOT the OS recycle bin (no send2trash dependency). 30-day retention
is project-owned per design § 6.4.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import secrets
import shutil
import sys
import threading
import time
from collections.abc import Iterator
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

# FP28-A2 lockfile staleness threshold: a lock this caller has watched stay
# unchanged for this long is taken to belong to a crashed process and is
# reclaimed. mame-curator-1201: watched, not aged by its mtime, so a share
# whose clock differs from ours cannot make a live lock look stale.
_LOCK_STALE_SECONDS = 60.0
# mame-curator-1193: a holder writes to its lock this often, so a long move
# (a large cross-drive file) never lets the lock reach the stale age above.
_LOCK_REFRESH_SECONDS = 10.0
# mame-curator-1193: how long a stale lock may refuse to be deleted before the
# wait gives up with a RecycleError naming it.
_LOCK_UNREMOVABLE_SECONDS = 5.0
# mame-curator-1201: the longest a caller waits for the lock, whatever holds
# it: a holder stuck on a dead share keeps its lock fresh for ever. Counted
# in steps capped as below.
_LOCK_WAIT_SECONDS = 600.0
# mame-curator-1201: the most one look at the lock adds to its watched age or
# to the wait, so a jump in this caller's clock (a suspend) counts as little.
_LOCK_WATCH_STEP_CAP = 1.0
# Same-process contention sleep between O_EXCL retry attempts. Short
# enough that the test's ThreadPoolExecutor barrier converges fast
# (~ms), long enough not to busy-loop the CPU.
_LOCK_RETRY_SLEEP = 0.01
# Windows only: how long an unbroken run of PermissionError on the lock may last
# before it counts as a real refusal. See _acquire_lock.
_LOCK_DENIED_RETRY_SECONDS = 5.0
_WINDOWS = sys.platform == "win32"
# Windows opens files in text mode unless told otherwise; the lock holds bytes.
_O_BINARY: int = getattr(os, "O_BINARY", 0)

type _LockSignature = tuple[int, int, int]


@contextlib.contextmanager
def _session_lock(recycle_root: Path, session_id: str) -> Iterator[None]:
    """FP28-A2: O_EXCL atomic lockfile serialising the recycle critical section.

    Wraps the counter walk + ``target_dir.mkdir`` + manifest write + move
    so two parallel ``recycle_file`` calls with the same ``session_id``
    cannot both pass ``target_dir.exists()`` at the same counter value.
    Avoids a ``filelock`` dependency (which pulls ``portalocker`` on
    Windows) by using stdlib ``os.O_EXCL``. mame-curator-1201: the lock holds
    a token, so the holder removes it only while it is still its own.
    """
    recycle_root.mkdir(parents=True, exist_ok=True)
    lock_path = recycle_root / f"{session_id}.lock"
    token = secrets.token_hex(16).encode()
    fd = _acquire_lock(lock_path, token)
    try:
        with _keep_lock_fresh(fd):
            yield
    finally:
        # Closed first: Windows will not delete a file that is open.
        with contextlib.suppress(OSError):
            os.close(fd)
        _release_lock(lock_path, token)


def _acquire_lock(lock_path: Path, token: bytes) -> int:
    """Create the lock holding ``token``; wait, reclaim a stale one, or raise."""
    waited, last_look = 0.0, time.monotonic()
    denied_since: float | None = None
    stuck_since: float | None = None
    watch = _LockWatch()
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | _O_BINARY)
        except PermissionError:
            # Windows is expected to refuse a file whose delete is still pending,
            # so a holder letting go can look like this for a moment. Elsewhere,
            # and once it has lasted, the refusal is real: retrying would spin on
            # a read-only folder for ever.
            now = time.monotonic()
            denied_since = now if denied_since is None else denied_since
            if not _WINDOWS or now - denied_since >= _LOCK_DENIED_RETRY_SECONDS:
                raise
        except FileExistsError:
            denied_since = None  # The lock is held and working; the refusals have ended.
            blocker = None
            if watch.is_stale(_lock_signature(lock_path), time.monotonic()):
                blocker = _reclaim_lock(lock_path, watch.signature)
            if blocker is None:
                stuck_since = None
            else:
                now = time.monotonic()
                stuck_since = now if stuck_since is None else stuck_since
                if now - stuck_since >= _LOCK_UNREMOVABLE_SECONDS:
                    raise RecycleError(
                        "recycle lock is stale and cannot be removed; delete it by hand",
                        path=blocker,
                    ) from None
        else:
            return _write_token(fd, lock_path, token)
        # Counted in capped steps, as _LockWatch counts, so a suspend cannot use it up.
        now = time.monotonic()
        waited, last_look = waited + min(now - last_look, _LOCK_WATCH_STEP_CAP), now
        if waited >= _LOCK_WAIT_SECONDS:
            raise RecycleError("recycle lock stayed in use too long; try again", path=lock_path)
        time.sleep(_LOCK_RETRY_SLEEP)


def _write_token(fd: int, lock_path: Path, token: bytes) -> int:
    try:
        os.write(fd, token)
    except OSError as exc:
        os.close(fd)
        with contextlib.suppress(OSError):
            lock_path.unlink()  # Just made by this caller, so its own.
        raise RecycleError(f"cannot write the recycle lock: {exc}", path=lock_path) from exc
    return fd


def _lock_signature(lock_path: Path) -> _LockSignature | None:
    """What the lock looks like now; None when it is gone or cannot be looked at.

    ``lstat``, so a lock that is a dangling symlink is seen, not followed.
    """
    try:
        st = os.lstat(lock_path)
    except OSError:
        return None
    return (st.st_ino, st.st_size, st.st_mtime_ns)


class _LockWatch:
    """How long this caller has seen the lock stay the same, by its own clock."""

    def __init__(self) -> None:
        self.signature: _LockSignature | None = None
        self._age = 0.0
        self._last_look: float | None = None

    def is_stale(self, signature: _LockSignature | None, now: float) -> bool:
        if signature is None or signature != self.signature:
            self.signature, self._age = signature, 0.0
        elif self._last_look is not None:
            self._age += min(now - self._last_look, _LOCK_WATCH_STEP_CAP)
        self._last_look = now
        return signature is not None and self._age > _LOCK_STALE_SECONDS


def _reclaim_lock(lock_path: Path, stale: _LockSignature | None) -> Path | None:
    """Delete the lock if it is still the stale one; return a file that would not go.

    mame-curator-1201: the ``.reclaim`` guard lets one waiter at a time check and
    delete, so two waiters cannot both reclaim and one delete the other's new lock.
    A lock that changed since it was judged stale is left; None, so look again.
    """
    guard = lock_path.with_name(f"{lock_path.name}.reclaim")
    try:
        os.close(os.open(guard, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
    except OSError:
        return guard  # Another waiter is reclaiming, or its guard was orphaned.
    try:
        if _lock_signature(lock_path) != stale:
            return None
        lock_path.unlink()
    except FileNotFoundError:
        return None
    except OSError:
        return lock_path
    finally:
        with contextlib.suppress(OSError):
            os.unlink(guard)
    return None


def _release_lock(lock_path: Path, token: bytes) -> None:
    """Delete the lock only while it still holds this holder's token (mame-curator-1201)."""
    try:
        owned = lock_path.read_bytes().startswith(token)
    except OSError:
        return  # Gone, or unreadable: not provably ours, so it is left to age out.
    if owned:
        with contextlib.suppress(OSError):
            lock_path.unlink()


@contextlib.contextmanager
def _keep_lock_fresh(fd: int) -> Iterator[None]:
    """Write a byte to the held lock every ``_LOCK_REFRESH_SECONDS`` so it keeps changing.

    mame-curator-1193. A crashed holder stops writing, so its lock stays the same
    and is reclaimed. mame-curator-1201: written through the holder's own open
    file, so it can only ever change the lock it made. Chosen over recording the
    holder's pid: telling whether a pid is alive differs per OS
    (``os.kill(pid, 0)`` terminates the process on Windows), and a reused pid
    would keep a dead lock for ever. ``Event.wait`` paces the thread, so release
    does not wait out an interval.
    """
    stop = threading.Event()

    def _refresh() -> None:
        while not stop.wait(_LOCK_REFRESH_SECONDS):
            with contextlib.suppress(OSError):
                os.write(fd, b".")

    refresher = threading.Thread(target=_refresh, name="recycle-lock-refresh", daemon=True)
    refresher.start()
    try:
        yield
    finally:
        stop.set()
        refresher.join()


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
    # FP28-A2: serialise the counter walk + mkdir + manifest write + move
    # via _session_lock so two parallel calls in the same session_id can't
    # both pass target_dir.exists() at the same counter value. A3 — the
    # two rollback paths below (manifest-write OSError and post-move
    # OSError) both rmdir(target_dir) when target_dir_existed was False;
    # with the lock held, that snapshot can't be invalidated by a sibling
    # call's mkdir(exist_ok=True), so neither rollback can rmdir a dir
    # another session relies on.
    with _session_lock(recycle_root, session_id):
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
        # FP28-A3: target_dir_existed snapshot is race-free under the
        # _session_lock above; the two rollback sites (L below) that
        # rmdir when this is False can no longer touch another session's
        # directory.
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

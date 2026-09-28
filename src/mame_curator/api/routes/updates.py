"""R36 — check for, apply and roll back an app update (mame-curator-1010).

The update logic is ``updates/app.py``; this module owns what that layer may
not touch: ``app.state``, the snapshot, ``data/update-state.json`` and the
activity log (spec §4.3 step 7).
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess  # nosec B404 — only the default `run` seam (subprocess.run) handed to updates/app.py, which calls git and uv with no shell (INV-13).
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse

from mame_curator import __version__
from mame_curator._resources import bundle_root
from mame_curator.api.errors import ApiErrorBody
from mame_curator.api.markdown import render_markdown
from mame_curator.api.persist import snapshot_files, write_json_atomic
from mame_curator.api.schemas import AppUpdateInfo, UpdateApplyResult, UpdatesCheck
from mame_curator.api.state import WorldState
from mame_curator.copy.activity import append_activity
from mame_curator.copy.types import ActivityEvent, ActivityEventType, AppUpdatedDetails
from mame_curator.media import _build_user_agent
from mame_curator.updates.app import (
    DEV_TARGET,
    ReleaseInfo,
    UpdateCheckError,
    UpdateError,
    apply_git_update,
    bundle_target,
    dev_status,
    download_bundle,
    head_commit,
    install_kind,
    is_commit_id,
    is_newer,
    latest_release,
    rollback_git_update,
)
from mame_curator.updates.ini import INI_DEFAULT_SOURCES

logger = logging.getLogger(__name__)

router = APIRouter()

CHECK_TTL_SECONDS = 3600.0
# A failed check (offline, rate-limited) is retried sooner than a good answer.
CHECK_FAILURE_TTL_SECONDS = 300.0
STATE_FILE = "update-state.json"


def init_update_state(app: FastAPI) -> None:
    """Lifespan setup: the lock, the check cache and the seams tests replace."""
    app.state.update_lock = asyncio.Lock()
    app.state.update_cache = {}
    app.state.update_repo = bundle_root()
    app.state.update_run = subprocess.run
    app.state.updates_client = httpx.AsyncClient(
        timeout=30.0, follow_redirects=True, headers={"User-Agent": _build_user_agent()}
    )
    app.state.ini_sources = INI_DEFAULT_SOURCES
    app.state.ini_staged = None
    app.state.started_commit = (
        head_commit(app.state.update_repo) if install_kind() == "git" else None
    )


def install_update_error_handler(app: FastAPI) -> None:
    """Render ``UpdateError`` as the API's error envelope."""

    async def _handler(_: Request, exc: Exception) -> JSONResponse:
        if not isinstance(exc, UpdateError):  # pragma: no cover - guard
            raise exc
        # `detail` is one line (api/spec.md § Error envelope): the output's
        # first line rides along, and the whole of it goes to the log.
        detail = exc.detail
        if exc.output:
            logger.warning("update failed (%s): %s", exc.code, exc.output)
            first = exc.output.strip().splitlines()[0] if exc.output.strip() else ""
            detail = f"{exc.detail}: {first}" if first else exc.detail
        body = ApiErrorBody(detail=detail, code=exc.code)
        return JSONResponse(status_code=exc.status, content=body.model_dump(mode="json"))

    app.add_exception_handler(UpdateError, _handler)


def _read_record(world: WorldState) -> dict[str, Any]:
    try:
        data = json.loads((world.data_dir / STATE_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_record(world: WorldState, record: dict[str, Any]) -> None:
    write_json_atomic(world.data_dir / STATE_FILE, record)


def _log(world: WorldState, old: str, new: str, summary: str) -> None:
    append_activity(
        ActivityEvent(
            timestamp=datetime.now(UTC),
            event_type=ActivityEventType.APP_UPDATED,
            summary=summary,
            session_id="",
            details=AppUpdatedDetails(version_old=old, version_new=new),
        ),
        log_path=world.data_dir / "activity.jsonl",
    )


# --- Check ------------------------------------------------------------------


async def _check_stable(request: Request) -> AppUpdateInfo:
    try:
        release = await latest_release(request.app.state.updates_client)
    except UpdateCheckError as e:
        return AppUpdateInfo(
            current_version=__version__,
            latest_version=None,
            update_available=False,
            check_error=str(e),
        )
    return AppUpdateInfo(
        current_version=__version__,
        latest_version=release.version,
        update_available=is_newer(release.version, __version__),
        notes_html=render_markdown(release.notes_markdown),
        release_url=release.html_url,
    )


async def _check_dev(request: Request) -> AppUpdateInfo:
    state = request.app.state
    try:
        short, behind = await asyncio.to_thread(dev_status, state.update_repo, state.update_run)
    except UpdateCheckError as e:
        return AppUpdateInfo(
            current_version=__version__,
            latest_version=None,
            update_available=False,
            check_error=str(e),
        )
    return AppUpdateInfo(
        current_version=__version__, latest_version=short, update_available=behind > 0
    )


@router.get("/api/updates/check", response_model=UpdatesCheck)
async def updates_check(request: Request, refresh: bool = False) -> UpdatesCheck:
    """Latest version, cached for an hour; never a 5xx (INV-3, INV-4)."""
    state = request.app.state
    world: WorldState = state.world
    kind = install_kind()
    dev = kind == "git" and world.config.updates.channel == "dev"
    key = "dev" if dev else "stable"
    now = time.monotonic()
    hit = state.update_cache.get(key)
    ttl = CHECK_FAILURE_TTL_SECONDS if hit and hit[1].check_error else CHECK_TTL_SECONDS
    if refresh or hit is None or now - hit[0] >= ttl:
        base = await (_check_dev(request) if dev else _check_stable(request))
        state.update_cache[key] = (now, base)
    else:
        base = hit[1]
    record = _read_record(world) if kind == "git" else {}
    to_commit = record.get("to_commit")
    return UpdatesCheck(
        app=base.model_copy(
            update={
                "install_kind": kind,
                "can_apply": kind != "package" and base.update_available,
                "restart_pending": bool(
                    to_commit and state.started_commit and to_commit != state.started_commit
                ),
                "rollback_available": is_commit_id(record.get("previous_commit")),
            }
        )
    )


# --- Apply / rollback ---------------------------------------------------------


def _snapshot_targets(world: WorldState) -> dict[str, Path]:
    parent = world.config_path.parent
    return {
        "config.yaml": world.config_path,
        "overrides.yaml": parent / "overrides.yaml",
        "sessions.yaml": parent / "sessions.yaml",
        "notes.json": world.data_dir / "notes.json",
        "state.yaml": world.data_dir / "state.yaml",
    }


async def _release(request: Request) -> ReleaseInfo:
    try:
        return await latest_release(request.app.state.updates_client)
    except UpdateCheckError as e:
        raise UpdateError("update_fetch_failed", 502, str(e)) from e


async def _newer_release(request: Request) -> ReleaseInfo:
    """The latest release, refused where it is not newer than this one."""
    release = await _release(request)
    if not is_newer(release.version, __version__):
        raise UpdateError(
            "update_not_available", 409, f"{release.version} is not newer than {__version__}"
        )
    return release


def _keep_record(world: WorldState, record: dict[str, Any], log: tuple[str, str] | None) -> None:
    """Write the record and the activity entry; a failure is logged, not raised.

    The tree or the download already changed, so the answer must still say so.
    """
    try:
        _write_record(world, record)
        if log is not None:
            _log(world, log[0], log[1], f"updated to {log[1]}")
    except OSError:
        logger.exception("update applied but its record could not be written")


async def _apply_git(request: Request, world: WorldState) -> UpdateApplyResult:
    state = request.app.state
    if world.config.updates.channel == "dev":
        target, to_version = DEV_TARGET, None
    else:
        release = await _newer_release(request)
        target, to_version = release.tag, release.version
    targets = _snapshot_targets(world)
    result = await asyncio.to_thread(
        apply_git_update,
        state.update_repo,
        target=target,
        before_move=lambda: snapshot_files(world.data_dir / "snapshots", targets),
        run=state.update_run,
    )
    dev = to_version is None
    from_version = result.previous_commit[:7] if dev else __version__
    if result.rolled_back:
        to_version = from_version
    else:
        to_version = result.to_commit[:7] if dev else to_version
        _keep_record(
            world,
            {
                "previous_commit": result.previous_commit,
                "to_commit": result.to_commit,
                "snapshot_id": result.snapshot_id,
                "from_version": from_version,
                "to_version": to_version,
            },
            (from_version, str(to_version)),
        )
    return UpdateApplyResult(
        install_kind="git",
        from_version=from_version,
        to_version=str(to_version),
        rolled_back=result.rolled_back,
        sync_failed=result.sync_failed,
        restart_required=not result.rolled_back,
        snapshot_id=result.snapshot_id,
        output=result.output,
    )


async def _apply_bundle(request: Request, world: WorldState) -> UpdateApplyResult:
    release = await _newer_release(request)
    name, folder = bundle_target(release.version)
    dest = await download_bundle(
        release, name=name, folder=folder, client=request.app.state.updates_client
    )
    _keep_record(
        world,
        {"downloaded_path": str(dest), "from_version": __version__, "to_version": release.version},
        None,
    )
    return UpdateApplyResult(
        install_kind="bundle",
        from_version=__version__,
        to_version=release.version,
        downloaded_path=str(dest),
    )


@router.post("/api/updates/apply", response_model=UpdateApplyResult)
async def updates_apply(request: Request) -> UpdateApplyResult:
    """Update a git clone in place, or download a bundle beside itself."""
    kind = install_kind()
    if kind == "package":
        raise UpdateError("update_not_supported", 409, "a package install cannot update itself")
    lock: asyncio.Lock = request.app.state.update_lock
    if lock.locked():
        raise UpdateError("update_in_progress", 409, "an update is already running")
    async with lock:
        world: WorldState = request.app.state.world
        if kind == "bundle":
            return await _apply_bundle(request, world)
        return await _apply_git(request, world)


@router.post("/api/updates/rollback", response_model=UpdateApplyResult)
async def updates_rollback(request: Request) -> UpdateApplyResult:
    """Reset a git clone to the commit recorded before the last update."""
    if install_kind() != "git":
        raise UpdateError("update_not_supported", 409, "only a git clone can roll back")
    lock: asyncio.Lock = request.app.state.update_lock
    if lock.locked():
        raise UpdateError("update_in_progress", 409, "an update is already running")
    async with lock:
        state = request.app.state
        world: WorldState = state.world
        record = _read_record(world)
        previous = record.get("previous_commit")
        if not is_commit_id(previous):
            raise UpdateError("update_nothing_to_roll_back", 409, "no update is recorded")
        sync_failed = await asyncio.to_thread(
            rollback_git_update, state.update_repo, previous_commit=previous, run=state.update_run
        )
        old, new = str(record.get("to_version", "")), str(record.get("from_version", ""))
        _write_record(
            world,
            {
                "to_commit": previous,
                "snapshot_id": record.get("snapshot_id"),
                "from_version": old,
                "to_version": new,
            },
        )
        _log(world, old, new, f"rolled back to {new}")
        return UpdateApplyResult(
            install_kind="git",
            from_version=old,
            to_version=new,
            sync_failed=sync_failed,
            restart_required=True,
        )

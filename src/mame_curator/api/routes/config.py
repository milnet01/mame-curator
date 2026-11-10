"""R14-R17 — config GET/PATCH and snapshots; export/import are in ``backup.py``."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import ValidationError

from mame_curator.api.errors import (
    ConfigError,
    FieldError,
    SnapshotNotFoundError,
    SnapshotUnusableError,
)
from mame_curator.api.persist import (
    is_snapshot_id,
    list_snapshots,
    restore_snapshot,
    snapshot_files,
    write_yaml_atomic,
)
from mame_curator.api.pictures import load_pictures
from mame_curator.api.routes._deps import get_world, set_world
from mame_curator.api.schemas import (
    AppConfig,
    AppConfigPatch,
    AppConfigResponse,
    Snapshot,
    SnapshotsListing,
)
from mame_curator.api.state import (
    WorldState,
    deep_merge,
    filter_relevant_changed,
    load_app_config,
    replace_world,
    retry_setup,
)
from mame_curator.filter import (
    FilterError,
    load_overrides,
    load_review_state,
    load_sessions,
)

router = APIRouter()


# The page shows `msg` for this type; a `path_` type reads "could not be found".
_SAME_FOLDER_WORDS = "Please choose a different folder from the one holding your games."


def _to_response(
    config: AppConfig, *, restart_required: bool, setup_ended: bool = False
) -> AppConfigResponse:
    return AppConfigResponse(
        paths=config.paths,
        server=config.server,
        filters=config.filters,
        media=config.media,
        ui=config.ui,
        updates=config.updates,
        fs=config.fs,
        restart_required=restart_required,
        setup_ended=setup_ended,
    )


def _restart_required(request: Request) -> bool:
    """Mame-curator-1145 §4.1: asked of the server, so a refetch keeps the prompt."""
    state = request.app.state
    world: WorldState = state.world
    return bool(
        world.config.server != state.started_server
        or (world.setup_required and state.setup_save_kept)
    )


async def _swap_in_and_reply(request: Request, new_world: WorldState) -> AppConfigResponse:
    """Swap in a save, restore or import; in setup mode, retry the DAT.

    mame-curator-1145 §4.1, INV-4, INV-15: the swap comes first, so an
    unexpected failure in the retry cannot leave the running config behind the
    file. Off the event loop, because a full DAT takes seconds to read.
    """
    state = request.app.state
    set_world(request, new_world)
    setup_ended = False
    if new_world.setup_required:
        retried = await asyncio.to_thread(retry_setup, new_world)
        if retried.setup_required:
            state.setup_save_kept = True
        else:
            set_world(request, retried)
            # Computed from the empty library; applying it would put its
            # context over the one just built.
            state.ini_staged = None
            setup_ended = True
    return _to_response(
        new_world.config,
        restart_required=_restart_required(request),
        setup_ended=setup_ended,
    )


def _nul_path_errors(config: AppConfig) -> tuple[FieldError, ...]:
    """A NUL byte reaches `resolve()`, which raises (mame-curator-1145 §4.1)."""
    return tuple(
        FieldError(loc=f"paths.{name}", msg="path holds a NUL byte", type="path_invalid")
        for name, value in config.paths
        if isinstance(value, Path) and "\0" in str(value)
    )


def _same_folder(config: AppConfig, previous: AppConfig) -> bool:
    """Would this save newly make the games folder the destination too?

    A save that changes neither path is not asked, and loading a config never
    runs this, so a config already naming one folder twice keeps working
    (mame-curator-1145 INV-11).
    """
    new, old = config.paths, previous.paths
    if new.source_roms == old.source_roms and new.dest_roms == old.dest_roms:
        return False
    try:
        return new.source_roms.resolve() == new.dest_roms.resolve()
    except OSError:
        return False


def _import_path_errors(config: AppConfig, previous: AppConfig) -> tuple[FieldError, ...]:
    """The save's checks a kept backup can fairly be held to (mame-curator-1177).

    Not existence: a backup may come from another machine, and setup mode or
    the next save reports a folder that is not there.
    """
    nul_errs = _nul_path_errors(config)
    if nul_errs or not _same_folder(config, previous):
        return nul_errs
    return (FieldError(loc="paths.dest_roms", msg=_SAME_FOLDER_WORDS, type="same_folder"),)


def _validate_paths(
    config: AppConfig, previous: AppConfig, *, setup_required: bool = False
) -> tuple[FieldError, ...]:
    """Collect `path_not_found` / `path_invalid` errors for the configured paths.

    mame-curator-1095 § 4.2a: while `setup_required` is true the
    `source_dat` check is **skipped entirely** — the starter config points
    at a DAT that by construction does not exist, so collecting it would
    reject every PATCH the user needs to make to fix it. Every other path
    error stays fatal in setup mode, and the check applies again as soon as
    the DAT parses. The missing DAT is already reported through
    `setup_required` on `SetupCheck` and `build_world`'s warning.
    """
    nul_errs = _nul_path_errors(config)
    if nul_errs:
        return nul_errs
    errs: list[FieldError] = []
    p = config.paths
    if not p.source_roms.exists():
        errs.append(
            FieldError(loc="paths.source_roms", msg="path does not exist", type="path_not_found")
        )
    if not setup_required and not p.source_dat.exists():
        errs.append(
            FieldError(loc="paths.source_dat", msg="path does not exist", type="path_not_found")
        )
    if not p.dest_roms.exists():
        errs.append(
            FieldError(loc="paths.dest_roms", msg="path does not exist", type="path_not_found")
        )
    if not p.retroarch_playlist.parent.exists():
        errs.append(
            FieldError(
                loc="paths.retroarch_playlist",
                msg="parent directory does not exist",
                type="path_not_found",
            )
        )
    # FP28 C1: gates the launch-RetroArch path at games.py:275 — any PATCH
    # that lands a non-executable retroarch path here would otherwise hit
    # subprocess.run with a bad arg. retroarch_core is a shared library
    # (.so / .dll / .dylib) loaded via dlopen / LoadLibrary, so only
    # existence is checked.
    if p.retroarch is not None:
        if sys.platform == "win32":
            # Windows: os.X_OK semantics differ (.exe / .bat / .cmd are
            # marked executable by extension, not POSIX mode bits).
            # shutil.which performs the Windows-correct extension check.
            if shutil.which(str(p.retroarch)) is None:
                errs.append(
                    FieldError(
                        loc="paths.retroarch",
                        msg="path is not an executable file",
                        type="path_invalid",
                    )
                )
        elif not (p.retroarch.exists() and os.access(p.retroarch, os.X_OK)):
            errs.append(
                FieldError(
                    loc="paths.retroarch",
                    msg="path is not an executable file",
                    type="path_invalid",
                )
            )
    if p.retroarch_core is not None and not p.retroarch_core.exists():
        errs.append(
            FieldError(
                loc="paths.retroarch_core",
                msg="path does not exist",
                type="path_invalid",
            )
        )
    if not errs and _same_folder(config, previous):
        errs.append(FieldError(loc="paths.dest_roms", msg=_SAME_FOLDER_WORDS, type="same_folder"))
    return tuple(errs)


@router.get("/api/config", response_model=AppConfigResponse)
def get_config(request: Request, world: WorldState = Depends(get_world)) -> AppConfigResponse:
    return _to_response(world.config, restart_required=_restart_required(request))


@router.patch("/api/config", response_model=AppConfigResponse)
async def patch_config(
    request: Request,
    body: AppConfigPatch,
) -> AppConfigResponse:
    """FP20-C: async + ``world_lock``-guarded read-merge-write-set_world.

    The Depends(get_world) injection is dropped on purpose — under the
    lock we re-read ``request.app.state.world`` so the merge sees the
    most recent committed state, not whatever was current when FastAPI
    started building the dependency graph.

    FP21-N: ``body`` is validated through ``AppConfigPatch`` (per spec
    line 647) before reaching ``deep_merge``. Unknown top-level keys are
    rejected at the FastAPI boundary so bare-dict ingestion can't ship
    arbitrary payloads into the merge. The merge itself is depth-capped
    via ``_MERGE_MAX_DEPTH`` as defence-in-depth.
    """
    async with request.app.state.world_lock:
        world: WorldState = request.app.state.world
        base = world.config.model_dump(mode="json")
        body_dict = body.model_dump(mode="json", exclude_none=True)
        merged = deep_merge(base, body_dict)
        try:
            new_config = AppConfig.model_validate(merged)
        except ValidationError as exc:
            from mame_curator.api.errors import field_errors_from_pydantic

            raise ConfigError(
                "config validation failed",
                fields=field_errors_from_pydantic(exc.errors()),
            ) from exc

        path_errs = _validate_paths(new_config, world.config, setup_required=world.setup_required)
        if path_errs:
            raise ConfigError("config validation failed", fields=path_errs)

        # FP09 B6: short-circuit no-op PATCH so the world (and its
        # filter_result / allowed_roots) preserves identity. Spec § "What does
        # NOT trigger a re-run" plus the P01 hypothesis property. Not in setup
        # mode: a DAT dropped at the configured path is found by this save
        # (mame-curator-1145 INV-3).
        if new_config == world.config and not world.setup_required:
            return _to_response(world.config, restart_required=_restart_required(request))

        snapshots_dir = world.data_dir / "snapshots"
        if world.config_path.exists():
            snapshot_files(snapshots_dir, {"config.yaml": world.config_path})

        write_yaml_atomic(world.config_path, _config_to_yaml(new_config))

        rerun = filter_relevant_changed(world.config, new_config)
        new_world = replace_world(base=world, config=new_config, rerun_filter=rerun)
        # mame-curator-1145 §4.1: in setup mode ANY save retries the DAT,
        # deliberately not just a `source_dat` change: the likeliest recovery
        # leaves the path string unchanged (mame-curator-1095 § 4.2b).
        return await _swap_in_and_reply(request, new_world)


@router.get("/api/config/snapshots", response_model=SnapshotsListing)
def list_config_snapshots(world: WorldState = Depends(get_world)) -> SnapshotsListing:
    items = tuple(Snapshot(**raw) for raw in list_snapshots(world.data_dir / "snapshots"))
    return SnapshotsListing(items=items)


@router.post("/api/config/snapshots/{snap_id}/restore", response_model=AppConfigResponse)
async def restore_config_snapshot(
    snap_id: str,
    request: Request,
) -> AppConfigResponse:
    """FP20-C: async + world_lock-guarded read-merge-write-set_world."""
    async with request.app.state.world_lock:
        world: WorldState = request.app.state.world
        snapshots_dir = world.data_dir / "snapshots"
        snap_dir = snapshots_dir / snap_id
        if not is_snapshot_id(snap_id) or not snap_dir.is_dir():
            raise SnapshotNotFoundError(f"snapshot id not found: {snap_id!r}")

        targets = {
            "config.yaml": world.config_path,
            "overrides.yaml": world.config_path.parent / "overrides.yaml",
            "sessions.yaml": world.config_path.parent / "sessions.yaml",
            "notes.json": world.data_dir / "notes.json",
            "state.yaml": world.data_dir / "state.yaml",
            # mame-curator-1146: a snapshot from before choices does not
            # cover this name, so restore_snapshot leaves the file alone.
            "pictures.json": world.data_dir / "pictures.json",
        }
        # The restore is itself undoable: keep what it is about to replace.
        undo_id = snapshot_files(snapshots_dir, targets, keep=snap_id)

        try:
            restore_snapshot(snapshots_dir, snap_id, targets)
            new_config = load_app_config(world.config_path)
            new_overrides = load_overrides(targets["overrides.yaml"])
            new_sessions = load_sessions(targets["sessions.yaml"])
            new_notes = _read_json_dict(targets["notes.json"])
            new_review_state = load_review_state(targets["state.yaml"])
            new_pictures = load_pictures(targets["pictures.json"])
        except (ConfigError, FilterError, OSError, ValueError) as exc:
            # Otherwise the next save would write the old config over the
            # restored files around it (mame-curator-1145 INV-16). This is also
            # the answer to a snapshot from an older schema (mame-curator-1132).
            restore_snapshot(snapshots_dir, undo_id, targets)
            raise SnapshotUnusableError(f"snapshot {snap_id!r} not restored: {exc!r}") from exc
        new_world = replace_world(
            base=world,
            config=new_config,
            overrides=new_overrides,
            sessions=new_sessions,
            notes=new_notes,
            review_state=new_review_state,
            pictures=new_pictures,
            rerun_filter=True,
        )
        return await _swap_in_and_reply(request, new_world)


def _config_to_yaml(config: AppConfig) -> dict[str, Any]:
    """Dump AppConfig in a form ready for YAML write (Path → str)."""
    out = _stringify(config.model_dump(mode="json"))
    if not isinstance(out, dict):  # pragma: no cover - model_dump always dict
        raise TypeError("config did not serialise to a dict")
    return out


def _stringify(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _stringify(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_stringify(v) for v in obj]
    return obj


def _read_json_dict(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):  # ValueError: bad JSON, or bad UTF-8.
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items()}

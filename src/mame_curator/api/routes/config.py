"""R14-R19 — config GET/PATCH, snapshots, export/import."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Depends, Request
from pydantic import ValidationError

from mame_curator.api.errors import (
    ConfigError,
    FieldError,
    SnapshotNotFoundError,
)
from mame_curator.api.persist import (
    list_snapshots,
    restore_snapshot,
    snapshot_files,
    write_json_atomic,
    write_yaml_atomic,
)
from mame_curator.api.routes._deps import get_world, set_world
from mame_curator.api.schemas import (
    AppConfig,
    AppConfigResponse,
    ConfigExportBundle,
    Snapshot,
    SnapshotsListing,
)
from mame_curator.api.state import (
    WorldState,
    deep_merge,
    filter_relevant_changed,
    load_app_config,
    replace_world,
)
from mame_curator.filter import Overrides, Sessions, load_overrides, load_sessions

router = APIRouter()


def _to_response(config: AppConfig, *, restart_required: bool = False) -> AppConfigResponse:
    return AppConfigResponse(
        paths=config.paths,
        server=config.server,
        filters=config.filters,
        media=config.media,
        ui=config.ui,
        updates=config.updates,
        fs=config.fs,
        restart_required=restart_required,
    )


def _validate_paths(config: AppConfig) -> tuple[FieldError, ...]:
    errs: list[FieldError] = []
    p = config.paths
    if not p.source_roms.exists():
        errs.append(
            FieldError(loc="paths.source_roms", msg="path does not exist", type="path_not_found")
        )
    if not p.source_dat.exists():
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
    return tuple(errs)


@router.get("/api/config", response_model=AppConfigResponse)
def get_config(world: WorldState = Depends(get_world)) -> AppConfigResponse:
    return _to_response(world.config)


@router.patch("/api/config", response_model=AppConfigResponse)
def patch_config(
    request: Request,
    body: dict[str, Any] = Body(...),
    world: WorldState = Depends(get_world),
) -> AppConfigResponse:
    base = world.config.model_dump(mode="json")
    merged = deep_merge(base, body)
    try:
        new_config = AppConfig.model_validate(merged)
    except ValidationError as exc:
        from mame_curator.api.errors import field_errors_from_pydantic

        raise ConfigError(
            "config validation failed",
            fields=field_errors_from_pydantic(exc.errors()),
        ) from exc

    path_errs = _validate_paths(new_config)
    if path_errs:
        raise ConfigError("config validation failed", fields=path_errs)

    snapshots_dir = world.data_dir / "snapshots"
    if world.config_path.exists():
        snapshot_files(snapshots_dir, {"config.yaml": world.config_path})

    write_yaml_atomic(world.config_path, _config_to_yaml(new_config))

    server_changed = new_config.server != world.config.server
    rerun = filter_relevant_changed(world.config, new_config)
    new_world = replace_world(base=world, config=new_config, rerun_filter=rerun)
    set_world(request, new_world)
    return _to_response(new_config, restart_required=server_changed)


@router.get("/api/config/snapshots", response_model=SnapshotsListing)
def list_config_snapshots(world: WorldState = Depends(get_world)) -> SnapshotsListing:
    items = tuple(Snapshot(**raw) for raw in list_snapshots(world.data_dir / "snapshots"))
    return SnapshotsListing(items=items)


@router.post("/api/config/snapshots/{snap_id}/restore", response_model=AppConfigResponse)
def restore_config_snapshot(
    snap_id: str,
    request: Request,
    world: WorldState = Depends(get_world),
) -> AppConfigResponse:
    snapshots_dir = world.data_dir / "snapshots"
    snap_dir = snapshots_dir / snap_id
    if not snap_dir.exists() or not snap_dir.is_dir():
        raise SnapshotNotFoundError(f"snapshot id not found: {snap_id!r}")

    targets = {
        "config.yaml": world.config_path,
        "overrides.yaml": world.config_path.parent / "overrides.yaml",
        "sessions.yaml": world.config_path.parent / "sessions.yaml",
        "notes.json": world.data_dir / "notes.json",
    }
    restore_snapshot(snapshots_dir, snap_id, targets)

    new_config = load_app_config(world.config_path)
    new_overrides = load_overrides(targets["overrides.yaml"])
    new_sessions = load_sessions(targets["sessions.yaml"])
    new_notes = _read_json_dict(targets["notes.json"])
    new_world = replace_world(
        base=world,
        config=new_config,
        overrides=new_overrides,
        sessions=new_sessions,
        notes=new_notes,
        rerun_filter=True,
    )
    set_world(request, new_world)
    return _to_response(new_config)


@router.post("/api/config/export", response_model=ConfigExportBundle)
def export_config(world: WorldState = Depends(get_world)) -> ConfigExportBundle:
    return ConfigExportBundle(
        config=world.config.model_dump(mode="json"),
        overrides={"overrides": dict(world.overrides.entries)},
        sessions={
            "active": world.sessions.active,
            "sessions": {
                k: v.model_dump(mode="json", exclude_defaults=True)
                for k, v in world.sessions.sessions.items()
            },
        },
        notes=dict(world.notes),
    )


@router.post("/api/config/import", response_model=AppConfigResponse)
def import_config(
    bundle: ConfigExportBundle,
    request: Request,
    world: WorldState = Depends(get_world),
) -> AppConfigResponse:
    try:
        new_config = AppConfig.model_validate(bundle.config)
    except ValidationError as exc:
        from mame_curator.api.errors import field_errors_from_pydantic

        raise ConfigError(
            "config import: invalid config",
            fields=field_errors_from_pydantic(exc.errors()),
        ) from exc

    try:
        new_overrides = Overrides.model_validate(bundle.overrides)
    except ValidationError as exc:
        from mame_curator.api.errors import field_errors_from_pydantic

        raise ConfigError(
            "config import: invalid overrides",
            fields=field_errors_from_pydantic(exc.errors()),
        ) from exc

    try:
        new_sessions = Sessions.model_validate(bundle.sessions)
    except ValidationError as exc:
        from mame_curator.api.errors import field_errors_from_pydantic

        raise ConfigError(
            "config import: invalid sessions",
            fields=field_errors_from_pydantic(exc.errors()),
        ) from exc

    snapshots_dir = world.data_dir / "snapshots"
    snapshot_files(
        snapshots_dir,
        {
            "config.yaml": world.config_path,
            "overrides.yaml": world.config_path.parent / "overrides.yaml",
            "sessions.yaml": world.config_path.parent / "sessions.yaml",
            "notes.json": world.data_dir / "notes.json",
        },
    )

    write_yaml_atomic(world.config_path, _config_to_yaml(new_config))
    write_yaml_atomic(
        world.config_path.parent / "overrides.yaml",
        {"overrides": dict(new_overrides.entries)},
    )
    write_yaml_atomic(
        world.config_path.parent / "sessions.yaml",
        {
            "active": new_sessions.active,
            "sessions": {
                k: v.model_dump(mode="json", exclude_defaults=True)
                for k, v in new_sessions.sessions.items()
            },
        },
    )
    write_json_atomic(world.data_dir / "notes.json", bundle.notes)

    new_world = replace_world(
        base=world,
        config=new_config,
        overrides=new_overrides,
        sessions=new_sessions,
        notes=bundle.notes,
        rerun_filter=True,
    )
    set_world(request, new_world)
    return _to_response(new_config)


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
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items()}

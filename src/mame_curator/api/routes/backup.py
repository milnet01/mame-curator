"""R18-R19 — Backup export and import, moved out of ``config.py``.

mame-curator-1146 §4.7: a backup holds the picture choices under
``pictures`` only when there are some, so a backup without choices still
opens in an older release. Importing one without them clears the choices;
the snapshot taken first keeps them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from mame_curator.api.errors import ConfigError, SessionNameInvalidError
from mame_curator.api.persist import (
    restore_snapshot,
    snapshot_files,
    write_json_atomic,
    write_yaml_atomic,
)
from mame_curator.api.pictures import PictureChoices, pictures_path
from mame_curator.api.routes._deps import get_world
from mame_curator.api.routes.config import (
    _config_to_yaml,
    _import_path_errors,
    _swap_in_and_reply,
)
from mame_curator.api.schemas import (
    AppConfig,
    AppConfigResponse,
    ConfigExportBundle,
    merge_picker_into_filters,
)
from mame_curator.api.state import WorldState, replace_world
from mame_curator.filter import Overrides, Sessions

router = APIRouter()


@router.post("/api/config/export", response_model=ConfigExportBundle)
def export_config(world: WorldState = Depends(get_world)) -> JSONResponse:
    """The whole setup; ``pictures`` only when a choice exists (1146 §4.7)."""
    extra: dict[str, Any] = {}
    if world.pictures.pictures:
        extra["pictures"] = world.pictures.model_dump(mode="json")
    bundle = ConfigExportBundle(
        config=world.config.model_dump(mode="json"),
        overrides={"overrides": dict(world.overrides.entries)},
        sessions=_sessions_dump(world.sessions),
        notes=dict(world.notes),
        **extra,
    )
    # exclude_unset drops only an unset `pictures`; exclude_none would also
    # drop the nulls inside `config`, which the backup holds.
    return JSONResponse(bundle.model_dump(mode="json", exclude_unset=True))


def _sessions_dump(sessions: Sessions) -> dict[str, Any]:
    return {
        "active": sessions.active,
        "sessions": {
            k: v.model_dump(mode="json", exclude_defaults=True)
            for k, v in sessions.sessions.items()
        },
    }


def _validated[M: BaseModel](model: type[M], data: object, what: str) -> M:
    """``model`` from ``data``, or 422 naming ``what`` with its field errors."""
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        from mame_curator.api.errors import field_errors_from_pydantic

        raise ConfigError(
            f"config import: invalid {what}",
            fields=field_errors_from_pydantic(exc.errors()),
        ) from exc


@dataclass(frozen=True)
class _Bundle:
    """A backup that passed every check, ready to write."""

    config: AppConfig
    overrides: Overrides
    sessions: Sessions
    notes: dict[str, str]
    pictures: PictureChoices


def _check_bundle(bundle: ConfigExportBundle, world: WorldState) -> _Bundle:
    """Validate every part before anything is written."""
    # versioning-overrides item 1: the same old forms load_app_config reads.
    try:
        raw_config = merge_picker_into_filters(dict(bundle.config))
    except ValueError as exc:
        raise ConfigError(f"config import: {exc}") from exc
    # mame-curator-1225 (user decision 2026-11-11): a restore never grants
    # folder access; the grants in force stay, and the user approves again.
    new_config = _validated(AppConfig, raw_config, "config").model_copy(
        update={"fs": world.config.fs}
    )
    new_overrides = _validated(Overrides, bundle.overrides, "overrides")
    new_sessions = _validated(Sessions, bundle.sessions, "sessions")
    # Absent means no choices (1146 §4.7).
    pictures = _validated(PictureChoices, bundle.pictures or {}, "pictures")

    # FP09 A3: R11 (POST /api/sessions) enforces `_SESSION_NAME_RE`; R19's
    # import path was bypassing it, so a malicious bundle could write a
    # session named `_deactivate` (or any reserved control name) into
    # sessions.yaml. Re-apply the regex per session-name on import.
    from mame_curator.api.routes.curate import _SESSION_NAME_RE

    for name in new_sessions.sessions:
        if not _SESSION_NAME_RE.fullmatch(name):
            raise SessionNameInvalidError(f"session name invalid in import: {name!r}")

    path_errs = _import_path_errors(new_config, world.config)
    if path_errs:
        raise ConfigError("config import: invalid paths", fields=path_errs)
    return _Bundle(new_config, new_overrides, new_sessions, dict(bundle.notes), pictures)


def _write_bundle(world: WorldState, new: _Bundle) -> None:
    """Snapshot every target, then write each; a failure puts them back.

    Each write is atomic but the five together are not. A crash between
    writes leaves a mixed set, and that snapshot, listed in Settings, is the
    way back.
    """
    snapshots_dir = world.data_dir / "snapshots"
    pictures_file = pictures_path(world.data_dir)
    targets = {
        "config.yaml": world.config_path,
        "overrides.yaml": world.config_path.parent / "overrides.yaml",
        "sessions.yaml": world.config_path.parent / "sessions.yaml",
        "notes.json": world.data_dir / "notes.json",
        "pictures.json": pictures_file,
    }
    undo_id = snapshot_files(snapshots_dir, targets)
    try:
        write_yaml_atomic(world.config_path, _config_to_yaml(new.config))
        write_yaml_atomic(targets["overrides.yaml"], {"overrides": dict(new.overrides.entries)})
        write_yaml_atomic(targets["sessions.yaml"], _sessions_dump(new.sessions))
        write_json_atomic(targets["notes.json"], new.notes)
        if new.pictures.pictures or pictures_file.exists():
            write_json_atomic(pictures_file, new.pictures.model_dump(mode="json"))
    except OSError:
        restore_snapshot(snapshots_dir, undo_id, targets)
        raise


@router.post("/api/config/import", response_model=AppConfigResponse)
async def import_config(
    bundle: ConfigExportBundle,
    request: Request,
) -> AppConfigResponse:
    """FP20-C: async + world_lock-guarded read-merge-write-set_world."""
    async with request.app.state.world_lock:
        world: WorldState = request.app.state.world
        new = _check_bundle(bundle, world)
        _write_bundle(world, new)
        new_world = replace_world(
            base=world,
            config=new.config,
            overrides=new.overrides,
            sessions=new.sessions,
            notes=new.notes,
            pictures=new.pictures,
            rerun_filter=True,
        )
        return await _swap_in_and_reply(request, new_world)

"""R29-R34 — sandbox listing + allowed-roots grant API."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request

from mame_curator.api.errors import (
    FsAlreadyCoveredError,
    FsConfigRootNotRevocableError,
    FsPathInvalidError,
    FsRootNotFoundError,
)
from mame_curator.api.fs import (
    os_drive_roots,
    resolve_path,
    validate_fs_path,
)
from mame_curator.api.persist import snapshot_files, write_yaml_atomic
from mame_curator.api.routes._deps import get_world, set_world
from mame_curator.api.schemas import (
    AppConfig,
    FsAllowedRoot,
    FsAllowedRoots,
    FsConfig,
    FsDriveRoots,
    FsEntry,
    FsGrantRootRequest,
    FsListing,
    FsPath,
)
from mame_curator.api.state import WorldState, replace_world

router = APIRouter()


@router.get("/api/fs/list", response_model=FsListing)
def fs_list(path: str, world: WorldState = Depends(get_world)) -> FsListing:
    requested = validate_fs_path(path, world.allowed_roots, require_dir=True)
    entries: list[FsEntry] = []
    try:
        for child in sorted(requested.iterdir()):
            try:
                stat = child.stat()
            except OSError:
                continue
            entries.append(
                FsEntry(
                    name=child.name,
                    path=str(child),
                    is_dir=child.is_dir(),
                    size=stat.st_size if not child.is_dir() else None,
                    mtime=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
                )
            )
    except OSError as exc:
        raise FsPathInvalidError(f"failed to list {str(requested)!r}: {exc}") from exc

    parent: str | None = None
    for root in world.allowed_roots:
        if str(requested) == root.path:
            parent = None
            break
    else:
        if requested.parent != requested:
            parent = str(requested.parent)
    return FsListing(path=str(requested), entries=tuple(entries), parent=parent)


@router.get("/api/fs/home", response_model=FsPath)
def fs_home() -> FsPath:
    return FsPath(path=str(Path.home()))


@router.get("/api/fs/roots", response_model=FsDriveRoots)
def fs_drive_roots() -> FsDriveRoots:
    return FsDriveRoots(roots=os_drive_roots())


@router.get("/api/fs/allowed-roots", response_model=FsAllowedRoots)
def fs_allowed_roots(world: WorldState = Depends(get_world)) -> FsAllowedRoots:
    return FsAllowedRoots(roots=world.allowed_roots)


@router.post("/api/fs/allowed-roots", response_model=FsAllowedRoots)
def fs_grant_root(
    body: FsGrantRootRequest,
    request: Request,
    world: WorldState = Depends(get_world),
) -> FsAllowedRoots:
    candidate = resolve_path(body.path)
    if not candidate.exists() or not candidate.is_dir():
        raise FsPathInvalidError(f"path is not an existing directory: {str(candidate)!r}")
    for root in world.allowed_roots:
        try:
            if candidate.is_relative_to(Path(root.path)):
                raise FsAlreadyCoveredError(f"path already covered by allowlist root {root.path!r}")
        except ValueError:
            continue

    new_granted = (*world.config.fs.granted_roots, candidate)
    new_fs = FsConfig(granted_roots=new_granted)
    new_config = world.config.model_copy(update={"fs": new_fs})

    snapshots_dir = world.data_dir / "snapshots"
    if world.config_path.exists():
        snapshot_files(snapshots_dir, {"config.yaml": world.config_path})
    write_yaml_atomic(world.config_path, _config_to_yaml(new_config))

    new_world = replace_world(base=world, config=new_config)
    set_world(request, new_world)
    return FsAllowedRoots(roots=new_world.allowed_roots)


@router.delete("/api/fs/allowed-roots/{root_id}", response_model=FsAllowedRoots)
def fs_revoke_root(
    root_id: str,
    request: Request,
    world: WorldState = Depends(get_world),
) -> FsAllowedRoots:
    target: FsAllowedRoot | None = None
    for r in world.allowed_roots:
        if r.id == root_id:
            target = r
            break
    if target is None:
        raise FsRootNotFoundError(f"allowlist root not found: {root_id!r}")
    if target.source == "config":
        raise FsConfigRootNotRevocableError(
            f"config-derived roots are not user-revocable: {root_id!r}"
        )

    target_path = Path(target.path).resolve(strict=False)
    new_granted = tuple(
        p for p in world.config.fs.granted_roots if Path(p).resolve(strict=False) != target_path
    )
    new_fs = FsConfig(granted_roots=new_granted)
    new_config = world.config.model_copy(update={"fs": new_fs})

    snapshots_dir = world.data_dir / "snapshots"
    if world.config_path.exists():
        snapshot_files(snapshots_dir, {"config.yaml": world.config_path})
    write_yaml_atomic(world.config_path, _config_to_yaml(new_config))

    new_world = replace_world(base=world, config=new_config)
    set_world(request, new_world)
    return FsAllowedRoots(roots=new_world.allowed_roots)


def _config_to_yaml(config: AppConfig) -> dict[str, Any]:
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

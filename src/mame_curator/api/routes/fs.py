"""R29-R34 — sandbox listing + allowed-roots grant API."""

from __future__ import annotations

import stat
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request

from mame_curator.api.errors import (
    FsAlreadyCoveredError,
    FsConfigRootNotRevocableError,
    FsFolderExistsError,
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
    FsMakeFolderRequest,
    FsPath,
)
from mame_curator.api.state import WorldState, replace_world

router = APIRouter()


def is_hidden(name: str, st: object) -> bool:
    """Hidden as the user's own system counts it: a dot, or its mark on the file."""
    return (
        name.startswith(".")
        or bool(getattr(st, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_HIDDEN)  # Windows
        or bool(getattr(st, "st_flags", 0) & stat.UF_HIDDEN)  # macOS
    )


def _fs_entry(child: Path) -> FsEntry | None:
    """One row, or None for one the picker cannot show. One odd entry never stops a listing."""
    try:
        child.name.encode("utf-8")  # A name that is not UTF-8 cannot travel as JSON.
        st = child.stat()
    except (OSError, UnicodeEncodeError):
        return None
    is_dir = stat.S_ISDIR(st.st_mode)
    try:
        mtime = datetime.fromtimestamp(st.st_mtime, tz=UTC)
    except (OverflowError, OSError, ValueError):
        # A date the clock cannot express says nothing about the file, so it stays.
        mtime = datetime.fromtimestamp(0, tz=UTC)
    return FsEntry(
        name=child.name,
        path=str(child),
        is_dir=is_dir,
        hidden=is_hidden(child.name, st),
        size=None if is_dir else st.st_size,
        mtime=mtime,
    )


@router.get("/api/fs/list", response_model=FsListing)
def fs_list(path: str, world: WorldState = Depends(get_world)) -> FsListing:
    requested = validate_fs_path(path, world.allowed_roots, require_dir=True)
    try:
        entries = [entry for child in sorted(requested.iterdir()) if (entry := _fs_entry(child))]
    except OSError as exc:
        # FP09 A1: repr-quote `exc` so a multi-line OSError str can't break
        # the FP06-FP08 single-line `detail` invariant.
        raise FsPathInvalidError(f"failed to list {str(requested)!r}: {exc!r}") from exc

    # FP09 B7: simplified from a dead-branch for-else. `parent` is the next
    # navigable ancestor — None when at an allowlist root, or when going up
    # would leave the sandbox (the Browse UI mustn't offer a click that
    # immediately 403s).
    parent: str | None = None
    is_root = any(str(requested) == r.path for r in world.allowed_roots)
    if not is_root and requested.parent != requested:
        candidate = requested.parent
        if any(candidate.is_relative_to(Path(r.path)) for r in world.allowed_roots):
            parent = str(candidate)
    return FsListing(path=str(requested), entries=tuple(entries), parent=parent)


# ext4's limit, in bytes. NTFS and APFS count characters, so allow at least this.
_MAX_NAME_BYTES = 255


def _check_folder_name(name: str) -> None:
    """One folder's name, the same on every system the app runs on."""
    try:
        fits = len(name.encode("utf-8")) <= _MAX_NAME_BYTES
    except UnicodeEncodeError:  # A lone surrogate can arrive in JSON; no disk takes it.
        fits = False
    if (
        not name
        or not fits
        or any(c in name for c in "/\\\0")
        # Covers "." and "..". Windows drops a trailing dot or space, so the
        # folder made would not be the one named.
        or name.endswith((".", " "))
    ):
        raise FsPathInvalidError(f"not a usable folder name: {name!r}")


@router.post("/api/fs/folders", response_model=FsPath)
def fs_make_folder(body: FsMakeFolderRequest, world: WorldState = Depends(get_world)) -> FsPath:
    """mame-curator-1169: make one folder, only inside an allowed root."""
    parent = validate_fs_path(body.parent, world.allowed_roots, require_dir=True)
    _check_folder_name(body.name)
    target = parent / body.name
    try:
        target.mkdir()
    except FileExistsError as exc:
        raise FsFolderExistsError(f"already there: {str(target)!r}") from exc
    except OSError as exc:
        raise FsPathInvalidError(f"failed to make {str(target)!r}: {exc!r}") from exc
    return FsPath(path=str(target))


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
async def fs_grant_root(
    body: FsGrantRootRequest,
    request: Request,
) -> FsAllowedRoots:
    """FP20-C: async + world_lock-guarded read-merge-write-set_world."""
    async with request.app.state.world_lock:
        world: WorldState = request.app.state.world
        candidate = resolve_path(body.path)
        if not candidate.exists() or not candidate.is_dir():
            raise FsPathInvalidError(f"path is not an existing directory: {str(candidate)!r}")
        for root in world.allowed_roots:
            try:
                if candidate.is_relative_to(Path(root.path)):
                    raise FsAlreadyCoveredError(
                        f"path already covered by allowlist root {root.path!r}"
                    )
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
async def fs_revoke_root(
    root_id: str,
    request: Request,
) -> FsAllowedRoots:
    """FP20-C: async + world_lock-guarded read-merge-write-set_world."""
    async with request.app.state.world_lock:
        world: WorldState = request.app.state.world
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

"""R08-R13b — overrides + sessions."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, Request

from mame_curator.api.errors import (
    OverrideNotFoundError,
    SessionNameInvalidError,
    SessionNotFoundError,
)
from mame_curator.api.persist import write_yaml_atomic
from mame_curator.api.routes._deps import get_world, set_world
from mame_curator.api.schemas import (
    EmptyBody,
    OverridePostRequest,
    OverridesView,
    SessionsListing,
    SessionUpsertRequest,
)
from mame_curator.api.state import WorldState, replace_world
from mame_curator.filter import Overrides, Sessions

_SESSION_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")

router = APIRouter()


def _persist_overrides(world: WorldState, overrides: Overrides) -> None:
    path = world.config_path.parent / "overrides.yaml"
    snapshots_dir = world.data_dir / "snapshots"
    from mame_curator.api.persist import snapshot_files

    if path.exists():
        snapshot_files(snapshots_dir, {"overrides.yaml": path})
    write_yaml_atomic(path, {"overrides": dict(overrides.entries)})


def _persist_sessions(world: WorldState, sessions: Sessions) -> None:
    path = world.config_path.parent / "sessions.yaml"
    snapshots_dir = world.data_dir / "snapshots"
    from mame_curator.api.persist import snapshot_files

    if path.exists():
        snapshot_files(snapshots_dir, {"sessions.yaml": path})
    write_yaml_atomic(
        path,
        {
            "active": sessions.active,
            "sessions": {
                k: v.model_dump(mode="json", exclude_defaults=True)
                for k, v in sessions.sessions.items()
            },
        },
    )


@router.post("/api/overrides", response_model=OverridesView)
async def post_override(
    body: OverridePostRequest,
    request: Request,
) -> OverridesView:
    """FP25-A: async + ``world_lock``-guarded read-merge-write-set_world."""
    async with request.app.state.world_lock:
        world: WorldState = request.app.state.world
        entries = dict(world.overrides.entries)
        entries[body.parent] = body.winner
        new_overrides = Overrides.model_validate({"entries": entries})
        _persist_overrides(world, new_overrides)
        new_world = replace_world(base=world, overrides=new_overrides)
        set_world(request, new_world)
        return OverridesView(
            entries=dict(new_overrides.entries),
            warnings=new_world.filter_result.warnings,
        )


@router.delete("/api/overrides/{parent}", response_model=OverridesView)
async def delete_override(
    parent: str,
    request: Request,
) -> OverridesView:
    """FP25-A: async + ``world_lock``-guarded read-merge-write-set_world."""
    async with request.app.state.world_lock:
        world: WorldState = request.app.state.world
        if parent not in world.overrides.entries:
            raise OverrideNotFoundError(f"no override for parent {parent!r}")
        entries = dict(world.overrides.entries)
        del entries[parent]
        new_overrides = Overrides.model_validate({"entries": entries})
        _persist_overrides(world, new_overrides)
        new_world = replace_world(base=world, overrides=new_overrides)
        set_world(request, new_world)
        return OverridesView(entries=dict(new_overrides.entries))


def _listing(sessions: Sessions) -> SessionsListing:
    return SessionsListing(active=sessions.active, sessions=dict(sessions.sessions))


@router.get("/api/sessions", response_model=SessionsListing)
def list_sessions(world: WorldState = Depends(get_world)) -> SessionsListing:
    return _listing(world.sessions)


@router.post("/api/sessions", response_model=SessionsListing)
async def upsert_session(
    body: SessionUpsertRequest,
    request: Request,
) -> SessionsListing:
    """FP25-A: async + ``world_lock``-guarded read-merge-write-set_world.

    Name validation happens before the lock acquire — a 422 on a bad name
    is read-only and shouldn't block a concurrent good-name writer.
    """
    if not _SESSION_NAME_RE.match(body.name):
        raise SessionNameInvalidError(f"session name invalid: {body.name!r}")
    async with request.app.state.world_lock:
        world: WorldState = request.app.state.world
        sessions_map = dict(world.sessions.sessions)
        sessions_map[body.name] = body.session
        new_sessions = Sessions(active=world.sessions.active, sessions=sessions_map)
        _persist_sessions(world, new_sessions)
        new_world = replace_world(base=world, sessions=new_sessions)
        set_world(request, new_world)
        return _listing(new_sessions)


@router.delete("/api/sessions/{name}", response_model=SessionsListing)
async def delete_session(
    name: str,
    request: Request,
) -> SessionsListing:
    """FP25-A: async + ``world_lock``-guarded read-merge-write-set_world."""
    async with request.app.state.world_lock:
        world: WorldState = request.app.state.world
        if name not in world.sessions.sessions:
            raise SessionNotFoundError(f"session not found: {name!r}")
        sessions_map = dict(world.sessions.sessions)
        del sessions_map[name]
        new_active = None if world.sessions.active == name else world.sessions.active
        new_sessions = Sessions(active=new_active, sessions=sessions_map)
        _persist_sessions(world, new_sessions)
        new_world = replace_world(base=world, sessions=new_sessions)
        set_world(request, new_world)
        return _listing(new_sessions)


# R13b: deactivate (distinct from /sessions/{name}/activate so a session named
# "_deactivate" can't collide). MUST be declared BEFORE the dynamic
# /api/sessions/{name}/activate route so FastAPI matches the static path first.
@router.post("/api/sessions/_deactivate", response_model=SessionsListing)
async def deactivate_session(
    body: EmptyBody,
    request: Request,
) -> SessionsListing:
    """FP25-A: async + ``world_lock``-guarded read-merge-write-set_world."""
    async with request.app.state.world_lock:
        world: WorldState = request.app.state.world
        new_sessions = Sessions(active=None, sessions=dict(world.sessions.sessions))
        _persist_sessions(world, new_sessions)
        new_world = replace_world(base=world, sessions=new_sessions)
        set_world(request, new_world)
        return _listing(new_sessions)


@router.post("/api/sessions/{name}/activate", response_model=SessionsListing)
async def activate_session(
    name: str,
    body: EmptyBody,
    request: Request,
) -> SessionsListing:
    """FP25-A: async + ``world_lock``-guarded read-merge-write-set_world."""
    async with request.app.state.world_lock:
        world: WorldState = request.app.state.world
        if name not in world.sessions.sessions:
            raise SessionNotFoundError(f"session not found: {name!r}")
        new_sessions = Sessions(active=name, sessions=dict(world.sessions.sessions))
        _persist_sessions(world, new_sessions)
        new_world = replace_world(base=world, sessions=new_sessions)
        set_world(request, new_world)
        return _listing(new_sessions)

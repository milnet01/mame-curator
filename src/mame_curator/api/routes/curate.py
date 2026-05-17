"""R08-R13b — overrides + sessions. P14 — per-game review state routes."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request

from mame_curator.api.errors import (
    GameNotFoundError,
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
    StatePostRequest,
    StateView,
)
from mame_curator.api.state import WorldState, replace_world
from mame_curator.copy.activity import append_activity
from mame_curator.copy.types import (
    ActivityEvent,
    ActivityEventType,
    ReviewStateDetails,
)
from mame_curator.filter import Overrides, ReviewState, Sessions

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


# P14 — per-game review state ------------------------------------------------


def _persist_review_state(world: WorldState, review_state: ReviewState) -> None:
    """Atomic YAML write — no per-change snapshot (spec §"Snapshot policy").

    State writes are keypress-frequency; snapshotting would churn the 200-entry
    LRU pool and evict every overrides / sessions / config snapshot in minutes.
    Recovery is via ``data/activity.jsonl`` replay.
    """
    path = world.config_path.parent / "data" / "state.yaml"
    write_yaml_atomic(path, {"state": dict(review_state.entries)})


def _build_review_event(
    short_name: str,
    state: str,
    previous: str,
) -> ActivityEvent:
    """Construct the ``review_state`` ActivityEvent for a single transition.

    ``state`` / ``previous`` are plain strings — the activity log records the
    literal transition including the sparse-store sentinel ``"pending"``,
    which the storage enum (:class:`ReviewStateValue`) excludes by design.

    ``session_id`` is the empty string per spec — review state is a global
    per-game annotation, not a job-scoped event.
    """
    summary = f"cleared {short_name}" if state == "pending" else f"marked {short_name} as {state}"
    return ActivityEvent(
        timestamp=datetime.now(UTC),
        event_type=ActivityEventType.REVIEW_STATE,
        summary=summary,
        session_id="",
        details=ReviewStateDetails(
            short_name=short_name,
            state=state,
            previous=previous,
        ),
    )


@router.get("/api/state", response_model=StateView)
def get_state(world: WorldState = Depends(get_world)) -> StateView:
    """Full review-state map — hydrated by the frontend on page load."""
    return StateView(entries=dict(world.review_state.entries))


@router.post("/api/state", response_model=StateView)
async def post_state(body: StatePostRequest, request: Request) -> StateView:
    """Set a non-pending state on a known game.

    INV-13 — a same-value re-post is a no-op: no YAML write, no activity
    event, returns current state at 200.
    """
    async with request.app.state.world_lock:
        world: WorldState = request.app.state.world
        if body.short_name not in world.machines:
            raise GameNotFoundError(f"game not found: {body.short_name!r}")

        previous_enum = world.review_state.entries.get(body.short_name)
        if previous_enum == body.state:
            # INV-13: no-op write skip.
            return StateView(entries=dict(world.review_state.entries))

        entries = dict(world.review_state.entries)
        entries[body.short_name] = body.state
        new_state = ReviewState.model_validate({"entries": entries})

        # Disk-write order: persist YAML before activity append before world
        # swap. A YAML failure raises 500 with state unchanged. An activity
        # failure after a successful YAML write leaves on-disk state ahead
        # of the log; recovery walks the YAML (source of truth).
        _persist_review_state(world, new_state)
        previous_str = previous_enum.value if previous_enum is not None else "pending"
        append_activity(
            _build_review_event(body.short_name, body.state.value, previous_str),
            log_path=world.data_dir / "activity.jsonl",
        )

        new_world = replace_world(base=world, review_state=new_state)
        set_world(request, new_world)
        return StateView(entries=dict(new_state.entries))


@router.delete("/api/state/{short_name}", response_model=StateView)
async def delete_state(short_name: str, request: Request) -> StateView:
    """Clear a game's review state back to pending.

    INV-13 — DELETE on a game already at pending is a no-op: no YAML write,
    no activity event, returns current state at 200.
    """
    async with request.app.state.world_lock:
        world: WorldState = request.app.state.world
        if short_name not in world.machines:
            raise GameNotFoundError(f"game not found: {short_name!r}")

        previous_enum = world.review_state.entries.get(short_name)
        if previous_enum is None:
            # INV-13: no-op write skip (entry already absent).
            return StateView(entries=dict(world.review_state.entries))

        entries = dict(world.review_state.entries)
        del entries[short_name]
        new_state = ReviewState.model_validate({"entries": entries})

        _persist_review_state(world, new_state)
        append_activity(
            _build_review_event(short_name, "pending", previous_enum.value),
            log_path=world.data_dir / "activity.jsonl",
        )

        new_world = replace_world(base=world, review_state=new_state)
        set_world(request, new_world)
        return StateView(entries=dict(new_state.entries))

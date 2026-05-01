"""Shared dependencies for route handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request

if TYPE_CHECKING:
    from mame_curator.api.jobs import JobManager
    from mame_curator.api.state import WorldState


def get_world(request: Request) -> WorldState:
    return request.app.state.world  # type: ignore[no-any-return]


def get_jobs(request: Request) -> JobManager:
    return request.app.state.job  # type: ignore[no-any-return]


def set_world(request: Request, world: WorldState) -> None:
    request.app.state.world = world

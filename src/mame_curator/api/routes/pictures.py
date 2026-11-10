"""mame-curator-1146 — list a game's pictures, save a choice, clear it.

Per ``docs/specs/mame-curator-1146-picture-choice.md`` §4.4. The choice is a
``(source, kind)`` pair; the save checks only that the card could be served
from it, and fetches nothing.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, Request

from mame_curator.api.errors import GameNotFoundError
from mame_curator.api.pictures import PictureChoice, PictureChoices, write_pictures
from mame_curator.api.routes import media as media_routes
from mame_curator.api.routes._deps import get_world, set_world
from mame_curator.api.schemas_pictures import (
    PictureCandidate,
    PictureCandidates,
    PictureChoiceView,
)
from mame_curator.api.state import WorldState, replace_world
from mame_curator.media import (
    Found,
    MediaError,
    MediaSourceRegistry,
    file_digest,
    list_candidates,
    resolve_image_found,
    resolve_pair,
)
from mame_curator.parser.models import Machine

router = APIRouter()


def _machine(world: WorldState, name: str) -> Machine:
    machine = world.machines.get(name)
    if machine is None:
        raise GameNotFoundError(f"game not found: {name!r}")
    return machine


async def _in_use(
    machine: Machine,
    chosen: PictureChoice | None,
    registry: MediaSourceRegistry,
    fetch: dict[str, Any],
) -> tuple[Found | None, bool]:
    """The picture the card shows now, and False when a stored choice missed."""
    if chosen is not None:
        try:
            path = await resolve_pair(
                machine, chosen.source, chosen.kind, registry=registry, **fetch
            )
        except MediaError:
            path = None
        if path is not None:
            return Found(source=chosen.source, kind=chosen.kind, path=path), True
    found = await resolve_image_found(machine, "boxart", registry=registry, **fetch)
    return found, chosen is None


async def _ordered(found: tuple[Found, ...], in_use: Found | None) -> list[PictureCandidate]:
    """The in-use picture first, marked; the rest in the listing's order."""
    rest = [PictureCandidate(source=f.source, kind=f.kind, in_use=False) for f in found]
    if in_use is None:
        return rest
    digest = await asyncio.to_thread(file_digest, in_use.path)
    head = PictureCandidate(source=in_use.source, kind=in_use.kind, in_use=True)
    for i, f in enumerate(found):
        if await asyncio.to_thread(file_digest, f.path) == digest:
            head = rest.pop(i).model_copy(update={"in_use": True})
            break
    return [head, *rest]


@router.get("/api/games/{name}/picture/candidates", response_model=PictureCandidates)
async def get_picture_candidates(
    name: str,
    request: Request,
    further: bool = False,
    world: WorldState = Depends(get_world),
) -> PictureCandidates:
    """Every picture for the game; ``further`` also asks the rate-limited sources."""
    machine = _machine(world, name)
    registry = media_routes.request_registry(request, world)
    fetch: dict[str, Any] = {
        "cache_dir": world.config.media.cache_dir,
        "client": request.app.state.media_client,
    }
    chosen = world.pictures.pictures.get(name)
    in_use, chosen_found = await _in_use(machine, chosen, registry, fetch)
    listing = await list_candidates(machine, registry=registry, ask_limited=further, **fetch)
    return PictureCandidates(
        short_name=name,
        chosen=chosen,
        chosen_found=chosen_found,
        candidates=tuple(await _ordered(listing.found, in_use)),
        not_asked=listing.not_asked,
        not_answered=listing.not_answered,
    )


def _swap_pictures(request: Request, world: WorldState, pictures: dict[str, PictureChoice]) -> None:
    """Write the choices, then swap the world; a failed write changes nothing."""
    choices = PictureChoices(pictures=pictures)
    write_pictures(world.data_dir, choices)
    set_world(request, replace_world(base=world, pictures=choices))


@router.put("/api/games/{name}/picture", response_model=PictureChoiceView)
async def put_picture(name: str, body: PictureChoice, request: Request) -> PictureChoiceView:
    """Save a choice the card could be served from; fetch nothing (INV-9)."""
    world: WorldState = request.app.state.world
    _machine(world, name)
    registry = media_routes.request_registry(request, world)
    media_routes.require_in_chain(registry, body.source, body.kind)
    async with request.app.state.world_lock:
        world = request.app.state.world
        _swap_pictures(request, world, {**world.pictures.pictures, name: body})
        return PictureChoiceView(short_name=name, chosen=body)


@router.delete("/api/games/{name}/picture", response_model=PictureChoiceView)
async def delete_picture(name: str, request: Request) -> PictureChoiceView:
    """Remove the game's choice; with none stored, write nothing."""
    async with request.app.state.world_lock:
        world: WorldState = request.app.state.world
        _machine(world, name)
        if name in world.pictures.pictures:
            rest = {k: v for k, v in world.pictures.pictures.items() if k != name}
            _swap_pictures(request, world, rest)
        return PictureChoiceView(short_name=name, chosen=None)

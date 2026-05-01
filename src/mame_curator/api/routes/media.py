"""R39 — media proxy with libretro-thumbnails URL builder + sha256 disk cache.

P04 shipped a minimal pass-through proxy; P05 swaps in the real escape rules
and lazy-fetch cache via ``mame_curator.media``. URL surface unchanged.
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from mame_curator.api.errors import (
    GameNotFoundError,
    MediaKindInvalidError,
    MediaUpstreamError,
    MediaUpstreamNotFoundError,
)
from mame_curator.api.routes._deps import get_world
from mame_curator.api.state import WorldState
from mame_curator.media import MediaFetchError, fetch_with_cache, urls_for

router = APIRouter()

_VALID_KINDS = {"boxart", "title", "snap", "video"}


@router.get("/media/{name}/{kind}")
async def media_proxy(
    name: str, kind: str, request: Request, world: WorldState = Depends(get_world)
) -> Response:
    if kind not in _VALID_KINDS:
        raise MediaKindInvalidError(f"unknown media kind: {kind!r}")
    machine = world.machines.get(name)
    if machine is None:
        raise GameNotFoundError(f"game not found: {name!r}")
    if kind == "video":
        # Load-bearing short-circuit: MediaUrls has no `video` field, so
        # `getattr(urls, kind)` below would raise AttributeError. Also reflects
        # design §6.3 — video thumbnails route through progettoSnaps (P06+),
        # not libretro-thumbnails.
        raise MediaUpstreamNotFoundError(f"video upstream not configured for {name!r}")
    urls = urls_for(machine)
    url: str = getattr(urls, kind)
    cache_dir = world.config.media.cache_dir
    client: httpx.AsyncClient = request.app.state.media_client
    try:
        path = await fetch_with_cache(url, cache_dir, client=client)
    except MediaFetchError as exc:
        raise MediaUpstreamError(f"upstream error: {exc!r}") from exc
    if path is None:
        raise MediaUpstreamNotFoundError(f"upstream 404 for {url!r}")
    return Response(content=path.read_bytes(), media_type="image/png")

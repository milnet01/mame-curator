"""R39 — minimal media proxy (P05 wires the cache + escape rules)."""

from __future__ import annotations

from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import Response

from mame_curator.api.errors import (
    GameNotFoundError,
    MediaKindInvalidError,
    MediaUpstreamError,
    MediaUpstreamNotFoundError,
)
from mame_curator.api.routes._deps import get_world
from mame_curator.api.state import WorldState

router = APIRouter()

_KIND_FOLDER = {
    "boxart": "Named_Boxarts",
    "title": "Named_Titles",
    "snap": "Named_Snaps",
    "video": "Named_Videos",
}
_BASE_URL = "https://raw.githubusercontent.com/libretro-thumbnails/MAME/master"


@router.get("/media/{name}/{kind}")
async def media_proxy(name: str, kind: str, world: WorldState = Depends(get_world)) -> Response:
    if kind not in _KIND_FOLDER:
        raise MediaKindInvalidError(f"unknown media kind: {kind!r}")
    machine = world.machines.get(name)
    if machine is None:
        raise GameNotFoundError(f"game not found: {name!r}")
    url = f"{_BASE_URL}/{_KIND_FOLDER[kind]}/{quote(machine.description)}.png"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10.0)
    except httpx.HTTPError as exc:
        raise MediaUpstreamError(f"upstream error: {exc}") from exc
    if resp.status_code == 404:
        raise MediaUpstreamNotFoundError(f"upstream 404 for {url!r}")
    if resp.status_code != 200:
        raise MediaUpstreamError(f"upstream returned {resp.status_code} for {url!r}")
    return Response(content=resp.content, media_type="image/png")

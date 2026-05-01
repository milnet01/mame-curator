"""R39 — minimal media proxy (P05 wires the cache + escape rules)."""

from __future__ import annotations

from urllib.parse import quote

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

router = APIRouter()

_KIND_FOLDER = {
    "boxart": "Named_Boxarts",
    "title": "Named_Titles",
    "snap": "Named_Snaps",
    "video": "Named_Videos",
}
_BASE_URL = "https://raw.githubusercontent.com/libretro-thumbnails/MAME/master"


@router.get("/media/{name}/{kind}")
async def media_proxy(
    name: str, kind: str, request: Request, world: WorldState = Depends(get_world)
) -> Response:
    if kind not in _KIND_FOLDER:
        raise MediaKindInvalidError(f"unknown media kind: {kind!r}")
    machine = world.machines.get(name)
    if machine is None:
        raise GameNotFoundError(f"game not found: {name!r}")
    # FP09 C2: P05 swaps in proper libretro escape rules (`&*/:\<>?\|"` → `_`)
    # plus sha256-keyed disk cache. P04 ships a minimal pass-through proxy.
    url = f"{_BASE_URL}/{_KIND_FOLDER[kind]}/{quote(machine.description)}.png"
    # FP09 B4: reuse the lifespan-managed shared client; per-request
    # AsyncClient creates a fresh TLS handshake on every request which
    # blows up on the 50-thumbnail browse view.
    client: httpx.AsyncClient = request.app.state.media_client
    try:
        resp = await client.get(url, timeout=10.0)
    except httpx.HTTPError as exc:
        # FP09 A1: repr-quote `exc` (multi-line httpx error messages exist).
        raise MediaUpstreamError(f"upstream error: {exc!r}") from exc
    if resp.status_code == 404:
        raise MediaUpstreamNotFoundError(f"upstream 404 for {url!r}")
    if resp.status_code != 200:
        raise MediaUpstreamError(f"upstream returned {resp.status_code} for {url!r}")
    return Response(content=resp.content, media_type="image/png")

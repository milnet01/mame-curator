"""R39 — media proxy with libretro-thumbnails URL builder + sha256 disk cache.

P04 shipped a minimal pass-through proxy; P05 swaps in the real escape rules
and lazy-fetch cache via ``mame_curator.media``. URL surface unchanged.
"""

from __future__ import annotations

import mimetypes
from typing import cast

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, Response

from mame_curator.api.errors import (
    GameNotFoundError,
    MediaKindInvalidError,
    MediaUpstreamNotFoundError,
)
from mame_curator.api.routes._deps import get_world
from mame_curator.api.state import WorldState
from mame_curator.media import Kind, build_registry, resolve_image

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
        # Load-bearing short-circuit: `video` is not a source-chain `Kind`
        # (no source covers it — MediaUrls has no `video` field). Also
        # reflects design §6.3 — video thumbnails route through progettoSnaps
        # (P06+), not libretro-thumbnails.
        raise MediaUpstreamNotFoundError(f"video upstream not configured for {name!r}")
    cache_dir = world.config.media.cache_dir
    client: httpx.AsyncClient = request.app.state.media_client
    # P10 chunk 7: the fallback chain replaces the single-source URL build.
    # Per-source token buckets + the MobyGames disabled flag live on
    # app.state (process-wide); build_registry injects them into the
    # per-request source instances. resolve_image swallows per-source
    # MediaFetchError / MediaRateLimited and falls through, so an upstream
    # 5xx no longer surfaces as 502 — a chain that misses everywhere yields
    # None → 404 (see P10 spec § "Route contract").
    registry = build_registry(
        configured=world.config.media.sources,
        cache_dir=cache_dir,
        arcadedb_limiter=request.app.state.arcadedb_limiter,
        wikipedia_limiter=request.app.state.wikipedia_limiter,
        mobygames_limiter=request.app.state.mobygames_limiter,
        mobygames_disabled=request.app.state.mobygames_disabled,
    )
    # `kind` is one of boxart/title/snap here (video short-circuited above,
    # invalid kinds rejected above) — narrow the untyped route param to Kind.
    path = await resolve_image(
        machine, cast(Kind, kind), registry=registry, cache_dir=cache_dir, client=client
    )
    if path is None:
        raise MediaUpstreamNotFoundError(f"no media source resolved {kind!r} for {name!r}")
    # FP21-H: ``FileResponse`` streams the bytes via ``anyio.to_thread``
    # instead of doing a synchronous ``path.read_bytes()`` inside the
    # async handler. Under fan-out (50 thumbnails on a Library view) the
    # sync read serialised against the event loop; streaming lets the
    # asyncio scheduler interleave the I/O. Same wire-bytes contract.
    # FP28 C2: sniff content-type from the cached file's suffix so JPGs
    # don't get served as image/png. 30-day immutable Cache-Control per
    # design § 6.3 ("Cache is permanent by default") — without this header
    # browsers re-fetched every page-load.
    return FileResponse(
        path,
        media_type=mimetypes.guess_type(str(path))[0] or "image/png",
        headers={"Cache-Control": "public, max-age=2592000, immutable"},
    )

"""R39 — media proxy with libretro-thumbnails URL builder + sha256 disk cache.

P04 shipped a minimal pass-through proxy; P05 swaps in the real escape rules
and lazy-fetch cache via ``mame_curator.media``. P10 chunk 7 swaps the
single-source URL build for the fallback-chain orchestrator; chunk 8 adds the
``GET /media/{name}/wiki`` flavor-text endpoint.
"""

from __future__ import annotations

import logging
import mimetypes
from typing import cast

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, Response

from mame_curator._atomic import atomic_write_text
from mame_curator.api.errors import (
    GameNotFoundError,
    MediaKindInvalidError,
    MediaSourceUnknownError,
    MediaUpstreamNotFoundError,
)
from mame_curator.api.routes._deps import get_world
from mame_curator.api.schemas import SourceReadiness, SourceReadinessRow, SourceSecret
from mame_curator.api.state import WorldState
from mame_curator.media import (
    Kind,
    MediaError,
    MediaSource,
    WikipediaExtract,
    build_all_sources,
    build_registry,
    mobygames_key_path,
    resolve_image,
    resolve_wikipedia_extract,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_VALID_KINDS = {"boxart", "title", "snap", "video"}
# P10 chunk 9 — sources that accept a pasted secret (value-paste config).
_SECRET_SOURCES = frozenset({"mobyGames"})
# Sources the readiness surface marks as "needs a pasted value" (Configure-key
# button). progettoSnaps also self-disables, but its fix is a pack download
# (surfaced via disabled_reason), not a value — so it is NOT needs_config.
_NEEDS_CONFIG = frozenset({"mobyGames"})


# P10 chunk 8 — Wikipedia "About" flavor text. Registered BEFORE the
# `/media/{name}/{kind}` proxy so `/media/pacman/wiki` matches this literal
# path rather than binding `kind="wiki"` (which the proxy would 400 as an
# unknown kind). Returns `WikipediaExtract | None`; `None` serialises to JSON
# `null` and the frontend hides the AboutSection.
@router.get("/media/{name}/wiki", response_model=WikipediaExtract | None)
async def media_wiki(
    name: str, request: Request, world: WorldState = Depends(get_world)
) -> WikipediaExtract | None:
    machine = world.machines.get(name)
    if machine is None:
        raise GameNotFoundError(f"game not found: {name!r}")
    client: httpx.AsyncClient = request.app.state.media_client
    try:
        return await resolve_wikipedia_extract(
            machine,
            cache_dir=world.config.media.cache_dir,
            client=client,
            limiter=request.app.state.wikipedia_limiter,
        )
    except MediaError:
        # About text is non-essential flavor — degrade to null on ANY
        # media-layer failure (rate-limit / network / parse) rather than 500.
        # MediaError is the base of MediaRateLimited + MediaFetchError.
        return None


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


# --- P10 chunk 9: readiness surface + secret write -------------------------


def _readiness_row(source: MediaSource, configured: tuple[str, ...]) -> SourceReadinessRow:
    """Project a constructed source into its readiness wire row."""
    return SourceReadinessRow(
        name=source.name,
        enabled=source.disabled_reason is None,
        in_chain=source.name in configured,
        # source.kinds is a frozenset (no order) — sort for a stable wire shape.
        kinds=tuple(sorted(source.kinds)),
        license_compatible=source.license_compatible,
        disabled_reason=source.disabled_reason,
        needs_config=source.name in _NEEDS_CONFIG,
    )


@router.get("/api/media/sources", response_model=SourceReadiness)
def media_sources(request: Request, world: WorldState = Depends(get_world)) -> SourceReadiness:
    """Per-source readiness for the Settings → Media tab.

    Surface-only — no upstream hits, no side effects. Constructs every known
    source (via ``build_all_sources``, using the app-state limiters + disabled
    flag) to read its real ``disabled_reason``. Rows are ordered: configured
    sources in ``media.sources`` order first, then any unconfigured known
    sources alphabetised.
    """
    sources = build_all_sources(
        cache_dir=world.config.media.cache_dir,
        arcadedb_limiter=request.app.state.arcadedb_limiter,
        wikipedia_limiter=request.app.state.wikipedia_limiter,
        mobygames_limiter=request.app.state.mobygames_limiter,
        mobygames_disabled=request.app.state.mobygames_disabled,
    )
    configured = world.config.media.sources
    ordered = [n for n in configured if n in sources]
    ordered += sorted(n for n in sources if n not in configured)
    return SourceReadiness(sources=tuple(_readiness_row(sources[n], configured) for n in ordered))


@router.put("/api/media/sources/{name}/secret", status_code=204)
def media_source_secret(name: str, body: SourceSecret) -> None:
    """Atomically write a per-source secret to its 0600 dotfile.

    Only ``mobyGames`` is supported (the sole value-paste source) — any other
    name is 422 (``media_source_unknown``) before any write. An empty secret
    is rejected by ``SourceSecret`` (min_length=1) → 422. Loopback-trust per
    P10 spec § Open verification items #5 — no auth gate (consistent with the
    app's other mutation routes behind the default 127.0.0.1 bind). The value
    is never logged; only the source name is.
    """
    if name not in _SECRET_SOURCES:
        raise MediaSourceUnknownError(f"unknown media source for secret write: {name!r}")
    # NOTE (FP33 L5): _SECRET_SOURCES holds only "mobyGames" today, so `name` is
    # necessarily mobyGames here and the hardcoded mobygames_key_path() is
    # correct. Adding a second value-paste source MUST replace this with a
    # name -> key_path map — else the new source's secret clobbers this one.
    atomic_write_text(mobygames_key_path(), body.secret, mode=0o600)
    logger.info("media/sources: secret saved for %s", name)

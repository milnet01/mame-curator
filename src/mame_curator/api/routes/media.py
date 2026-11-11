"""R39 — media proxy with libretro-thumbnails URL builder + sha256 disk cache.

P04 shipped a minimal pass-through proxy; P05 swaps in the real escape rules
and lazy-fetch cache via ``mame_curator.media``. P10 chunk 7 swaps the
single-source URL build for the fallback-chain orchestrator; chunk 8 adds the
``GET /media/{name}/wiki`` flavor-text endpoint.
"""

from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from typing import Any, cast

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
from mame_curator.api.pictures import PictureChoice
from mame_curator.api.routes._deps import get_world
from mame_curator.api.schemas import SourceReadiness, SourceReadinessRow, SourceSecret
from mame_curator.api.state import WorldState
from mame_curator.media import (
    Kind,
    MediaError,
    MediaSource,
    MediaSourceRegistry,
    WikipediaExtract,
    build_all_sources,
    build_registry,
    mobygames_key_path,
    resolve_image,
    resolve_pair,
    resolve_wikipedia_extract,
)
from mame_curator.parser.models import Machine

logger = logging.getLogger(__name__)

router = APIRouter()

_VALID_KINDS = {"boxart", "title", "snap", "video"}
_IMMUTABLE = "public, max-age=2592000, immutable"
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


def request_registry(request: Request, world: WorldState) -> MediaSourceRegistry:
    """The configured sources for one request, sharing the app's rate limits.

    P10 chunk 7: per-source token buckets + the MobyGames disabled flag live
    on app.state (process-wide); build_registry injects them into the
    per-request source instances. The media proxy and the picture routes
    (mame-curator-1146) both build their chain here.
    """
    return build_registry(
        configured=world.config.media.sources,
        cache_dir=world.config.media.cache_dir,
        arcadedb_limiter=request.app.state.arcadedb_limiter,
        wikipedia_limiter=request.app.state.wikipedia_limiter,
        mobygames_limiter=request.app.state.mobygames_limiter,
        mobygames_disabled=request.app.state.mobygames_disabled,
        # mame-curator-1081: bind the progettoSnaps read-path to config so it
        # tracks `refresh-snaps --dest` / `media.snaps_dir` instead of the fixed
        # ./data/snaps/snap default. Pack PNGs live under `<snaps_dir>/snap/`.
        snap_dir=world.config.media.snaps_dir / "snap",
        # mame-curator-1105: read the key from the config's data dir.
        secrets_dir=world.data_dir / "secrets",
        # mame-curator-1126: art ES-DE / RetroArch already scraped.
        esde_media_dir=world.config.media.esde_media_dir,
        retroarch_thumbnails_dir=world.config.media.retroarch_thumbnails_dir,
    )


def require_in_chain(registry: MediaSourceRegistry, source: str, kind: Kind) -> None:
    """422 unless ``source`` is ready, configured and covers ``kind`` (1146 §4.3)."""
    if source not in {s.name for s in registry.chain_for(kind)}:
        raise MediaSourceUnknownError(f"media source {source!r} cannot serve {kind!r}")


async def _pair_or_none(
    machine: Machine, choice: PictureChoice, registry: MediaSourceRegistry, **fetch: Any
) -> Path | None:
    """A stored choice's picture; ``None`` when it misses or its source fails."""
    try:
        return await resolve_pair(machine, choice.source, choice.kind, registry=registry, **fetch)
    except MediaError as exc:  # MediaRateLimited + MediaFetchError: fall back.
        logger.info(
            "media: chosen picture %s.%s did not answer: %s", choice.source, choice.kind, exc
        )
        return None


async def _serve_boxart(
    machine: Machine, world: WorldState, registry: MediaSourceRegistry, v: str | None, **fetch: Any
) -> tuple[Path | None, bool]:
    """The game's picture and whether its address may be cached for good.

    mame-curator-1146 §4.3: a stored choice serves first; the address is
    immutable only when it names what it served. A fallback is ``no-store``,
    so the card shows the chosen picture again once it resolves.
    """
    choice = world.pictures.pictures.get(machine.name)
    if choice is not None:
        path = await _pair_or_none(machine, choice, registry, **fetch)
        if path is not None:
            return path, v == f"{choice.source}.{choice.kind}"
    elif v is None:
        return await resolve_image(machine, "boxart", registry=registry, **fetch), True
    return await resolve_image(machine, "boxart", registry=registry, **fetch), False


@router.get("/media/{name}/{kind}")
async def media_proxy(
    name: str,
    kind: str,
    request: Request,
    source: str | None = None,
    v: str | None = None,
    world: WorldState = Depends(get_world),
) -> Response:
    """One game's picture of one kind; ``source`` asks one source only.

    ``v`` is the card's address part naming a stored choice (mame-curator-1146
    §4.5); it only chooses ``Cache-Control``.
    """
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
    # `kind` is one of boxart/title/snap here (video short-circuited above,
    # invalid kinds rejected above) — narrow the untyped route param to Kind.
    chain_kind = cast(Kind, kind)
    registry = request_registry(request, world)
    fetch: dict[str, Any] = {
        "cache_dir": world.config.media.cache_dir,
        "client": request.app.state.media_client,
    }
    cacheable = True
    if source is not None:
        # mame-curator-1146 INV-5: one pair only — a miss is 404, never the chain.
        require_in_chain(registry, source, chain_kind)
        path = await _pair_or_none(
            machine, PictureChoice(source=source, kind=chain_kind), registry, **fetch
        )
    elif chain_kind == "boxart":
        path, cacheable = await _serve_boxart(machine, world, registry, v, **fetch)
    else:
        # resolve_image swallows per-source MediaFetchError / MediaRateLimited
        # and falls through, so an upstream 5xx no longer surfaces as 502 — a
        # chain that misses everywhere yields None → 404 (P10 spec § "Route
        # contract").
        path = await resolve_image(machine, chain_kind, registry=registry, **fetch)
    if path is None:
        raise MediaUpstreamNotFoundError(f"no media source resolved {kind!r} for {name!r}")
    # FP21-H: ``FileResponse`` streams the bytes via ``anyio.to_thread``
    # instead of doing a synchronous ``path.read_bytes()`` inside the
    # async handler. FP28 C2: sniff content-type from the cached file's
    # suffix so JPGs don't get served as image/png. 30-day immutable
    # Cache-Control per design § 6.3 ("Cache is permanent by default") —
    # without this header browsers re-fetched every page-load.
    return FileResponse(
        path,
        media_type=mimetypes.guess_type(str(path))[0] or "image/png",
        headers={
            "Cache-Control": _IMMUTABLE if cacheable else "no-store",
            # mame-curator-1225: never let a browser guess a cached file is a page.
            "X-Content-Type-Options": "nosniff",
        },
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
        # mame-curator-1081: readiness must reflect the configured pack folder
        # too, else Settings → Media shows progettoSnaps disabled while the
        # media-proxy route (which now reads snaps_dir) serves it, or vice versa.
        snap_dir=world.config.media.snaps_dir / "snap",
        # mame-curator-1105: read the key from the config's data dir.
        secrets_dir=world.data_dir / "secrets",
        # mame-curator-1126: art ES-DE / RetroArch already scraped.
        esde_media_dir=world.config.media.esde_media_dir,
        retroarch_thumbnails_dir=world.config.media.retroarch_thumbnails_dir,
    )
    configured = world.config.media.sources
    ordered = [n for n in configured if n in sources]
    ordered += sorted(n for n in sources if n not in configured)
    return SourceReadiness(sources=tuple(_readiness_row(sources[n], configured) for n in ordered))


@router.put("/api/media/sources/{name}/secret", status_code=204)
def media_source_secret(
    name: str, body: SourceSecret, world: WorldState = Depends(get_world)
) -> None:
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
    # mame-curator-1105: the config's data dir, never the process cwd.
    atomic_write_text(mobygames_key_path(world.data_dir / "secrets"), body.secret, mode=0o600)
    logger.info("media/sources: secret saved for %s", name)

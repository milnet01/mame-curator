"""P10 chunk 7 — image-resolution orchestrator + registry composition root.

``resolve_image`` walks the per-kind fallback chain (``MediaSourceRegistry``),
awaiting each source's ``prepare`` then reading its ``url_for`` candidate, and
returns the first cached image ``Path`` (or ``None`` when every source misses
— the route maps that to 404). ``build_registry`` is the composition root: it
constructs the concrete sources named in ``media.sources`` (injecting the
app-state limiters + the ``SourceDisabledFlag``) and hands them to the
registry, keeping ``media/`` free of any ``api/`` import.

Per ``docs/specs/P10.md`` § "async resolve_image" + § "Chunk 7 implementation
notes".
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

import httpx

from mame_curator.media.cache import MediaFetchError, fetch_with_cache
from mame_curator.media.mobygames import MobyGamesSource, SourceDisabledFlag
from mame_curator.media.rate_limit import MediaRateLimited, TokenBucket
from mame_curator.media.sources import (
    ArcadeDBSource,
    Kind,
    LibretroSource,
    MediaSource,
    MediaSourceRegistry,
    ProgettoSnapsSource,
    WikipediaImageSource,
)
from mame_curator.parser.models import Machine

logger = logging.getLogger(__name__)

# Default local snap-pack directory. Mirrors ``refresh-snaps``'s extraction
# target (``updates.snaps.DEFAULT_DEST / "snap"`` == ``./data/snaps/snap``).
# NOT derived from ``cache_dir``: the CLI writes to this fixed CWD-relative
# path regardless of the media cache location, so the source must read the
# same fixed path. A ``media.snaps_dir`` config field binding both is a
# deferred follow-up (P10 spec § chunk-7 notes).
_DEFAULT_SNAP_DIR = Path("./data/snaps/snap")


async def resolve_image(
    machine: Machine,
    kind: Kind,
    *,
    registry: MediaSourceRegistry,
    cache_dir: Path,
    client: httpx.AsyncClient,
) -> Path | None:
    """Walk the fallback chain; return the first cached image path, or ``None``.

    A source's ``prepare`` may raise ``MediaRateLimited`` (empty bucket / 429)
    or ``MediaFetchError`` (network / parse) — both are swallowed and the
    chain advances. A ``file://`` candidate (ProgettoSnaps local pack) is
    served directly, short-circuiting ``fetch_with_cache`` (whose scheme guard
    rejects ``file://`` by design). Every source missing → ``None``.
    """
    for source in registry.chain_for(kind):
        try:
            await source.prepare(machine, client=client)
        except MediaRateLimited:
            logger.info("media: %s rate-limited during prepare; falling through", source.name)
            continue
        except MediaFetchError:
            logger.warning(
                "media: %s prepare failed for %s; falling through", source.name, machine.name
            )
            continue
        url = source.url_for(machine, kind)
        if url is None:
            continue  # source has no candidate for this (machine, kind)
        if url.startswith("file://"):
            # Local-pack source (ProgettoSnaps). fetch_with_cache's
            # _ALLOWED_URL_SCHEMES rejects file:// (P05 FP27 B4 guard), so
            # serve the path directly. url2pathname handles the Windows
            # ``/C:/…`` → ``C:\`` conversion a naive ``urlparse().path`` won't.
            local = Path(url2pathname(urlparse(url).path))
            if local.is_file():
                return local
            continue  # pack file vanished between url_for and here; fall through
        try:
            path = await fetch_with_cache(url, cache_dir, client=client)
        except MediaFetchError:
            logger.warning(
                "media: %s fetch failed for %s/%s; falling through",
                source.name,
                machine.name,
                kind,
            )
            continue
        if path is not None:
            return path
        # path is None → upstream 404 → try the next source
    return None


def _source_factories(
    *,
    cache_dir: Path,
    arcadedb_limiter: TokenBucket,
    wikipedia_limiter: TokenBucket,
    mobygames_limiter: TokenBucket,
    mobygames_disabled: SourceDisabledFlag,
    snap_dir: Path,
) -> dict[str, Callable[[], MediaSource]]:
    """The name → source-constructor table (insertion order = default order).

    Shared by ``build_registry`` (constructs only the configured subset) and
    ``build_all_sources`` (constructs every known source for the readiness
    endpoint) so the five-source roster + their dep-injection live in one
    place.
    """
    return {
        "libretro": LibretroSource,
        "progettoSnaps": lambda: ProgettoSnapsSource(snap_dir=snap_dir),
        "arcadeDB": lambda: ArcadeDBSource(limiter=arcadedb_limiter, cache_dir=cache_dir),
        "wikipediaImage": lambda: WikipediaImageSource(
            limiter=wikipedia_limiter, cache_dir=cache_dir
        ),
        "mobyGames": lambda: MobyGamesSource(
            limiter=mobygames_limiter,
            cache_dir=cache_dir,
            disabled_flag=mobygames_disabled,
        ),
    }


def build_registry(
    *,
    configured: tuple[str, ...],
    cache_dir: Path,
    arcadedb_limiter: TokenBucket,
    wikipedia_limiter: TokenBucket,
    mobygames_limiter: TokenBucket,
    mobygames_disabled: SourceDisabledFlag,
    snap_dir: Path = _DEFAULT_SNAP_DIR,
) -> MediaSourceRegistry:
    """Construct the configured sources (+ libretro baseline) and wrap them.

    Only sources named in ``configured`` (plus ``libretro``) are built, so
    dropping ``mobyGames`` from ``media.sources`` also suppresses its
    keyless-startup WARNING. Deps are injected here (the composition root);
    per-source token buckets + the disabled flag live on ``app.state`` and are
    passed in, so the per-request source instances share the process-wide
    rate-limit / disabled state.
    """
    factories = _source_factories(
        cache_dir=cache_dir,
        arcadedb_limiter=arcadedb_limiter,
        wikipedia_limiter=wikipedia_limiter,
        mobygames_limiter=mobygames_limiter,
        mobygames_disabled=mobygames_disabled,
        snap_dir=snap_dir,
    )
    wanted = set(configured) | {"libretro"}
    available = {name: make() for name, make in factories.items() if name in wanted}
    return MediaSourceRegistry(configured, available)


def build_all_sources(
    *,
    cache_dir: Path,
    arcadedb_limiter: TokenBucket,
    wikipedia_limiter: TokenBucket,
    mobygames_limiter: TokenBucket,
    mobygames_disabled: SourceDisabledFlag,
    snap_dir: Path = _DEFAULT_SNAP_DIR,
) -> dict[str, MediaSource]:
    """Construct ALL five known sources, regardless of config.

    The readiness endpoint (``GET /api/media/sources``) reports every known
    source's real state — including ones the user removed from
    ``media.sources`` — so it can't use ``build_registry``'s configured-only
    subset. Constructing ``mobyGames`` here fires its keyless WARNING at most
    once per process (the chunk-6 dedup guard), acceptable for a rare
    surface-only call.
    """
    factories = _source_factories(
        cache_dir=cache_dir,
        arcadedb_limiter=arcadedb_limiter,
        wikipedia_limiter=wikipedia_limiter,
        mobygames_limiter=mobygames_limiter,
        mobygames_disabled=mobygames_disabled,
        snap_dir=snap_dir,
    )
    return {name: make() for name, make in factories.items()}

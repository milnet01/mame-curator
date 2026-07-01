"""Media subsystem — libretro-thumbnails URL builder and lazy-fetch disk cache.

Public surface per ``docs/specs/P05.md`` + ``docs/specs/P10.md``:

P05 (image cache):

- ``escape_libretro`` — apply the libretro-thumbnails filename escape rule.
- ``urls_for`` — build boxart / title / snap URLs for a ``Machine``.
- ``MediaUrls`` — frozen Pydantic model holding the three URLs.
- ``fetch_with_cache`` — async download-or-hit-cache helper.
- ``cache_path_for`` — pure helper exposing the sha256 → path mapping.
- ``MediaError`` / ``MediaFetchError`` — exception hierarchy.

P10 chunk 1 (foundations for the source-chain expansion):

- ``TokenBucket`` — per-source rate limiter; injectable clock.
- ``MediaRateLimited`` — typed exception sources raise on empty bucket.
- ``fetch_text_with_cache`` — text/JSON sibling of ``fetch_with_cache``.
- ``DEFAULT_TEXT_MAX_BYTES`` — public cap (256 KiB) callers may override.

P10 chunk 2 (source protocol + libretro carried under it):

- ``Kind`` — the source-chain kind literal ("boxart" | "title" | "snap").
- ``MediaSource`` — Protocol every source implements (runtime_checkable).
- ``LibretroSource`` — P05 baseline, re-homed under the new shape.

P10 chunk 3b (progettoSnaps local-pack source):

- ``ProgettoSnapsSource`` — file:// source for snap kind only; reads
  ``data/snaps/snap/<name>.png`` produced by ``mame-curator
  refresh-snaps``.

P10 chunk 4 (ArcadeDB JSON scraper):

- ``ArcadeDBSource`` — two-step lookup against ArcadeDB's scraper
  endpoint; parse-before-trust JSON handling; per-source token bucket.

P10 chunk 5 (Wikipedia REST summary, image-only):

- ``WikipediaImageSource`` — REST summary endpoint, boxart kind only;
  title canonicalisation drops trailing parenthesised qualifier.
- ``_build_user_agent`` — descriptive UA string the lifespan client sends
  per Wikipedia's API:Etiquette guidance (``mame-curator/{VERSION}
  (+https://github.com/milnet01/mame-curator)``). Underscore-prefixed
  because it's an implementation helper, not a stable consumer API —
  callers should let the lifespan client own the header.

P10 chunk 6 (MobyGames key-handling — lives in ``mobygames.py``):

- ``MobyGamesSource`` — port-cover source, boxart only; resolves an API key
  (env var / mode-0600 dotfile), self-disables when no key resolves, and
  flips a process-wide disabled flag on a 401/403. The success-path cover
  parse is deferred pending a real-key fixture.
- ``SourceDisabledFlag`` — injectable holder for a source's process-wide
  runtime-disabled reason (survives per-request source re-creation while
  keeping ``media/`` free of any ``api/`` import).

P10 chunk 7 (registry + orchestrator):

- ``MediaSourceRegistry`` — orders + filters configured sources into a
  per-kind fallback chain (lives in ``sources.py``).
- ``resolve_image`` — the orchestrator: walks the chain, serves the first
  hit, handles the ``file://`` short-circuit for the local snap pack.
- ``build_registry`` — composition root that constructs the configured
  sources with the app-state limiters + disabled flag injected. Both live
  in ``resolve.py``.

P10 chunk 8 (Wikipedia flavor-text endpoint):

- ``WikipediaExtract`` — frozen wire model (title / extract / url / license)
  for the Alternatives-drawer "About" paragraph.
- ``resolve_wikipedia_extract`` — fetches + parses the Wikipedia REST summary
  (shared cache slot + rate-limit bucket with ``WikipediaImageSource``).
  Both live in ``wikipedia.py``.
"""

from __future__ import annotations

from mame_curator.media.cache import (
    MediaError,
    MediaFetchError,
    cache_path_for,
    fetch_with_cache,
)
from mame_curator.media.cache_text import (
    DEFAULT_TEXT_MAX_BYTES,
    fetch_text_with_cache,
)
from mame_curator.media.mobygames import (
    MobyGamesSource,
    SourceDisabledFlag,
    mobygames_key_path,
)
from mame_curator.media.rate_limit import MediaRateLimited, TokenBucket
from mame_curator.media.resolve import build_all_sources, build_registry, resolve_image
from mame_curator.media.sources import (
    ArcadeDBSource,
    Kind,
    LibretroSource,
    MediaSource,
    MediaSourceRegistry,
    ProgettoSnapsSource,
    WikipediaImageSource,
)
from mame_curator.media.urls import MediaUrls, escape_libretro, urls_for
from mame_curator.media.wikipedia import WikipediaExtract, resolve_wikipedia_extract


def _build_user_agent() -> str:
    """Return the User-Agent string the media client identifies as.

    Per Wikipedia's API:Etiquette: include the project name, version,
    and a contact URL. Single source of truth so both the lifespan
    constructor and any future test that pins the UA shape agree.
    """
    from mame_curator import __version__

    return f"mame-curator/{__version__} (+https://github.com/milnet01/mame-curator)"


__all__ = [
    "DEFAULT_TEXT_MAX_BYTES",
    "ArcadeDBSource",
    "Kind",
    "LibretroSource",
    "MediaError",
    "MediaFetchError",
    "MediaRateLimited",
    "MediaSource",
    "MediaSourceRegistry",
    "MediaUrls",
    "MobyGamesSource",
    "ProgettoSnapsSource",
    "SourceDisabledFlag",
    "TokenBucket",
    "WikipediaExtract",
    "WikipediaImageSource",
    "_build_user_agent",
    "build_all_sources",
    "build_registry",
    "cache_path_for",
    "escape_libretro",
    "fetch_text_with_cache",
    "fetch_with_cache",
    "mobygames_key_path",
    "resolve_image",
    "resolve_wikipedia_extract",
    "urls_for",
]

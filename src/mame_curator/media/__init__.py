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
from mame_curator.media.rate_limit import MediaRateLimited, TokenBucket
from mame_curator.media.sources import Kind, LibretroSource, MediaSource
from mame_curator.media.urls import MediaUrls, escape_libretro, urls_for

__all__ = [
    "DEFAULT_TEXT_MAX_BYTES",
    "Kind",
    "LibretroSource",
    "MediaError",
    "MediaFetchError",
    "MediaRateLimited",
    "MediaSource",
    "MediaUrls",
    "TokenBucket",
    "cache_path_for",
    "escape_libretro",
    "fetch_text_with_cache",
    "fetch_with_cache",
    "urls_for",
]

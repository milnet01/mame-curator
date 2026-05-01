"""Media subsystem — libretro-thumbnails URL builder and lazy-fetch disk cache.

Public surface per ``docs/specs/P05.md``:

- ``escape_libretro`` — apply the libretro-thumbnails filename escape rule.
- ``urls_for`` — build boxart / title / snap URLs for a ``Machine``.
- ``MediaUrls`` — frozen Pydantic model holding the three URLs.
- ``fetch_with_cache`` — async download-or-hit-cache helper.
- ``cache_path_for`` — pure helper exposing the sha256 → path mapping.
- ``MediaError`` / ``MediaFetchError`` — exception hierarchy.
"""

from __future__ import annotations

from mame_curator.media.cache import (
    MediaError,
    MediaFetchError,
    cache_path_for,
    fetch_with_cache,
)
from mame_curator.media.urls import MediaUrls, escape_libretro, urls_for

__all__ = [
    "MediaError",
    "MediaFetchError",
    "MediaUrls",
    "cache_path_for",
    "escape_libretro",
    "fetch_with_cache",
    "urls_for",
]

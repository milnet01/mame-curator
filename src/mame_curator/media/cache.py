"""Lazy-fetch disk cache for media URLs.

Per ``docs/specs/P05.md`` § Public API:

- ``cache_path_for`` is pure (no I/O).
- ``fetch_with_cache`` returns the on-disk path if cached; otherwise downloads
  via the caller-supplied ``httpx.AsyncClient`` and writes atomically.
- 404 is the no-image sentinel (returns ``None``); no negative caching.
- Other upstream errors raise ``MediaFetchError``.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import urlparse

import httpx

from mame_curator._atomic import atomic_write_bytes


class MediaError(Exception):
    """Base class for media subsystem errors."""


class MediaFetchError(MediaError):
    """Upstream non-200 (other than 404) or network failure."""


def cache_path_for(url: str, cache_dir: Path) -> Path:
    """Return ``cache_dir / f"{sha256(url).hexdigest()}{ext}"``.

    ``ext`` is the URL path's suffix (``.png`` for libretro thumbnails). URLs
    with no path suffix produce a bare-hex filename. Pure function — no I/O,
    no directory creation.
    """
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    ext = Path(urlparse(url).path).suffix
    return cache_dir / f"{digest}{ext}"


async def fetch_with_cache(
    url: str,
    cache_dir: Path,
    *,
    client: httpx.AsyncClient,
) -> Path | None:
    """Return cached path if present; otherwise download, cache, return path.

    404 returns ``None`` (sentinel; no negative caching). Other upstream
    failures raise ``MediaFetchError`` with the underlying ``httpx.HTTPError``
    chained via ``__cause__`` when applicable.

    Concurrent calls for the same URL are safe: ``atomic_write_bytes`` uses a
    unique ``.tmp`` sibling + ``os.replace`` so the cache file is never torn.
    The wasted second download is acceptable at single-user scale.
    """
    path = cache_path_for(url, cache_dir)
    # FP10 A4: TOCTOU-safe — cache writes are append-only via atomic_write_bytes
    # (no delete path); a concurrent rename produces a new inode whose bytes
    # any reader after this exists() check sees correctly under POSIX.
    if path.exists():
        return path
    try:
        resp = await client.get(url)
    except httpx.HTTPError as exc:
        raise MediaFetchError(f"network error for {url!r}: {exc}") from exc
    if resp.status_code == 404:
        return None
    if resp.status_code != 200:
        raise MediaFetchError(f"upstream {resp.status_code} for {url!r}")
    if not resp.content:
        # FP10 A2: raw.githubusercontent.com rate-limit interstitials and CDN
        # edge cases occasionally return 200 + Content-Length: 0. Caching that
        # poisons the slot; treat as a fetch error instead.
        raise MediaFetchError(f"empty body for {url!r}")
    atomic_write_bytes(path, resp.content)
    return path

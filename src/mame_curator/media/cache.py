"""Lazy-fetch disk cache for media URLs.

Per ``docs/specs/P05-media.md`` § Public API:

- ``cache_path_for`` is pure (no I/O).
- ``fetch_with_cache`` returns the on-disk path if cached; otherwise downloads
  via the caller-supplied ``httpx.AsyncClient`` and writes atomically.
- 404 is the no-image sentinel (returns ``None``); it is never cached here.
  A whole-chain miss is remembered one level up, in ``misses.py``.
- Other upstream errors raise ``MediaFetchError``.
"""

from __future__ import annotations

import contextlib
import hashlib
import ipaddress
import logging
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

import httpx

from mame_curator._atomic import fsync_parent_dir

logger = logging.getLogger(__name__)

# FP27 B4: 16 MiB default cap. Libretro-thumbnails images at the
# typical 90th percentile are ~500 KiB; 16 MiB leaves ~30x headroom
# for fanart while putting a hard ceiling on accidental OOMs from a
# misconfigured or malicious upstream.
DEFAULT_MAX_BYTES = 16 * 1024 * 1024

_ALLOWED_URL_SCHEMES = frozenset({"http", "https"})

# mame-curator-1225: the cached file's suffix picks the MIME type it is served
# with, and the URL comes from upstream JSON. Only picture suffixes survive, so
# an upstream ".html" can never be served as a page from the app's own origin.
_PICTURE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp"})


class MediaError(Exception):
    """Base class for media subsystem errors."""


class MediaFetchError(MediaError):
    """Upstream non-200 (other than 404) or network failure."""


async def refuse_private_hosts(request: httpx.Request) -> None:
    """Refuse a request to a local or private address (an ``httpx`` request hook).

    mame-curator-1225: picture URLs come from upstream JSON (ArcadeDB,
    Wikipedia, MobyGames), so a hostile or spoofed reply could point the app
    at the user's own machine or LAN. Installed as a request hook, it runs on
    every redirect hop too. Names are not resolved, so a public name that
    resolves to a private address still passes.
    """
    host = request.url.host
    if host == "localhost" or host.endswith(".localhost"):
        refused = True
    else:
        try:
            refused = not ipaddress.ip_address(host).is_global
        except ValueError:
            refused = False  # a name, not an address literal
    if refused:
        raise httpx.RequestError(f"refused a fetch from local address {host!r}", request=request)


def cache_path_for(url: str, cache_dir: Path) -> Path:
    """Return ``cache_dir / f"{sha256(url).hexdigest()}{ext}"``.

    ``ext`` is the URL path's suffix (``.png`` for libretro thumbnails) when it
    is a picture suffix, compared case-blind; any other suffix, or none, gives
    a bare-hex filename. Pure function — no I/O, no directory creation.
    """
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    ext = Path(urlparse(url).path).suffix
    if ext.lower() not in _PICTURE_SUFFIXES:
        ext = ""
    return cache_dir / f"{digest}{ext}"


def _require_picture(resp: httpx.Response, url: str) -> None:
    """Raise unless a 200's ``Content-Type`` could be a picture.

    mame-curator-1225: a soft-404 HTML page would otherwise be cached for
    good. A missing type and ``application/octet-stream`` pass, since some
    hosts send pictures that way.
    """
    content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()
    allowed = not content_type or content_type == "application/octet-stream"
    if not allowed and not content_type.startswith("image/"):
        raise MediaFetchError(f"not a picture ({content_type}) for {url!r}")


async def fetch_with_cache(
    url: str,
    cache_dir: Path,
    *,
    client: httpx.AsyncClient,
    max_bytes: int = DEFAULT_MAX_BYTES,
    before_network: Callable[[], None] | None = None,
) -> Path | None:
    """Return cached path if present; otherwise download, cache, return path.

    ``before_network`` runs only on a miss, just before the request: a rate
    limit's courtesy token is spent there, never on a hit (mame-curator-1235).

    404 returns ``None`` (sentinel; no negative caching). Other upstream
    failures raise ``MediaFetchError`` with the underlying ``httpx.HTTPError``
    chained via ``__cause__`` when applicable.

    Concurrent calls for the same URL are safe: ``download_into`` writes a
    uniquely named ``.tmp`` sibling and ``os.replace``s it, so the cache file
    is never torn.
    The wasted second download is acceptable at single-user scale.

    FP27 B4: rejects non-http(s) schemes (``file://``, ``data:``, etc.)
    before any network call; caps the body at ``max_bytes`` (default
    16 MiB) — both abort with ``MediaFetchError``; streams chunks
    straight to the tmp file instead of buffering ``resp.content``.
    Mirrors the streaming-cap pattern from ``downloads.py`` (same
    ``BodyTooLarge: …`` log-line prefix; control flow differs because
    media has no mirror list — failures raise immediately).
    """
    # FP27 B4: scheme check first, before any I/O. file:// / data: /
    # ftp: URLs would otherwise be processed by httpx and might leak
    # filesystem-path semantics.
    scheme = urlparse(url).scheme
    if scheme not in _ALLOWED_URL_SCHEMES:
        raise MediaFetchError(f"unsupported scheme: {scheme!r} for {url!r}")

    path = cache_path_for(url, cache_dir)
    # FP10 A4: TOCTOU-safe — cache writes are append-only via the
    # atomic replace in download_into (no delete path); a concurrent rename
    # produces a new inode whose bytes any reader after this exists()
    # check sees correctly under POSIX.
    if path.exists():
        return path

    if before_network is not None:
        before_network()
    if not await download_into(
        url, path, client=client, max_bytes=max_bytes, accept=_require_picture
    ):
        return None
    return path


async def download_into(
    url: str,
    path: Path,
    *,
    client: httpx.AsyncClient,
    max_bytes: int,
    accept: Callable[[httpx.Response, str], None] | None = None,
    check: Callable[[bytes], None] | None = None,
) -> bool:
    """Download ``url`` into ``path`` through a unique tmp file; False on a 404.

    ``accept`` vets a 200 before its body is read; ``check`` vets the whole
    body before it is kept. Each raises ``MediaFetchError`` to refuse. Any
    failure, a full disk included, raises ``MediaFetchError`` and leaves no
    tmp file behind (mame-curator-1235). Shared by the picture and text
    caches.
    """
    tmp: Path | None = None
    kept = False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
        tmp = Path(tmp_name)
        total = 0
        with os.fdopen(fd, "wb") as out:
            async with client.stream("GET", url) as resp:
                if resp.status_code == 404:
                    return False
                if resp.status_code != 200:
                    raise MediaFetchError(f"upstream {resp.status_code} for {url!r}")
                if accept is not None:
                    accept(resp, url)
                async for chunk in resp.aiter_bytes(chunk_size=64 * 1024):
                    total += len(chunk)
                    if total > max_bytes:
                        msg = f"BodyTooLarge: {url}: streamed {total} bytes exceeds cap {max_bytes}"
                        logger.warning("media/cache: %s", msg)
                        raise MediaFetchError(msg)
                    out.write(chunk)
            out.flush()
            os.fsync(out.fileno())
        if total == 0:
            # FP10 A2: a CDN rate-limit page can be 200 with no body; caching
            # it would poison the slot.
            raise MediaFetchError(f"empty body for {url!r}")
        if check is not None:
            check(tmp.read_bytes())
        os.replace(tmp, path)
        kept = True
        fsync_parent_dir(path)
        return True
    except httpx.HTTPError as exc:
        raise MediaFetchError(f"network error for {url!r}: {exc}") from exc
    except OSError as exc:
        raise MediaFetchError(f"could not cache {url!r}: {exc}") from exc
    finally:
        if tmp is not None and not kept:
            with contextlib.suppress(OSError):
                tmp.unlink(missing_ok=True)

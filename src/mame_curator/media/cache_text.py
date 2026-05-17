"""Lazy-fetch disk cache for text / JSON bodies.

Per ``docs/specs/P10.md`` § "Public API". Parallel to P05's
``fetch_with_cache`` (binary images) but returns ``str``, decodes
UTF-8, defaults to a smaller ``max_bytes`` cap matching the text
payloads we're storing (Wikipedia extracts < 2 KiB, ArcadeDB
responses < 50 KiB; 256 KiB cap = 5x headroom).

Same SHA-256-keyed cache layout, same ``.tmp + os.replace`` atomic
write protocol, same 404 sentinel, same ``MediaFetchError`` semantics
for non-200 / oversize / decode failure / network errors. Lives in
``cache.py``'s sibling so the binary-image path stays untouched.
"""

from __future__ import annotations

import contextlib
import logging
import os
from pathlib import Path
from urllib.parse import urlparse

import httpx

from mame_curator._atomic import fsync_parent_dir
from mame_curator.media.cache import (
    MediaFetchError,
    cache_path_for,
)

logger = logging.getLogger(__name__)

# P10: 256 KiB cap. Wikipedia REST summary responses are <2 KiB typical;
# ArcadeDB scraper responses for one machine are <50 KiB; 256 KiB gives
# 5x headroom while putting a hard ceiling on accidental OOMs from a
# misconfigured upstream that streams MB of HTML on a soft-404.
DEFAULT_TEXT_MAX_BYTES = 256 * 1024

_ALLOWED_URL_SCHEMES = frozenset({"http", "https"})


__all__ = ["DEFAULT_TEXT_MAX_BYTES", "fetch_text_with_cache"]


async def fetch_text_with_cache(
    url: str,
    cache_dir: Path,
    *,
    client: httpx.AsyncClient,
    max_bytes: int = DEFAULT_TEXT_MAX_BYTES,
) -> str | None:
    """Return cached text if present; otherwise download, cache, return.

    404 returns ``None`` (sentinel; no negative caching). Other upstream
    failures raise ``MediaFetchError`` with the underlying ``httpx.HTTPError``
    chained via ``__cause__`` when applicable. Body is decoded as UTF-8;
    decode failure raises ``MediaFetchError`` chained from the
    ``UnicodeDecodeError``.

    Concurrency: same as P05's binary path — atomic ``.tmp + os.replace``
    means a concurrent same-URL pair never tears the cache file; the
    wasted second download is acceptable at single-user scale.
    """
    scheme = urlparse(url).scheme
    if scheme not in _ALLOWED_URL_SCHEMES:
        raise MediaFetchError(f"unsupported scheme: {scheme!r} for {url!r}")

    path = cache_path_for(url, cache_dir)
    if path.exists():
        return path.read_text(encoding="utf-8")

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    aborted = False
    total = 0
    try:
        async with client.stream("GET", url) as resp:
            if resp.status_code == 404:
                return None
            if resp.status_code != 200:
                raise MediaFetchError(f"upstream {resp.status_code} for {url!r}")
            tmp_handle = tmp.open("wb")
            try:
                async for chunk in resp.aiter_bytes(chunk_size=64 * 1024):
                    total += len(chunk)
                    if total > max_bytes:
                        msg = f"BodyTooLarge: {url}: streamed {total} bytes exceeds cap {max_bytes}"
                        logger.warning("media/cache_text: %s", msg)
                        aborted = True
                        raise MediaFetchError(msg)
                    tmp_handle.write(chunk)
                tmp_handle.flush()
                os.fsync(tmp_handle.fileno())
            finally:
                tmp_handle.close()
    except httpx.HTTPError as exc:
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)
        raise MediaFetchError(f"network error for {url!r}: {exc}") from exc
    except MediaFetchError:
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)
        raise

    if aborted:
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)
        return None  # unreachable; the raise above fires first
    if total == 0:
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)
        raise MediaFetchError(f"empty body for {url!r}")

    # Validate UTF-8 BEFORE committing the cache file so a non-decodable
    # body never poisons the slot. Read once into memory at this point
    # — we already streamed it to .tmp, the bytes are bounded by
    # max_bytes, and the parent caller is going to .read_text() anyway.
    raw_bytes = tmp.read_bytes()
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)
        raise MediaFetchError(f"decode failed for {url!r}: {exc}") from exc

    os.replace(tmp, path)
    fsync_parent_dir(path)
    return text

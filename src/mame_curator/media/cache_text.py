"""Lazy-fetch disk cache for text / JSON bodies.

Per ``docs/specs/P10-media-coverage.md`` § "Public API". Parallel to P05's
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
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

import httpx

from mame_curator.media.cache import (
    MediaFetchError,
    cache_path_for,
    download_into,
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
    before_network: Callable[[], None] | None = None,
) -> str | None:
    """Return cached text if present; otherwise download, cache, return.

    404 returns ``None`` (sentinel; no negative caching). Other upstream
    failures raise ``MediaFetchError`` with the underlying ``httpx.HTTPError``
    chained via ``__cause__`` when applicable. A body that is not UTF-8 is
    never kept, and raises ``MediaFetchError``.

    ``before_network`` runs only on a miss, just before the request: a rate
    limit's courtesy token is spent there (mame-curator-1235). The write is
    ``download_into``'s: a unique tmp file and ``os.replace``, so concurrent
    fetches of one URL never tear the slot.
    """
    scheme = urlparse(url).scheme
    if scheme not in _ALLOWED_URL_SCHEMES:
        raise MediaFetchError(f"unsupported scheme: {scheme!r} for {url!r}")

    path = cache_path_for(url, cache_dir)
    if not path.exists():
        if before_network is not None:
            before_network()
        if not await download_into(
            url, path, client=client, max_bytes=max_bytes, check=_require_utf8(url)
        ):
            return None
    return _read_slot(path, url)


def _require_utf8(url: str) -> Callable[[bytes], None]:
    """A ``download_into`` check refusing a body that is not UTF-8."""

    def check(body: bytes) -> None:
        try:
            body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise MediaFetchError(f"decode failed for {url!r}: {exc}") from exc

    return check


def _read_slot(path: Path, url: str) -> str:
    """The cached text; a slot that cannot be read is dropped (mame-curator-1235).

    Raises ``MediaFetchError`` then, so a caller answers as for any failed
    fetch, and the next request downloads it again.
    """
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        with contextlib.suppress(OSError):
            path.unlink(missing_ok=True)
        raise MediaFetchError(f"cached text for {url!r} could not be read: {exc}") from exc

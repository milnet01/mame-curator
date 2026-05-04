"""HTTP download primitive: sha256-verified, atomic, with retry and manual fallback.

Used by P07 INI refresh and P08 setup wizard. The caller supplies the
``httpx.AsyncClient`` (project convention — see ``media/cache.py``) so a single
client is reused across many downloads.

Contract:

- Returns the destination ``Path`` on success.
- Returns ``ManualFallback`` (sentinel) on total failure — caller surfaces the
  URL to the user for manual download.
- Atomic via ``_atomic.atomic_write_bytes`` — destination is never partially
  written; checksum-failed bodies are dropped before any write happens.
- Retry with exponential backoff on network errors; a checksum mismatch does
  NOT retry the same URL (a server serving the wrong file won't fix itself)
  but DOES try the next mirror.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import httpx

from mame_curator._atomic import atomic_write_bytes

logger = logging.getLogger(__name__)


class DownloadError(Exception):
    """Base class for download failures."""


class ChecksumMismatch(DownloadError):
    """Downloaded file's sha256 didn't match the expected value."""


@dataclass(frozen=True)
class ManualFallback:
    """All retries exhausted. Caller surfaces ``url`` to the user."""

    url: str
    reason: str


async def download(
    *,
    url: str,
    dest: Path,
    client: httpx.AsyncClient,
    sha256: str | None = None,
    mirrors: Sequence[str] = (),
    max_attempts: int = 4,
) -> Path | ManualFallback:
    """Download ``url`` to ``dest`` atomically.

    Verifies sha256 if given. Retries each URL with exponential backoff
    (1s, 2s, 4s before retries 1/2/3) up to ``max_attempts`` per URL. On a
    checksum mismatch, falls through to the next mirror immediately.

    Returns the dest ``Path`` on success or ``ManualFallback`` on total
    failure. The caller-supplied ``AsyncClient`` is reused; lifecycle is
    the caller's responsibility.
    """
    urls_to_try = [url, *mirrors]
    last_error = ""

    for u in urls_to_try:
        for attempt in range(max_attempts):
            if attempt > 0:
                await asyncio.sleep(2 ** (attempt - 1))
            try:
                response = await client.get(u)
                response.raise_for_status()
                body = response.content
            except httpx.HTTPError as e:
                last_error = f"{type(e).__name__}: {e}"
                logger.warning(
                    "downloads: attempt %d/%d for %s failed: %s",
                    attempt + 1,
                    max_attempts,
                    u,
                    last_error,
                )
                continue

            if sha256 is not None:
                actual = hashlib.sha256(body).hexdigest()
                if actual != sha256:
                    last_error = f"ChecksumMismatch: {u}: expected {sha256}, got {actual}"
                    logger.warning("downloads: %s", last_error)
                    # Server is serving wrong content; same URL won't fix it.
                    break

            atomic_write_bytes(dest, body)
            return dest

    return ManualFallback(url=url, reason=last_error or "no attempts made")

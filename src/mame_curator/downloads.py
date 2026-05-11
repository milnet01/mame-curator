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
from urllib.parse import urlparse

import httpx

from mame_curator._atomic import atomic_write_bytes

logger = logging.getLogger(__name__)

# FP20-F: schemes accepted by ``download()``. Everything else (file, data,
# ftp, javascript, gopher, …) raises ``InvalidUrlError`` at function entry
# before any ``httpx.AsyncClient.get`` call. A misconfigured transport
# could otherwise let ``file://`` exfiltrate local content or ``data:``
# inject arbitrary bodies.
_ALLOWED_URL_SCHEMES = frozenset({"http", "https"})


class DownloadError(Exception):
    """Base class for download failures."""


class ChecksumMismatch(DownloadError):
    """Downloaded file's sha256 didn't match the expected value."""


class InvalidUrlError(DownloadError):
    """FP20-F: URL scheme is not in the http/https allowlist."""


def _check_scheme(u: str) -> None:
    scheme = urlparse(u).scheme.lower()
    if scheme not in _ALLOWED_URL_SCHEMES:
        raise InvalidUrlError(
            f"download(): URL scheme {scheme!r} not allowed (expected one of "
            f"{sorted(_ALLOWED_URL_SCHEMES)}): {u!r}"
        )


@dataclass(frozen=True)
class ManualFallback:
    """All retries exhausted. Caller surfaces ``url`` to the user."""

    url: str
    reason: str


# FP21-P: cap on download body size. Today's INI sources are < 1 MB; a
# future listxml (~50 MB) needs streaming + a cap to prevent runaway
# responses from a misbehaving mirror from blowing up worker memory.
# 100 MB is generous for our use cases (DAT files, listxml, INIs) while
# still defending against gigabyte-scale exfiltration attacks.
DEFAULT_MAX_BYTES = 100 * 1024 * 1024


async def download(
    *,
    url: str,
    dest: Path,
    client: httpx.AsyncClient,
    sha256: str | None = None,
    mirrors: Sequence[str] = (),
    max_attempts: int = 4,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> Path | ManualFallback:
    """Download ``url`` to ``dest`` atomically.

    Verifies sha256 if given. Retries each URL with exponential backoff
    (1s, 2s, 4s before retries 1/2/3) up to ``max_attempts`` per URL. On a
    checksum mismatch, falls through to the next mirror immediately.

    FP21-P: body bytes are streamed and summed against ``max_bytes``;
    the request is aborted if the running total exceeds the cap. The
    Content-Length header (when present) is also pre-checked so an
    obviously oversized download fails fast without consuming bandwidth.

    Returns the dest ``Path`` on success or ``ManualFallback`` on total
    failure. The caller-supplied ``AsyncClient`` is reused; lifecycle is
    the caller's responsibility.
    """
    urls_to_try = [url, *mirrors]
    # FP20-F: validate every URL up-front so a poisoned mirror can't
    # trigger a transport-level attack on fallback.
    for u in urls_to_try:
        _check_scheme(u)

    last_error = ""

    for u in urls_to_try:
        for attempt in range(max_attempts):
            if attempt > 0:
                await asyncio.sleep(2 ** (attempt - 1))
            try:
                # FP21-P: stream-mode request so we can enforce the
                # byte cap incrementally and avoid buffering oversized
                # bodies in memory.
                async with client.stream("GET", u) as response:
                    response.raise_for_status()
                    declared = response.headers.get("Content-Length")
                    if declared is not None:
                        try:
                            if int(declared) > max_bytes:
                                last_error = (
                                    f"BodyTooLarge: {u}: Content-Length "
                                    f"{declared} exceeds cap {max_bytes}"
                                )
                                logger.warning("downloads: %s", last_error)
                                break  # next mirror; same URL won't shrink
                        except ValueError:
                            pass  # malformed header; fall through to streaming cap
                    chunks: list[bytes] = []
                    total = 0
                    async for chunk in response.aiter_bytes(chunk_size=64 * 1024):
                        total += len(chunk)
                        if total > max_bytes:
                            last_error = (
                                f"BodyTooLarge: {u}: streamed {total} bytes exceeds cap {max_bytes}"
                            )
                            logger.warning("downloads: %s", last_error)
                            chunks = []
                            break
                        chunks.append(chunk)
                    if last_error.startswith("BodyTooLarge"):
                        break  # next mirror
                    body = b"".join(chunks)
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

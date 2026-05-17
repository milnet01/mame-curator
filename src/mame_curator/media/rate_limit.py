"""Per-source rate-limit primitives for the P10 media-source chain.

Per ``docs/specs/P10.md`` § "Public API" + § "Source contracts". Each
source that hits an upstream owns a ``TokenBucket`` instance constructed
at lifespan startup; the source calls ``bucket.acquire()`` before any
upstream I/O and raises ``MediaRateLimited`` on a False return so the
orchestrator falls through to the next source.

``TokenBucket`` takes an injectable ``time_fn`` so tests advance time
deterministically without ``time.sleep``. Production constructs it
without overriding the default ``time.monotonic``.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from mame_curator.media.cache import MediaError


class MediaRateLimited(MediaError):
    """Source's per-process rate limiter is empty.

    Raised by source ``prepare`` implementations after a False ``acquire``.
    The orchestrator catches and falls through to the next source.
    """


class TokenBucket:
    """Classic token-bucket rate limiter, in-memory, single-process.

    Tokens accumulate at ``rate`` per second up to ``capacity``. Each
    ``acquire()`` consumes one token if available. No async — the bucket
    is consulted before kicking off any await-able I/O.
    """

    __slots__ = ("_capacity", "_last", "_rate", "_time_fn", "_tokens")

    def __init__(
        self,
        *,
        rate: float,
        capacity: int,
        time_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        """Construct a token bucket with ``capacity`` initial tokens.

        ``rate`` is tokens-per-second; ``capacity`` is the burst cap.
        ``time_fn`` is the monotonic clock — overridden in tests.
        """
        if rate <= 0:
            raise ValueError(f"rate must be positive; got {rate}")
        if capacity <= 0:
            raise ValueError(f"capacity must be positive; got {capacity}")
        self._rate = rate
        self._capacity = capacity
        self._time_fn = time_fn
        self._tokens: float = float(capacity)
        self._last: float = time_fn()

    def acquire(self) -> bool:
        """Consume one token if available; return True on success."""
        now = self._time_fn()
        elapsed = now - self._last
        if elapsed > 0:
            self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
            self._last = now
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True
        return False

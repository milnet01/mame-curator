"""Tests for ``TokenBucket`` + ``MediaRateLimited``.

Per ``docs/specs/P10.md`` § Public API. Pure tests — no network, no real
clock. The bucket takes an injectable ``time_fn`` so tests advance time
deterministically via a fake monotonic clock.
"""

from __future__ import annotations

import pytest


def test_token_bucket_admits_burst_up_to_capacity() -> None:
    """Capacity 10, refill rate 1/sec → ten immediate acquires succeed;
    eleventh fails until at least 1 second has elapsed."""
    from mame_curator.media import TokenBucket

    now = 1000.0
    bucket = TokenBucket(rate=1.0, capacity=10, time_fn=lambda: now)

    for _ in range(10):
        assert bucket.acquire() is True
    assert bucket.acquire() is False, "11th immediate acquire should fail"

    now += 0.5
    assert bucket.acquire() is False, "Half-second later, still no token"

    now += 0.6  # total elapsed 1.1s → one full token refilled
    assert bucket.acquire() is True
    assert bucket.acquire() is False


def test_token_bucket_refills_at_configured_rate() -> None:
    """0 tokens, 5s elapsed at 1/sec → 5 tokens available."""
    from mame_curator.media import TokenBucket

    now = 0.0
    bucket = TokenBucket(rate=1.0, capacity=10, time_fn=lambda: now)

    for _ in range(10):
        bucket.acquire()
    assert bucket.acquire() is False

    now = 5.0
    for _ in range(5):
        assert bucket.acquire() is True, "Should have 5 tokens after 5s"
    assert bucket.acquire() is False, "6th should fail"


def test_token_bucket_caps_at_capacity() -> None:
    """10/sec refill, capacity 10, idle for an hour → still only 10 tokens."""
    from mame_curator.media import TokenBucket

    now = 0.0
    bucket = TokenBucket(rate=10.0, capacity=10, time_fn=lambda: now)

    # Burn down to 0
    for _ in range(10):
        bucket.acquire()

    now = 3600.0  # 1 hour idle
    # Should be exactly capacity tokens, not 36_000
    for _ in range(10):
        assert bucket.acquire() is True
    assert bucket.acquire() is False, "Should cap at capacity, not overflow"


def test_token_bucket_advances_last_on_backward_clock_step() -> None:
    """FP32 LOW: ``_last`` advances on every ``acquire`` — even when the injected
    clock reports elapsed<=0 (a non-monotonic step backward). Pre-fix ``_last``
    stayed anchored to the pre-step time, so a later forward read measured a
    negative delta and never re-credited. Observable: after draining at a
    stepped-back time, a genuine forward delta refills a token."""
    from mame_curator.media import TokenBucket

    times = iter([100.0, 90.0, 95.0])  # construct=100, step back to 90, then 95
    bucket = TokenBucket(rate=1.0, capacity=1, time_fn=lambda: next(times))

    assert bucket.acquire() is True, "drains the only token at t=90"
    # Pre-fix: _last stuck at 100 → t=95 reads elapsed=-5 → no credit → False.
    # Fixed: _last==90 → t=95 credits 5*rate (capped at capacity=1) → True.
    assert bucket.acquire() is True


def test_media_rate_limited_inherits_media_error() -> None:
    """MediaRateLimited subclasses MediaError so callers can catch the base."""
    from mame_curator.media import MediaError, MediaRateLimited

    with pytest.raises(MediaError):
        raise MediaRateLimited("test")

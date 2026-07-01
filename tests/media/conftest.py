"""Shared helpers for the per-source ``test_sources_*.py`` files.

FP31 (mame-curator-1046) split the 554-line ``test_sources.py`` into one
file per concrete source. ``_machine`` and ``_make_unbounded_limiter`` were
module-level helpers used across all of them, so they move here and are
imported explicitly — mirroring ``tests/filter/conftest.py``'s ``m()``
pattern (plain functions, not fixtures, since call sites pass per-test args).
"""

from __future__ import annotations

import pytest

from mame_curator.media import TokenBucket
from mame_curator.parser.models import Machine


def _machine(name: str = "pacman", description: str = "Pac-Man") -> Machine:
    return Machine(name=name, description=description)


def _make_unbounded_limiter() -> TokenBucket:
    """Return a TokenBucket with capacity high enough for one prepare call."""
    return TokenBucket(rate=10.0, capacity=10)


@pytest.fixture(autouse=True)
def _reset_media_warn_dedup() -> None:
    """Clear the process-wide WARNING dedup guards before every media test.

    Chunk 7 dedups two WARNINGs process-wide (an unknown ``media.sources``
    name; a keyless MobyGames), so per-request source reconstruction can't
    spam the log. Those module-level guards persist across tests, so a test
    asserting a WARNING *count* would see zero if an earlier test already
    tripped the guard. Reset both before each test for isolation.
    """
    from mame_curator.media import mobygames
    from mame_curator.media.sources import _reset_unknown_source_warn_dedup

    _reset_unknown_source_warn_dedup()
    mobygames._reset_missing_key_warn_dedup()

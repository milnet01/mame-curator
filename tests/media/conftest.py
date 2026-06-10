"""Shared helpers for the per-source ``test_sources_*.py`` files.

FP31 (mame-curator-1046) split the 554-line ``test_sources.py`` into one
file per concrete source. ``_machine`` and ``_make_unbounded_limiter`` were
module-level helpers used across all of them, so they move here and are
imported explicitly — mirroring ``tests/filter/conftest.py``'s ``m()``
pattern (plain functions, not fixtures, since call sites pass per-test args).
"""

from __future__ import annotations

from mame_curator.media import TokenBucket
from mame_curator.parser.models import Machine


def _machine(name: str = "pacman", description: str = "Pac-Man") -> Machine:
    return Machine(name=name, description=description)


def _make_unbounded_limiter() -> TokenBucket:
    """Return a TokenBucket with capacity high enough for one prepare call."""
    return TokenBucket(rate=10.0, capacity=10)

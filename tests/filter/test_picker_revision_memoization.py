"""DS02 G1 — `revision_key_of` is memoized via `functools.lru_cache`.

`revision_key_of` re-runs the same regex chain every time it is
called.  `_cmp_revision` in `filter.picker` calls it twice per
comparison (a, b) in the picker comparator chain, which `sorted()`
drives O(N log N) times across a candidate group. For a candidate
group of N=50 machines that's ~600 comparisons → ~1200 regex
evaluations on the same handful of description strings.

The fix wraps the function with ``@functools.lru_cache(maxsize=8192)``
so identical inputs are answered from the cache. Description strings
are short hashable str; cardinality is bounded by the DAT (~43k).
8 K covers any realistic candidate-group sort without unbounded
growth.

Test contract:
- The wrapper exposes a `cache_info()` method (the lru_cache attribute
  surface). Pre-fix the function has no such attribute.
- Two calls with the same input result in `hits >= 1`.
- A sort over N pairs with K distinct descriptions performs at most
  K misses (every unique description is computed at most once).
"""

from __future__ import annotations

import random

import pytest

from mame_curator.filter import heuristics


@pytest.mark.xfail(strict=True, reason="DS02 G1 — RED until @lru_cache wraps revision_key_of")
def test_revision_key_of_exposes_lru_cache_attribute() -> None:
    """Post-fix the function is wrapped with `functools.lru_cache`."""
    assert hasattr(heuristics.revision_key_of, "cache_info"), (
        "revision_key_of is not wrapped with functools.lru_cache; "
        "pre-DS02-G1 it was a bare function — apply @lru_cache(maxsize=8192)"
    )
    assert hasattr(heuristics.revision_key_of, "cache_clear")


@pytest.mark.xfail(strict=True, reason="DS02 G1 — RED until @lru_cache wraps revision_key_of")
def test_revision_key_of_caches_duplicate_calls() -> None:
    """Calling twice with the same input registers a cache hit."""
    heuristics.revision_key_of.cache_clear()
    heuristics.revision_key_of("Pac-Man (rev A)")
    heuristics.revision_key_of("Pac-Man (rev A)")
    info = heuristics.revision_key_of.cache_info()
    assert info.hits >= 1, f"expected at least one cache hit, cache_info={info}"
    assert info.misses >= 1


@pytest.mark.xfail(strict=True, reason="DS02 G1 — RED until @lru_cache wraps revision_key_of")
def test_revision_key_of_miss_count_bounded_by_unique_inputs() -> None:
    """Sorting a 1000-pair workload over K unique descriptions

    drives at most K misses through the cache — every other call
    answers from the lru_cache table.
    """
    descriptions = [f"Game (rev {chr(ord('A') + (i % 8))})" for i in range(8)]
    rng = random.Random(20260515)  # noqa: S311 — deterministic test seed, not crypto
    workload = [rng.choice(descriptions) for _ in range(1000)]

    heuristics.revision_key_of.cache_clear()
    for desc in workload:
        heuristics.revision_key_of(desc)

    info = heuristics.revision_key_of.cache_info()
    assert info.misses == len(set(descriptions)), (
        f"expected misses == unique inputs ({len(set(descriptions))}), "
        f"got misses={info.misses} hits={info.hits} (total={len(workload)})"
    )
    assert info.hits == len(workload) - info.misses

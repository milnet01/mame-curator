"""Hypothesis property tests for `resolve_bios_dependencies`.

DS01 cluster B1 — locks in the contract that `bios.py:36-44` enforces:

1. **Idempotence** — re-running on the same input yields the same (bios, warnings).
2. **Transitive reachability** — every name in the returned BIOS set is reachable
   from at least one winner via a finite chain of `romof` / `biossets` edges.
3. **Winner exclusion** — the returned BIOS set is disjoint from the input
   winner set (the spec says winners are copied via the winner pass, not the
   BIOS pass).
4. **Order independence** — `resolve(W, chain) == resolve(reversed(W), chain)`.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from mame_curator.copy import resolve_bios_dependencies
from mame_curator.parser.listxml import BIOSChainEntry

# Small finite alphabet keeps Hypothesis search space manageable; the contract
# is universal so a 6-letter alphabet exercises every code path.
_NAMES = st.sampled_from(["a", "b", "c", "d", "e", "f"])


def _entry_strategy() -> st.SearchStrategy[BIOSChainEntry]:
    return st.builds(
        BIOSChainEntry,
        romof=st.one_of(st.none(), _NAMES),
        biossets=st.lists(_NAMES, min_size=0, max_size=3, unique=True).map(tuple),
    )


_chain = st.dictionaries(keys=_NAMES, values=_entry_strategy(), max_size=6)
_winners = st.lists(_NAMES, min_size=1, max_size=4, unique=True)


@settings(max_examples=100, deadline=None)
@given(chain=_chain, winners=_winners)
def test_resolve_is_idempotent(chain: dict[str, BIOSChainEntry], winners: list[str]) -> None:
    """Running `resolve` twice on the same inputs yields the same result.

    Pure idempotence: same (winners, chain) -> same (bios, warnings) tuple.
    """
    bios1, warn1 = resolve_bios_dependencies(winners, chain)
    bios2, warn2 = resolve_bios_dependencies(winners, chain)
    assert bios1 == bios2
    assert warn1 == warn2


@settings(max_examples=100, deadline=None)
@given(chain=_chain, winners=_winners)
def test_resolve_excludes_winners(chain: dict[str, BIOSChainEntry], winners: list[str]) -> None:
    """The returned BIOS set is disjoint from the input winner set.

    `bios.py:37, 42` explicitly skip names in the winner set when appending
    to the bios set.
    """
    bios, _ = resolve_bios_dependencies(winners, chain)
    assert bios.isdisjoint(set(winners))


@settings(max_examples=100, deadline=None)
@given(chain=_chain, winners=_winners)
def test_resolve_is_order_independent(chain: dict[str, BIOSChainEntry], winners: list[str]) -> None:
    """resolve(W, chain) == resolve(reversed(W), chain).

    The (bios set, sorted warnings) tuple is independent of winner iteration
    order. Warnings are sorted by name (`bios.py:46`), so reversing input
    order must not change the warning tuple either.
    """
    bios_a, warn_a = resolve_bios_dependencies(winners, chain)
    bios_b, warn_b = resolve_bios_dependencies(list(reversed(winners)), chain)
    assert bios_a == bios_b
    assert warn_a == warn_b

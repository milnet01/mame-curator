"""Tests for `resolve_bios_dependencies` (Phase 3 step 3).

Spec clauses pinned:
- Transitive `romof` + `<biosset>` walk.
- Dedup across multiple winners.
- Cycle safety via `seen` set.
- Self-reference filter.
- Missing-from-listxml warning (non-fatal).
- Winner set NOT included in returned BIOS set.
"""

from __future__ import annotations

from mame_curator.copy import resolve_bios_dependencies
from mame_curator.parser.listxml import BIOSChainEntry


def test_parse_listxml_bios_chain_extracts_romof_and_biossets(
    bios_chain: dict[str, BIOSChainEntry],
) -> None:
    """Parser extension returns BIOSChainEntry per machine with romof + biossets."""
    assert "kof94" in bios_chain
    assert bios_chain["kof94"].romof == "neogeo"
    assert bios_chain["kof94"].biossets == ("euro", "us")
    # Machines without romof or biosset are absent from the map.
    assert "orphan" not in bios_chain


def test_parse_listxml_bios_chain_handles_self_reference(
    bios_chain: dict[str, BIOSChainEntry],
) -> None:
    """A `romof` that points at the same name is captured faithfully."""
    assert bios_chain["selfref"].romof == "selfref"


def test_resolve_bios_chain_simple(bios_chain: dict[str, BIOSChainEntry]) -> None:
    """One winner with romof + biosset → returns parent + biossets."""
    bios, warnings = resolve_bios_dependencies(["kof94"], bios_chain)
    # neogeo (romof), euro + us (biossets); kof94 itself NOT included.
    assert bios == frozenset({"neogeo", "euro", "us"})
    assert warnings == ()


def test_resolve_bios_chain_transitive(bios_chain: dict[str, BIOSChainEntry]) -> None:
    """sf2ce → sf2 (romof) → cps1bios (romof)."""
    bios, warnings = resolve_bios_dependencies(["sf2ce"], bios_chain)
    assert bios == frozenset({"sf2", "cps1bios"})
    assert warnings == ()


def test_bios_dedup_across_winners(bios_chain: dict[str, BIOSChainEntry]) -> None:
    """Multiple winners sharing a parent BIOS chain → deduplicated set.

    Per spec: the winner set itself is NOT included in the returned BIOS set
    (it covers only *additional* dependencies). kof94 is a winner here, so
    even though kof94a's romof references it, kof94 stays out of the BIOS
    set — `run_copy` will copy kof94 once via its winner pass, and the
    BIOS pass adds only neogeo + biossets.
    """
    bios, _ = resolve_bios_dependencies(["kof94", "kof94a"], bios_chain)
    assert bios == frozenset({"neogeo", "euro", "us"})


def test_resolve_bios_chain_cycle_safety(bios_chain: dict[str, BIOSChainEntry]) -> None:
    """Self-referencing romof does not loop."""
    bios, _ = resolve_bios_dependencies(["selfref"], bios_chain)
    # selfref's romof is itself; the spec's `entry.romof != name` guard
    # filters it out, so no BIOS is added.
    assert bios == frozenset()


def test_resolve_bios_chain_winner_not_in_listxml_emits_warning(
    bios_chain: dict[str, BIOSChainEntry],
) -> None:
    """Winner absent from bios_chain emits BIOSResolutionWarning, no crash."""
    bios, warnings = resolve_bios_dependencies(["unknownmachine"], bios_chain)
    assert bios == frozenset()
    assert len(warnings) == 1
    assert warnings[0].name == "unknownmachine"
    assert warnings[0].kind == "missing_from_listxml"


def test_resolve_bios_chain_warnings_canonical_order(bios_chain: dict[str, BIOSChainEntry]) -> None:
    """Multiple warnings sorted alphabetically by name for byte-identical reports."""
    _, warnings = resolve_bios_dependencies(["zeta", "alpha", "beta"], bios_chain)
    assert [w.name for w in warnings] == ["alpha", "beta", "zeta"]


def test_resolve_bios_chain_winners_not_in_returned_set(
    bios_chain: dict[str, BIOSChainEntry],
) -> None:
    """A winner is never in its own returned BIOS set even when it's
    referenced as a romof target by another machine."""
    bios, _ = resolve_bios_dependencies(["kof94"], bios_chain)
    assert "kof94" not in bios


def test_resolve_bios_chain_orphan_machine(bios_chain: dict[str, BIOSChainEntry]) -> None:
    """An orphan (machine in DAT but not in bios_chain map because it has
    no romof and no biosset) emits the missing-from-listxml warning."""
    bios, warnings = resolve_bios_dependencies(["orphan"], bios_chain)
    assert bios == frozenset()
    assert any(w.name == "orphan" for w in warnings)

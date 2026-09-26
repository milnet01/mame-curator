"""Tests for `resolve_bios_dependencies` (Phase 3 step 3).

Spec clauses pinned:
- Transitive `romof` walk; `<biosset>` names are display-only and never
  copied or added to the BIOS set (mame-curator-1109).
- Dedup across multiple winners.
- Cycle safety via `seen` set.
- Self-reference filter.
- Missing-from-listxml warning (non-fatal, winners only).
- Winner set NOT included in returned BIOS set.
- Every `<machine>` gets a `BIOSChainEntry`, carrying `is_bios`; a name is
  added to the resolved BIOS set only when its entry's `is_bios` is True
  (mame-curator-1109 -- membership in the chain is not a BIOS signal).

Why this exists: mame-curator-1109 -- the BIOS resolver was copying
`<biosset>` option names and clone parents as if they were BIOS romsets.
The fix restricts the copied BIOS set to machines the listxml actually
flags `isbios="yes"`, reached by walking `romof` alone.
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
    # mame-curator-1109: EVERY machine gets an entry now, including one with
    # neither romof nor biosset -- an earlier version recorded only machines
    # with a romof or a <biosset>, which made a plain winner like sf2 look
    # missing. "orphan" (no romof, no biosset) must be present, with the
    # all-default entry.
    assert "orphan" in bios_chain, (
        "orphan missing from bios_chain -- every-machine-gets-an-entry "
        "(mame-curator-1109) is not implemented"
    )
    assert bios_chain["orphan"].romof is None
    assert bios_chain["orphan"].biossets == ()


def test_parse_listxml_bios_chain_records_is_bios(
    bios_chain: dict[str, BIOSChainEntry],
) -> None:
    """mame-curator-1109: BIOSChainEntry.is_bios reflects <machine isbios="yes">.

    neogeo and cps1bios carry isbios="yes" in the fixture; kof94 (a regular
    game with a romof + biossets) does not.
    """
    assert "neogeo" in bios_chain, (
        "neogeo missing from bios_chain -- every-machine-gets-an-entry "
        "(mame-curator-1109) is not implemented"
    )
    assert bios_chain["neogeo"].is_bios is True
    assert "cps1bios" in bios_chain
    assert bios_chain["cps1bios"].is_bios is True
    assert bios_chain["kof94"].is_bios is False


def test_parse_listxml_bios_chain_handles_self_reference(
    bios_chain: dict[str, BIOSChainEntry],
) -> None:
    """A `romof` that points at the same name is captured faithfully."""
    assert bios_chain["selfref"].romof == "selfref"


def test_resolve_bios_chain_simple(bios_chain: dict[str, BIOSChainEntry]) -> None:
    """One winner with romof + biosset → returns only the BIOS parent.

    mame-curator-1109: only machines the listxml flags isbios="yes" are
    copied as BIOS dependencies. neogeo qualifies; kof94's own biossets
    ("euro", "us") are option names inside kof94's own romset, not short
    names of other machines, and must never appear in the returned set.
    """
    bios, warnings = resolve_bios_dependencies(["kof94"], bios_chain)
    assert bios == frozenset({"neogeo"})
    assert warnings == ()


def test_resolve_bios_chain_transitive(bios_chain: dict[str, BIOSChainEntry]) -> None:
    """sf2ce → sf2 (romof, not a BIOS) → cps1bios (romof, is_bios="yes").

    mame-curator-1109: sf2 is walked (its non-merged-set clone sf2ce still
    needs to reach cps1bios) but is NOT itself added to the BIOS set --
    only cps1bios (the actual BIOS machine) is copied as a dependency.
    """
    bios, warnings = resolve_bios_dependencies(["sf2ce"], bios_chain)
    assert bios == frozenset({"cps1bios"})
    assert warnings == ()


def test_bios_dedup_across_winners(bios_chain: dict[str, BIOSChainEntry]) -> None:
    """Multiple winners sharing a parent BIOS chain → deduplicated set.

    Per spec: the winner set itself is NOT included in the returned BIOS set
    (it covers only *additional* dependencies). kof94 is a winner here, so
    even though kof94a's romof references it, kof94 stays out of the BIOS
    set — `run_copy` will copy kof94 once via its winner pass. Per
    mame-curator-1109, kof94's own biossets never enter the BIOS set either
    (option names, not machines) -- only the actual BIOS machine (neogeo)
    does.
    """
    bios, _ = resolve_bios_dependencies(["kof94", "kof94a"], bios_chain)
    assert bios == frozenset({"neogeo"})


def test_resolve_bios_chain_clone_reaches_bios_through_non_bios_parent(
    bios_chain: dict[str, BIOSChainEntry],
) -> None:
    """mame-curator-1109: kof94a (romof=kof94, not itself a BIOS) still
    reaches neogeo transitively through its non-BIOS parent kof94.

    Decided by the user 2026-09-26 (mame-curator-1109): a parent that is not
    a BIOS is not copied (a non-merged clone's zip already holds its
    parent's ROMs) -- so kof94 is walked but never added, and neither are
    its biossets ("euro"); only neogeo (the actual BIOS at the top of the
    chain) is in the result.
    """
    bios, warnings = resolve_bios_dependencies(["kof94a"], bios_chain)
    assert bios == frozenset({"neogeo"})
    assert "kof94" not in bios
    assert "euro" not in bios
    assert warnings == ()


def test_resolve_bios_chain_clone_with_non_bios_parent_and_no_bios_is_empty() -> None:
    """mame-curator-1109: a clone whose romof chain never reaches an
    is_bios=True machine resolves to an empty BIOS set -- an ordinary
    parent/clone relationship is not itself a BIOS signal (spec example:
    "pacman (romof puckman) resolves to no BIOS").

    Hand-built chain (the copy fixture's own romof chains all eventually
    reach a real BIOS, so this constructs a small chain dict where they
    don't).
    """
    chain: dict[str, BIOSChainEntry] = {
        "clonegame": BIOSChainEntry(romof="regularparent"),
        "regularparent": BIOSChainEntry(romof=None),
    }
    bios, warnings = resolve_bios_dependencies(["clonegame"], chain)
    assert bios == frozenset()
    assert warnings == ()


def test_resolve_bios_chain_biossets_never_in_returned_set(
    bios_chain: dict[str, BIOSChainEntry],
) -> None:
    """mame-curator-1109: <biosset> names are BIOS *option* names inside a
    machine's own romset, never short names of other machines -- they must
    never appear in the resolved BIOS set, for any winner whose chain
    touches a machine that declares biossets."""
    bios, _ = resolve_bios_dependencies(["kof94"], bios_chain)
    assert "euro" not in bios
    assert "us" not in bios
    bios_transitive, _ = resolve_bios_dependencies(["kof94a"], bios_chain)
    assert "euro" not in bios_transitive
    assert "us" not in bios_transitive


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
    """mame-curator-1109: orphan (no romof, no biosset) now HAS an entry in
    bios_chain (every-machine-gets-an-entry), so resolving it hits a real
    entry rather than an absent name -- no warning, empty BIOS set.

    Old contract: orphan was absent from the map entirely (no romof, no
    biosset recorded), so resolving a winner named "orphan" looked exactly
    like a listxml/DAT mismatch and emitted `missing_from_listxml`. That
    conflated "no BIOS dependency" with "not in the listxml at all" -- the
    every-machine rule fixes the conflation, so the warning must disappear.
    """
    bios, warnings = resolve_bios_dependencies(["orphan"], bios_chain)
    assert bios == frozenset()
    assert warnings == (), (
        f"expected no warning for orphan (it has a real, if empty, chain "
        f"entry per mame-curator-1109), got {warnings!r}"
    )


# FP05 — B1 test below


def test_resolve_silently_handles_transitive_missing_intermediary() -> None:
    """B1 (reclassified) — a winner whose chain transitively reaches a name
    absent from `bios_chain` emits NO warning. Transitive misses conflate
    with leaf-BIOS machines that simply have no upstream chain entry; the
    real "missing BIOS file" failure mode is surfaced later as
    `SKIPPED_MISSING_SOURCE` during the copy phase. This test pins the
    silent-handling contract so future fix-passes don't accidentally
    re-introduce a noisy transitive warning.

    mame-curator-1109: `missingY` is popped but its entry is absent (`None`),
    so it can never be confirmed `is_bios` -- it is NOT added to the
    returned BIOS set (only `entry.is_bios` machines are). The no-warning
    assertion is unchanged; only the membership assertion inverts.
    """
    chain: dict[str, BIOSChainEntry] = {
        "winnerW": BIOSChainEntry(romof="bridgeX", biossets=()),
        "bridgeX": BIOSChainEntry(romof="missingY", biossets=()),
        # missingY absent from the chain — can't be confirmed as a BIOS, no warning.
    }
    bios, warnings = resolve_bios_dependencies(["winnerW"], chain)
    # missingY is absent from bios_chain, so it can't be confirmed is_bios;
    # it is never added to the returned set (mame-curator-1109 inversion of
    # the old "present in the chain at all == BIOS" membership test).
    assert "missingY" not in bios
    # No warning — transitive misses don't surface here.
    assert warnings == ()

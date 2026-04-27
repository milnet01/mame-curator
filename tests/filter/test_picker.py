"""Tests for Phase B tiebreaker comparators and pick_winner."""

from __future__ import annotations

from mame_curator.filter.config import FilterConfig
from mame_curator.filter.picker import explain_pick, pick_winner
from mame_curator.filter.types import FilterContext
from mame_curator.parser.models import DriverStatus, Machine


def m(**kw: object) -> Machine:
    name = str(kw.pop("name", "x"))
    description = str(kw.pop("description", name))
    return Machine(name=name, description=description, **kw)  # type: ignore[arg-type]


def test_tier_tiebreaker_wins() -> None:
    pacman = m(name="pacman", description="Pac-Man (USA)")
    pacmanf = m(name="pacmanf", description="Pac-Man speedup (USA)")
    ctx = FilterContext(bestgames_tier={"pacman": "Best", "pacmanf": "Average"})
    winner = pick_winner([pacman, pacmanf], parent="pacman", ctx=ctx, cfg=FilterConfig())
    assert winner.name == "pacman"


def test_preferred_genre_boost_breaks_tier_tie() -> None:
    a = m(name="a", description="A (World)")
    b = m(name="b", description="B (World)")
    ctx = FilterContext(category={"a": "Maze / Collect", "b": "Shooter / Vertical"})
    cfg = FilterConfig(preferred_genres=("Vertical",))
    assert pick_winner([a, b], parent="a", ctx=ctx, cfg=cfg).name == "b"


def test_parent_over_clone() -> None:
    parent = m(name="sf2", description="SF II (World)")
    clone = m(name="sf2ce", description="SF II CE (World)", cloneof="sf2")
    ctx = FilterContext(cloneof_map={"sf2ce": "sf2"})
    assert pick_winner([clone, parent], parent="sf2", ctx=ctx, cfg=FilterConfig()).name == "sf2"


def test_good_driver_beats_imperfect() -> None:
    a = m(name="a", description="A (World)", driver_status=DriverStatus.GOOD)
    b = m(name="b", description="B (World)", driver_status=DriverStatus.IMPERFECT)
    assert pick_winner([a, b], parent="a", ctx=FilterContext(), cfg=FilterConfig()).name == "a"


def test_region_priority() -> None:
    world = m(name="w", description="Foo (World)")
    usa = m(name="u", description="Foo (USA)")
    winner = pick_winner([usa, world], parent="w", ctx=FilterContext(), cfg=FilterConfig())
    assert winner.name == "w"


def test_revision_key_prefers_later() -> None:
    """Revision (rule 6) only fires when rules 1-5 tie. Parent-over-clone (rule 3)
    would otherwise short-circuit if either candidate's name == parent, so we use
    a parent name absent from the candidate list (the "all-clones, parent dropped
    in Phase A" scenario).
    """
    early = m(name="foo_s1", description="Foo (Set 1) (World)")
    late = m(name="foo_s3", description="Foo (Set 3) (World)")
    winner = pick_winner(
        [early, late], parent="foo_parent_absent", ctx=FilterContext(), cfg=FilterConfig()
    )
    assert winner.name == "foo_s3"


def test_alphabetical_fallback() -> None:
    a = m(name="abc", description="X (World)")
    b = m(name="xyz", description="X (World)")
    assert pick_winner([b, a], parent="abc", ctx=FilterContext(), cfg=FilterConfig()).name == "abc"


def test_explain_records_decisive_steps_only() -> None:
    pacman = m(name="pacman", description="Pac-Man (USA)")
    pacmanf = m(name="pacmanf", description="Pac-Man speedup (USA)")
    ctx = FilterContext(bestgames_tier={"pacman": "Best", "pacmanf": "Average"})
    chain = explain_pick([pacman, pacmanf], parent="pacman", ctx=ctx, cfg=FilterConfig())
    names = [hit.name for hit in chain]
    assert "tier" in names
    # Region is identical for both — must NOT appear.
    assert "region" not in names

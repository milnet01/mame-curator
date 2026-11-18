"""mame-curator-1236 — Phase C warning order, Phase D genre rule, region names.

CR-01-13: Phase C warnings followed the overrides file's order; filter/spec.md
says they are sorted.
CR-01-5: a session's `include_genres` matches the whole catver category, the
value the Library saves (user decision 2026-11-18), not the short genre
`drop_genres` uses.
"""

from __future__ import annotations

import pytest

from mame_curator.filter.config import FilterConfig
from mame_curator.filter.heuristics import Region, region_of
from mame_curator.filter.overrides import Overrides
from mame_curator.filter.runner import run_filter
from mame_curator.filter.sessions import Session, Sessions
from mame_curator.filter.types import FilterContext
from tests.filter.conftest import m, o


def test_phase_c_warnings_follow_override_key_order() -> None:
    machines = {"pacman": m(name="pacman")}
    result = run_filter(
        machines, FilterContext(), FilterConfig(), o(zz="pacman", aa="pacman"), Sessions()
    )
    assert result.ignored_overrides == ("aa", "zz")
    assert [w.split("'")[1] for w in result.warnings] == ["aa", "zz"]


def _visible(pattern: str) -> tuple[str, ...]:
    machines = {"xevious": m(name="xevious")}
    ctx = FilterContext(category={"xevious": "Shooter / Flying Vertical"})
    sessions = Sessions(active="s", sessions={"s": Session(include_genres=(pattern,))})
    return run_filter(machines, ctx, FilterConfig(), Overrides(), sessions).winners


def test_session_genre_matches_the_whole_category() -> None:
    assert _visible("Shooter / Flying Vertical") == ("xevious",)
    assert _visible("Shooter*") == ("xevious",)


def test_session_genre_does_not_match_the_short_genre_alone() -> None:
    assert _visible("Flying Vertical") == ()


@pytest.mark.parametrize("region", [r for r in Region if r is not Region.UNKNOWN])
def test_every_region_name_is_recognised(region: Region) -> None:
    """RR-01-10: the pattern's region names and the enum are one list."""
    assert region_of(f"Game ({region.value})") is region

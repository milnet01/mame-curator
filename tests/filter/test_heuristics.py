"""Tests for region and revision heuristics."""

import pytest

from mame_curator.filter.heuristics import Region, region_of, revision_key_of


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("Street Fighter II (World 910411)", Region.WORLD),
        ("Galaxian (USA, Set 2)", Region.USA),
        ("Sonic (Europe v2.1)", Region.EUROPE),
        ("Strider (Japan, prototype)", Region.JAPAN),
        ("Mahjong (Asia)", Region.ASIA),
        ("Mortal Kombat (Brazil)", Region.BRAZIL),
        ("Pac-Man (Midway)", Region.UNKNOWN),  # manufacturer parenthetical, not region
        ("Standalone Game", Region.UNKNOWN),
        ("Game (Germany 1998)", Region.GERMANY),
    ],
)
def test_region_of(description: str, expected: Region) -> None:
    assert region_of(description) is expected


def test_region_picks_first_match_only() -> None:
    """If two parentheticals look like regions, the first one wins."""
    assert region_of("Foo (World) (Japan)") is Region.WORLD


@pytest.mark.parametrize(
    ("description", "left_expected_higher_than"),
    [
        ("Foo (rev B)", "Foo (rev A)"),
        ("Foo (Set 3)", "Foo (Set 2)"),
        ("Foo v2.0", "Foo v1.5"),
        ("Foo v1.5", "Foo (rev Z)"),  # v-version family > rev-letter family
        ("Foo (rev A)", "Foo (Set 9)"),  # rev-letter family > set-number family
        ("Foo (Set 1)", "Foo"),  # any family > unmarked
    ],
)
def test_revision_key_orders_correctly(description: str, left_expected_higher_than: str) -> None:
    assert revision_key_of(description) > revision_key_of(left_expected_higher_than)


def test_revision_key_equal_for_no_marker() -> None:
    assert revision_key_of("Foo") == revision_key_of("Bar")

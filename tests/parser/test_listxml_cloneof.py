"""Tests for parse_listxml_cloneof.

FP31: the missing-file / malformed-XML error-path tests for ALL three
``parse_listxml_*`` functions live in ``test_listxml.py`` as a single
parametrized pair. Keeping `cloneof`-specific behavioural tests here.
"""

from pathlib import Path

from mame_curator.parser.listxml import parse_listxml_cloneof


def test_returns_clone_to_parent_map(listxml_cloneof: Path) -> None:
    cloneof = parse_listxml_cloneof(listxml_cloneof)
    assert cloneof == {
        "sf2ce": "sf2",
        "sf2t": "sf2",
        "pacmanf": "pacman",
    }


def test_parents_and_standalones_excluded(listxml_cloneof: Path) -> None:
    """Machines without a cloneof attribute do not appear in the map."""
    cloneof = parse_listxml_cloneof(listxml_cloneof)
    for parent in ("sf2", "pacman", "standalone"):
        assert parent not in cloneof

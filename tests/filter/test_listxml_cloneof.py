"""Tests for parse_listxml_cloneof."""

from pathlib import Path

import pytest

from mame_curator.parser.errors import ListxmlError
from mame_curator.parser.listxml import parse_listxml_cloneof


def test_returns_clone_to_parent_map(fixtures_dir: Path) -> None:
    cloneof = parse_listxml_cloneof(fixtures_dir / "listxml_cloneof.xml")
    assert cloneof == {
        "sf2ce": "sf2",
        "sf2t": "sf2",
        "pacmanf": "pacman",
    }


def test_parents_and_standalones_excluded(fixtures_dir: Path) -> None:
    """Machines without a cloneof attribute do not appear in the map."""
    cloneof = parse_listxml_cloneof(fixtures_dir / "listxml_cloneof.xml")
    for parent in ("sf2", "pacman", "standalone"):
        assert parent not in cloneof


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ListxmlError, match="not exist"):
        parse_listxml_cloneof(tmp_path / "nope.xml")


def test_malformed_xml_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.xml"
    bad.write_text("<mame><machine name='x' cloneof='y'>")
    with pytest.raises(ListxmlError):
        parse_listxml_cloneof(bad)

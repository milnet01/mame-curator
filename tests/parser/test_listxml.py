"""Tests for parse_listxml_disks."""

from pathlib import Path

import pytest

from mame_curator.parser.errors import ListxmlError
from mame_curator.parser.listxml import parse_listxml_disks


def test_returns_machines_with_disk_elements(listxml_with_disks: Path) -> None:
    chd_required = parse_listxml_disks(listxml_with_disks)
    assert chd_required == {"kinst", "kinst2"}


def test_machines_without_disk_excluded(listxml_with_disks: Path) -> None:
    chd_required = parse_listxml_disks(listxml_with_disks)
    assert "pacman" not in chd_required


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ListxmlError, match="not exist"):
        parse_listxml_disks(tmp_path / "nope.xml")


def test_malformed_xml_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.xml"
    bad.write_text("<mame><machine name='x'>")
    with pytest.raises(ListxmlError):
        parse_listxml_disks(bad)

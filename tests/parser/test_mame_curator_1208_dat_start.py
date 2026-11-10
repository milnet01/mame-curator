"""mame-curator-1208 — tell a game list from another file in a moment.

The setup wizard accepted any file on its list step and found out only when
the last step read it in full. ``check_dat_start`` reads up to the first
machine, so the list step can refuse a wrong file at once.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from mame_curator import parser
from mame_curator.parser import DATError, check_dat_start

FIXTURES = Path(__file__).parent / "fixtures"


def test_a_game_list_passes() -> None:
    check_dat_start(FIXTURES / "mini.dat.xml")


def test_a_zipped_game_list_passes(tmp_path: Path) -> None:
    zipped = tmp_path / "mame.zip"
    with zipfile.ZipFile(zipped, "w") as zf:
        zf.write(FIXTURES / "mini.dat.xml", "mame.xml")
    check_dat_start(zipped)


def test_a_file_that_is_not_xml_is_refused(tmp_path: Path) -> None:
    notes = tmp_path / "notes.xml"
    notes.write_text("<not a game list")
    with pytest.raises(DATError):
        check_dat_start(notes)


def test_xml_with_no_machine_is_refused(tmp_path: Path) -> None:
    other = tmp_path / "other.xml"
    other.write_text("<?xml version='1.0'?><playlist><item>x</item></playlist>")
    with pytest.raises(DATError):
        check_dat_start(other)


def test_a_first_machine_that_does_not_read_is_refused(tmp_path: Path) -> None:
    broken = tmp_path / "broken.xml"
    broken.write_text("<datafile><machine name='a'></machine></datafile>")
    with pytest.raises(DATError):
        check_dat_start(broken)


def test_a_missing_file_is_refused(tmp_path: Path) -> None:
    with pytest.raises(DATError):
        check_dat_start(tmp_path / "gone.xml")


def test_reads_no_further_than_the_first_machine(tmp_path: Path) -> None:
    """A fault after the first machine is left to the full read, by design."""
    late = tmp_path / "late.xml"
    late.write_text(
        "<datafile><machine name='a'><description>A</description></machine><machine><broken"
    )
    check_dat_start(late)
    with pytest.raises(DATError):
        parser.parse_dat(late)


def test_is_public() -> None:
    assert "check_dat_start" in parser.__all__

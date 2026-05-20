"""Tests for parse_dat — happy-path parsing (DS05 Cluster C basic seam).

Extracted from `tests/parser/test_dat.py` during DS05 to keep the
original file under the 300-line soft cap. This file covers the
happy-path: reading a well-formed DAT and asserting the parsed
Machine objects carry the expected fields. Security and validation
tests live in sibling files (`test_dat_security.py`,
`test_dat_validation.py`).
"""

import zipfile
from pathlib import Path

import pytest

from mame_curator.parser.dat import parse_dat
from mame_curator.parser.errors import DATError
from mame_curator.parser.models import DriverStatus


def test_parse_dat_returns_dict_keyed_by_short_name(mini_dat: Path) -> None:
    machines = parse_dat(mini_dat)
    assert set(machines.keys()) == {
        "pacman",
        "pacmanf",
        "neogeo",
        "z80",
        "3bagfull",
        "brokensim",
    }


def test_parent_clone_relationship_populated(mini_dat: Path) -> None:
    machines = parse_dat(mini_dat)
    assert machines["pacman"].cloneof is None
    assert machines["pacmanf"].cloneof == "pacman"
    assert machines["pacmanf"].romof == "pacman"


def test_bios_device_mechanical_flags(mini_dat: Path) -> None:
    machines = parse_dat(mini_dat)
    assert machines["neogeo"].is_bios is True
    assert machines["z80"].is_device is True
    assert machines["z80"].runnable is False
    assert machines["3bagfull"].is_mechanical is True


def test_unparseable_year_becomes_none(mini_dat: Path) -> None:
    machines = parse_dat(mini_dat)
    assert machines["brokensim"].year is None
    assert machines["pacman"].year == 1980


def test_manufacturer_split(mini_dat: Path) -> None:
    machines = parse_dat(mini_dat)
    assert machines["pacman"].publisher == "Namco"
    assert machines["pacman"].developer == "Midway"
    assert machines["neogeo"].publisher == "SNK"
    assert machines["neogeo"].developer == "SNK"


def test_driver_status_parsed(mini_dat: Path) -> None:
    machines = parse_dat(mini_dat)
    assert machines["pacman"].driver_status is None  # absent in fixture
    assert machines["pacmanf"].driver_status is DriverStatus.IMPERFECT
    assert machines["brokensim"].driver_status is DriverStatus.PRELIMINARY


def test_roms_attached_to_machine(mini_dat: Path) -> None:
    machines = parse_dat(mini_dat)
    pacman_roms = machines["pacman"].roms
    assert len(pacman_roms) == 1
    assert pacman_roms[0].name == "pacman.6e"
    assert pacman_roms[0].size == 4096
    assert pacman_roms[0].crc == "c1e6ab10"


def test_parse_dat_handles_zip_wrapper(mini_dat: Path, tmp_path: Path) -> None:
    zipped = tmp_path / "wrapped.zip"
    with zipfile.ZipFile(zipped, "w") as zf:
        zf.write(mini_dat, arcname="mini.dat.xml")
    machines = parse_dat(zipped)
    assert "pacman" in machines


def test_zip_with_no_xml_raises(tmp_path: Path) -> None:
    bad = tmp_path / "empty.zip"
    with zipfile.ZipFile(bad, "w") as zf:
        zf.writestr("notxml.txt", "hello")
    with pytest.raises(DATError, match="zero"):
        parse_dat(bad)


def test_zip_with_multiple_xmls_raises(tmp_path: Path, mini_dat: Path) -> None:
    bad = tmp_path / "two.zip"
    with zipfile.ZipFile(bad, "w") as zf:
        zf.write(mini_dat, arcname="a.xml")
        zf.write(mini_dat, arcname="b.xml")
    with pytest.raises(DATError, match="multiple"):
        parse_dat(bad)


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(DATError, match="not exist"):
        parse_dat(tmp_path / "nope.xml")


def test_malformed_xml_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.xml"
    bad.write_text("<datafile><machine name='x'><description>y")
    with pytest.raises(DATError, match="XML parse failed"):
        parse_dat(bad)

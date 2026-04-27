"""Tests for parse_dat."""

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
    with pytest.raises(DATError):
        parse_dat(bad)


def test_duplicate_machine_names_raise(tmp_path: Path) -> None:
    """Two machines with the same name short-circuit with a clear error."""
    dup = tmp_path / "dup.xml"
    dup.write_text(
        "<datafile>"
        '<machine name="x"><description>X1</description></machine>'
        '<machine name="x"><description>X2</description></machine>'
        "</datafile>"
    )
    with pytest.raises(DATError, match="duplicate"):
        parse_dat(dup)


def test_machine_without_name_raises(tmp_path: Path) -> None:
    bad = tmp_path / "noname.xml"
    bad.write_text("<datafile><machine><description>y</description></machine></datafile>")
    with pytest.raises(DATError, match="missing required 'name'"):
        parse_dat(bad)


def test_machine_without_description_raises(tmp_path: Path) -> None:
    bad = tmp_path / "nodesc.xml"
    bad.write_text('<datafile><machine name="x"></machine></datafile>')
    with pytest.raises(DATError, match="missing required <description>"):
        parse_dat(bad)


def test_biosset_parsed_when_present(tmp_path: Path) -> None:
    """`<biosset>` children are surfaced on the Machine record."""
    src = tmp_path / "bs.xml"
    src.write_text(
        "<datafile>"
        '<machine name="ng">'
        "<description>Neo</description>"
        '<biosset name="asia" description="Asia BIOS" default="yes"/>'
        '<biosset name="japan" description="Japan BIOS"/>'
        "</machine>"
        "</datafile>"
    )
    machines = parse_dat(src)
    biossets = machines["ng"].biossets
    assert {b.name for b in biossets} == {"asia", "japan"}
    asia = next(b for b in biossets if b.name == "asia")
    assert asia.description == "Asia BIOS"
    assert asia.default is True


def test_empty_rom_name_raises_DATError(tmp_path: Path) -> None:
    """Per parser/spec.md G1: <rom>/<biosset> with empty name → DATError."""
    bad = tmp_path / "empty-rom-name.xml"
    bad.write_text(
        "<datafile>"
        '<machine name="x"><description>X</description>'
        '<rom name="" size="1024" crc="aaaaaaaa"/>'
        "</machine></datafile>"
    )
    with pytest.raises(DATError, match="rom"):
        parse_dat(bad)


def test_empty_biosset_name_raises_DATError(tmp_path: Path) -> None:
    """Per parser/spec.md G1: <biosset> with empty name → DATError."""
    bad = tmp_path / "empty-bios-name.xml"
    bad.write_text(
        "<datafile>"
        '<machine name="x"><description>X</description>'
        '<biosset name="" description="A"/>'
        "</machine></datafile>"
    )
    with pytest.raises(DATError, match="biosset"):
        parse_dat(bad)


def test_negative_rom_size_raises_DATError(tmp_path: Path) -> None:
    """Per parser/spec.md G6: Rom.size is non-negative; negative → DATError."""
    bad = tmp_path / "neg-size.xml"
    bad.write_text(
        "<datafile>"
        '<machine name="x"><description>X</description>'
        '<rom name="a.bin" size="-5" crc="aaaaaaaa"/>'
        "</machine></datafile>"
    )
    with pytest.raises(DATError, match="rom"):
        parse_dat(bad)


def test_non_integer_rom_size_raises_DATError(tmp_path: Path) -> None:
    """Per parser/spec.md Errors clause: malformed inputs raise ParserError, never bare ValueError.

    A `<rom size>` attribute that isn't parseable as int previously propagated a bare
    ValueError out of _rom_from_element, breaking the typed-exception contract.
    """
    bad = tmp_path / "bad-size.xml"
    bad.write_text(
        "<datafile>"
        '<machine name="x"><description>X</description>'
        '<rom name="a.bin" size="not-a-number" crc="aaaaaaaa"/>'
        "</machine></datafile>"
    )
    with pytest.raises(DATError, match="size"):
        parse_dat(bad)


def test_empty_dat_raises(tmp_path: Path) -> None:
    """A valid-XML DAT with zero <machine> elements is treated as wrong-file-type."""
    empty = tmp_path / "empty.xml"
    empty.write_text("<datafile></datafile>")
    with pytest.raises(DATError, match="no <machine>"):
        parse_dat(empty)


def test_wrong_root_element_raises(tmp_path: Path) -> None:
    """A valid XML file that isn't a DAT (no <machine> children) surfaces clearly."""
    wrong = tmp_path / "wrong.xml"
    wrong.write_text("<not_a_datafile><foo/></not_a_datafile>")
    with pytest.raises(DATError, match="no <machine>"):
        parse_dat(wrong)


def test_unknown_driver_status_becomes_none(tmp_path: Path) -> None:
    """An unrecognized status value logs a warning and parses to None."""
    src = tmp_path / "weird.xml"
    src.write_text(
        "<datafile>"
        '<machine name="z"><description>Z</description>'
        '<driver status="bogus"/>'
        "</machine></datafile>"
    )
    machines = parse_dat(src)
    assert machines["z"].driver_status is None

"""Tests for parse_dat — validation + error-surface (DS05 Cluster C validation seam).

Extracted from `tests/parser/test_dat.py` during DS05. This file
covers the parser's validation gates: structural well-formedness
(duplicate names, missing fields, biosset structure), value-range
checks (year bounds, rom-size non-negative, integer-coercion),
file-typing (empty / wrong-root), driver-status rate-limiting, and
the FP04 parser-hardening sweep (OSError surfacing).
"""

import zipfile
from pathlib import Path

import pytest

from mame_curator.parser.dat import parse_dat
from mame_curator.parser.errors import DATError
from tests.parser.conftest import raise_oserror as _raise_oserror


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


def test_corrupt_zip_raises_DATError_not_BadZipFile(tmp_path: Path) -> None:
    """Per parser/spec.md "Edge cases": a `.zip` that is corrupt or truncated
    must raise `DATError` with the file path — never propagate `zipfile.BadZipFile`.

    The CLI catches `ParserError` (DATError's base) and converts to a
    user-facing stderr message. A bare `BadZipFile` would slip past the
    catch and crash with a Python traceback in the user's terminal —
    a CLI-spec violation (see cli/spec.md "Errors the CLI catches but
    never raises").
    """
    bad = tmp_path / "corrupt.zip"
    bad.write_bytes(b"this is not a zip file, just some bytes")
    with pytest.raises(DATError, match="zip"):
        parse_dat(bad)


def test_zip_slip_traversal_member_raises(tmp_path: Path, mini_dat: Path) -> None:
    """Per parser/spec.md G5: a .zip with a `..`-path member must raise DATError.

    Defense in depth — Python's zipfile.extract sanitizes leading slashes and
    drives, but allows nested `..` components which can escape the tempdir.
    """
    bad = tmp_path / "evil.zip"
    with zipfile.ZipFile(bad, "w") as zf:
        zf.write(mini_dat, arcname="../evil.xml")
    with pytest.raises(DATError, match="escape the extraction"):
        parse_dat(bad)


def test_year_out_of_range_becomes_none(tmp_path: Path) -> None:
    """Per parser/spec.md G2: <year> outside [1970, 2100] → None (not DATError)."""
    src = tmp_path / "year-bounds.xml"
    src.write_text(
        "<datafile>"
        '<machine name="too_early"><description>X</description><year>1</year></machine>'
        '<machine name="too_late"><description>Y</description><year>9999</year></machine>'
        '<machine name="just_right"><description>Z</description><year>1980</year></machine>'
        "</datafile>"
    )
    machines = parse_dat(src)
    assert machines["too_early"].year is None
    assert machines["too_late"].year is None
    assert machines["just_right"].year == 1980


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


def test_unknown_driver_status_warning_logged_once_per_status(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Per parser/spec.md G3: unknown status warnings rate-limit per unique string.

    With a 43k-machine DAT, one unknown status value would otherwise produce
    tens of thousands of identical warnings. The walker maintains a set of
    seen-unknowns and only emits one log line per distinct status string.
    """
    src = tmp_path / "many-bogus.xml"
    src.write_text(
        "<datafile>"
        '<machine name="a"><description>A</description><driver status="protection"/></machine>'
        '<machine name="b"><description>B</description><driver status="protection"/></machine>'
        '<machine name="c"><description>C</description><driver status="protection"/></machine>'
        '<machine name="d"><description>D</description><driver status="palette"/></machine>'
        "</datafile>"
    )
    import logging as _logging

    with caplog.at_level(_logging.WARNING, logger="mame_curator.parser.dat"):
        parse_dat(src)
    protection_warnings = [m for m in caplog.messages if "protection" in m]
    palette_warnings = [m for m in caplog.messages if "palette" in m]
    assert len(protection_warnings) == 1, "duplicate status string must warn at most once"
    assert len(palette_warnings) == 1


# ---- FP04 — parser hardening sweep ----


def test_zip_oserror_raises_DATError(tmp_path: Path) -> None:
    """FP04 A1 — `zipfile.ZipFile()` raising `OSError` (not `BadZipFile`) must
    surface as `DATError`, not propagate raw past the CLI's `ParserError` catch.

    Trigger: a directory at a `.zip`-suffixed path. `zipfile.ZipFile()` on a
    directory raises `IsADirectoryError` on POSIX / `PermissionError` on
    Windows — both `OSError` subclasses.
    """
    bad = tmp_path / "actually_a_dir.zip"
    bad.mkdir()
    with pytest.raises(DATError, match="open DAT zip"):
        parse_dat(bad)


def test_iterparse_oserror_raises_DATError(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """FP04 A3 — OSError from `etree.iterparse` (file disappeared race,
    EIO during read, perms revoked between exists() and read) must surface
    as `DATError`, not propagate raw past the CLI's ParserError catch.
    """
    src = tmp_path / "valid.xml"
    src.write_text("<datafile><machine name='x'><description>X</description></machine></datafile>")
    monkeypatch.setattr("lxml.etree.iterparse", _raise_oserror)
    with pytest.raises(DATError, match="read DAT XML"):
        parse_dat(src)

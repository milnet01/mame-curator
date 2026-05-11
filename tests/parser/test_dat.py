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


def test_xxe_external_entity_is_not_resolved(tmp_path: Path) -> None:
    """FP20-A: parser must not resolve external entities.

    A malicious DAT could declare ``<!ENTITY xxe SYSTEM "file:///etc/passwd">``
    and reference it inside a ``<description>`` to exfiltrate file contents
    via the parsed machine struct. Defaults on lxml.iterparse historically
    resolve internal entities; ``no_network=True`` blocks http(s) but NOT
    the ``file://`` scheme. The fix passes an explicit
    ``XMLParser(resolve_entities=False, ...)`` at every iterparse call site.
    """
    secret = tmp_path / "secret.txt"
    secret.write_text("SECRET_PASSWORD_DO_NOT_LEAK")
    secret_uri = secret.as_uri()  # file:///tmp/.../secret.txt
    xxe = tmp_path / "xxe.xml"
    xxe.write_text(
        f'<?xml version="1.0"?>\n'
        f"<!DOCTYPE datafile [\n"
        f'  <!ENTITY xxe SYSTEM "{secret_uri}">\n'
        f"]>\n"
        f'<datafile><machine name="evil" sourcefile="x.cpp">\n'
        f"  <description>&xxe;</description>\n"
        f"  <year>1984</year>\n"
        f"  <manufacturer>x</manufacturer>\n"
        f'  <driver status="good"/>\n'
        f"</machine></datafile>\n"
    )
    # Either the parser refuses to resolve the entity (preferred —
    # description ends up empty or literally "&xxe;") or it raises a
    # parse error. What it must NOT do is leak SECRET_PASSWORD into
    # the parsed Machine.
    try:
        machines = parse_dat(xxe)
    except DATError:
        return
    assert "evil" in machines
    assert "SECRET_PASSWORD_DO_NOT_LEAK" not in (machines["evil"].description or "")


def test_billion_laughs_internal_entity_does_not_expand(tmp_path: Path) -> None:
    """FP20-A: ``XMLParser(resolve_entities=False, ...)`` blocks the
    classic Billion Laughs DoS where deeply-nested internal entities
    expand to a multi-GB string in memory. Without ``resolve_entities=
    False`` lxml expands ``&lol9;`` even with ``no_network=True``.

    Either the parser refuses with a parse error or the description
    contains the literal "&lol;" reference rather than the expanded
    string. Critically, parse_dat must complete in under a second on
    the test fixture (anything slower implies expansion).
    """
    bomb = tmp_path / "lol.xml"
    entity_decl = "".join(
        [
            '<!ENTITY lol "lol">',
            '<!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">',
            '<!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">',
            '<!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">',
            '<!ENTITY lol5 "&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;">',
        ]
    )
    bomb.write_text(
        f'<?xml version="1.0"?>\n<!DOCTYPE datafile [{entity_decl}]>\n'
        f'<datafile><machine name="lol" sourcefile="x.cpp">'
        f"<description>&lol5;</description><year>1984</year>"
        f'<manufacturer>x</manufacturer><driver status="good"/>'
        f"</machine></datafile>"
    )
    import time

    start = time.perf_counter()
    try:
        machines = parse_dat(bomb)
    except DATError:
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"parse_dat took {elapsed:.2f}s — expansion happened despite raise"
        return
    elapsed = time.perf_counter() - start
    assert elapsed < 1.0, f"parse_dat took {elapsed:.2f}s — entity expansion ran"
    desc = machines["lol"].description or ""
    assert len(desc) < 1000, f"description has {len(desc)} chars — entities were expanded"


def test_zip_member_size_capped(tmp_path: Path) -> None:
    """FP20-A: a zip member declaring a decompressed size above
    ``_MAX_DAT_BYTES`` (256 MiB) must be rejected before extraction —
    otherwise a malicious 100 KB upload could decompress to gigabytes
    on disk. The cap reads ``zf.getinfo(member).file_size`` (the
    pre-decompression metadata) and refuses extraction without ever
    touching ``zf.extract``.
    """
    from mame_curator.parser.dat import _MAX_DAT_BYTES

    bomb = tmp_path / "bomb.zip"
    big_payload = b"<datafile></datafile>" + b"\0" * 1024  # tiny on disk
    with zipfile.ZipFile(bomb, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("dat.xml", big_payload)
        # Patch the central-dir entry's file_size so the metadata-side
        # check trips even though the actual payload is small.
        info = zf.getinfo("dat.xml")
        info.file_size = _MAX_DAT_BYTES + 1
    with pytest.raises(DATError, match=r"size cap|too large|exceeds"):
        parse_dat(bomb)


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


def _raise_oserror(*_args: object, **_kwargs: object) -> object:
    raise OSError("simulated EIO during iterparse")


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

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


# ---- a zipped list is read as a stream (mame-curator-1214) -------------------


def _zip_of(tmp_path: Path, members: dict[str, bytes]) -> Path:
    zipped = tmp_path / "mame.zip"
    with zipfile.ZipFile(zipped, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return zipped


def test_a_zipped_list_is_not_unpacked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The check reads the zip's member as it goes; it writes no copy of it."""

    def _no_extract(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("check_dat_start unpacked the zip")

    monkeypatch.setattr(zipfile.ZipFile, "extract", _no_extract)
    check_dat_start(_zip_of(tmp_path, {"mame.xml": (FIXTURES / "mini.dat.xml").read_bytes()}))


def test_a_zipped_list_whose_data_will_not_unpack_is_refused(tmp_path: Path) -> None:
    """Corrupt compressed data surfaces as DATError, not zlib.error."""
    zipped = _zip_of(tmp_path, {"mame.xml": (FIXTURES / "mini.dat.xml").read_bytes()})
    with zipfile.ZipFile(zipped) as zf:
        info = zf.infolist()[0]
    raw = bytearray(zipped.read_bytes())
    name_len = int.from_bytes(raw[info.header_offset + 26 : info.header_offset + 28], "little")
    extra_len = int.from_bytes(raw[info.header_offset + 28 : info.header_offset + 30], "little")
    data_start = info.header_offset + 30 + name_len + extra_len
    raw[data_start : data_start + 16] = b"\xff" * 16
    zipped.write_bytes(bytes(raw))

    with pytest.raises(DATError, match="corrupt"):
        check_dat_start(zipped)


@pytest.mark.parametrize(
    ("members", "message"),
    [
        ({"a.xml": b"<datafile/>", "b.xml": b"<datafile/>"}, "multiple"),
        ({"readme.txt": b"hi"}, "zero"),
        ({"../escape.xml": b"<datafile/>"}, "escape"),
    ],
)
def test_a_zipped_list_keeps_the_zip_rules(
    tmp_path: Path, members: dict[str, bytes], message: str
) -> None:
    with pytest.raises(DATError, match=message):
        check_dat_start(_zip_of(tmp_path, members))


def test_a_zipped_list_with_an_unsupported_method_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deflate64 or an encrypted member: zipfile refuses to open it."""
    zipped = _zip_of(tmp_path, {"mame.xml": (FIXTURES / "mini.dat.xml").read_bytes()})

    def _refuse(*_args: object, **_kwargs: object) -> object:
        raise NotImplementedError("That compression method is not supported")

    monkeypatch.setattr(zipfile.ZipFile, "open", _refuse)
    monkeypatch.setattr(zipfile.ZipFile, "extract", _refuse)
    with pytest.raises(DATError, match="not supported"):
        check_dat_start(zipped)

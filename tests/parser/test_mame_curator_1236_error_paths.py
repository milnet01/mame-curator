"""mame-curator-1236 — every DAT error names the file the user chose.

CR-01-4: a zipped DAT is unpacked to a temp file, and parse errors named that
temp file, which is gone by the time the user reads the message.
CR-01-8: errors raised while reading one machine carried no path at all,
against parser/spec.md § Errors ("All carry the source path").
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from mame_curator.parser import DATError, check_dat_start, parse_dat

_NO_DESCRIPTION = '<datafile><machine name="x"></machine></datafile>'
_NO_NAME = "<datafile><machine><description>y</description></machine></datafile>"
_BAD_ROM_SIZE = (
    '<datafile><machine name="x"><description>X</description>'
    '<rom name="a" size="big"/></machine></datafile>'
)
_DUPLICATE = (
    "<datafile>"
    '<machine name="x"><description>X1</description></machine>'
    '<machine name="x"><description>X2</description></machine>'
    "</datafile>"
)
_BROKEN_XML = '<datafile><machine name="x"><description>X</description>'

_BAD_DATS = {
    "no-description": _NO_DESCRIPTION,
    "no-name": _NO_NAME,
    "bad-rom-size": _BAD_ROM_SIZE,
    "duplicate": _DUPLICATE,
    "broken-xml": _BROKEN_XML,
}


def _write(tmp_path: Path, body: str, *, zipped: bool) -> Path:
    if not zipped:
        dat = tmp_path / "mame.xml"
        dat.write_text(body)
        return dat
    dat = tmp_path / "mame.zip"
    with zipfile.ZipFile(dat, "w") as zf:
        zf.writestr("mame.xml", body)
    return dat


@pytest.mark.parametrize("zipped", [False, True], ids=["xml", "zip"])
@pytest.mark.parametrize("body", _BAD_DATS.values(), ids=_BAD_DATS.keys())
def test_parse_dat_errors_name_the_users_file(tmp_path: Path, body: str, zipped: bool) -> None:
    dat = _write(tmp_path, body, zipped=zipped)
    with pytest.raises(DATError) as caught:
        parse_dat(dat)
    assert caught.value.path == dat
    assert repr(dat) in str(caught.value)


@pytest.mark.parametrize("zipped", [False, True], ids=["xml", "zip"])
@pytest.mark.parametrize(
    "body", [_NO_DESCRIPTION, _NO_NAME, _BAD_ROM_SIZE], ids=["no-description", "no-name", "rom"]
)
def test_check_dat_start_errors_name_the_users_file(
    tmp_path: Path, body: str, zipped: bool
) -> None:
    dat = _write(tmp_path, body, zipped=zipped)
    with pytest.raises(DATError) as caught:
        check_dat_start(dat)
    assert caught.value.path == dat

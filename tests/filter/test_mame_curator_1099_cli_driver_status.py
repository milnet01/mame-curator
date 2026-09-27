"""mame-curator-1099 — `mame-curator filter` takes driver status from `--listxml`.

A Pleasuredome DAT has no `<driver>`, so before the fix a preliminary game
was never dropped by the CLI filter either.
"""

from __future__ import annotations

import json
from pathlib import Path

from mame_curator.cli import build_parser, run

_DAT = """<?xml version="1.0"?>
<datafile>
    <machine name="okgame">
        <description>OK Game</description>
        <year>1990</year>
        <manufacturer>Acme</manufacturer>
    <rom name="ok.bin" size="1024" crc="44444444" sha1="0000000000000000000000000000000000000004"/>
    </machine>
    <machine name="brokengame">
        <description>Broken Game</description>
        <year>1990</year>
        <manufacturer>Acme</manufacturer>
    <rom name="br.bin" size="1024" crc="55555555" sha1="0000000000000000000000000000000000000005"/>
    </machine>
</datafile>
"""

_LISTXML = """<?xml version="1.0"?>
<mame build="0.287">
  <machine name="okgame"><driver status="good"/></machine>
  <machine name="brokengame"><driver status="preliminary"/></machine>
</mame>
"""


def test_filter_drops_preliminary_known_only_from_listxml(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    dat = tmp_path / "dat.xml"
    dat.write_text(_DAT, encoding="utf-8")
    listxml = tmp_path / "listxml.xml"
    listxml.write_text(_LISTXML, encoding="utf-8")
    report = tmp_path / "report.json"
    args = build_parser().parse_args(
        [
            "filter",
            "--dat",
            str(dat),
            "--listxml",
            str(listxml),
            "--catver",
            str(fixtures_dir / "snapshot_catver.ini"),
            "--languages",
            str(fixtures_dir / "snapshot_languages.ini"),
            "--bestgames",
            str(fixtures_dir / "snapshot_bestgames.ini"),
            "--out",
            str(report),
        ]
    )
    assert run(args) == 0
    payload = json.loads(report.read_text())
    assert "brokengame" not in payload["winners"]
    assert "brokengame" in json.dumps(payload["dropped"])

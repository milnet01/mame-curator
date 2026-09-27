"""mame-curator-1099 — a Pleasuredome-shaped DAT gets driver status from listxml.

The shared fixture DAT carries `<driver>` elements, which real Pleasuredome
DATs never do, so no API test saw every machine arrive with
`driver_status=None`. This one strips them, supplies them via `-listxml`
and checks the three consumers: the stats panel, the PRELIMINARY_DRIVER
drop and the machines themselves.

Pre-fix: `build_world` ignores listxml driver status, so brokensim is not
dropped and the stats panel reports "unknown".
"""

from __future__ import annotations

from pathlib import Path

from mame_curator.api.routes.games import get_stats
from mame_curator.api.state import build_world
from mame_curator.parser import DriverStatus

_LISTXML = """<?xml version="1.0"?>
<mame build="0.287">
  <machine name="pacman"><driver status="good"/></machine>
  <machine name="pacmanf" cloneof="pacman" romof="pacman"><driver status="imperfect"/></machine>
  <machine name="neogeo" isbios="yes"><driver status="good"/></machine>
  <machine name="3bagfull"><driver status="good"/></machine>
  <machine name="brokensim"><driver status="preliminary"/></machine>
</mame>
"""


def _pleasuredome_config(config_file: Path, mini_dat: Path, tmp_path: Path) -> Path:
    dat = tmp_path / "no-driver.dat.xml"
    lines = mini_dat.read_text(encoding="utf-8").splitlines(keepends=True)
    dat.write_text("".join(ln for ln in lines if "<driver" not in ln), encoding="utf-8")
    listxml = tmp_path / "listxml.xml"
    listxml.write_text(_LISTXML, encoding="utf-8")

    text = config_file.read_text(encoding="utf-8")
    out = []
    for ln in text.splitlines(keepends=True):
        if ln.lstrip().startswith("source_dat:"):
            ln = f"  source_dat: {dat}\n"
        elif ln.lstrip().startswith("listxml:"):
            ln = f"  listxml: {listxml}\n"
        out.append(ln)
    config_file.write_text("".join(out), encoding="utf-8")
    return config_file


def test_build_world_joins_driver_status_from_listxml(
    config_file: Path, mini_dat: Path, tmp_path: Path, fake_home: Path
) -> None:
    world = build_world(_pleasuredome_config(config_file, mini_dat, tmp_path))

    assert world.machines["pacman"].driver_status is DriverStatus.GOOD
    assert world.machines["brokensim"].driver_status is DriverStatus.PRELIMINARY
    assert "brokensim" not in world.filter_result.winners, "PRELIMINARY_DRIVER drop fires"
    stats = get_stats(world)
    assert stats.by_driver_status, "expected at least one winner"
    assert "unknown" not in stats.by_driver_status

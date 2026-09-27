"""mame-curator-1099 — driver status comes from `-listxml`, not only the DAT.

Pleasuredome DATs carry no `<driver>` element (verified 2026-09-27 on
"MAME 0.284 ROMs (non-merged).zip": zero occurrences), so every
`Machine.driver_status` was None. Stats showed one "unknown" bar, the
PRELIMINARY_DRIVER drop never fired and the picker's driver tiebreak never
separated anything. MAME's `-listxml` carries `<driver status>` per machine.

Pre-fix: `parse_listxml_driver_status` and `apply_driver_status` do not exist.
"""

from __future__ import annotations

from pathlib import Path

from mame_curator.parser import (
    DriverStatus,
    Machine,
    apply_driver_status,
    parse_listxml_driver_status,
)

_LISTXML = """<?xml version="1.0"?>
<mame build="0.287">
  <machine name="good1"><driver status="good" emulation="good"/></machine>
  <machine name="imp1"><driver status="imperfect" emulation="good"/></machine>
  <machine name="pre1"><driver status="preliminary" emulation="preliminary"/></machine>
  <machine name="odd1"><driver status="someday"/></machine>
  <machine name="nodrv"/>
</mame>
"""


def test_parse_listxml_driver_status(tmp_path: Path) -> None:
    src = tmp_path / "listxml.xml"
    src.write_text(_LISTXML, encoding="utf-8")
    assert parse_listxml_driver_status(src) == {
        "good1": DriverStatus.GOOD,
        "imp1": DriverStatus.IMPERFECT,
        "pre1": DriverStatus.PRELIMINARY,
    }


def test_apply_driver_status_fills_only_missing() -> None:
    machines = {
        "a": Machine(name="a", description="A"),
        "b": Machine(name="b", description="B", driver_status=DriverStatus.IMPERFECT),
        "c": Machine(name="c", description="C"),
    }
    statuses = {"a": DriverStatus.PRELIMINARY, "b": DriverStatus.GOOD}
    out = apply_driver_status(machines, statuses)
    assert out["a"].driver_status is DriverStatus.PRELIMINARY
    assert out["b"].driver_status is DriverStatus.IMPERFECT, "a DAT value wins"
    assert out["c"].driver_status is None, "absent from listxml stays unknown"

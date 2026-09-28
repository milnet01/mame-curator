"""mame-curator-1118 — one `-listxml` pass collects all four facts.

`build_world` used to call four `parse_listxml_*` functions, each a full
iterparse over a ~300 MB file. `parse_listxml` reads it once and returns
cloneof, BIOS chain, CHD set and driver status together. These tests pin
that it returns what the four single-fact functions return. The
`build_world` side is in tests/api/test_mame_curator_1118_listxml_once.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mame_curator.parser import DriverStatus
from mame_curator.parser.listxml import (
    BIOSChainEntry,
    parse_listxml,
    parse_listxml_bios_chain,
    parse_listxml_cloneof,
    parse_listxml_disks,
    parse_listxml_driver_status,
)

_LISTXML = """<?xml version="1.0"?>
<mame build="0.287">
  <machine name="neogeo" isbios="yes">
    <biosset name="euro" description="Europe"/>
    <biosset name="us" description="US"/>
    <driver status="good"/>
  </machine>
  <machine name="mslug" romof="neogeo"><driver status="good"/></machine>
  <machine name="mslugj" cloneof="mslug" romof="mslug"><driver status="imperfect"/></machine>
  <machine name="kinst"><disk name="kinst" sha1="0"/><driver status="good"/></machine>
  <machine name="brokensim"><driver status="preliminary"/></machine>
  <machine name="nodriver"/>
</mame>
"""


@pytest.fixture
def listxml(tmp_path: Path) -> Path:
    path = tmp_path / "listxml.xml"
    path.write_text(_LISTXML, encoding="utf-8")
    return path


def test_parse_listxml_collects_all_four_facts(listxml: Path) -> None:
    facts = parse_listxml(listxml)

    assert facts.cloneof == {"mslugj": "mslug"}
    assert facts.disks == frozenset({"kinst"})
    assert facts.driver_status["brokensim"] is DriverStatus.PRELIMINARY
    assert "nodriver" not in facts.driver_status
    assert facts.bios_chain["neogeo"] == BIOSChainEntry(biossets=("euro", "us"), is_bios=True)
    assert facts.bios_chain["mslug"].romof == "neogeo"
    assert "nodriver" in facts.bios_chain


def test_single_fact_functions_agree_with_parse_listxml(listxml: Path) -> None:
    facts = parse_listxml(listxml)

    assert parse_listxml_cloneof(listxml) == facts.cloneof
    assert parse_listxml_bios_chain(listxml) == facts.bios_chain
    assert frozenset(parse_listxml_disks(listxml)) == facts.disks
    assert parse_listxml_driver_status(listxml) == facts.driver_status

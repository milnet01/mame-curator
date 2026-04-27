"""Stream a MAME non-merged DAT XML into Machine records.

Uses lxml.iterparse so the 48 MB XML never lives in memory in full.
Each <machine> element is processed and then cleared.
"""

from __future__ import annotations

import logging
import tempfile
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

# bandit B410: lxml's iterparse defaults to no_network=True; we never parse XML from
# untrusted network sources, only user-supplied DAT files from trusted ROM aggregators.
# defusedxml.lxml is deprecated upstream, so this is the supported approach.
from lxml import etree  # nosec B410

from mame_curator.parser.errors import DATError
from mame_curator.parser.manufacturer import split_manufacturer
from mame_curator.parser.models import BiosSet, DriverStatus, Machine, Rom

logger = logging.getLogger(__name__)


def parse_dat(path: Path) -> dict[str, Machine]:
    """Parse a MAME non-merged DAT XML into a dict of Machine records.

    Accepts either a `.xml` file or a `.zip` containing a single `.xml`.
    """
    if not path.exists():
        raise DATError("DAT path does not exist", path=path)

    with _resolve_xml(path) as xml_path:
        return _stream_machines(xml_path)


@contextmanager
def _resolve_xml(path: Path) -> Iterator[Path]:
    """Yield a Path to the actual XML, extracting from .zip if needed."""
    if path.suffix.lower() != ".zip":
        yield path
        return
    with zipfile.ZipFile(path) as zf:
        xml_members = [n for n in zf.namelist() if n.lower().endswith(".xml")]
        if len(xml_members) == 0:
            raise DATError("DAT zip contains zero .xml files", path=path)
        if len(xml_members) > 1:
            raise DATError(f"DAT zip contains multiple .xml files: {xml_members}", path=path)
        with tempfile.TemporaryDirectory() as tmp:
            extracted = zf.extract(xml_members[0], path=tmp)
            yield Path(extracted)


def _stream_machines(xml_path: Path) -> dict[str, Machine]:
    machines: dict[str, Machine] = {}
    try:
        for _event, elem in etree.iterparse(str(xml_path), events=("end",), tag="machine"):
            machine = _machine_from_element(elem)
            if machine.name in machines:
                raise DATError(f"duplicate machine name: {machine.name}", path=xml_path)
            machines[machine.name] = machine
            # Canonical lxml fast-iter cleanup: clear() empties the element's children
            # but doesn't detach it from the parent <datafile>, so the spine accumulates
            # empty <machine> siblings throughout the parse — defeating streaming on a
            # 43k-machine DAT. Detaching previous siblings keeps memory bounded to ~1.
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]
    except etree.XMLSyntaxError as exc:
        raise DATError(f"XML parse failed: {exc}", path=xml_path) from exc
    if not machines:
        raise DATError(
            "DAT contained no <machine> elements; check that this file is actually a MAME DAT",
            path=xml_path,
        )
    return machines


def _machine_from_element(elem: Any) -> Machine:
    name = elem.get("name")
    if not name:
        raise DATError("machine element missing required 'name' attribute")
    description_elem = elem.find("description")
    if description_elem is None or not description_elem.text:
        raise DATError(f"machine '{name}' missing required <description>")

    raw_manufacturer = _text(elem, "manufacturer")
    publisher, developer = split_manufacturer(raw_manufacturer)

    return Machine(
        name=name,
        description=description_elem.text,
        year=_year_or_none(_text(elem, "year")),
        manufacturer_raw=raw_manufacturer,
        publisher=publisher,
        developer=developer,
        cloneof=elem.get("cloneof"),
        romof=elem.get("romof"),
        is_bios=elem.get("isbios") == "yes",
        is_device=elem.get("isdevice") == "yes",
        is_mechanical=elem.get("ismechanical") == "yes",
        runnable=elem.get("runnable") != "no",
        roms=tuple(_rom_from_element(r) for r in elem.findall("rom")),
        biossets=tuple(_biosset_from_element(b) for b in elem.findall("biosset")),
        driver_status=_driver_status_from_element(elem.find("driver")),
        sample_of=elem.get("sampleof"),
    )


def _text(elem: Any, child: str) -> str | None:
    found = elem.find(child)
    if found is None or not found.text:
        return None
    return str(found.text)


def _year_or_none(raw: str | None) -> int | None:
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _rom_from_element(elem: Any) -> Rom:
    raw_size = elem.get("size")
    try:
        size = int(raw_size) if raw_size else None
    except ValueError as exc:
        rom_name = elem.get("name", "<unnamed>")
        raise DATError(f"rom '{rom_name}' has non-integer size {raw_size!r}") from exc
    return Rom(
        name=elem.get("name", ""),
        size=size,
        crc=elem.get("crc"),
        sha1=elem.get("sha1"),
    )


def _biosset_from_element(elem: Any) -> BiosSet:
    return BiosSet(
        name=elem.get("name", ""),
        description=elem.get("description"),
        default=elem.get("default") == "yes",
    )


def _driver_status_from_element(elem: Any) -> DriverStatus | None:
    if elem is None:
        return None
    status = elem.get("status")
    if status is None:
        return None
    try:
        return DriverStatus(status)
    except ValueError:
        logger.warning("unknown driver status: %s", status)
        return None

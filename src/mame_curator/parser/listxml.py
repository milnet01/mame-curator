"""CHD detection from MAME's official `-listxml` output.

The Pleasuredome ROM-set DAT does not include <disk> entries; this module
reads the official MAME XML to identify which machines require a CHD.
"""

from __future__ import annotations

from pathlib import Path

# bandit B410: lxml's iterparse defaults to no_network=True; we never parse XML from
# untrusted network sources, only user-supplied listxml files from trusted MAME builds.
from lxml import etree  # nosec B410

from mame_curator.parser.errors import ListxmlError


def parse_listxml_disks(path: Path) -> set[str]:
    """Return the set of machine shortnames that have at least one <disk> child."""
    if not path.exists():
        raise ListxmlError("listxml path does not exist", path=path)

    chd_required: set[str] = set()
    try:
        for _event, elem in etree.iterparse(str(path), events=("end",), tag="machine"):
            if elem.find("disk") is not None:
                name = elem.get("name")
                if name:
                    chd_required.add(name)
            elem.clear()
    except etree.XMLSyntaxError as exc:
        raise ListxmlError(f"XML parse failed: {exc}", path=path) from exc
    return chd_required

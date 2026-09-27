"""CHD detection from MAME's official `-listxml` output.

The Pleasuredome ROM-set DAT does not include <disk> entries; this module
reads the official MAME XML to identify which machines require a CHD.
"""

from __future__ import annotations

from pathlib import Path

# bandit B410: lxml is wired through HARDENED_ITERPARSE_KWARGS (defined in
# dat.py) at every iterparse call site — resolve_entities=False blocks
# Billion Laughs, no_network=True blocks http(s)/ftp DTD fetches,
# huge_tree=False refuses pathologically deep trees, load_dtd=False blocks
# external-DTD fetches. FP25-K(1): the prior comment leaned on "trusted
# source" framing — but Phase 4 exposes the parser through the API where
# the upstream path is network-controlled, so the safety guarantee comes
# from the iterparse kwargs alone, not from the source of the file.
from lxml import etree  # nosec B410
from pydantic import BaseModel, ConfigDict

from mame_curator.parser.dat import HARDENED_ITERPARSE_KWARGS, _driver_status_from_element
from mame_curator.parser.errors import ListxmlError
from mame_curator.parser.models import DriverStatus, Machine


class BIOSChainEntry(BaseModel):
    """One machine's BIOS-chain references from `-listxml`.

    `romof` is the parent ROM-of relation (often equal to `cloneof` but not
    always). `biossets` is the tuple of `<biosset name="...">` children —
    BIOS option names inside this machine's own romset, not other romsets.
    `is_bios` is `<machine isbios="yes">` (mame-curator-1109).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    romof: str | None = None
    biossets: tuple[str, ...] = ()
    is_bios: bool = False


def parse_listxml_disks(path: Path) -> set[str]:
    """Return the set of machine shortnames that have at least one <disk> child."""
    if not path.exists():
        raise ListxmlError("listxml path does not exist", path=path)

    chd_required: set[str] = set()
    try:
        for _event, elem in etree.iterparse(
            str(path),
            events=("end",),
            tag="machine",
            **HARDENED_ITERPARSE_KWARGS,
        ):
            if elem.find("disk") is not None:
                name = elem.get("name")
                if name:
                    chd_required.add(name)
            # See dat.py:_stream_machines — clear() alone leaves empty siblings on the
            # parent's child list; the lxml fast-iter idiom detaches them.
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]
    except etree.XMLSyntaxError as exc:
        raise ListxmlError(f"XML parse failed: {exc}", path=path) from exc
    except OSError as exc:
        # FP04 A4-A6: iterparse opens the file lazily — OSError mid-iteration
        # (file disappeared race, EIO, perms revoked) would otherwise propagate
        # raw past the CLI's ParserError catch. Typed at the parser/CLI seam.
        raise ListxmlError(f"failed to read listxml: {exc}", path=path) from exc
    return chd_required


def parse_listxml_cloneof(path: Path) -> dict[str, str]:
    """Return {clone_short_name: parent_short_name} from MAME `-listxml`.

    Pleasuredome ROM-set DATs strip the `cloneof` attribute, so Phase 2 of the
    filter sources parent/clone relationships from the official MAME XML. Only
    machines with a non-empty `cloneof` attribute are included; parents and
    standalone machines are absent from the returned map.
    """
    if not path.exists():
        raise ListxmlError("listxml path does not exist", path=path)

    cloneof: dict[str, str] = {}
    try:
        for _event, elem in etree.iterparse(
            str(path),
            events=("end",),
            tag="machine",
            **HARDENED_ITERPARSE_KWARGS,
        ):
            name = elem.get("name")
            parent = elem.get("cloneof")
            if name and parent:
                cloneof[name] = parent
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]
    except etree.XMLSyntaxError as exc:
        raise ListxmlError(f"XML parse failed: {exc}", path=path) from exc
    except OSError as exc:
        # FP04 A4-A6: iterparse opens the file lazily — OSError mid-iteration
        # (file disappeared race, EIO, perms revoked) would otherwise propagate
        # raw past the CLI's ParserError catch. Typed at the parser/CLI seam.
        raise ListxmlError(f"failed to read listxml: {exc}", path=path) from exc
    return cloneof


def parse_listxml_driver_status(path: Path) -> dict[str, DriverStatus]:
    """Return {short_name: DriverStatus} from MAME `-listxml` `<driver status>`.

    Pleasuredome ROM-set DATs carry no `<driver>` element (mame-curator-1099).
    Machines with no `<driver>`, or a status outside `DriverStatus`, are absent;
    unknown statuses log once each, as in the DAT parser.
    """
    if not path.exists():
        raise ListxmlError("listxml path does not exist", path=path)

    statuses: dict[str, DriverStatus] = {}
    seen_unknown: set[str] = set()
    try:
        for _event, elem in etree.iterparse(
            str(path),
            events=("end",),
            tag="machine",
            **HARDENED_ITERPARSE_KWARGS,
        ):
            name = elem.get("name")
            status = _driver_status_from_element(elem.find("driver"), seen_unknown)
            if name and status is not None:
                statuses[name] = status
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]
    except etree.XMLSyntaxError as exc:
        raise ListxmlError(f"XML parse failed: {exc}", path=path) from exc
    except OSError as exc:
        raise ListxmlError(f"failed to read listxml: {exc}", path=path) from exc
    return statuses


def apply_driver_status(
    machines: dict[str, Machine], statuses: dict[str, DriverStatus]
) -> dict[str, Machine]:
    """Fill each machine's missing `driver_status` from `statuses`; a DAT value wins."""
    return {
        name: m.model_copy(update={"driver_status": statuses[name]})
        if m.driver_status is None and name in statuses
        else m
        for name, m in machines.items()
    }


def parse_listxml_bios_chain(path: Path) -> dict[str, BIOSChainEntry]:
    """Return `{short_name: BIOSChainEntry}` from MAME `-listxml`.

    Captures both `romof` (parent ROM-of relation) and the set of
    `<biosset name="...">` children. Phase 3's `copy/` module walks
    these to compute the transitive BIOS dependency closure for a
    winner set.
    """
    if not path.exists():
        raise ListxmlError("listxml path does not exist", path=path)

    chain: dict[str, BIOSChainEntry] = {}
    try:
        for _event, elem in etree.iterparse(
            str(path),
            events=("end",),
            tag="machine",
            **HARDENED_ITERPARSE_KWARGS,
        ):
            name = elem.get("name")
            if not name:
                elem.clear()
                while elem.getprevious() is not None:
                    del elem.getparent()[0]
                continue
            romof = elem.get("romof") or None
            biossets = tuple(bs.get("name", "") for bs in elem.findall("biosset") if bs.get("name"))
            # mame-curator-1109: every machine gets an entry, so a name absent
            # from the chain is absent from the listxml.
            chain[name] = BIOSChainEntry(
                romof=romof, biossets=biossets, is_bios=elem.get("isbios") == "yes"
            )
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]
    except etree.XMLSyntaxError as exc:
        raise ListxmlError(f"XML parse failed: {exc}", path=path) from exc
    except OSError as exc:
        # FP04 A4-A6: iterparse opens the file lazily — OSError mid-iteration
        # (file disappeared race, EIO, perms revoked) would otherwise propagate
        # raw past the CLI's ParserError catch. Typed at the parser/CLI seam.
        raise ListxmlError(f"failed to read listxml: {exc}", path=path) from exc
    return chain

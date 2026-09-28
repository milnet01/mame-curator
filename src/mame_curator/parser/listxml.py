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


class ListxmlFacts(BaseModel):
    """Every fact the app takes from `-listxml`, read in one pass (mame-curator-1118).

    `cloneof` maps clone → parent. `bios_chain` has an entry for every named
    machine. `disks` names machines with a `<disk>` child. `driver_status`
    holds each `<driver status>` that is a known `DriverStatus`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    cloneof: dict[str, str]
    bios_chain: dict[str, BIOSChainEntry]
    disks: frozenset[str]
    driver_status: dict[str, DriverStatus]


def parse_listxml(path: Path) -> ListxmlFacts:
    """Stream MAME `-listxml` once and collect all four facts.

    The real file is ~300 MB and one iterparse over it takes 5.5-8.7 s, so a
    caller needing more than one fact calls this rather than several of the
    single-fact wrappers below, each of which is a full pass.
    """
    if not path.exists():
        raise ListxmlError("listxml path does not exist", path=path)

    cloneof: dict[str, str] = {}
    chain: dict[str, BIOSChainEntry] = {}
    disks: set[str] = set()
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
            if name:
                parent = elem.get("cloneof")
                if parent:
                    cloneof[name] = parent
                if elem.find("disk") is not None:
                    disks.add(name)
                status = _driver_status_from_element(elem.find("driver"), seen_unknown)
                if status is not None:
                    statuses[name] = status
                biossets = tuple(
                    bs.get("name", "") for bs in elem.findall("biosset") if bs.get("name")
                )
                # mame-curator-1109: every machine gets an entry, so a name
                # absent from the chain is absent from the listxml.
                chain[name] = BIOSChainEntry(
                    romof=elem.get("romof") or None,
                    biossets=biossets,
                    is_bios=elem.get("isbios") == "yes",
                )
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
    return ListxmlFacts(
        cloneof=cloneof, bios_chain=chain, disks=frozenset(disks), driver_status=statuses
    )


def parse_listxml_disks(path: Path) -> set[str]:
    """Return the set of machine shortnames that have at least one <disk> child."""
    return set(parse_listxml(path).disks)


def parse_listxml_cloneof(path: Path) -> dict[str, str]:
    """Return {clone_short_name: parent_short_name} from MAME `-listxml`.

    Pleasuredome ROM-set DATs strip the `cloneof` attribute, so Phase 2 of the
    filter sources parent/clone relationships from the official MAME XML. Only
    machines with a non-empty `cloneof` attribute are included; parents and
    standalone machines are absent from the returned map.
    """
    return parse_listxml(path).cloneof


def parse_listxml_driver_status(path: Path) -> dict[str, DriverStatus]:
    """Return {short_name: DriverStatus} from MAME `-listxml` `<driver status>`.

    Pleasuredome ROM-set DATs carry no `<driver>` element (mame-curator-1099).
    Machines with no `<driver>`, or a status outside `DriverStatus`, are absent;
    unknown statuses log once each, as in the DAT parser.
    """
    return parse_listxml(path).driver_status


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
    return parse_listxml(path).bios_chain

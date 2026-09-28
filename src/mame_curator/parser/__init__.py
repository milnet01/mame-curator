"""DAT XML and INI reference-file parsers.

Public API surface — see spec.md for the full contract.
"""

from mame_curator.parser.dat import parse_dat
from mame_curator.parser.errors import DATError, INIError, ListxmlError, ParserError
from mame_curator.parser.ini import (
    parse_bestgames,
    parse_catver,
    parse_languages,
    parse_mature,
    parse_series,
)
from mame_curator.parser.listxml import (
    BIOSChainEntry,
    ListxmlFacts,
    apply_driver_status,
    parse_listxml,
    parse_listxml_bios_chain,
    parse_listxml_cloneof,
    parse_listxml_disks,
    parse_listxml_driver_status,
)
from mame_curator.parser.manufacturer import split_manufacturer
from mame_curator.parser.models import BiosSet, DriverStatus, Machine, Rom

__all__ = [
    "BIOSChainEntry",
    "BiosSet",
    "DATError",
    "DriverStatus",
    "INIError",
    "ListxmlError",
    "ListxmlFacts",
    "Machine",
    "ParserError",
    "Rom",
    "apply_driver_status",
    "parse_bestgames",
    "parse_catver",
    "parse_dat",
    "parse_languages",
    "parse_listxml",
    "parse_listxml_bios_chain",
    "parse_listxml_cloneof",
    "parse_listxml_disks",
    "parse_listxml_driver_status",
    "parse_mature",
    "parse_series",
    "split_manufacturer",
]

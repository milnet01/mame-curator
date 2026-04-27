"""Pure heuristics on machine descriptions: region + revision key.

These are best-effort string parsers — MAME descriptions are free-form text.
The recognized patterns are documented in spec.md and pinned by tests.
"""

from __future__ import annotations

import re
from enum import StrEnum

REGION_RE = re.compile(
    r"\(\s*(?P<region>"
    r"World|USA|Europe|Japan|Asia|Brazil|Korea|Spain|Italy|"
    r"Germany|France|UK|Australia|Taiwan|Hong Kong"
    r")\b"
)

_REV_LETTER_RE = re.compile(r"\(\s*rev\s+(?P<letter>[A-Z])\s*\)")
_SET_NUMBER_RE = re.compile(r"\(\s*[Ss]et\s+(?P<n>\d+)\s*\)")
_V_VERSION_RE = re.compile(r"\bv(?P<major>\d+)(?:\.(?P<minor>\d+))?\b")


class Region(StrEnum):
    """Parsed region tag from a machine description."""

    WORLD = "World"
    USA = "USA"
    EUROPE = "Europe"
    JAPAN = "Japan"
    ASIA = "Asia"
    BRAZIL = "Brazil"
    KOREA = "Korea"
    SPAIN = "Spain"
    ITALY = "Italy"
    GERMANY = "Germany"
    FRANCE = "France"
    UK = "UK"
    AUSTRALIA = "Australia"
    TAIWAN = "Taiwan"
    HONG_KONG = "Hong Kong"
    UNKNOWN = "Unknown"


def region_of(description: str) -> Region:
    """Return the first recognized region tag in the description, or UNKNOWN."""
    match = REGION_RE.search(description)
    if match is None:
        return Region.UNKNOWN
    return Region(match.group("region"))


def revision_key_of(description: str) -> tuple[int, ...]:
    """Return a tuple sortable lexicographically; higher = later revision.

    Family ranks: v-version (3) > rev-letter (2) > set-number (1) > unmarked (0).
    """
    if (m := _V_VERSION_RE.search(description)) is not None:
        major = int(m.group("major"))
        minor = int(m.group("minor")) if m.group("minor") is not None else 0
        return (3, major, minor)
    if (m := _REV_LETTER_RE.search(description)) is not None:
        return (2, ord(m.group("letter")))
    if (m := _SET_NUMBER_RE.search(description)) is not None:
        return (1, int(m.group("n")))
    return (0,)

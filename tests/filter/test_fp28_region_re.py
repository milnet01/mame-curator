"""FP28 B2 — `REGION_RE` must not match parenthetical titles starting with a region word.

Current pattern ``r"\\(\\s*(?P<region>World|USA|...)\\b"`` matches any
parenthetical text whose first word is a region token. So a description like
``"(World Heroes 2)"`` (an SNK fighting-game series whose name happens to
begin with "World") falsely matches ``region=World``.

Post-fix tightens to ``r"\\(\\s*(?P<region>World|USA|...)\\s*(?:,|\\)|$)"`` —
the region must be followed by a comma, close-paren, or end-of-string. This
rejects ``(World Heroes 2)`` (the word after "World" is "Heroes", neither ","
nor ")") while preserving ``(World)`` and ``(World, Europe)``.

Pre-fix: the fourth parametrise case fails — returns ``Region.WORLD``.
Post-fix: returns ``Region.UNKNOWN``.

See ``docs/specs/FP28.md`` § B2.
"""

from __future__ import annotations

import pytest

from mame_curator.filter.heuristics import Region, region_of


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        # Happy path — region appears alone in its parenthetical.
        ("World Heroes (Japan)", Region.JAPAN),
        # Negative control — parenthetical doesn't contain a region word.
        # (`region_of` returns `Region.UNKNOWN` when no match.)
        ("World Heroes (set 1)", Region.UNKNOWN),
        # Region with trailing comma — preserved by the tightening.
        ("World Heroes 2 (USA, Europe)", Region.USA),
        # FP28 B2 regression-lock — parenthetical starts with a region word
        # but continues with non-region text.
        ("(World Heroes 2)", Region.UNKNOWN),
    ],
)
def test_region_re_rejects_parenthetical_title_words(description: str, expected: Region) -> None:
    assert region_of(description) is expected

"""mame-curator-1225 CR-01-1 — split_manufacturer runs in linear time.

The old licence regex backtracked quadratically, so a crafted DAT field
could stall parsing. The replacement must split every string exactly as
the old regex did; the old pattern is kept here as the oracle.
"""

from __future__ import annotations

import re
import time

from hypothesis import given, settings
from hypothesis import strategies as st

from mame_curator.parser.manufacturer import split_manufacturer

_OLD_RE = re.compile(r"^\s*(?P<publisher>.+?)\s*\((?P<developer>[^()]+?)\s+license\)\s*$")


def _old_split(raw: str | None) -> tuple[str | None, str | None]:
    if raw is None or not raw.strip():
        return (None, None)
    cleaned = raw.strip()
    match = _OLD_RE.match(cleaned)
    if match is None:
        return (cleaned, cleaned)
    return (match.group("publisher").strip(), match.group("developer").strip())


@settings(max_examples=3000)
@given(st.text(alphabet="ab ()\t\nlicens", max_size=40))
def test_split_matches_the_old_pattern(raw: str) -> None:
    assert split_manufacturer(raw) == _old_split(raw)


@settings(max_examples=500)
@given(st.text(max_size=12), st.text(alphabet="ab ", max_size=12))
def test_split_matches_the_old_pattern_on_licence_shapes(pub: str, dev: str) -> None:
    raw = f"{pub} ({dev} license)"
    assert split_manufacturer(raw) == _old_split(raw)


def test_a_crafted_field_splits_in_linear_time() -> None:
    """A long run of spaces after "(": the old pattern took 3 s at 20,000
    (measured 2026-11-11), so 40,000 takes over 10 s."""
    raw = "a (" + " " * 40_000 + "b"
    start = time.perf_counter()
    split_manufacturer(raw)
    assert time.perf_counter() - start < 1.0

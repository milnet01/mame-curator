"""Tests for ``escape_libretro``.

Per ``docs/specs/P05.md`` § Public API. The libretro-thumbnails MAME repo
escapes 10 filename-illegal characters (``& * / : \\ < > ? | "``) to ``_``.
Apostrophes, spaces, parens, hyphens, periods, and unicode pass through.
"""

from __future__ import annotations

import pytest


def test_escape_libretro_qbert_canonical() -> None:
    """The canonical roadmap example: ``Q*bert's Qubes`` → ``Q_bert's Qubes``."""
    from mame_curator.media import escape_libretro

    assert escape_libretro("Q*bert's Qubes") == "Q_bert's Qubes"


@pytest.mark.parametrize(
    ("raw", "escaped"),
    [
        ("ampersand & co", "ampersand _ co"),
        ("star*name", "star_name"),
        ("Tron / Discs of Tron", "Tron _ Discs of Tron"),
        ("Robotron: 2084", "Robotron_ 2084"),
        ("dos\\path", "dos_path"),
        ("less<than", "less_than"),
        ("greater>than", "greater_than"),
        ("question?mark", "question_mark"),
        ("Foo | Bar", "Foo _ Bar"),
        ('quote"here', "quote_here"),
    ],
)
def test_escape_libretro_special_chars(raw: str, escaped: str) -> None:
    """Each of the 10 special chars maps to ``_`` in isolation."""
    from mame_curator.media import escape_libretro

    assert escape_libretro(raw) == escaped


@pytest.mark.parametrize(
    "preserved",
    [
        "Pac-Man",
        "Donkey Kong (US)",
        "Street Fighter II: The World Warrior",  # only the colon is escaped
        "Q*bert's Qubes",  # apostrophe preserved
        "100% [hack]",
        "Über Game",
        "Foo.bar",
        "X+Y",
        "(set 1)",
    ],
)
def test_escape_libretro_preserves_non_special(preserved: str) -> None:
    """Apostrophes, spaces, parens, hyphens, periods, brackets, plus, unicode pass through."""
    from mame_curator.media import escape_libretro

    out = escape_libretro(preserved)
    # Every non-special char in the input must appear in the output unchanged.
    for ch in preserved:
        if ch not in '&*/:\\<>?|"':
            assert ch in out, f"non-special char {ch!r} should be preserved"


def test_escape_libretro_idempotent() -> None:
    """Applying the escape twice is the same as applying once (``_`` is not in the special set)."""
    from mame_curator.media import escape_libretro

    raw = "a*b/c?d"
    once = escape_libretro(raw)
    twice = escape_libretro(once)
    assert once == twice == "a_b_c_d"


def test_escape_libretro_empty_string() -> None:
    """Empty input returns empty output (no crash)."""
    from mame_curator.media import escape_libretro

    assert escape_libretro("") == ""


def test_escape_libretro_all_special_at_once() -> None:
    """All 10 special chars in one string → all 10 underscores."""
    from mame_curator.media import escape_libretro

    raw = '&*/:\\<>?|"'
    assert escape_libretro(raw) == "_" * 10

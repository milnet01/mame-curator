"""Tests for split_manufacturer."""

import pytest

from mame_curator.parser.manufacturer import split_manufacturer


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, (None, None)),
        ("", (None, None)),
        ("   ", (None, None)),
        ("Capcom", ("Capcom", "Capcom")),
        ("Capcom (Sega license)", ("Capcom", "Sega")),
        ("Konami (Sun Electronics license)", ("Konami", "Sun Electronics")),
        ("Bally / Midway", ("Bally / Midway", "Bally / Midway")),
        ("Atari (no license info)", ("Atari (no license info)", "Atari (no license info)")),
    ],
)
def test_split_manufacturer(raw: str | None, expected: tuple[str | None, str | None]) -> None:
    assert split_manufacturer(raw) == expected

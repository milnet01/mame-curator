"""Tests for INI parsers."""

from pathlib import Path

import pytest

from mame_curator.parser.errors import INIError
from mame_curator.parser.ini import (
    parse_bestgames,
    parse_catver,
    parse_languages,
    parse_mature,
    parse_series,
)


def test_parse_catver(catver_ini: Path) -> None:
    cats = parse_catver(catver_ini)
    assert cats["pacman"] == "Maze / Collect"
    assert cats["3bagfull"] == "Casino / Slot Machine"
    assert "neogeo" in cats


def test_parse_catver_skips_comments_and_section_headers(catver_ini: Path) -> None:
    cats = parse_catver(catver_ini)
    # neither the leading comment nor [Category] should appear as a key
    assert ";" not in "".join(cats.keys())
    assert "[Category]" not in cats


def test_parse_languages_multivalue(languages_ini: Path) -> None:
    langs = parse_languages(languages_ini)
    assert langs["pacman"] == ["English"]
    assert langs["mahjongx"] == ["Japanese", "English"]


def test_parse_languages_includes_machines_not_in_dat(languages_ini: Path) -> None:
    langs = parse_languages(languages_ini)
    # mahjongx isn't in our DAT fixture; that's fine — INI is independent
    assert "mahjongx" in langs


def test_parse_bestgames_tier_per_machine(bestgames_ini: Path) -> None:
    tiers = parse_bestgames(bestgames_ini)
    assert tiers["pacman"] == "Best"
    assert tiers["neogeo"] == "Great"
    assert tiers["3bagfull"] == "Good"
    assert tiers["brokensim"] == "Average"


def test_parse_mature_returns_set(mature_ini: Path) -> None:
    mature = parse_mature(mature_ini)
    assert mature == {"brokensim"}


def test_parse_series(series_ini: Path) -> None:
    series = parse_series(series_ini)
    assert series["pacman"] == "Pac-Man"
    assert series["pacmanf"] == "Pac-Man"
    assert series["neogeo"] == "Neo-Geo"


def test_parse_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(INIError, match="not exist"):
        parse_catver(tmp_path / "nope.ini")


def test_parse_handles_blank_lines(tmp_path: Path) -> None:
    f = tmp_path / "blank.ini"
    f.write_text("[Cat]\n\n\npacman=Maze\n\n")
    assert parse_catver(f) == {"pacman": "Maze"}


def test_parse_skips_lines_with_no_separator(tmp_path: Path) -> None:
    """Lines with no `=` and lines with no key are skipped silently."""
    f = tmp_path / "junk.ini"
    f.write_text("[Cat]\nbroken-line-no-equals\n=value-with-empty-key\npacman=Maze\n")
    assert parse_catver(f) == {"pacman": "Maze"}


def test_parse_skips_hash_comments(tmp_path: Path) -> None:
    """`#` comments are skipped along with `;` ones."""
    f = tmp_path / "hash.ini"
    f.write_text("# top comment\n[Cat]\n# inside comment\npacman=Maze\n")
    assert parse_catver(f) == {"pacman": "Maze"}

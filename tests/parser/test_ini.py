"""Tests for INI parsers."""

import logging
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


def test_parse_series_excludes_progettosnaps_metadata_sections(tmp_path: Path) -> None:
    """progettoSnaps series.ini ships [FOLDER_SETTINGS] and [ROOT_FOLDER] metadata.

    Per parser/spec.md parse_series: "Each section header is the series name; the keys
    are member shortnames" — implicitly excluding configuration metadata. Without this
    guard, every metadata-key-value pair becomes a fake series.
    """
    f = tmp_path / "series.ini"
    f.write_text(
        "[FOLDER_SETTINGS]\nRootFolderIcon=foo\nSubFolderIcon=bar\n\n"
        "[ROOT_FOLDER]\n\n"
        "[Pac-Man]\npacman=\npacmanf=\n"
    )
    result = parse_series(f)
    assert result == {"pacman": "Pac-Man", "pacmanf": "Pac-Man"}
    assert "RootFolderIcon" not in result
    assert "SubFolderIcon" not in result


def test_parse_catver_excludes_progettosnaps_metadata_sections(tmp_path: Path) -> None:
    """catver.ini sometimes ships the same metadata sections — must not pollute categories."""
    f = tmp_path / "catver.ini"
    f.write_text("[FOLDER_SETTINGS]\nRootFolderIcon=foo\n\n[Category]\npacman=Maze / Collect\n")
    result = parse_catver(f)
    assert result == {"pacman": "Maze / Collect"}
    assert "RootFolderIcon" not in result


def test_duplicate_ini_key_emits_warning(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Duplicate INI shortname → last write wins; warn via logger.warning (parser/spec.md).

    The implementation previously silently overwrote without warning, breaking the
    spec's documented contract.
    """
    f = tmp_path / "dup.ini"
    f.write_text("[Cat]\npacman=Maze\npacman=Shooter\n")
    with caplog.at_level(logging.WARNING, logger="mame_curator.parser.ini"):
        result = parse_catver(f)
    assert result == {"pacman": "Shooter"}, "last write must win per spec"
    assert any("pacman" in m for m in caplog.messages), "duplicate key must emit a warning"


def test_parse_skips_hash_comments(tmp_path: Path) -> None:
    """`#` comments are skipped along with `;` ones."""
    f = tmp_path / "hash.ini"
    f.write_text("# top comment\n[Cat]\n# inside comment\npacman=Maze\n")
    assert parse_catver(f) == {"pacman": "Maze"}

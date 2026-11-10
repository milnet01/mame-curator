"""Tests for INI parsers."""

import logging
from collections.abc import Callable
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
    """A game listed under two language sections gets both, in file order.

    The real languages.ini lists bare short names under one [Language] section
    each (mame-curator-1220); a key=value reader found no entries in it.
    """
    langs = parse_languages(languages_ini)
    assert langs == {
        "pacman": ["English"],
        "brokensim": ["Japanese"],
        "mahjongx": ["English", "Japanese"],
    }


def test_parse_languages_includes_machines_not_in_dat(languages_ini: Path) -> None:
    langs = parse_languages(languages_ini)
    # mahjongx isn't in our DAT fixture; that's fine — INI is independent
    assert "mahjongx" in langs


def test_parse_bestgames_tier_per_machine(bestgames_ini: Path) -> None:
    """Each short name maps to the rating band whose section lists it."""
    tiers = parse_bestgames(bestgames_ini)
    assert tiers == {
        "pacman": "90 to 100 (Best Games)",
        "neogeo": "80 to 90 (Very Good)",
        "3bagfull": "70 to 80 (Good)",
        "brokensim": "40 to 50 (Decent)",
    }


def test_parse_mature_returns_set(mature_ini: Path) -> None:
    """The real mature.ini lists names directly under [ROOT_FOLDER]."""
    mature = parse_mature(mature_ini)
    assert mature == {"brokensim"}


def test_parse_mature_reads_named_sections_too(tmp_path: Path) -> None:
    """A name under any non-settings section is mature; settings lines never are."""
    f = tmp_path / "mature.ini"
    f.write_bytes(b"[FOLDER_SETTINGS]\r\nRootFolderIcon mame\r\n[Mature]\r\nbrokensim\r\n")
    assert parse_mature(f) == {"brokensim"}


def test_parse_series(series_ini: Path) -> None:
    series = parse_series(series_ini)
    assert series == {"pacman": "Pac-Man", "pacmanf": "Pac-Man", "neogeo": "Neo-Geo"}


@pytest.mark.parametrize("name", ["languages.ini", "bestgames.ini", "mature.ini", "series.ini"])
def test_sectioned_fixtures_copy_the_real_format(name: str) -> None:
    """The fixtures must stay CRLF with the real header, or the tests above stop
    exercising what progettoSnaps ships (.gitattributes keeps their bytes)."""
    raw = (Path(__file__).parent / "fixtures" / name).read_bytes()
    assert raw.startswith(b"[FOLDER_SETTINGS]\r\n")
    assert b"\r\n[ROOT_FOLDER]\r\n" in raw
    assert b"\n;;" in raw
    assert b"=" not in raw


@pytest.mark.parametrize("parser", [parse_bestgames, parse_series])
def test_name_in_two_sections_warns_and_last_wins(
    parser: Callable[[Path], dict[str, str]], tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A game in two bands or two series is a conflict: warn, keep the last."""
    f = tmp_path / "dup.ini"
    f.write_bytes(b"[ROOT_FOLDER]\r\n\r\n[A]\r\npacman\r\n\r\n[B]\r\npacman\r\n")
    with caplog.at_level(logging.WARNING, logger="mame_curator.parser.ini"):
        result = parser(f)
    assert result == {"pacman": "B"}
    assert any("pacman" in m for m in caplog.messages)


def test_languages_name_in_two_sections_does_not_warn(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Two languages for one game is normal data, not a conflict."""
    f = tmp_path / "languages.ini"
    f.write_bytes(b"[English]\r\npacman\r\n[Japanese]\r\npacman\r\n")
    with caplog.at_level(logging.WARNING, logger="mame_curator.parser.ini"):
        assert parse_languages(f) == {"pacman": ["English", "Japanese"]}
    assert caplog.messages == []


def test_same_section_listing_a_name_twice_does_not_warn(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Only a name in two DIFFERENT sections is a conflict worth a warning."""
    f = tmp_path / "series.ini"
    f.write_bytes(b"[Pac-Man]\r\npacman\r\npacman\r\n")
    with caplog.at_level(logging.WARNING, logger="mame_curator.parser.ini"):
        assert parse_series(f) == {"pacman": "Pac-Man"}
    assert caplog.messages == []


@pytest.mark.parametrize("parser", [parse_languages, parse_bestgames, parse_mature, parse_series])
def test_names_before_any_section_header_are_skipped(
    parser: Callable[[Path], object], tmp_path: Path
) -> None:
    """parser/spec.md: lines before the first header belong to no section."""
    f = tmp_path / "stray.ini"
    f.write_bytes(b"stray\r\n[ROOT_FOLDER]\r\n[X]\r\npacman\r\n")
    result = parser(f)
    assert "stray" not in result  # type: ignore[operator]  # dict or set; both support `in`
    assert "pacman" in result  # type: ignore[operator]  # same


@pytest.mark.parametrize("parser", [parse_languages, parse_bestgames, parse_mature, parse_series])
@pytest.mark.parametrize("shape", ["missing", "a folder"])
def test_sectioned_parsers_raise_inierror_on_unreadable_input(
    parser: Callable[[Path], object], shape: str, tmp_path: Path
) -> None:
    bad = tmp_path / "bad.ini"
    if shape == "a folder":
        bad.mkdir()
    with pytest.raises(INIError):
        parser(bad)


def test_sectioned_parser_falls_back_to_latin1(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Same encoding policy as catver (parser/spec.md G4)."""
    f = tmp_path / "languages.ini"
    f.write_bytes(b"[Fran\xe7ais]\r\npacman\r\n")
    with caplog.at_level(logging.WARNING, logger="mame_curator.parser.ini"):
        assert parse_languages(f) == {"pacman": ["Français"]}
    assert any("latin-1" in m for m in caplog.messages)


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
        "[FOLDER_SETTINGS]\nRootFolderIcon mame\nSubFolderIcon folder\n\n"
        "[ROOT_FOLDER]\n\n"
        "[Pac-Man]\npacman\npacmanf\n"
    )
    result = parse_series(f)
    assert result == {"pacman": "Pac-Man", "pacmanf": "Pac-Man"}
    assert "RootFolderIcon" not in result
    assert "SubFolderIcon" not in result


def test_parse_languages_excludes_progettosnaps_metadata_sections(tmp_path: Path) -> None:
    """Per parser/spec.md G7: _META_SECTIONS filter applies to all five INI parsers."""
    f = tmp_path / "languages.ini"
    f.write_text("[FOLDER_SETTINGS]\nRootFolderIcon mame\n\n[ROOT_FOLDER]\n\n[English]\npacman\n")
    result = parse_languages(f)
    assert result == {"pacman": ["English"]}
    assert "RootFolderIcon mame" not in result


def test_parse_bestgames_excludes_progettosnaps_metadata_sections(tmp_path: Path) -> None:
    """Per parser/spec.md G7: _META_SECTIONS filter applies to all five INI parsers."""
    f = tmp_path / "bestgames.ini"
    f.write_text("[FOLDER_SETTINGS]\nRootFolderIcon mame\n\n[ROOT_FOLDER]\n\n[Best]\npacman\n")
    result = parse_bestgames(f)
    assert result == {"pacman": "Best"}
    assert "RootFolderIcon mame" not in result


def test_parse_catver_excludes_progettosnaps_metadata_sections(tmp_path: Path) -> None:
    """catver.ini sometimes ships the same metadata sections — must not pollute categories."""
    f = tmp_path / "catver.ini"
    f.write_text("[FOLDER_SETTINGS]\nRootFolderIcon=foo\n\n[Category]\npacman=Maze / Collect\n")
    result = parse_catver(f)
    assert result == {"pacman": "Maze / Collect"}
    assert "RootFolderIcon" not in result


def test_parse_catver_ignores_veradded_section(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Real catver.ini carries a [VerAdded] section keyed by the same shortnames.

    Its values are MAME versions, not categories; reading it overwrote every
    category with a version string (mame-curator-1098).
    """
    f = tmp_path / "catver.ini"
    f.write_text("[Category]\npacman=Maze / Collect\n\n[VerAdded]\npacman=0.36b1\n")
    with caplog.at_level(logging.WARNING, logger="mame_curator.parser.ini"):
        result = parse_catver(f)
    assert result == {"pacman": "Maze / Collect"}
    assert "duplicate" not in caplog.text


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


def test_invalid_utf8_falls_back_to_latin1_with_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Per parser/spec.md G4: bad UTF-8 bytes warn and fall back to latin-1.

    Never silent U+FFFD substitution; never strict-fail on real-world files.
    """
    f = tmp_path / "latin1.ini"
    # 0xE9 is é in latin-1 but invalid as a UTF-8 lead byte standalone.
    f.write_bytes(b"[Cat]\npacman=Maze caf\xe9\n")
    with caplog.at_level(logging.WARNING, logger="mame_curator.parser.ini"):
        result = parse_catver(f)
    assert result == {"pacman": "Maze café"}, "latin-1 fallback must decode é correctly"
    assert any("UTF-8" in m and "latin-1" in m for m in caplog.messages)


def test_parse_skips_hash_comments(tmp_path: Path) -> None:
    """`#` comments are skipped along with `;` ones."""
    f = tmp_path / "hash.ini"
    f.write_text("# top comment\n[Cat]\n# inside comment\npacman=Maze\n")
    assert parse_catver(f) == {"pacman": "Maze"}


def test_section_header_with_inline_comment_filters_meta_correctly(tmp_path: Path) -> None:
    """Per parser/spec.md "INI section header tolerance":
    `[Section] ; trailing comment` must be parsed as `Section`, including for
    META filtering. Previously `line.endswith(']')` was required, so
    `[FOLDER_SETTINGS] ; tool config` fell through and its keys leaked into
    the categories output.
    """
    f = tmp_path / "inline.ini"
    f.write_text(
        "[FOLDER_SETTINGS] ; progettoSnaps tool config\n"
        "RootFolderIcon=foo\n"
        "[Category]\n"
        "pacman=Maze / Collect\n"
    )
    result = parse_catver(f)
    assert result == {"pacman": "Maze / Collect"}
    assert "RootFolderIcon" not in result, "META filter must work even with inline comment"


def test_bestgames_section_header_with_inline_comment_classifies_correctly(
    tmp_path: Path,
) -> None:
    """Bestgames is the case where inline comments on section headers actually
    matter for correctness — the section name *is* the value (the tier).
    """
    f = tmp_path / "best.ini"
    f.write_text("[Best] ; the cream of the crop\npacman\n[Great]# also strong\nneogeo\n")
    result = parse_bestgames(f)
    assert result == {"pacman": "Best", "neogeo": "Great"}

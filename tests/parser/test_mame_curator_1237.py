"""mame-curator-1237 — INI preamble, language duplicates, listxml emptiness and version.

CR-01-7: catver.ini `name=value` lines before any `[Section]` were kept,
against parser/spec.md § Edge cases.
CR-01-16: a name listed twice under one language got that language twice.
CR-01-3: a listxml with no machines read as empty facts, so every clone
became its own group without a word.
CR-01-2: ADR-0003 has the MAME build in the listxml header logged; nothing
read it.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from mame_curator.parser import ListxmlError
from mame_curator.parser.ini import parse_catver, parse_languages
from mame_curator.parser.listxml import parse_listxml


def test_catver_skips_lines_before_any_section(tmp_path: Path) -> None:
    ini = tmp_path / "catver.ini"
    ini.write_text("stray=Not A Category\n[Category]\npacman=Maze / Collect\n")
    assert parse_catver(ini) == {"pacman": "Maze / Collect"}


def test_languages_lists_a_language_once_per_name(tmp_path: Path) -> None:
    ini = tmp_path / "languages.ini"
    ini.write_text("[English]\npacman\npacman\n[Japanese]\npacman\n")
    assert parse_languages(ini) == {"pacman": ["English", "Japanese"]}


def test_listxml_with_no_machines_is_refused(tmp_path: Path) -> None:
    xml = tmp_path / "listxml.xml"
    xml.write_text('<mame build="0.262 (mame0262)"></mame>')
    with pytest.raises(ListxmlError, match="no <machine> elements"):
        parse_listxml(xml)


def test_listxml_build_is_read_and_logged(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    xml = tmp_path / "listxml.xml"
    xml.write_text('<mame build="0.262 (mame0262)"><machine name="pacman"/></mame>')
    with caplog.at_level(logging.INFO, logger="mame_curator.parser.listxml"):
        facts = parse_listxml(xml)
    assert facts.build == "0.262 (mame0262)"
    assert "0.262 (mame0262)" in caplog.text


def test_listxml_without_a_build_reads_as_none(tmp_path: Path) -> None:
    xml = tmp_path / "listxml.xml"
    xml.write_text('<mame><machine name="pacman"/></mame>')
    assert parse_listxml(xml).build is None

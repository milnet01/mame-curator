"""mame-curator-1149: old `overrides.yaml` entries keyed by a clone keep working."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from mame_curator.cli import build_parser, run
from mame_curator.filter import Overrides, migrate_clone_keys

# puckg is a clone in the -listxml that this DAT does not hold.
CLONEOF = {"puckf": "puck", "puckj": "puck", "puckg": "puck", "rock2": "rock"}
KNOWN = {"puck", "puckf", "puckj", "rock", "rock2", "solo"}


def _migrate(entries: dict[str, str]) -> dict[str, str]:
    return migrate_clone_keys(
        Overrides.model_validate({"entries": entries}), CLONEOF, KNOWN
    ).entries


def test_clone_key_moves_to_its_parent() -> None:
    assert _migrate({"puckf": "puckj"}) == {"puck": "puckj"}


def test_clone_key_choosing_itself_moves_too() -> None:
    assert _migrate({"puckf": "puckf"}) == {"puck": "puckf"}


def test_entry_keyed_by_the_shown_game_is_the_newer_choice() -> None:
    """`puck: puckf` showed puckf, so the user's `puckf: puckj` came after it."""
    assert _migrate({"puck": "puckf", "puckf": "puckj"}) == {"puck": "puckj"}


def test_parent_entry_wins_over_a_clone_key_for_a_game_no_longer_shown() -> None:
    """`puck: puckj` shows puckj, so `puckf: puck` was saved before it."""
    assert _migrate({"puck": "puckj", "puckf": "puck"}) == {"puck": "puckj"}


def test_unusable_parent_entry_gives_way_to_the_clone_key() -> None:
    assert _migrate({"puck": "gone", "puckf": "puckj"}) == {"puck": "puckj"}


def test_several_clone_keys_with_no_parent_entry_keep_one_and_log_the_rest(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger="mame_curator.filter.overrides"):
        assert _migrate({"puckj": "puck", "puckf": "puckj"}) == {"puck": "puckj"}
    assert "puckj: puck" in caplog.text


@pytest.mark.parametrize(
    "entries",
    [
        {"ghost": "puck"},  # the key is no machine we know of
        {"puckf": "rock"},  # the target is in another family
        {"puckf": "gone"},  # the target is no machine we know of
        {"puckf": "puckg"},  # the target has left the DAT
        {"puck": "puckf", "rock": "rock2"},  # already the right form
    ],
)
def test_entries_it_cannot_place_stay_exactly_as_they_are(entries: dict[str, str]) -> None:
    assert _migrate(entries) == entries


def test_without_clone_data_nothing_moves_or_is_lost() -> None:
    entries = {"puckf": "puckj"}
    assert (
        migrate_clone_keys(Overrides.model_validate({"entries": entries}), {}, KNOWN).entries
        == entries
    )


def test_the_filter_command_applies_an_old_clone_key(fixtures_dir: Path, tmp_path: Path) -> None:
    """`filter --overrides` reads a saved file too (versioning-overrides item 3)."""
    rom = '<rom name="a" size="1" crc="00000001"/><driver status="good"/>'
    (tmp_path / "dat.xml").write_text(
        f"""<datafile>
        <machine name="puck"><description>Puck</description><year>1980</year>{rom}</machine>
        <machine name="puckf" cloneof="puck"><description>F</description>{rom}</machine>
        </datafile>"""
    )
    (tmp_path / "listxml.xml").write_text(
        """<mame>
        <machine name="puck"><driver status="good"/></machine>
        <machine name="puckf" cloneof="puck"><driver status="good"/></machine>
        </mame>"""
    )
    (tmp_path / "overrides.yaml").write_text("overrides:\n  puckf: puckf\n")
    report = tmp_path / "report.json"
    args = build_parser().parse_args(
        [
            "filter",
            "--dat",
            str(tmp_path / "dat.xml"),
            "--listxml",
            str(tmp_path / "listxml.xml"),
            "--catver",
            str(fixtures_dir / "snapshot_catver.ini"),
            "--languages",
            str(fixtures_dir / "snapshot_languages.ini"),
            "--bestgames",
            str(fixtures_dir / "snapshot_bestgames.ini"),
            "--overrides",
            str(tmp_path / "overrides.yaml"),
            "--out",
            str(report),
        ]
    )
    assert run(args) == 0
    assert json.loads(report.read_text())["winners"] == ["puckf"]

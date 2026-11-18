"""mame-curator-1236 — the filter/ YAML loaders agree with each other and with the writer.

CR-01-10: `sessions: null` reads as no sessions, but `overrides: null` and
`state: null` were refused.
CR-01-12: the app can write a state.yaml its own loader refused as too big.
RR-01-8: the size message named "1 MiB" by hand beside the constant.
RR-01-11: an empty session key was refused by an early loader check whose
error carried no path; the model validator already refuses it, with one.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mame_curator.api.persist import write_yaml_atomic
from mame_curator.filter import _io
from mame_curator.filter.errors import SessionsError
from mame_curator.filter.overrides import Overrides, load_overrides
from mame_curator.filter.review_state import (
    ReviewState,
    ReviewStateValue,
    load_review_state,
)
from mame_curator.filter.sessions import load_sessions


def test_null_overrides_section_reads_as_no_overrides(tmp_path: Path) -> None:
    path = tmp_path / "overrides.yaml"
    path.write_text("overrides:\n", encoding="utf-8")
    assert load_overrides(path) == Overrides()


def test_null_state_section_reads_as_no_state(tmp_path: Path) -> None:
    path = tmp_path / "state.yaml"
    path.write_text("state:\n", encoding="utf-8")
    assert load_review_state(path) == ReviewState()


def test_a_state_file_the_app_writes_for_every_game_loads(tmp_path: Path) -> None:
    """100k games, each with a 16-character name, the longest state value."""
    entries = {f"g{i:015d}": ReviewStateValue.NEEDS_DECISION for i in range(100_000)}
    path = tmp_path / "state.yaml"
    write_yaml_atomic(path, {"state": entries})
    assert len(load_review_state(path).entries) == len(entries)


def test_size_message_states_the_cap_from_the_constant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_io, "_MAX_YAML_BYTES", 2 * 1024 * 1024)
    path = tmp_path / "big.yaml"
    path.write_bytes(b"0" * (2 * 1024 * 1024 + 1))
    with pytest.raises(ValueError, match=r"exceeds the 2 MiB cap"):
        _io.read_capped_text(path, exc_cls=ValueError)


def test_empty_session_key_error_names_the_file(tmp_path: Path) -> None:
    path = tmp_path / "sessions.yaml"
    path.write_text("sessions:\n  '':\n    include_genres: ['Fighter*']\n", encoding="utf-8")
    with pytest.raises(SessionsError, match=r"sessions\.yaml"):
        load_sessions(path)

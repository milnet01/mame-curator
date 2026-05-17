"""Tests for the ReviewState schema and loader (P14)."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from mame_curator.filter.errors import ReviewStateError
from mame_curator.filter.review_state import (
    ReviewState,
    ReviewStateValue,
    load_review_state,
)


def test_round_trips_via_yaml(tmp_path: Path) -> None:
    f = tmp_path / "state.yaml"
    f.write_text("state:\n  sf2: reviewed\n  pacman: skipped\n  galaga: needs-decision\n")
    s = load_review_state(f)
    assert s.entries == {
        "sf2": ReviewStateValue.REVIEWED,
        "pacman": ReviewStateValue.SKIPPED,
        "galaga": ReviewStateValue.NEEDS_DECISION,
    }


def test_missing_file_returns_empty_state(tmp_path: Path) -> None:
    s = load_review_state(tmp_path / "nope.yaml")
    assert s.entries == {}


def test_malformed_yaml_raises_review_state_error(tmp_path: Path) -> None:
    """Top-level is a list — not a mapping. Must raise typed error."""
    f = tmp_path / "list.yaml"
    f.write_text("- entry1\n- entry2\n")
    with pytest.raises(ReviewStateError, match="not a YAML mapping"):
        load_review_state(f)


def test_pending_value_rejected(tmp_path: Path) -> None:
    """INV-1 — ``pending`` is sparse-store implicit; schema disallows it."""
    f = tmp_path / "pending.yaml"
    f.write_text("state:\n  sf2: pending\n")
    with pytest.raises(ReviewStateError):
        load_review_state(f)


def test_unknown_state_value_raises(tmp_path: Path) -> None:
    f = tmp_path / "weird.yaml"
    f.write_text("state:\n  sf2: approved\n")
    with pytest.raises(ReviewStateError):
        load_review_state(f)


def test_sparse_invariant_pending_not_written() -> None:
    """INV-1 — building :class:`ReviewState` from a dict whose values
    include ``pending`` is rejected at validation time, so the sparse
    store can never contain it."""
    with pytest.raises(ValidationError):
        ReviewState.model_validate({"entries": {"sf2": "pending"}})


def test_empty_file_returns_empty_state(tmp_path: Path) -> None:
    """Empty file / top-level ``null`` → empty model (matches missing-file)."""
    f = tmp_path / "empty.yaml"
    f.write_text("")
    s = load_review_state(f)
    assert s.entries == {}


def test_yaml_syntax_error_raises(tmp_path: Path) -> None:
    f = tmp_path / "broken.yaml"
    f.write_text("state:\n  unbalanced: [\n")
    with pytest.raises(ReviewStateError, match="failed to parse"):
        load_review_state(f)

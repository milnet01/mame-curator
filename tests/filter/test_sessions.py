"""Tests for the Sessions schema, loader, and slicer."""

from pathlib import Path

import pytest

from mame_curator.filter.errors import SessionsError
from mame_curator.filter.sessions import Session, load_sessions


def test_session_requires_at_least_one_include_rule() -> None:
    with pytest.raises(SessionsError):
        Session.from_raw(name="empty", raw={})


def test_session_year_range_lo_must_not_exceed_hi() -> None:
    with pytest.raises(SessionsError):
        Session.from_raw(name="bad", raw={"include_year_range": [1995, 1990]})


def test_active_must_reference_a_defined_session(tmp_path: Path) -> None:
    f = tmp_path / "sessions.yaml"
    f.write_text("active: missing\nsessions: {}\n")
    with pytest.raises(SessionsError):
        load_sessions(f)


def test_minimal_session_round_trip(tmp_path: Path) -> None:
    f = tmp_path / "sessions.yaml"
    f.write_text("active: null\nsessions:\n  shooters:\n    include_genres: ['Shooter*']\n")
    s = load_sessions(f)
    assert s.active is None
    assert s.sessions["shooters"].include_genres == ("Shooter*",)


def test_missing_file_returns_empty_sessions(tmp_path: Path) -> None:
    s = load_sessions(tmp_path / "nope.yaml")
    assert s.active is None
    assert s.sessions == {}


def test_full_session_with_all_includes(tmp_path: Path) -> None:
    f = tmp_path / "sessions.yaml"
    f.write_text(
        "active: capcom_fighters\n"
        "sessions:\n"
        "  capcom_fighters:\n"
        "    include_publishers: ['Capcom*']\n"
        "    include_genres: ['Fighter*']\n"
        "    include_year_range: [1991, 1995]\n"
    )
    s = load_sessions(f)
    cf = s.sessions["capcom_fighters"]
    assert cf.include_publishers == ("Capcom*",)
    assert cf.include_genres == ("Fighter*",)
    assert cf.include_year_range == (1991, 1995)

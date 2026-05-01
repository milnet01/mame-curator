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


def test_yaml_syntax_error_raises(tmp_path: Path) -> None:
    f = tmp_path / "bad.yaml"
    f.write_text("active: [unclosed\n")
    with pytest.raises(SessionsError, match="failed to parse"):
        load_sessions(f)


def test_top_level_not_a_mapping_raises(tmp_path: Path) -> None:
    f = tmp_path / "list.yaml"
    f.write_text("- not\n- a\n- mapping\n")
    with pytest.raises(SessionsError, match="not a YAML mapping"):
        load_sessions(f)


def test_sessions_field_not_a_mapping_raises(tmp_path: Path) -> None:
    f = tmp_path / "wrong-sessions.yaml"
    f.write_text("active: null\nsessions:\n  - not_a_mapping\n")
    with pytest.raises(SessionsError, match="must be a mapping"):
        load_sessions(f)


def test_session_with_invalid_field_type_raises(tmp_path: Path) -> None:
    """Pydantic ValidationError on a field is wrapped as SessionsError."""
    f = tmp_path / "bad-types.yaml"
    f.write_text("active: null\nsessions:\n  bad:\n    include_year_range: not-a-list\n")
    with pytest.raises(SessionsError):
        load_sessions(f)


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


# DS01 — Cluster C tests below


def test_sessions_active_validator_rejects_unknown_in_programmatic_construction() -> None:
    """C1 — `Sessions(active=...)` must validate via `model_validator`, not just
    in the YAML loader. Programmatic construction with `active` referencing a
    non-existent session must raise `SessionsError` (or `ValidationError`),
    not silently produce a broken `Sessions`."""
    from mame_curator.filter.sessions import Sessions

    with pytest.raises((SessionsError, ValueError)):
        Sessions(active="bogus", sessions={})


def test_sessions_oversized_yaml_rejected(tmp_path: Path) -> None:
    """C3 — file size cap of 1 MB before `yaml.safe_load`. Defends against
    YAML alias-bomb DoS when P07's `setup/` ships preset downloads."""
    f = tmp_path / "huge.yaml"
    # 2 MB of valid YAML (just a giant single key-value).
    payload = "active: null\nsessions:\n  big:\n    include_genres: ['" + ("X" * 2_000_000) + "']\n"
    f.write_text(payload)
    with pytest.raises(SessionsError):
        load_sessions(f)


def test_sessions_top_level_sessions_key_falsy_rejects(tmp_path: Path) -> None:
    """C4 — explicit-None semantics: `sessions: null` is the legitimate empty
    default; `sessions: 0`, `sessions: ""`, `sessions: []` are malformed and
    must raise. Currently `or {}` silently coerces all four to an empty map."""
    cases = [
        "active: null\nsessions: 0\n",
        "active: null\nsessions: ''\n",
        "active: null\nsessions: []\n",
    ]
    for i, payload in enumerate(cases):
        f = tmp_path / f"falsy_{i}.yaml"
        f.write_text(payload)
        with pytest.raises(SessionsError):
            load_sessions(f)


def test_sessions_null_active_and_null_sessions_ok(tmp_path: Path) -> None:
    """C4 — `null` values for both `active` and `sessions` keys must be
    accepted as the legitimate "no active session, no sessions defined"
    default, since YAML `null` deserialises to Python `None`."""
    f = tmp_path / "null.yaml"
    f.write_text("active: null\nsessions: null\n")
    s = load_sessions(f)
    assert s.active is None
    assert s.sessions == {}


def test_sessions_oserror_wrapped(tmp_path: Path) -> None:
    """C5 — `OSError` from `read_text` (e.g. path is a directory, EIO,
    deleted-after-exists) must be wrapped in `SessionsError` per the
    loader's typed-error contract. Currently raw `OSError` escapes."""
    # Pointing the loader at a directory triggers an OSError on `read_text`.
    d = tmp_path / "is_a_dir.yaml"
    d.mkdir()
    with pytest.raises(SessionsError):
        load_sessions(d)


# FP05 — cluster A2 + B7 tests below


def test_sessions_rejects_empty_string_active() -> None:
    """A2a — `Sessions(active="", sessions={"": Session(...)})` should raise.

    Empty-string keys are valid Python dict keys; the membership test in
    `Sessions._active_must_reference_a_defined_session` would pass. The
    `_apply_session` runner.py:100 would then silently activate the
    empty-name session — bypassing the user's intent.
    """
    from mame_curator.filter.sessions import Sessions

    valid_session = Session(include_genres=("Fighter*",))
    with pytest.raises((SessionsError, ValueError)):
        Sessions(active="", sessions={"": valid_session})


def test_sessions_loader_rejects_empty_string_session_key(tmp_path: Path) -> None:
    """A2b — `sessions.yaml` with an empty-string key in `sessions:` mapping
    must raise. Loader-path counterpart to A2a's model-validator-path."""
    f = tmp_path / "empty_key.yaml"
    f.write_text(
        "active: null\nsessions:\n  '':\n    include_genres: ['Fighter*']\n",
        encoding="utf-8",
    )
    with pytest.raises(SessionsError):
        load_sessions(f)


def test_session_year_range_validator_rejects_reversed() -> None:
    """B7 — `Session(include_year_range=(1995, 1990))` should raise.

    Currently only `Session.from_raw` enforces `lo <= hi`. Direct construction
    bypasses the check (same bug class C1 closed for `Sessions.active`)."""
    from mame_curator.filter.sessions import Session

    with pytest.raises((SessionsError, ValueError)):
        Session(include_genres=("X*",), include_year_range=(1995, 1990))


def test_session_validator_rejects_no_include_rules() -> None:
    """B7 — programmatic `Session()` with no include rules must also raise.

    `from_raw` enforces this via the "session 'X' has no include rules" path;
    the model_validator should enforce the same invariant on direct
    construction."""
    from mame_curator.filter.sessions import Session

    with pytest.raises((SessionsError, ValueError)):
        Session()


# FP06 — B1 + B3d tests below


def test_direct_sessions_construction_raises_validation_error_on_bad_active() -> None:
    """FP06 B1a — pin the post-B2 contract for direct `Sessions(...)` construction.

    Pre-B2: validator raises `SessionsError` directly; Pydantic propagates.
    `pytest.raises(ValidationError)` would NOT match → test fails.
    Post-B2: validator raises `ValueError`; Pydantic wraps in `ValidationError`;
    test passes. The `errors()[0]['ctx']['error']` lookup pins Pydantic v2.x's
    structural shape (verified against 2.13)."""
    from pydantic import ValidationError

    from mame_curator.filter.sessions import Session, Sessions

    valid = Session(include_genres=("X*",))
    with pytest.raises(ValidationError) as exc_info:
        Sessions(active="bogus", sessions={"only": valid})
    # Loose primary check — survives Pydantic patch-version wrapping changes.
    assert "active session 'bogus' is not defined" in str(exc_info.value)
    # Strict structural check — pins the v2.x ctx.error shape.
    inner = exc_info.value.errors()[0]["ctx"]["error"]
    assert isinstance(inner, ValueError)


def test_load_sessions_wraps_validation_error_with_path_context(tmp_path: Path) -> None:
    """FP06 B1b — pin the loader path's contract: a YAML with bad `active` must
    surface as `SessionsError` whose message contains the (quoted) path.

    Combines B2 (validator raises ValueError → Pydantic wraps → loader's
    `try: Sessions(...) except ValidationError → SessionsError(f"{path!r}: ...")`
    rewrap fires) and B3 (path quoted via repr in the rewrapped message).

    FP06 Cluster R / M1: fixture path now contains an LF byte. The strict
    "no literal LF in head" assertion is what survives the "I'll just
    simplify the f-string" refactor — a future drop of `!r` would
    re-introduce the raw LF byte and fail the test."""
    try:
        f = tmp_path / "evil\nname.yaml"
        f.write_text("active: bogus\nsessions: {}\n", encoding="utf-8")
    except OSError:  # pragma: no cover
        pytest.skip("filesystem rejects \\n in path names")
    with pytest.raises(SessionsError) as exc_info:
        load_sessions(f)
    msg = str(exc_info.value)
    # Path appears in repr-escaped form.
    assert "evil\\nname.yaml" in msg
    # Original validator message survives the rewrap.
    assert "not defined" in msg
    # Strict: the path-bearing prefix has no literal LF byte.
    head = msg.split(":", 1)[0]
    assert "\n" not in head


def test_active_with_control_char_quoted_in_error() -> None:
    """FP06 Cluster R / R2 — `Sessions(active="evil\\nname", ...)` must surface
    the `active` value via `repr()` in the validator error. Pre-R2 the bare
    `f"'{self.active}'"` interpolation leaked a literal LF byte through
    Pydantic's `ValidationError.__str__`, breaking the single-line contract."""
    from pydantic import ValidationError

    from mame_curator.filter.sessions import Sessions

    valid = Session(include_genres=("X*",))
    with pytest.raises(ValidationError) as exc_info:
        Sessions(active="evil\nname", sessions={"other": valid})
    msg = str(exc_info.value)
    # Post-R2: name is repr-escaped.
    assert "evil\\nname" in msg
    # Strict: no literal LF in the validator's error line. (Pydantic adds
    # surrounding context; we check the segment between "active session "
    # and " is not defined" — the user-controlled portion.)
    user_segment = msg.split("active session ", 1)[1].split(" is not defined", 1)[0]
    assert "\n" not in user_segment


def test_session_with_control_char_in_name_quoted_in_error(tmp_path: Path) -> None:
    """FP06 B3d — name-quoting at `sessions.py:125`. A YAML session-key with a
    literal LF must surface in the error message via `repr(name)` (escaped form),
    NOT as a raw LF byte that breaks the single-line error contract.

    Fixture-content gotcha: Python source `"\\n"` writes one backslash + 'n'
    to disk; PyYAML's double-quoted scalar then decodes that to one LF byte
    at parse time. The resulting key has LF in the middle.
    """
    fixture = tmp_path / "sessions.yaml"
    try:
        fixture.write_text(
            "active: null\n"
            "sessions:\n"
            '  "evil\\nname": 42\n',  # body=42 (non-mapping) → trips sessions.py:125
            encoding="utf-8",
        )
    except OSError:  # pragma: no cover
        pytest.skip("filesystem rejects \\n in path names")
    with pytest.raises(SessionsError) as exc_info:
        load_sessions(fixture)
    msg = str(exc_info.value)
    # Post-fix: name is repr-escaped — backslash-n appears as 2 chars.
    assert "evil\\nname" in msg
    # Strict: no literal LF byte in the rendered message (the SessionsError
    # f-string is single-line; pre-fix the user-controlled LF byte breaks
    # that contract).
    assert "\n" not in msg

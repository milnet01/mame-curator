"""Tests for `filter/_io.read_capped_text` (FP05 C1 + B5).

FP06 B3 path-quoting tests live here — the helper is the canonical place
to lock in the `f"{path!r}"` contract since both `sessions.py` and
`overrides.py` route through it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mame_curator.filter._io import read_capped_text

_OVER_CAP = b"0" * (1024 * 1024 + 1)  # > 1 MiB


def test_read_capped_text_path_with_newline_in_error_is_quoted(tmp_path: Path) -> None:
    """FP06 B3a — a path whose name contains LF must surface in the error
    message via `repr(path)` (escaped form), NOT as a literal LF byte that
    breaks the single-line error contract.

    Pre-fix the size-cap error message uses bare `f"{path}"` and the LF
    byte renders raw. Post-fix `f"{path!r}"` quotes it as the 2-char
    sequence `\\n` (backslash + n) per `Path.__repr__`.
    """
    bad = tmp_path / "evil\nname.yaml"
    try:
        bad.write_bytes(_OVER_CAP)
    except OSError:  # pragma: no cover
        pytest.skip("filesystem rejects \\n in path names")
    with pytest.raises(ValueError) as exc_info:
        read_capped_text(bad, exc_cls=ValueError)
    msg = str(exc_info.value)
    # Post-fix: repr-escaped form (Python source `\\n` = 2 chars `\` + `n`).
    assert "evil\\nname.yaml" in msg
    # Strict: no literal LF byte in the rendered message.
    assert "\n" not in msg


def test_read_capped_text_size_cap_error_quotes_path_with_escape(tmp_path: Path) -> None:
    """FP06 B3b — a path containing an ANSI escape (`\\x1b[31m`) must be
    quoted in the error message, defending against terminal-control-byte
    spoofing of legitimate error output.
    """
    bad = tmp_path / "evil\x1b[31m.yaml"
    try:
        bad.write_bytes(_OVER_CAP)
    except OSError:  # pragma: no cover
        pytest.skip("filesystem rejects ESC in path names")
    with pytest.raises(ValueError) as exc_info:
        read_capped_text(bad, exc_cls=ValueError)
    msg = str(exc_info.value)
    # Post-fix: repr quotes the ESC byte (verified at Python 3.13).
    # Use `or` to absorb minor cross-version repr formatting drift.
    assert "\\x1b" in msg or "evil\\x1b[31m" in msg
    # Strict: no literal ESC byte in the rendered message.
    assert "\x1b" not in msg


def test_read_capped_text_oserror_path_quoted(tmp_path: Path) -> None:
    """FP06 B3 — pointing at a directory triggers an `OSError`
    (`IsADirectoryError`) which the loader wraps into the typed exc_cls.
    The wrapped message must quote the path via `repr`, not interpolate raw.
    """
    a_directory = tmp_path / "evil\nname.yaml"
    try:
        a_directory.mkdir()
    except OSError:  # pragma: no cover
        pytest.skip("filesystem rejects \\n in path names")
    with pytest.raises(ValueError) as exc_info:
        read_capped_text(a_directory, exc_cls=ValueError)
    msg = str(exc_info.value)
    assert "evil\\nname.yaml" in msg
    assert "\n" not in msg

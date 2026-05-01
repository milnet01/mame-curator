"""Tests for the `copy/` typed-error hierarchy (FP07 A4)."""

from __future__ import annotations

from pathlib import Path

from mame_curator.copy.errors import (
    CopyError,
    CopyExecutionError,
    PlaylistError,
    PreflightError,
    RecycleError,
)


def test_copy_error_str_quotes_path_with_control_byte() -> None:
    """FP07 A4 — `CopyError.__str__` must render `self.path` via `repr()`
    so a path with a control byte (newline, ANSI escape) doesn't break
    the single-line error contract or spoof terminal output.

    Single test covers every CopyError subclass via the shared `__str__`
    at `copy/errors.py:26`.
    """
    bad = Path("evil\nname.zip")
    for cls in (CopyError, PreflightError, PlaylistError, RecycleError, CopyExecutionError):
        exc = cls("test message", path=bad)
        rendered = str(exc)
        # Post-fix: repr-escaped form (Python source `\\n` = backslash + n).
        assert "evil\\nname.zip" in rendered, f"{cls.__name__} did not quote the path"
        # Strict: no literal LF byte in the rendered message.
        assert "\n" not in rendered, f"{cls.__name__} leaked a literal LF byte"


def test_copy_error_str_no_path_renders_message_only() -> None:
    """`CopyError.__str__` without `path=` returns the bare message
    (no `(path=...)` suffix). A4's repr fix must not change this branch."""
    exc = CopyError("just a message")
    assert str(exc) == "just a message"


def test_copy_error_path_attribute_preserved(tmp_path: Path) -> None:
    """`exc.path` accessor stays a `Path` object; the repr fix is
    rendering-only, not storage."""
    bad = tmp_path / "x.zip"
    exc = RecycleError("test", path=bad)
    assert exc.path == bad
    assert isinstance(exc.path, Path)

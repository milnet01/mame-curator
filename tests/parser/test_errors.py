"""Tests for the `parser/` typed-error hierarchy (FP07 A5)."""

from __future__ import annotations

from pathlib import Path

from mame_curator.parser.errors import (
    DATError,
    INIError,
    ListxmlError,
    ParserError,
)


def test_parser_error_str_quotes_path_with_control_byte() -> None:
    """FP07 A5 — `ParserError.__init__` must interpolate `path` via
    `repr()` so a control byte in the source path doesn't break the
    single-line error contract.

    `ParserError` freezes the message at construction time (unlike
    `CopyError` which renders lazily via `__str__`), so the fix lands
    in `__init__`. Single test covers every subclass.
    """
    bad = Path("evil\nname.xml")
    for cls in (ParserError, DATError, INIError, ListxmlError):
        exc = cls("test message", bad)
        rendered = str(exc)
        # Post-fix: repr-escaped form (Python source `\\n` = backslash + n).
        assert "evil\\nname.xml" in rendered, f"{cls.__name__} did not quote the path"
        # Strict: no literal LF byte in the rendered message.
        assert "\n" not in rendered, f"{cls.__name__} leaked a literal LF byte"


def test_parser_error_no_path_renders_message_only() -> None:
    """`ParserError("msg")` without `path` argument returns the bare
    message (no `(path=...)` suffix)."""
    exc = ParserError("just a message")
    assert str(exc) == "just a message"


def test_parser_error_path_attribute_preserved(tmp_path: Path) -> None:
    """`exc.path` accessor remains accessible after the repr fix."""
    bad = tmp_path / "x.xml"
    exc = DATError("test", bad)
    assert exc.path == bad
    assert isinstance(exc.path, Path)

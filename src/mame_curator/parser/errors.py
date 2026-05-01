"""Typed parser exceptions. Each carries the source path."""

from __future__ import annotations

from pathlib import Path


class ParserError(Exception):
    """Base for all parser-related errors."""

    def __init__(self, message: str, path: Path | None = None) -> None:
        """Build a parser error carrying the optional source path.

        FP07 A5: `path` is interpolated via `repr()` so a control byte in
        a user-controlled path can't break the single-line error contract.
        Single message-construction site for every ParserError subclass.
        Type contract: every `path=` caller in `src/` passes a `Path`;
        `repr(Path("x"))` renders `PosixPath('x')`, `repr("x")` renders
        `'x'` — both safe re. control bytes.
        """
        self.path = path
        super().__init__(f"{message} (path={path!r})" if path else message)


class DATError(ParserError):
    """Malformed DAT XML or unsupported wrapper."""


class INIError(ParserError):
    """Malformed INI file."""


class ListxmlError(ParserError):
    """Malformed `mame -listxml` output."""

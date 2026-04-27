"""Typed parser exceptions. Each carries the source path."""

from __future__ import annotations

from pathlib import Path


class ParserError(Exception):
    """Base for all parser-related errors."""

    def __init__(self, message: str, path: Path | None = None) -> None:
        """Build a parser error carrying the optional source path."""
        self.path = path
        super().__init__(f"{message} (path={path})" if path else message)


class DATError(ParserError):
    """Malformed DAT XML or unsupported wrapper."""


class INIError(ParserError):
    """Malformed INI file."""


class ListxmlError(ParserError):
    """Malformed `mame -listxml` output."""

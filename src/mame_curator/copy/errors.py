"""Typed exception hierarchy for the copy module.

Every CLI-visible error path stays inside `CopyError` so the CLI's
catch boundary holds and users see structured messages, not Python
tracebacks. See `coding-standards.md` § 9 and `cli/spec.md`
"Errors the CLI catches but never raises".
"""

from __future__ import annotations

from pathlib import Path


class CopyError(Exception):
    """Base for every error raised by the copy module."""

    def __init__(self, message: str, *, path: Path | None = None) -> None:
        """Construct with a message and an optional offending path."""
        super().__init__(message)
        self.path = path

    def __str__(self) -> str:
        """Render with `(path=...)` suffix when a path is attached."""
        base = super().__str__()
        if self.path is not None:
            return f"{base} (path={self.path})"
        return base


class BIOSResolutionError(CopyError):
    """Raised on a malformed `bios_chain` map structure."""


class PreflightError(CopyError):
    """Destination not writable, free-space shortfall, source missing."""


class PlaylistError(CopyError):
    """Existing playlist corrupt; required append decisions missing; write failure."""


class RecycleError(CopyError):
    """Filesystem read-only, permission denied, etc., during recycle move."""


class CopyExecutionError(CopyError):
    """Wrapped OSError from copy_one that escaped retry."""

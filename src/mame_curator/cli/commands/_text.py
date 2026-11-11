"""How a CLI command shows a user's path (mame-curator-1180)."""

from __future__ import annotations

from pathlib import Path

from rich.markup import escape


def shown_path(path: Path | str) -> str:
    """A path for a ``rich`` Console line: quoted, on one line, as typed.

    ``repr`` quotes it and writes a control byte as an escape, so a newline in
    a path cannot split the line (FP07). ``str`` first, so it never reads
    ``PosixPath(...)``. ``escape`` stops ``rich`` reading ``[bold]`` as markup.
    """
    # Typed here: pre-commit's mypy sees rich's escape as returning Any.
    shown: str = escape(repr(str(path)))
    return shown

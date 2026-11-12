"""How a CLI command shows a user's path (mame-curator-1180)."""

from __future__ import annotations

from pathlib import Path

from rich.markup import escape


def shown_path(path: Path | str) -> str:
    """A path for a ``rich`` Console line: quoted, on one line, as typed.

    A character that cannot be printed, such as a newline, is written as its
    escape, so it cannot split the line (FP07). Not ``repr``: that doubles
    every backslash, and a Windows path must stay copyable. ``escape`` stops
    ``rich`` reading ``[bold]`` as markup.
    """
    text = "".join(
        ch if ch.isprintable() else ch.encode("unicode_escape").decode("ascii") for ch in str(path)
    )
    shown: str = escape(f"'{text}'")  # Typed: pre-commit's mypy sees escape as Any.
    return shown

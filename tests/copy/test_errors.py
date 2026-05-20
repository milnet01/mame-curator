"""Tests for the `copy/` typed-error hierarchy (FP07 A4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from mame_curator.copy.errors import (
    CopyError,
    CopyExecutionError,
    PlaylistError,
    RecycleError,
)


@pytest.mark.parametrize("cls", [CopyError, PlaylistError, RecycleError, CopyExecutionError])
def test_copy_error_str_quotes_path_with_control_byte(cls: type[CopyError]) -> None:
    """FP07 A4 — `CopyError.__str__` must render `self.path` via `repr()`
    so a path with a control byte (newline, ANSI escape) doesn't break
    the single-line error contract or spoof terminal output.

    Parametrized per subclass so a failure names the offending class
    (shared `__str__` at `copy/errors.py:26`).
    """
    bad = Path("evil\nname.zip")
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


def test_copy_preflight_error_class_removed() -> None:
    """FP27 A2 — `copy.PreflightError` must not be importable post-fix.

    FP07's spec at `docs/specs/FP07.md:101` flagged this class as
    "exported but never raised in `src/`". Three releases later, no
    raise site has appeared. FP27 closes the dead surface.

    Pre-fix: passes because `PreflightError` is still exported. This
    assertion fails. Post-fix: the symbol is absent from the package
    surface; assertion passes.
    """
    from mame_curator import copy as copy_mod

    assert not hasattr(copy_mod, "PreflightError"), (
        "copy.PreflightError should be removed from the public surface "
        "(no non-test raise sites). See `docs/specs/FP27.md` § A2."
    )
    assert "PreflightError" not in copy_mod.__all__, (
        "copy.__all__ should no longer list 'PreflightError' (see `docs/specs/FP27.md` § A2)."
    )

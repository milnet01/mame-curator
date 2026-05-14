"""FP27 A1 — `filter.ConfigError` removed from the public surface.

The class was declared at `filter/errors.py:10`, exported via
`filter/__init__.py:8,27`, and named in `filter/spec.md:204`, but had zero
non-test `raise` sites in `src/`. The reachable validation work happens in
Pydantic validators on `FilterConfig`, which raise `ValidationError`. A1
removes the dead surface so the docs match the code.

Pre-fix: passes because `ConfigError` is still exported. Test fails.
Post-fix: `ConfigError` no longer importable from `mame_curator.filter`.
"""

from __future__ import annotations

from mame_curator import filter as filter_mod


def test_filter_config_error_class_removed() -> None:
    """`mame_curator.filter.ConfigError` must not be importable post-fix.

    Asserted via the package surface rather than an import line, so the
    test's own import doesn't break collection pre-fix.
    """
    assert not hasattr(filter_mod, "ConfigError"), (
        "filter.ConfigError should be removed from the public surface "
        "(no non-test raise sites; superseded by ValidationError on "
        "FilterConfig). See `docs/specs/FP27.md` § A1."
    )


def test_filter_config_error_not_in_all() -> None:
    """The `__all__` re-export must drop `'ConfigError'` post-fix."""
    assert "ConfigError" not in filter_mod.__all__, (
        "filter.__all__ should no longer list 'ConfigError' (see `docs/specs/FP27.md` § A1)."
    )

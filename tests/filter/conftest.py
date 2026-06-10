"""Shared fixtures and helpers for filter tests."""

from pathlib import Path

import pytest

from mame_curator.filter.overrides import Overrides
from mame_curator.filter.types import FilterContext
from mame_curator.parser.models import Machine

FIXTURES = Path(__file__).parent / "fixtures"

# Oversized YAML payload threshold — `filter/io.py` caps YAML reads at 1 MiB.
# Cross-referenced from test_io / test_overrides / test_sessions to assert the
# cap is enforced consistently.
OVER_CAP = b"0" * (1024 * 1024 + 1)


def m(**kw: object) -> Machine:
    """Minimal Machine builder used across filter tests.

    Description defaults to ``name`` so callers can omit it for the
    common case. Tests that pin a specific description still supply it.
    """
    name = str(kw.pop("name", "x"))
    description = str(kw.pop("description", name))
    # `arg-type` silences the CI mypy (which sees Machine's full field
    # types and can't prove `**kw: object` is field-compatible);
    # `unused-ignore` lets the pre-commit isolated mypy (which can't
    # resolve `mame_curator.parser.models` and infers `Any`) skip the
    # arg-type check without complaining the ignore is unused.
    return Machine(name=name, description=description, **kw)  # type: ignore[arg-type, unused-ignore]


def o(**entries: str) -> Overrides:
    """Minimal ``Overrides`` builder: ``o(pacman="pacmanf")`` →
    ``Overrides(entries={"pacman": "pacmanf"})``.

    Centralises the `call-arg` suppression the isolated pre-commit mypy
    needs (it can't resolve `Overrides`'s signature and flags `entries=`);
    `unused-ignore` lets the CI mypy — which sees the real signature — skip
    the check without complaining the ignore is unused.
    """
    return Overrides(entries=entries)  # type: ignore[call-arg, unused-ignore]


def make_empty_ctx() -> FilterContext:
    """An empty ``FilterContext`` — useful for tests that only exercise drop
    predicates or runner paths that ignore the context maps.
    """
    return FilterContext(
        cloneof_map={},
        category={},
        chd_required=frozenset(),
        mature=frozenset(),
    )


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Path to the filter test fixtures directory.

    Session-scoped because the value is a constant; nothing mutates it.
    """
    return FIXTURES

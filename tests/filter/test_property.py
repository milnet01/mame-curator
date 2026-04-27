"""Property-based regression: determinism + idempotency."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from mame_curator.filter.config import FilterConfig
from mame_curator.filter.overrides import Overrides
from mame_curator.filter.runner import run_filter
from mame_curator.filter.sessions import Sessions
from mame_curator.filter.types import FilterContext
from mame_curator.parser.models import Machine


def _machine(name: str, year: int) -> Machine:
    return Machine(
        name=name,
        description=f"{name} (USA)",
        year=year,
        publisher="Acme",
        developer="Acme",
    )


short_names = st.text(
    alphabet=st.characters(min_codepoint=ord("a"), max_codepoint=ord("z")),
    min_size=2,
    max_size=8,
)


@settings(max_examples=100, deadline=None)
@given(names=st.lists(short_names, min_size=1, max_size=15, unique=True))
def test_determinism_same_input_same_output(names: list[str]) -> None:
    machines = {n: _machine(n, 1980 + i) for i, n in enumerate(names)}
    a = run_filter(machines, FilterContext(), FilterConfig(), Overrides(), Sessions())
    b = run_filter(machines, FilterContext(), FilterConfig(), Overrides(), Sessions())
    assert a == b


@settings(max_examples=50, deadline=None)
@given(names=st.lists(short_names, min_size=2, max_size=10, unique=True))
def test_idempotent(names: list[str]) -> None:
    """Re-running on the prior result's winners (as new machines) yields the same winners."""
    machines = {n: _machine(n, 1980 + i) for i, n in enumerate(names)}
    first = run_filter(machines, FilterContext(), FilterConfig(), Overrides(), Sessions())
    survivors = {n: machines[n] for n in first.winners}
    second = run_filter(survivors, FilterContext(), FilterConfig(), Overrides(), Sessions())
    assert second.winners == first.winners

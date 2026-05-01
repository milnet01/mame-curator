"""End-to-end tests for run_filter."""

from __future__ import annotations

import pytest

from mame_curator.filter.config import FilterConfig
from mame_curator.filter.overrides import Overrides
from mame_curator.filter.runner import run_filter
from mame_curator.filter.sessions import Session, Sessions
from mame_curator.filter.types import DroppedReason, FilterContext
from mame_curator.parser.models import DriverStatus, Machine


def m(**kw: object) -> Machine:
    name = str(kw.pop("name", "x"))
    description = str(kw.pop("description", name))
    return Machine(name=name, description=description, **kw)  # type: ignore[arg-type, unused-ignore]


@pytest.fixture
def sample() -> tuple[dict[str, Machine], FilterContext]:
    machines = {
        "pacman": m(
            name="pacman",
            description="Pac-Man (USA)",
            year=1980,
            publisher="Namco",
            developer="Namco",
        ),
        "pacmanf": m(
            name="pacmanf",
            description="Pac-Man speedup (USA)",
            cloneof="pacman",
            year=1981,
            publisher="Namco",
            developer="Namco",
        ),
        "neogeo": m(name="neogeo", description="Neo-Geo", is_bios=True),
        "z80": m(name="z80", description="Z80 device", is_device=True, runnable=False),
        "3bagfull": m(name="3bagfull", description="3 Bags Full", is_mechanical=True),
        "kinst": m(
            name="kinst",
            description="Killer Instinct (USA)",
            year=1994,
            publisher="Rare",
            developer="Rare",
        ),
        "brokensim": m(
            name="brokensim",
            description="Broken Sim",
            driver_status=DriverStatus.PRELIMINARY,
        ),
    }
    ctx = FilterContext(
        category={
            "pacman": "Maze / Collect",
            "pacmanf": "Maze / Collect",
            "kinst": "Fighter / Versus",
        },
        chd_required=frozenset({"kinst"}),
        cloneof_map={"pacmanf": "pacman"},
        bestgames_tier={"pacman": "Best", "pacmanf": "Average"},
    )
    return machines, ctx


def test_phase_a_drops(sample: tuple[dict[str, Machine], FilterContext]) -> None:
    machines, ctx = sample
    result = run_filter(machines, ctx, FilterConfig(), Overrides(), Sessions())
    # `result.dropped` is `tuple[tuple[str, DroppedReason], ...]` (DS01 C2);
    # `dict()` re-conversion preserves the original lookup-by-short-name API.
    dropped = dict(result.dropped)
    assert dropped["neogeo"] is DroppedReason.BIOS
    assert dropped["z80"] is DroppedReason.DEVICE
    assert dropped["3bagfull"] is DroppedReason.MECHANICAL
    assert dropped["kinst"] is DroppedReason.CHD_REQUIRED
    assert dropped["brokensim"] is DroppedReason.PRELIMINARY_DRIVER


def test_winners_are_alphabetically_sorted_and_one_per_group(
    sample: tuple[dict[str, Machine], FilterContext],
) -> None:
    machines, ctx = sample
    result = run_filter(machines, ctx, FilterConfig(), Overrides(), Sessions())
    assert result.winners == ("pacman",)


def test_idempotent(sample: tuple[dict[str, Machine], FilterContext]) -> None:
    machines, ctx = sample
    a = run_filter(machines, ctx, FilterConfig(), Overrides(), Sessions())
    b = run_filter(machines, ctx, FilterConfig(), Overrides(), Sessions())
    assert a == b


def test_overrides_replace_pick(sample: tuple[dict[str, Machine], FilterContext]) -> None:
    machines, ctx = sample
    result = run_filter(
        machines,
        ctx,
        FilterConfig(),
        # mypy doesn't see through Pydantic's populate_by_name=True; works at runtime.
        Overrides(entries={"pacman": "pacmanf"}),  # type: ignore[call-arg, unused-ignore]
        Sessions(),
    )
    assert result.winners == ("pacmanf",)


def test_unknown_override_warns_doesnt_crash(
    sample: tuple[dict[str, Machine], FilterContext],
) -> None:
    machines, ctx = sample
    result = run_filter(
        machines,
        ctx,
        FilterConfig(),
        Overrides(entries={"pacman": "no_such_machine"}),  # type: ignore[call-arg, unused-ignore]
        Sessions(),
    )
    assert any("no_such_machine" in w for w in result.warnings)
    assert result.winners == ("pacman",)


def test_session_slices_winners(sample: tuple[dict[str, Machine], FilterContext]) -> None:
    machines, ctx = sample
    fighters_session = Session(include_genres=("Fighter*",))
    sessions = Sessions(active="fighters", sessions={"fighters": fighters_session})
    result = run_filter(machines, ctx, FilterConfig(), Overrides(), sessions)
    # pacman is a maze game, not a fighter — sliced out by the session.
    assert result.winners == ()


def test_override_with_unknown_parent_warns(
    sample: tuple[dict[str, Machine], FilterContext],
) -> None:
    machines, ctx = sample
    result = run_filter(
        machines,
        ctx,
        FilterConfig(),
        Overrides(entries={"no_such_parent": "pacman"}),  # type: ignore[call-arg, unused-ignore]
        Sessions(),
    )
    assert any("no_such_parent" in w and "not a known parent" in w for w in result.warnings)


def test_override_with_cross_group_target_warns(
    sample: tuple[dict[str, Machine], FilterContext],
) -> None:
    """The override target must belong to the same parent/clone group as the key."""
    machines = {
        "a": Machine(name="a", description="A (USA)"),
        "b": Machine(name="b", description="B (USA)", cloneof="a"),
        "c": Machine(name="c", description="C (USA)"),  # different group
    }
    ctx = FilterContext(cloneof_map={"b": "a"})
    result = run_filter(
        machines,
        ctx,
        FilterConfig(),
        Overrides(entries={"a": "c"}),  # type: ignore[call-arg, unused-ignore]
        Sessions(),
    )
    assert any("different group" in w for w in result.warnings)


def test_session_publisher_developer_year_filter() -> None:
    """Phase D include_publishers / include_developers / include_year_range branches."""
    machines = {
        "match_all": Machine(
            name="match_all",
            description="Match (USA)",
            publisher="Capcom",
            developer="Capcom",
            year=1992,
        ),
        "wrong_pub": Machine(
            name="wrong_pub",
            description="WP (USA)",
            publisher="Sega",
            developer="Capcom",
            year=1992,
        ),
        "wrong_year": Machine(
            name="wrong_year",
            description="WY (USA)",
            publisher="Capcom",
            developer="Capcom",
            year=1985,
        ),
        "wrong_dev": Machine(
            name="wrong_dev",
            description="WD (USA)",
            publisher="Capcom",
            developer="Konami",
            year=1992,
        ),
    }
    capcom_only = Session(
        include_publishers=("Capcom",),
        include_developers=("Capcom",),
        include_year_range=(1990, 1995),
    )
    sessions = Sessions(active="capcom", sessions={"capcom": capcom_only})
    result = run_filter(machines, FilterContext(), FilterConfig(), Overrides(), sessions)
    assert result.winners == ("match_all",)

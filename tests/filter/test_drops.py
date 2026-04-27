"""Tests for Phase A drop predicates — one test per rule."""

from __future__ import annotations

from mame_curator.filter.config import FilterConfig
from mame_curator.filter.drops import drop_reason
from mame_curator.filter.types import DroppedReason, FilterContext
from mame_curator.parser.models import DriverStatus, Machine


def m(**kw: object) -> Machine:
    """Minimal Machine builder; description defaults to name."""
    name = str(kw.pop("name", "x"))
    description = str(kw.pop("description", name))
    return Machine(name=name, description=description, **kw)  # type: ignore[arg-type]


def test_bios_dropped() -> None:
    assert (
        drop_reason(m(name="ng", is_bios=True), FilterContext(), FilterConfig())
        is DroppedReason.BIOS
    )


def test_device_dropped() -> None:
    assert (
        drop_reason(m(name="z80", is_device=True), FilterContext(), FilterConfig())
        is DroppedReason.DEVICE
    )


def test_non_runnable_dropped_as_device() -> None:
    assert (
        drop_reason(m(name="z80", runnable=False), FilterContext(), FilterConfig())
        is DroppedReason.DEVICE
    )


def test_mechanical_dropped() -> None:
    assert (
        drop_reason(m(name="x", is_mechanical=True), FilterContext(), FilterConfig())
        is DroppedReason.MECHANICAL
    )


def test_category_pattern_dropped() -> None:
    ctx = FilterContext(category={"slot1": "Casino / Slot Machine"})
    cfg = FilterConfig(drop_categories=("Casino*",))
    assert drop_reason(m(name="slot1"), ctx, cfg) is DroppedReason.CATEGORY


def test_mature_dropped() -> None:
    ctx = FilterContext(mature=frozenset({"adultx"}))
    assert drop_reason(m(name="adultx"), ctx, FilterConfig()) is DroppedReason.MATURE


def test_japanese_only_dropped() -> None:
    ctx = FilterContext(languages={"jp": ("Japanese",)})
    assert drop_reason(m(name="jp"), ctx, FilterConfig()) is DroppedReason.JAPANESE_ONLY


def test_japanese_with_other_language_kept() -> None:
    ctx = FilterContext(languages={"x": ("Japanese", "English")})
    assert drop_reason(m(name="x"), ctx, FilterConfig()) is None


def test_preliminary_driver_dropped() -> None:
    assert (
        drop_reason(
            m(name="b", driver_status=DriverStatus.PRELIMINARY),
            FilterContext(),
            FilterConfig(),
        )
        is DroppedReason.PRELIMINARY_DRIVER
    )


def test_chd_required_dropped() -> None:
    ctx = FilterContext(chd_required=frozenset({"kinst"}))
    assert drop_reason(m(name="kinst"), ctx, FilterConfig()) is DroppedReason.CHD_REQUIRED


def test_genre_pattern_dropped() -> None:
    ctx = FilterContext(category={"x": "Maze / Collect"})
    cfg = FilterConfig(drop_genres=("Collect",))
    assert drop_reason(m(name="x"), ctx, cfg) is DroppedReason.GENRE


def test_publisher_pattern_dropped() -> None:
    cfg = FilterConfig(drop_publishers=("Aristocrat*",))
    assert (
        drop_reason(
            m(name="x", publisher="Aristocrat", developer="Aristocrat"),
            FilterContext(),
            cfg,
        )
        is DroppedReason.PUBLISHER
    )


def test_developer_pattern_dropped() -> None:
    cfg = FilterConfig(drop_developers=("Bad*",))
    assert (
        drop_reason(
            m(name="x", publisher="Good", developer="BadStudio"),
            FilterContext(),
            cfg,
        )
        is DroppedReason.DEVELOPER
    )


def test_year_before_dropped() -> None:
    cfg = FilterConfig(drop_year_before=1980)
    assert drop_reason(m(name="x", year=1979), FilterContext(), cfg) is DroppedReason.YEAR_BEFORE


def test_year_after_dropped() -> None:
    cfg = FilterConfig(drop_year_after=2010)
    assert drop_reason(m(name="x", year=2011), FilterContext(), cfg) is DroppedReason.YEAR_AFTER


def test_clean_machine_not_dropped() -> None:
    assert (
        drop_reason(
            m(name="pacman", year=1980, publisher="Namco", developer="Namco"),
            FilterContext(category={"pacman": "Maze / Collect"}),
            FilterConfig(),
        )
        is None
    )

"""Tests for Phase A drop predicates — one test per rule."""

from __future__ import annotations

import pytest

from mame_curator.filter.config import FilterConfig
from mame_curator.filter.drops import drop_reason
from mame_curator.filter.types import DroppedReason, FilterContext
from mame_curator.parser.models import DriverStatus, Machine
from tests.filter.conftest import m


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


def test_fp21_c_runnable_strict_identity_no_drop_when_none() -> None:
    """FP21-C: ``_device`` matches spec rule 2 (``m.runnable is False``), not
    truthiness (``not m.runnable``).

    ``Machine.runnable`` is ``bool`` today, but the spec is keyed to strict
    identity so that any future widening to ``bool | None`` (a model whose
    DAT did not declare the attribute) doesn't silently flip "runnable
    unknown" machines into the DEVICE bucket. ``model_construct`` bypasses
    Pydantic validation to inject ``None`` for the regression check.
    """
    machine = Machine.model_construct(
        name="unknown",
        description="unknown",
        is_device=False,
        is_bios=False,
        runnable=None,  # FP21-C: validation skipped via model_construct
    )
    assert drop_reason(machine, FilterContext(), FilterConfig()) is None


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


def test_year_none_survives_year_range_filter() -> None:
    """FP31: machines with unknown year MUST survive year-range filters.

    ``drops.py`` guards both year comparisons with ``m.year is not None``.
    Real-world MAME catalogs have many machines with no year (parser sets it
    to None when the DAT omits ``<year>``); dropping them would clobber ~half
    the catalog. This test pins the ``year is None`` short-circuit so a
    refactor that removes the guard fails immediately.
    """
    cfg = FilterConfig(drop_year_before=1980, drop_year_after=2010)
    assert drop_reason(m(name="x", year=None), FilterContext(), cfg) is None


@pytest.mark.parametrize(
    "machine",
    [
        m(name="ng", is_bios=True),
        m(name="z80", is_device=True),
        m(name="z80", runnable=False),
        m(name="x", is_mechanical=True),
    ],
    ids=["bios", "device", "non_runnable", "mechanical"],
)
def test_drop_bios_devices_mechanical_false_keeps_them(machine: Machine) -> None:
    """Per filter/spec.md FilterConfig: `drop_bios_devices_mechanical: bool = True`
    is a togglable filter. When set to False, BIOS / device / mechanical machines
    must survive Phase A. Split per-predicate so a failure names the offending rule.

    Was a zombie field (declared, never read) until indie-review pass 3 Tier 1.
    """
    cfg = FilterConfig(drop_bios_devices_mechanical=False)
    assert drop_reason(machine, FilterContext(), cfg) is None


def test_drop_bios_devices_mechanical_default_true_drops_them() -> None:
    """Default is True; baseline behavior must keep dropping these."""
    cfg = FilterConfig()  # default
    assert drop_reason(m(name="ng", is_bios=True), FilterContext(), cfg) is DroppedReason.BIOS
    assert drop_reason(m(name="z80", is_device=True), FilterContext(), cfg) is DroppedReason.DEVICE
    assert (
        drop_reason(m(name="x", is_mechanical=True), FilterContext(), cfg)
        is DroppedReason.MECHANICAL
    )


@pytest.mark.parametrize(
    ("cfg", "ctx", "machine"),
    [
        (
            FilterConfig(drop_mature=False),
            FilterContext(mature=frozenset({"adultx"})),
            m(name="adultx"),
        ),
        (
            FilterConfig(drop_preliminary_emulation=False),
            FilterContext(),
            m(name="b", driver_status=DriverStatus.PRELIMINARY),
        ),
        (
            FilterConfig(drop_chd_required=False),
            FilterContext(chd_required=frozenset({"kinst"})),
            m(name="kinst"),
        ),
        (
            FilterConfig(drop_japanese_only_text=False),
            FilterContext(languages={"jp": ("Japanese",)}),
            m(name="jp"),
        ),
    ],
    ids=["mature", "preliminary_emulation", "chd_required", "japanese_only_text"],
)
def test_togglable_drop_flags_false_keeps_them(
    cfg: FilterConfig, ctx: FilterContext, machine: Machine
) -> None:
    """Each remaining boolean Phase-A flag, when False, must keep machines its
    enabled form drops. Mirrors `test_drop_bios_devices_mechanical_false_keeps_them`
    for `drop_mature`, `drop_preliminary_emulation`, `drop_chd_required`, and
    `drop_japanese_only_text` — every togglable drop predicate now has a
    flag-disabled regression lock. Split per-flag so a failure names the rule.
    """
    assert drop_reason(machine, ctx, cfg) is None


def test_clean_machine_not_dropped() -> None:
    assert (
        drop_reason(
            m(name="pacman", year=1980, publisher="Namco", developer="Namco"),
            FilterContext(category={"pacman": "Maze / Collect"}),
            FilterConfig(),
        )
        is None
    )


@pytest.mark.parametrize(
    "category",
    [
        "MultiGame / Compilation",
        "MultiGame / Mini-Games",
        "Multiplay / Mini-Games * Mature *",
        "Game Console / Multi-Games",
        "Board Game / Multi-Games Machine",
    ],
)
def test_multigame_dropped(category: str) -> None:
    """mame-curator-1216: a multi-game board goes when drop_multigame is on."""
    assert (
        drop_reason(
            m(name="mg"),
            FilterContext(category={"mg": category}),
            FilterConfig(drop_multigame=True),
        )
        is DroppedReason.MULTIGAME
    )


@pytest.mark.parametrize(
    ("category", "cfg"),
    [
        ("MultiGame / Compilation", FilterConfig()),
        ("Misc. / Multiplay", FilterConfig(drop_multigame=True)),
        ("Handheld / Plug n' Play TV Game / Multi-Sport", FilterConfig(drop_multigame=True)),
        ("Shooter / Flying Vertical", FilterConfig(drop_multigame=True)),
        (None, FilterConfig(drop_multigame=True)),
    ],
    ids=["switch_off_by_default", "multiplay_not_first", "multi_sport", "plain", "no_category"],
)
def test_multigame_kept(category: str | None, cfg: FilterConfig) -> None:
    """mame-curator-1216: only the three catver shapes count, and only when on."""
    ctx = FilterContext(category={} if category is None else {"mg": category})
    assert drop_reason(m(name="mg"), ctx, cfg) is None


@pytest.mark.parametrize(
    ("langs", "keep"),
    [
        (("Spanish",), ("English",)),
        (("German", "Italian"), ("English", "French")),
        (("Japanese", "Chinese"), ("English",)),
    ],
    ids=["one_language", "none_of_several", "japanese_and_another"],
)
def test_keep_languages_dropped(langs: tuple[str, ...], keep: tuple[str, ...]) -> None:
    """mame-curator-1217: a listed game with none of the chosen languages goes."""
    ctx = FilterContext(languages={"x": langs})
    assert drop_reason(m(name="x"), ctx, FilterConfig(keep_languages=keep)) is (
        DroppedReason.LANGUAGE
    )


@pytest.mark.parametrize(
    ("languages", "cfg"),
    [
        ({"x": ("Spanish",)}, FilterConfig()),
        ({"x": ("Japanese", "English")}, FilterConfig(keep_languages=("English",))),
        ({"x": ("French",)}, FilterConfig(keep_languages=("English", "French"))),
        ({}, FilterConfig(keep_languages=("English",))),
    ],
    ids=["every_language_by_default", "one_chosen_of_several", "second_choice", "not_listed"],
)
def test_keep_languages_kept(languages: dict[str, tuple[str, ...]], cfg: FilterConfig) -> None:
    """mame-curator-1217: kept when no list, a chosen language, or no languages.ini entry."""
    ctx = FilterContext(languages=languages)
    assert drop_reason(m(name="x"), ctx, cfg) is None


def test_japanese_only_still_applies_beside_keep_languages() -> None:
    """mame-curator-1217: drop_japanese_only_text still applies, and runs first."""
    ctx = FilterContext(languages={"jp": ("Japanese",)})
    assert (
        drop_reason(m(name="jp"), ctx, FilterConfig(keep_languages=("Japanese",)))
        is DroppedReason.JAPANESE_ONLY
    )
    assert (
        drop_reason(m(name="jp"), ctx, FilterConfig(keep_languages=("English",)))
        is DroppedReason.JAPANESE_ONLY
    )

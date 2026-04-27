"""Phase A drop predicates.

Each predicate returns the matching DroppedReason or None. The public
`drop_reason()` runs them in spec order and returns the first hit.
"""

from __future__ import annotations

from collections.abc import Callable
from fnmatch import fnmatchcase

from mame_curator.filter.config import FilterConfig
from mame_curator.filter.types import DroppedReason, FilterContext
from mame_curator.parser.models import DriverStatus, Machine


def _matches_any(value: str | None, patterns: tuple[str, ...]) -> bool:
    if value is None or not patterns:
        return False
    return any(fnmatchcase(value, p) for p in patterns)


def _genre_of(category: str | None) -> str | None:
    if category is None:
        return None
    return category.rsplit("/", 1)[-1].strip()


def _bios(m: Machine, _c: FilterContext, _f: FilterConfig) -> DroppedReason | None:
    return DroppedReason.BIOS if m.is_bios else None


def _device(m: Machine, _c: FilterContext, _f: FilterConfig) -> DroppedReason | None:
    return DroppedReason.DEVICE if (m.is_device or not m.runnable) else None


def _mechanical(m: Machine, _c: FilterContext, _f: FilterConfig) -> DroppedReason | None:
    return DroppedReason.MECHANICAL if m.is_mechanical else None


def _category(m: Machine, ctx: FilterContext, cfg: FilterConfig) -> DroppedReason | None:
    cat = ctx.category.get(m.name)
    return DroppedReason.CATEGORY if _matches_any(cat, cfg.drop_categories) else None


def _mature(m: Machine, ctx: FilterContext, cfg: FilterConfig) -> DroppedReason | None:
    return DroppedReason.MATURE if (cfg.drop_mature and m.name in ctx.mature) else None


def _japanese_only(m: Machine, ctx: FilterContext, cfg: FilterConfig) -> DroppedReason | None:
    if not cfg.drop_japanese_only_text:
        return None
    langs = ctx.languages.get(m.name)
    if langs == ("Japanese",):
        return DroppedReason.JAPANESE_ONLY
    return None


def _preliminary(m: Machine, _c: FilterContext, cfg: FilterConfig) -> DroppedReason | None:
    if cfg.drop_preliminary_emulation and m.driver_status is DriverStatus.PRELIMINARY:
        return DroppedReason.PRELIMINARY_DRIVER
    return None


def _chd(m: Machine, ctx: FilterContext, cfg: FilterConfig) -> DroppedReason | None:
    if cfg.drop_chd_required and m.name in ctx.chd_required:
        return DroppedReason.CHD_REQUIRED
    return None


def _genre(m: Machine, ctx: FilterContext, cfg: FilterConfig) -> DroppedReason | None:
    genre = _genre_of(ctx.category.get(m.name))
    return DroppedReason.GENRE if _matches_any(genre, cfg.drop_genres) else None


def _publisher(m: Machine, _c: FilterContext, cfg: FilterConfig) -> DroppedReason | None:
    return DroppedReason.PUBLISHER if _matches_any(m.publisher, cfg.drop_publishers) else None


def _developer(m: Machine, _c: FilterContext, cfg: FilterConfig) -> DroppedReason | None:
    return DroppedReason.DEVELOPER if _matches_any(m.developer, cfg.drop_developers) else None


def _year_before(m: Machine, _c: FilterContext, cfg: FilterConfig) -> DroppedReason | None:
    if cfg.drop_year_before is not None and m.year is not None and m.year < cfg.drop_year_before:
        return DroppedReason.YEAR_BEFORE
    return None


def _year_after(m: Machine, _c: FilterContext, cfg: FilterConfig) -> DroppedReason | None:
    if cfg.drop_year_after is not None and m.year is not None and m.year > cfg.drop_year_after:
        return DroppedReason.YEAR_AFTER
    return None


_PREDICATES: tuple[Callable[[Machine, FilterContext, FilterConfig], DroppedReason | None], ...] = (
    _bios,
    _device,
    _mechanical,
    _category,
    _mature,
    _japanese_only,
    _preliminary,
    _chd,
    _genre,
    _publisher,
    _developer,
    _year_before,
    _year_after,
)


def drop_reason(m: Machine, ctx: FilterContext, cfg: FilterConfig) -> DroppedReason | None:
    """Return the first matching DroppedReason, or None if the machine survives."""
    for predicate in _PREDICATES:
        reason = predicate(m, ctx, cfg)
        if reason is not None:
            return reason
    return None

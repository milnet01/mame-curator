"""Phase B picker — tiebreaker chain produces a winner per parent group.

Each tiebreaker is a `cmp(a, b, ctx, cfg, parent) -> int` returning -1, 0, or +1
per spec line 55. Comparators are evaluated in spec order; the first non-zero
result decides the comparison. Composed via `functools.cmp_to_key` and used to
sort the candidate list; the first element after sort is the winner.

`explain_pick` walks the comparators against the winner's pairings to record
which one actually made the decisive call.
"""

from __future__ import annotations

import functools
from collections.abc import Callable, Iterable

from mame_curator.filter.config import FilterConfig
from mame_curator.filter.heuristics import Region, region_of, revision_key_of
from mame_curator.filter.types import FilterContext, TiebreakerHit
from mame_curator.parser.models import DriverStatus, Machine

_TIER_RANK: dict[str, int] = {
    "Best": 6,
    "Great": 5,
    "Good": 4,
    "Average": 3,
    "Bad": 2,
    "Awful": 1,
}
_DRIVER_RANK: dict[DriverStatus | None, int] = {
    DriverStatus.GOOD: 3,
    DriverStatus.IMPERFECT: 2,
    DriverStatus.PRELIMINARY: 1,
    None: 0,
}

# Each comparator: (a, b, ctx, cfg, parent) -> int.
# Return -1 if a should rank ABOVE b (i.e., sort earlier — winner is first
# after sort), +1 if b should rank above a, 0 if this comparator is silent.
# This polarity matches Python's standard `cmp(a, b)` convention so that
# `sorted()` puts winners first.
CmpFn = Callable[[Machine, Machine, FilterContext, FilterConfig, str], int]


def _sign(diff: int) -> int:
    """Return -1 / 0 / +1 from any int. We invert at call time for higher-wins."""
    if diff < 0:
        return -1
    if diff > 0:
        return 1
    return 0


def _cmp_tier(a: Machine, b: Machine, ctx: FilterContext, _cfg: FilterConfig, _p: str) -> int:
    """Higher bestgames tier wins; absent tier ranks 0."""
    rank_a = _TIER_RANK.get(ctx.bestgames_tier.get(a.name, ""), 0)
    rank_b = _TIER_RANK.get(ctx.bestgames_tier.get(b.name, ""), 0)
    return -_sign(rank_a - rank_b)  # higher rank → wins → cmp says a < b


def _preferred_score(m: Machine, ctx: FilterContext, cfg: FilterConfig) -> int:
    """+1 per matching preferred_{genres,publishers,developers} (substring match).

    Substring match is intentional and pinned by spec — `preferred_*` differs
    from `drop_*` (which uses fnmatch) and is documented in filter/spec.md.
    """
    score = 0
    cat = ctx.category.get(m.name)
    if cat is not None and any(p in cat for p in cfg.preferred_genres):
        score += 1
    if m.publisher and any(p in m.publisher for p in cfg.preferred_publishers):
        score += 1
    if m.developer and any(p in m.developer for p in cfg.preferred_developers):
        score += 1
    return score


def _cmp_preferred(a: Machine, b: Machine, ctx: FilterContext, cfg: FilterConfig, _p: str) -> int:
    return -_sign(_preferred_score(a, ctx, cfg) - _preferred_score(b, ctx, cfg))


def _cmp_parent_over_clone(
    a: Machine, b: Machine, _ctx: FilterContext, cfg: FilterConfig, parent: str
) -> int:
    if not cfg.prefer_parent_over_clone:
        return 0
    a_is = 1 if a.name == parent else 0
    b_is = 1 if b.name == parent else 0
    return -_sign(a_is - b_is)


def _cmp_driver(a: Machine, b: Machine, _ctx: FilterContext, cfg: FilterConfig, _p: str) -> int:
    if not cfg.prefer_good_driver:
        return 0
    return -_sign(_DRIVER_RANK[a.driver_status] - _DRIVER_RANK[b.driver_status])


def _region_score(m: Machine, cfg: FilterConfig) -> int:
    """Lower index in `cfg.region_priority` ranks higher; UNKNOWN ranks below all listed.

    Returns a comparable int where higher = wins. UNKNOWN gets a sentinel
    strictly below every listed region (which run from 0 .. len-1).
    """
    region = region_of(m.description)
    if region is Region.UNKNOWN:
        return -(len(cfg.region_priority) + 1)  # below every listed region
    try:
        return -cfg.region_priority.index(region.value)
    except ValueError:
        return -len(cfg.region_priority)  # listed Region enum value not in cfg priority


def _cmp_region(a: Machine, b: Machine, _ctx: FilterContext, cfg: FilterConfig, _p: str) -> int:
    return -_sign(_region_score(a, cfg) - _region_score(b, cfg))


def _cmp_revision(a: Machine, b: Machine, _ctx: FilterContext, _cfg: FilterConfig, _p: str) -> int:
    """Higher revision tuple wins (later set/rev/version)."""
    ra, rb = revision_key_of(a.description), revision_key_of(b.description)
    if ra == rb:
        return 0
    return -1 if ra > rb else 1


def _cmp_alpha(a: Machine, b: Machine, _ctx: FilterContext, _cfg: FilterConfig, _p: str) -> int:
    """Alphabetically lower short-name wins (deterministic fallback per spec line 53).

    Direct string compare — no tuple-length surprises.
    """
    if a.name == b.name:
        return 0
    return -1 if a.name < b.name else 1


_TIEBREAKERS: tuple[tuple[str, CmpFn], ...] = (
    ("tier", _cmp_tier),
    ("preferred", _cmp_preferred),
    ("parent_over_clone", _cmp_parent_over_clone),
    ("driver", _cmp_driver),
    ("region", _cmp_region),
    ("revision", _cmp_revision),
    ("alpha", _cmp_alpha),
)


def _compose_cmp(
    ctx: FilterContext, cfg: FilterConfig, parent: str
) -> Callable[[Machine, Machine], int]:
    """Build a single (a, b) -> int from the tiebreaker chain. First non-zero decides."""

    def chain(a: Machine, b: Machine) -> int:
        for _name, cmp in _TIEBREAKERS:
            result = cmp(a, b, ctx, cfg, parent)
            if result != 0:
                return result
        return 0

    return chain


def pick_winner(
    candidates: Iterable[Machine], parent: str, ctx: FilterContext, cfg: FilterConfig
) -> Machine:
    """Pick the highest-ranked candidate per the spec's tiebreaker chain."""
    chain = _compose_cmp(ctx, cfg, parent)
    return sorted(candidates, key=functools.cmp_to_key(chain))[0]


def explain_pick(
    candidates: Iterable[Machine], parent: str, ctx: FilterContext, cfg: FilterConfig
) -> tuple[TiebreakerHit, ...]:
    """List the tiebreakers that actually decided the winner.

    Per spec line 57: a tiebreaker is recorded only if it produced a non-zero
    cmp result against at least one other candidate (i.e., it broke a tie that
    earlier comparators couldn't resolve, OR it was the first to discriminate).
    """
    cand_list = list(candidates)
    winner = pick_winner(cand_list, parent, ctx, cfg)
    hits: list[TiebreakerHit] = []
    others = [c for c in cand_list if c.name != winner.name]
    for name, cmp in _TIEBREAKERS:
        decisive = any(cmp(winner, other, ctx, cfg, parent) < 0 for other in others)
        if decisive:
            hits.append(TiebreakerHit(name=name, detail=f"{winner.name} wins via {name}"))
    return tuple(hits)

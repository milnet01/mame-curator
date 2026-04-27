"""Phase B picker — tiebreaker chain produces a winner per parent group.

Each tiebreaker is a `score(machine) -> int | tuple` higher-is-better function.
We sort the candidate list by the composite key (score_1, score_2, ..., name)
and pick the maximum. `explain_pick` re-runs the tiebreakers to identify the
ones that actually decided the result (i.e., produced a non-uniform score).
"""

from __future__ import annotations

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

ScoreFn = Callable[[Machine, FilterContext, FilterConfig, str], "tuple[int, ...] | int"]


def _score_tier(m: Machine, ctx: FilterContext, _cfg: FilterConfig, _parent: str) -> int:
    return _TIER_RANK.get(ctx.bestgames_tier.get(m.name, ""), 0)


def _score_preferred(m: Machine, ctx: FilterContext, cfg: FilterConfig, _parent: str) -> int:
    score = 0
    cat = ctx.category.get(m.name)
    if cat is not None:
        for pattern in cfg.preferred_genres:
            if pattern in cat:
                score += 1
                break
    if m.publisher and any(p in m.publisher for p in cfg.preferred_publishers):
        score += 1
    if m.developer and any(p in m.developer for p in cfg.preferred_developers):
        score += 1
    return score


def _score_parent_over_clone(
    m: Machine, _ctx: FilterContext, cfg: FilterConfig, parent: str
) -> int:
    if not cfg.prefer_parent_over_clone:
        return 0
    return 1 if m.name == parent else 0


def _score_driver(m: Machine, _ctx: FilterContext, cfg: FilterConfig, _parent: str) -> int:
    return _DRIVER_RANK[m.driver_status] if cfg.prefer_good_driver else 0


def _score_region(m: Machine, _ctx: FilterContext, cfg: FilterConfig, _parent: str) -> int:
    region = region_of(m.description)
    if region is Region.UNKNOWN:
        return -1  # ranks below every listed region
    try:
        return -cfg.region_priority.index(region.value)  # earlier = higher score
    except ValueError:
        return -len(cfg.region_priority)  # listed regions absent from priority list


def _score_revision(
    m: Machine, _ctx: FilterContext, _cfg: FilterConfig, _parent: str
) -> tuple[int, ...]:
    return revision_key_of(m.description)


def _score_alpha(
    m: Machine, _ctx: FilterContext, _cfg: FilterConfig, _parent: str
) -> tuple[int, ...]:
    # Negate so higher composite key still wins; alphabetical-first → highest score.
    return tuple(-ord(c) for c in m.name)


_TIEBREAKERS: tuple[tuple[str, ScoreFn], ...] = (
    ("tier", _score_tier),
    ("preferred", _score_preferred),
    ("parent_over_clone", _score_parent_over_clone),
    ("driver", _score_driver),
    ("region", _score_region),
    ("revision", _score_revision),
    ("alpha", _score_alpha),
)


def _composite_key(
    m: Machine, ctx: FilterContext, cfg: FilterConfig, parent: str
) -> tuple[object, ...]:
    return tuple(score(m, ctx, cfg, parent) for _name, score in _TIEBREAKERS)


def pick_winner(
    candidates: Iterable[Machine], parent: str, ctx: FilterContext, cfg: FilterConfig
) -> Machine:
    """Pick the highest-ranked candidate per the spec's tiebreaker chain."""
    return max(candidates, key=lambda c: _composite_key(c, ctx, cfg, parent))


def explain_pick(
    candidates: Iterable[Machine], parent: str, ctx: FilterContext, cfg: FilterConfig
) -> tuple[TiebreakerHit, ...]:
    """List the tiebreakers that actually decided the winner."""
    cand_list = list(candidates)
    winner = pick_winner(cand_list, parent, ctx, cfg)
    hits: list[TiebreakerHit] = []
    for name, score in _TIEBREAKERS:
        scores = {c.name: score(c, ctx, cfg, parent) for c in cand_list}
        if len({repr(v) for v in scores.values()}) <= 1:
            continue  # no signal from this tiebreaker
        hits.append(TiebreakerHit(name=name, detail=f"{winner.name}={scores[winner.name]!r}"))
    return tuple(hits)

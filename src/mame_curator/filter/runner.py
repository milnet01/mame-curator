"""Orchestrator: drop (A) → pick (B) → override (C) → session-slice (D)."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Iterable
from fnmatch import fnmatchcase

from mame_curator.filter.config import FilterConfig
from mame_curator.filter.drops import drop_reason
from mame_curator.filter.overrides import Overrides
from mame_curator.filter.picker import explain_pick, pick_winner
from mame_curator.filter.sessions import Session, Sessions
from mame_curator.filter.types import (
    ContestedGroup,
    DroppedReason,
    FilterContext,
    FilterResult,
)
from mame_curator.parser.models import Machine

logger = logging.getLogger(__name__)


def run_filter(
    machines: dict[str, Machine],
    ctx: FilterContext,
    cfg: FilterConfig,
    overrides: Overrides,
    sessions: Sessions,
) -> FilterResult:
    """Run the four-phase filter and return a FilterResult."""
    survivors: dict[str, Machine] = {}
    dropped: dict[str, DroppedReason] = {}
    for name, machine in machines.items():
        reason = drop_reason(machine, ctx, cfg)
        if reason is None:
            survivors[name] = machine
        else:
            dropped[name] = reason

    groups: dict[str, list[Machine]] = defaultdict(list)
    for machine in survivors.values():
        parent = ctx.cloneof_map.get(machine.name, machine.name)
        groups[parent].append(machine)

    winners: dict[str, str] = {}
    contested: list[ContestedGroup] = []
    for parent, candidates in groups.items():
        winner = pick_winner(candidates, parent, ctx, cfg)
        winners[parent] = winner.name
        if len(candidates) > 1:
            contested.append(
                ContestedGroup(
                    parent=parent,
                    candidates=tuple(sorted(c.name for c in candidates)),
                    winner=winner.name,
                    chain=explain_pick(candidates, parent, ctx, cfg),
                )
            )

    warnings: list[str] = []
    for parent, override_name in overrides.entries.items():
        if parent not in groups:
            warnings.append(f"override key '{parent}' is not a known parent; ignored")
            continue
        if override_name not in machines:
            warnings.append(f"override target '{override_name}' is not in the DAT; ignored")
            continue
        target_parent = ctx.cloneof_map.get(override_name, override_name)
        if target_parent != parent:
            warnings.append(
                f"override '{parent} -> {override_name}': target belongs to "
                "a different group; ignored"
            )
            continue
        winners[parent] = override_name
        dropped.pop(override_name, None)

    visible = _apply_session(winners, machines, ctx, sessions)

    return FilterResult(
        winners=tuple(sorted(visible)),
        dropped=dict(dropped),
        contested_groups=tuple(contested),
        warnings=tuple(warnings),
    )


def _apply_session(
    winners: dict[str, str],
    machines: dict[str, Machine],
    ctx: FilterContext,
    sessions: Sessions,
) -> list[str]:
    """Slice winners to those matching the active session, if any."""
    if sessions.active is None:
        return list(winners.values())
    session = sessions.sessions[sessions.active]
    return [
        name for name in winners.values() if _machine_matches_session(machines[name], session, ctx)
    ]


def _machine_matches_session(m: Machine, session: Session, ctx: FilterContext) -> bool:
    if session.include_genres:
        cat = ctx.category.get(m.name)
        if cat is None or not _any_fnmatch(cat, session.include_genres):
            return False
    if session.include_publishers and (
        m.publisher is None or not _any_fnmatch(m.publisher, session.include_publishers)
    ):
        return False
    if session.include_developers and (
        m.developer is None or not _any_fnmatch(m.developer, session.include_developers)
    ):
        return False
    if session.include_year_range is not None:
        lo, hi = session.include_year_range
        if m.year is None or m.year < lo or m.year > hi:
            return False
    return True


def _any_fnmatch(value: str, patterns: Iterable[str]) -> bool:
    return any(fnmatchcase(value, p) for p in patterns)

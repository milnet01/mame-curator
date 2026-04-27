"""Filter rule chain — drop, pick, override, session-slice.

Public API surface — see spec.md for the full contract.
"""

from mame_curator.filter.config import FilterConfig
from mame_curator.filter.errors import (
    ConfigError,
    FilterError,
    OverridesError,
    SessionsError,
)
from mame_curator.filter.heuristics import Region, region_of, revision_key_of
from mame_curator.filter.overrides import Overrides, load_overrides
from mame_curator.filter.picker import explain_pick, pick_winner
from mame_curator.filter.runner import run_filter
from mame_curator.filter.sessions import Session, Sessions, load_sessions
from mame_curator.filter.types import (
    ContestedGroup,
    DroppedReason,
    FilterContext,
    FilterResult,
    TiebreakerHit,
)

__all__ = [
    "ConfigError",
    "ContestedGroup",
    "DroppedReason",
    "FilterConfig",
    "FilterContext",
    "FilterError",
    "FilterResult",
    "Overrides",
    "OverridesError",
    "Region",
    "Session",
    "Sessions",
    "SessionsError",
    "TiebreakerHit",
    "explain_pick",
    "load_overrides",
    "load_sessions",
    "pick_winner",
    "region_of",
    "revision_key_of",
    "run_filter",
]

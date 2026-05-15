"""Games / metadata wire-models — extracted from schemas.py by DS02 A5.

Re-exported from ``mame_curator.api.schemas`` so existing
``from mame_curator.api.schemas import GameCard, Badge, ...`` callers keep
working unchanged.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from mame_curator.filter.types import TiebreakerHit
from mame_curator.parser.models import Machine


class Badge(StrEnum):
    CONTESTED = "contested"
    OVERRIDDEN = "overridden"
    CHD_MISSING = "chd_missing"
    BIOS_MISSING = "bios_missing"
    HAS_NOTES = "has_notes"


class GameCard(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    short_name: str
    description: str
    year: int | None
    manufacturer: str | None
    publisher: str | None
    developer: str | None
    badges: tuple[Badge, ...]


class GamesPage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[GameCard, ...]
    page: int
    page_size: int
    total: int
    total_bytes: int


class ValidateRequest(BaseModel):
    """FP24-F: bounded to cap user-controlled memory pressure.

    10,000 items matches the frontend cart's MAX_CART_SIZE; the 64-char
    per-item cap sits comfortably above real MAME shortnames (max ~24)
    without admitting pathological input.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    short_names: Annotated[
        tuple[Annotated[str, Field(max_length=64)], ...],
        Field(max_length=10_000),
    ]


class ValidateResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    existing: tuple[str, ...]
    missing: tuple[str, ...]


class GameDetail(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    short_name: str
    machine: Machine
    category: str | None
    languages: tuple[str, ...]
    bestgames_tier: str | None
    mature: bool
    chd_required: bool
    badges: tuple[Badge, ...]
    override: str | None
    parent: str


class Alternatives(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[GameCard, ...]


class Explanation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    short_name: str
    parent: str
    candidates: tuple[str, ...]
    hits: tuple[TiebreakerHit, ...]


class Notes(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    notes: str = Field(max_length=4096)


class Stats(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    by_genre: dict[str, int]
    by_decade: dict[str, int]
    by_publisher: dict[str, int]
    by_driver_status: dict[str, int]
    total_bytes: int


class LibraryFacets(BaseModel):
    """Discrete facet values for FiltersSidebar dropdowns (FP17).

    Each list is sorted ascending and deduped. ``letters`` covers the
    first-character bucket of every winner's description; ``'#'`` is
    used for digit-prefixed games.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    genres: tuple[str, ...]
    publishers: tuple[str, ...]
    developers: tuple[str, ...]
    letters: tuple[str, ...]

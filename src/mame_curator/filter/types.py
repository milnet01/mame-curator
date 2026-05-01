"""Result types for the filter rule chain."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DroppedReason(StrEnum):
    """Why a machine was dropped in Phase A.

    Order matches the spec's drop-rule ordering. The first rule to match wins.
    """

    BIOS = "bios"
    DEVICE = "device"
    MECHANICAL = "mechanical"
    CATEGORY = "category"
    MATURE = "mature"
    JAPANESE_ONLY = "japanese_only"
    PRELIMINARY_DRIVER = "preliminary_driver"
    CHD_REQUIRED = "chd_required"
    GENRE = "genre"
    PUBLISHER = "publisher"
    DEVELOPER = "developer"
    YEAR_BEFORE = "year_before"
    YEAR_AFTER = "year_after"


class TiebreakerHit(BaseModel):
    """One step in the picker chain that influenced the winner."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    detail: str


class ContestedGroup(BaseModel):
    """A parent/clone group with >=2 Phase-A survivors; records how the winner was chosen."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    parent: str
    candidates: tuple[str, ...]
    winner: str
    chain: tuple[TiebreakerHit, ...]


class FilterResult(BaseModel):
    """Output of `run_filter`. Frozen and deterministic for a given input."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    winners: tuple[str, ...]
    dropped: tuple[tuple[str, DroppedReason], ...]
    contested_groups: tuple[ContestedGroup, ...]
    warnings: tuple[str, ...] = ()


class FilterContext(BaseModel):
    """INI-augmented per-machine context consumed by Phase A predicates."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    category: dict[str, str] = Field(default_factory=dict)
    languages: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    mature: frozenset[str] = Field(default_factory=frozenset)
    chd_required: frozenset[str] = Field(default_factory=frozenset)
    cloneof_map: dict[str, str] = Field(default_factory=dict)
    bestgames_tier: dict[str, str] = Field(default_factory=dict)

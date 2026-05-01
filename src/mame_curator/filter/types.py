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
    """INI-augmented per-machine context consumed by Phase A predicates.

    The dict-shaped fields below (`category`, `languages`, `cloneof_map`,
    `bestgames_tier`) are owner-mutable Python dicts: Pydantic's
    `frozen=True` freezes field rebinding on the model, NOT the contained
    dicts' internal state. By convention, every `filter/` consumer treats
    these fields as read-only — no `result.category["x"] = "y"` mutations
    anywhere in the codebase. A future fix-pass may migrate to
    `MappingProxyType` views for runtime enforcement; the migration was
    deferred from FP05 because Pydantic v2 round-trip serialisation
    (`model_dump_json` → `model_validate`) needs an explicit `BeforeValidator`
    *and* `PlainSerializer` pair to round-trip MappingProxyType cleanly.
    Until that lands, callers honour the convention.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # FP05 B6: convention is read-only despite dict type. See class docstring.
    category: dict[str, str] = Field(default_factory=dict)
    languages: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    mature: frozenset[str] = Field(default_factory=frozenset)
    chd_required: frozenset[str] = Field(default_factory=frozenset)
    # FP05 B6: convention is read-only despite dict type. See class docstring.
    cloneof_map: dict[str, str] = Field(default_factory=dict)
    # FP05 B6: convention is read-only despite dict type. See class docstring.
    bestgames_tier: dict[str, str] = Field(default_factory=dict)

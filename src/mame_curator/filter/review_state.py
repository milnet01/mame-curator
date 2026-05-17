"""Schema + loader for state.yaml (P14 — per-game review state)."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from mame_curator.filter._io import read_capped_text
from mame_curator.filter.errors import ReviewStateError


class ReviewStateValue(StrEnum):
    """Storage values — what ``state.yaml`` ever holds.

    ``pending`` is the sparse-store default and is intentionally absent:
    a game in pending state has NO entry in ``state.yaml``.
    """

    REVIEWED = "reviewed"
    SKIPPED = "skipped"
    NEEDS_DECISION = "needs-decision"


class ReviewStateFilter(StrEnum):
    """Query-parameter values for ``?review_state=``.

    Distinct from :class:`ReviewStateValue` — the filter accepts two
    sentinel values (``all``, ``pending``) that never appear on disk.
    """

    ALL = "all"
    PENDING = "pending"
    REVIEWED = "reviewed"
    SKIPPED = "skipped"
    NEEDS_DECISION = "needs-decision"


class ReviewState(BaseModel):
    """Per-game review state. Frozen; mutations create a new instance.

    Mirrors :class:`Overrides`: the dict field is named ``entries`` in
    code but serialises under the top-level YAML key ``state`` via the
    Pydantic alias.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    entries: dict[str, ReviewStateValue] = Field(default_factory=dict, alias="state")


def load_review_state(path: Path) -> ReviewState:
    """Read and validate ``state.yaml``. Missing file → empty ReviewState."""
    if not path.exists():
        return ReviewState()
    text = read_capped_text(path, exc_cls=ReviewStateError)
    try:
        raw: Any = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        # FP06 B3: quote user-controlled paths via repr().
        raise ReviewStateError(f"failed to parse {path!r}: {exc}") from exc
    # Empty file / YAML `null` at top level → empty ReviewState (matches
    # the missing-file case).
    if raw is None:
        return ReviewState()
    if not isinstance(raw, dict):
        raise ReviewStateError(f"{path!r} is not a YAML mapping")
    try:
        return ReviewState.model_validate(raw)
    except ValidationError as exc:
        raise ReviewStateError(f"{path!r} failed schema validation: {exc}") from exc

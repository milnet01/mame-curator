"""Schema + loader for state.yaml (P14 — per-game review state)."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from mame_curator.filter._io import read_yaml_mapping
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
    """Read and validate ``state.yaml``. Missing, empty or ``null`` → empty ReviewState."""
    raw = read_yaml_mapping(path, exc_cls=ReviewStateError)
    if raw is None:
        return ReviewState()
    # mame-curator-1236: an empty `state:` section is no state.
    if "state" in raw and raw["state"] is None:
        raw = {**raw, "state": {}}
    try:
        return ReviewState.model_validate(raw)
    except ValidationError as exc:
        raise ReviewStateError(f"{path!r} failed schema validation: {exc}") from exc

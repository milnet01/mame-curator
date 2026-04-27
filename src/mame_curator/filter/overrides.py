"""Schema + loader for overrides.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from mame_curator.filter.errors import OverridesError


class Overrides(BaseModel):
    """User-supplied parent → winner short-name pinning.

    Loaded from `overrides.yaml`; missing file is treated as no overrides.
    Single winner per parent (multi-winner is a post-v1 enhancement).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    entries: dict[str, str] = Field(default_factory=dict, alias="overrides")


def load_overrides(path: Path) -> Overrides:
    """Read and validate `overrides.yaml`. Missing file → empty Overrides."""
    if not path.exists():
        return Overrides()
    try:
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise OverridesError(f"failed to parse {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise OverridesError(f"{path} is not a YAML mapping")
    try:
        return Overrides.model_validate(raw)
    except ValidationError as exc:
        raise OverridesError(f"{path} failed schema validation: {exc}") from exc

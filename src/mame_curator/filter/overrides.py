"""Schema + loader for overrides.yaml."""

from __future__ import annotations

import logging
from collections.abc import Container, Mapping
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from mame_curator.filter._io import read_capped_text
from mame_curator.filter.errors import OverridesError

logger = logging.getLogger(__name__)


class Overrides(BaseModel):
    """User-supplied parent → winner short-name pinning.

    Loaded from `overrides.yaml`; missing file is treated as no overrides.
    Single winner per parent (multi-winner is a post-v1 enhancement).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    entries: dict[str, str] = Field(default_factory=dict, alias="overrides")


def migrate_clone_keys(
    overrides: Overrides, cloneof_map: Mapping[str, str], known: Container[str]
) -> Overrides:
    """Read entries an earlier release keyed by a clone as the user's choice.

    Those releases saved the game on show as the key, and Phase C ignores a key
    that is not a group. `filter/spec.md` § `overrides.yaml` states the rule.
    `known` is the DAT's machines; an entry that cannot be placed stays as it is.
    """

    def usable(target: str, parent: str) -> bool:
        return target in known and cloneof_map.get(target, target) == parent

    by_family: dict[str, dict[str, str]] = {}
    for key, target in overrides.entries.items():
        parent = cloneof_map.get(key)
        if parent is not None and usable(target, parent):
            by_family.setdefault(parent, {})[key] = target
    if not by_family:
        return overrides

    entries = dict(overrides.entries)
    for parent, clone_keyed in by_family.items():
        for key in clone_keyed:
            del entries[key]
        shown = entries.get(parent)
        if shown is not None and usable(shown, parent):
            choice = clone_keyed.get(shown, shown)
        else:
            choice = clone_keyed[min(clone_keyed)]
            for key in sorted(clone_keyed)[1:]:
                logger.warning(
                    "overrides.yaml: more than one old choice for %r; kept %s, dropped %s: %s",
                    parent,
                    choice,
                    key,
                    clone_keyed[key],
                )
        entries[parent] = choice
    return Overrides.model_validate({"entries": entries})


def load_overrides(path: Path) -> Overrides:
    """Read and validate `overrides.yaml`. Missing file → empty Overrides."""
    if not path.exists():
        return Overrides()
    text = read_capped_text(path, exc_cls=OverridesError)
    try:
        raw: Any = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        # FP06 B3: quote user-controlled paths via repr().
        raise OverridesError(f"failed to parse {path!r}: {exc}") from exc
    # Empty file / YAML `null` at top level → empty Overrides (matches the
    # missing-file case).
    if raw is None:
        return Overrides()
    if not isinstance(raw, dict):
        raise OverridesError(f"{path!r} is not a YAML mapping")
    try:
        return Overrides.model_validate(raw)
    except ValidationError as exc:
        raise OverridesError(f"{path!r} failed schema validation: {exc}") from exc

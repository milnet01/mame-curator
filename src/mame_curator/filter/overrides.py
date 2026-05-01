"""Schema + loader for overrides.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from mame_curator.filter.errors import OverridesError

# Defends against YAML alias-bomb DoS when P07's `setup/` ships preset
# downloads. Self-authored configs are nowhere near this size.
_MAX_YAML_BYTES = 1 * 1024 * 1024  # 1 MiB


class Overrides(BaseModel):
    """User-supplied parent → winner short-name pinning.

    Loaded from `overrides.yaml`; missing file is treated as no overrides.
    Single winner per parent (multi-winner is a post-v1 enhancement).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    entries: dict[str, str] = Field(default_factory=dict, alias="overrides")


def _read_yaml_text(path: Path) -> str:
    """Read `path` as UTF-8 text, enforcing the 1 MiB cap and wrapping `OSError`.

    OSError is raised by `read_text` on directories, EIO, perm-denied, NFS
    hiccups; the bare-OSError escape was a TOCTOU finding from the pre-P03
    indie-review (DS01 C5). The size cap (DS01 C3) defends against alias-bombs.
    """
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise OverridesError(f"failed to stat {path}: {exc}") from exc
    if size > _MAX_YAML_BYTES:
        raise OverridesError(
            f"{path} exceeds {_MAX_YAML_BYTES}-byte cap "
            f"(actual: {size}); refusing to parse to defend against YAML alias bombs"
        )
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise OverridesError(f"failed to read {path}: {exc}") from exc


def load_overrides(path: Path) -> Overrides:
    """Read and validate `overrides.yaml`. Missing file → empty Overrides."""
    if not path.exists():
        return Overrides()
    text = _read_yaml_text(path)
    try:
        raw: Any = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise OverridesError(f"failed to parse {path}: {exc}") from exc
    # Empty file / YAML `null` at top level → empty Overrides (matches the
    # missing-file case).
    if raw is None:
        return Overrides()
    if not isinstance(raw, dict):
        raise OverridesError(f"{path} is not a YAML mapping")
    try:
        return Overrides.model_validate(raw)
    except ValidationError as exc:
        raise OverridesError(f"{path} failed schema validation: {exc}") from exc

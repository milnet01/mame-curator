"""WorldState — frozen blob of parsed-data + filter-result on ``app.state.world``.

Per ``docs/specs/P04.md`` § Lifespan + ``app.state`` model.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from mame_curator.api.errors import ConfigError
from mame_curator.api.fs import compose_allowlist
from mame_curator.api.schemas import AppConfig, FsAllowedRoot
from mame_curator.filter import (
    FilterContext,
    FilterResult,
    Overrides,
    Sessions,
    load_overrides,
    load_sessions,
    run_filter,
)
from mame_curator.parser import (
    Machine,
    parse_bestgames,
    parse_catver,
    parse_dat,
    parse_languages,
    parse_mature,
    parse_series,
)
from mame_curator.parser.listxml import (
    BIOSChainEntry,
    parse_listxml_bios_chain,
    parse_listxml_cloneof,
    parse_listxml_disks,
)

logger = logging.getLogger(__name__)


class WorldState(BaseModel):
    """Frozen snapshot of all parsed state. Swapped wholesale on writes."""

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    config_path: Path
    config: AppConfig
    machines: dict[str, Machine]
    cloneof_map: dict[str, str]
    bios_chain: dict[str, BIOSChainEntry]
    chd_required: frozenset[str]
    ctx: FilterContext
    overrides: Overrides
    sessions: Sessions
    filter_result: FilterResult
    notes: dict[str, str]
    allowed_roots: tuple[FsAllowedRoot, ...]
    data_dir: Path


def load_app_config(config_path: Path) -> AppConfig:
    """Read and validate ``config.yaml`` from disk."""
    if not config_path.exists():
        raise ConfigError(f"config file does not exist: {str(config_path)!r}")
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        # FP09 A1: repr-quote `exc` so a multi-line YAML error message can't
        # break the FP06-FP08 single-line `detail` invariant.
        raise ConfigError(f"failed to parse {str(config_path)!r}: {exc!r}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"{str(config_path)!r} must be a YAML mapping")
    try:
        return AppConfig.model_validate(raw)
    except ValidationError as exc:
        from mame_curator.api.errors import field_errors_from_pydantic

        # FP09 A1: repr-quote `exc` (Pydantic ValidationError str is multi-line).
        raise ConfigError(
            f"config validation failed: {exc!r}",
            fields=field_errors_from_pydantic(exc.errors()),
        ) from exc


def build_world(config_path: Path) -> WorldState:
    """Parse all inputs and assemble a WorldState. Called from lifespan startup."""
    config = load_app_config(config_path)
    paths = config.paths

    machines = parse_dat(paths.source_dat)

    # Reference data (each optional in config; missing → empty default).
    category = parse_catver(paths.catver) if paths.catver else {}
    languages_raw = parse_languages(paths.languages) if paths.languages else {}
    languages = {k: tuple(v) for k, v in languages_raw.items()}
    bestgames = parse_bestgames(paths.bestgames) if paths.bestgames else {}
    mature = frozenset(parse_mature(paths.mature)) if paths.mature else frozenset()
    if paths.series:
        # parse_series result not needed by FilterContext but call to validate file.
        parse_series(paths.series)

    if paths.listxml:
        cloneof_map = parse_listxml_cloneof(paths.listxml)
        bios_chain = parse_listxml_bios_chain(paths.listxml)
        chd_required: frozenset[str] = frozenset(parse_listxml_disks(paths.listxml))
    else:
        cloneof_map = {}
        bios_chain = {}
        chd_required = frozenset()

    ctx = FilterContext(
        category=category,
        languages=languages,
        mature=mature,
        chd_required=chd_required,
        cloneof_map=cloneof_map,
        bestgames_tier=bestgames,
    )

    overrides = load_overrides(config_path.parent / "overrides.yaml")
    sessions = load_sessions(config_path.parent / "sessions.yaml")

    data_dir = config_path.parent / "data"
    notes = _load_notes(data_dir / "notes.json")

    filter_result = run_filter(machines, ctx, config.filters, overrides, sessions)

    allowed_roots = compose_allowlist(config)

    return WorldState(
        config_path=config_path,
        config=config,
        machines=machines,
        cloneof_map=cloneof_map,
        bios_chain=bios_chain,
        chd_required=chd_required,
        ctx=ctx,
        overrides=overrides,
        sessions=sessions,
        filter_result=filter_result,
        notes=notes,
        allowed_roots=allowed_roots,
        data_dir=data_dir,
    )


def _load_notes(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.exception("failed to read notes file %r", str(path))
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items()}


def replace_world(
    *,
    base: WorldState,
    config: AppConfig | None = None,
    overrides: Overrides | None = None,
    sessions: Sessions | None = None,
    notes: Mapping[str, str] | None = None,
    rerun_filter: bool = False,
) -> WorldState:
    """Build a new WorldState from ``base`` with the given mutations applied.

    Recomputes ``filter_result`` and ``allowed_roots`` per the spec's
    re-computation triggers.
    """
    new_config = config if config is not None else base.config
    new_overrides = overrides if overrides is not None else base.overrides
    new_sessions = sessions if sessions is not None else base.sessions
    new_notes = dict(notes) if notes is not None else dict(base.notes)

    if rerun_filter or config is not None or overrides is not None or sessions is not None:
        filter_result = run_filter(
            base.machines, base.ctx, new_config.filters, new_overrides, new_sessions
        )
    else:
        filter_result = base.filter_result

    # FP09 B6: re-resolve allowlist only when config (the one input) changed.
    # Notes-only / sessions-only swaps preserve the prior tuple identity so
    # the no-op-PATCH idempotency contract (P01) holds end-to-end.
    #
    # FP09 Cluster R H2 — load-bearing invariant: `compose_allowlist` is a
    # PURE FUNCTION of `config.paths` + `config.fs.granted_roots`. If a
    # future refactor lets sessions / notes / overrides affect allowlist
    # composition (e.g. session-scoped path grants), DROP THIS SHORT-CIRCUIT
    # — silently eliding the recompute would break sandbox correctness.
    allowed_roots = compose_allowlist(new_config) if config is not None else base.allowed_roots

    return WorldState(
        config_path=base.config_path,
        config=new_config,
        machines=base.machines,
        cloneof_map=base.cloneof_map,
        bios_chain=base.bios_chain,
        chd_required=base.chd_required,
        ctx=base.ctx,
        overrides=new_overrides,
        sessions=new_sessions,
        filter_result=filter_result,
        notes=new_notes,
        allowed_roots=allowed_roots,
        data_dir=base.data_dir,
    )


def deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """Recursive merge: scalars/lists replace; nested dicts merge."""
    out = dict(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def filter_relevant_changed(old: AppConfig, new: AppConfig) -> bool:
    """Return True iff a filter recompute is required."""
    return old.filters != new.filters

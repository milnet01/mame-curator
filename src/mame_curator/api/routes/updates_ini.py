"""INI refresh with a preview (mame-curator-1010 §4.6).

Preview downloads the INI files into ``data/ini-staging/`` and reports how
the library's winners would change; apply moves exactly what was previewed
onto the configured paths. Neither step runs without the other's consent:
apply refuses without a staged preview.
"""

from __future__ import annotations

import asyncio
import hashlib
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml
from fastapi import APIRouter, Request

from mame_curator._atomic import atomic_write_bytes
from mame_curator.api.persist import snapshot_files, write_yaml_atomic
from mame_curator.api.routes._deps import set_world
from mame_curator.api.schemas import IniPreview
from mame_curator.api.state import (
    WorldState,
    ini_context_fields,
    load_app_config,
    replace_world,
)
from mame_curator.copy.activity import append_activity
from mame_curator.copy.types import ActivityEvent, ActivityEventType, IniRefreshedDetails
from mame_curator.filter import FilterContext, run_filter
from mame_curator.parser import ParserError
from mame_curator.updates.app import UpdateError
from mame_curator.updates.ini import INI_CONFIG_FIELDS, refresh_inis

router = APIRouter()


@dataclass(frozen=True)
class _Staged:
    changed: tuple[str, ...]
    ctx: FilterContext
    preview: IniPreview


def _live_paths(world: WorldState) -> dict[str, Path | None]:
    return {name: getattr(world.config.paths, field) for name, field in INI_CONFIG_FIELDS.items()}


def _differs(staged: Path, live: Path | None) -> bool:
    return live is None or not live.exists() or live.read_bytes() != staged.read_bytes()


def _sha(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


@router.post("/api/updates/ini/preview", response_model=IniPreview)
async def ini_preview(request: Request) -> IniPreview:
    """Stage fresh INI files and report the winners they would add and remove."""
    state = request.app.state
    world: WorldState = state.world
    staging = world.data_dir / "ini-staging"
    shutil.rmtree(staging, ignore_errors=True)
    report = await refresh_inis(
        dest_dir=staging, client=state.updates_client, sources=state.ini_sources
    )

    live = _live_paths(world)
    failed = list(report.failed)
    changed = tuple(sorted(n for n in report.updated if _differs(staging / n, live.get(n))))
    effective = {n: (staging / n if n in changed else live.get(n)) for n in INI_CONFIG_FIELDS}
    try:
        fields = ini_context_fields(
            **{INI_CONFIG_FIELDS[name]: path for name, path in effective.items()}
        )
    except ParserError as e:
        shutil.rmtree(staging, ignore_errors=True)
        raise UpdateError("ini_parse_failed", 502, f"a downloaded INI did not parse: {e}") from e
    new_ctx = world.ctx.model_copy(update=fields)
    result = await asyncio.to_thread(
        run_filter, world.machines, new_ctx, world.config.filters, world.overrides, world.sessions
    )
    before, after = set(world.filter_result.winners), set(result.winners)
    preview = IniPreview(
        changed_files=changed,
        failed=tuple(failed),
        winners_added=tuple(sorted(after - before)),
        winners_removed=tuple(sorted(before - after)),
    )
    state.ini_staged = _Staged(changed=changed, ctx=new_ctx, preview=preview)
    return preview


def _patch_config_paths(config_path: Path, new_paths: dict[str, Path]) -> None:
    """Point each unset ``paths.<field>`` at its new file, as the CLI does."""
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    paths = data.setdefault("paths", {})
    for field, path in new_paths.items():
        paths[field] = str(path)
    write_yaml_atomic(config_path, data)


@router.post("/api/updates/ini/apply", response_model=IniPreview)
async def ini_apply(request: Request) -> IniPreview:
    """Move the previewed files into place and swap the world to match."""
    state = request.app.state
    staged: _Staged | None = state.ini_staged
    if staged is None:
        raise UpdateError("ini_preview_missing", 409, "preview the INI refresh first")
    async with state.world_lock:
        world: WorldState = state.world
        staging = world.data_dir / "ini-staging"
        live = _live_paths(world)
        targets = {n: live[n] or world.data_dir / "ini" / n for n in staged.changed}
        snapshot_files(
            world.data_dir / "ini-snapshots",
            {n: p for n, p in targets.items() if live[n] is not None},
        )
        old_sha = {n: _sha(live[n]) for n in staged.changed}
        for name, target in targets.items():
            atomic_write_bytes(target, (staging / name).read_bytes())
        unset = {INI_CONFIG_FIELDS[n]: targets[n] for n in staged.changed if live[n] is None}
        new_config = None
        if unset:
            _patch_config_paths(world.config_path, unset)
            new_config = load_app_config(world.config_path)
        new_world = replace_world(base=world, config=new_config, ctx=staged.ctx, rerun_filter=True)
        set_world(request, new_world)
        for name in staged.changed:
            append_activity(
                ActivityEvent(
                    timestamp=datetime.now(UTC),
                    event_type=ActivityEventType.INI_REFRESHED,
                    summary=f"refreshed {name}",
                    session_id="",
                    details=IniRefreshedDetails(
                        ini_name=name, sha256_old=old_sha[name], sha256_new=_sha(targets[name])
                    ),
                ),
                log_path=world.data_dir / "activity.jsonl",
            )
        state.ini_staged = None
        shutil.rmtree(staging, ignore_errors=True)
        return staged.preview

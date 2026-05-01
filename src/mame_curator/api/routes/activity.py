"""R28 — paginated activity log."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query

from mame_curator.api.routes._deps import get_world
from mame_curator.api.schemas import ActivityPage
from mame_curator.api.state import WorldState

router = APIRouter()


@router.get("/api/activity", response_model=ActivityPage)
def get_activity(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    event_type: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    world: WorldState = Depends(get_world),
) -> ActivityPage:
    log_path = world.data_dir / "activity.jsonl"
    if not log_path.exists():
        return ActivityPage(items=(), page=page, page_size=page_size, total=0)

    items: list[dict[str, Any]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event_type and obj.get("event_type") != event_type:
            continue
        if since is not None or until is not None:
            ts_raw = obj.get("timestamp")
            ts = _parse_ts(ts_raw)
            if ts is None:
                continue
            if since is not None and ts < since:
                continue
            if until is not None and ts > until:
                continue
        items.append(obj)

    items.reverse()  # newest first
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return ActivityPage(
        items=tuple(items[start:end]),
        page=page,
        page_size=page_size,
        total=total,
    )


def _parse_ts(raw: Any) -> datetime | None:
    if not isinstance(raw, str):
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None

"""R28 — paginated activity log; mame-curator-1199 — a copy's skipped names."""

from __future__ import annotations

import json
import re
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Query

from mame_curator.api.errors import CopyReportCorruptError, JobNotFoundError
from mame_curator.api.routes._deps import get_world
from mame_curator.api.schemas import ActivityPage
from mame_curator.api.schemas_copy import CopyName, CopyNames
from mame_curator.api.state import WorldState
from mame_curator.copy.types import CopyOutcome, CopyReport

# A report names its copy session first; reading this much finds it without
# parsing every report in the history (each lists every file it copied).
_REPORT_HEAD_BYTES = 4096

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
    since = _as_utc(since)
    until = _as_utc(until)
    if not log_path.exists():
        return ActivityPage(items=(), page=page, page_size=page_size, total=0)

    # FP27 B5: stream the file line-by-line and keep only the newest
    # `page * page_size` matches in a bounded deque. Pre-fix the whole
    # file landed in RAM via `read_text().splitlines()` then pagination
    # sliced afterwards — request RAM scaled with the file regardless
    # of which page was asked for. Post-fix: per-request RAM is
    # `page * page_size * event_size` for the deque, independent of
    # total log size.
    window = deque[dict[str, Any]](maxlen=page * page_size)
    total = 0
    with log_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
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
            total += 1
            window.append(obj)

    # `window` holds the newest `page * page_size` matches in file order
    # (chronological). Reverse for newest-first, then slice to page N.
    newest_first = list(reversed(window))
    start = (page - 1) * page_size
    end = start + page_size
    return ActivityPage(
        items=tuple(newest_first[start:end]),
        page=page,
        page_size=page_size,
        total=total,
    )


def _as_utc(dt: datetime | None) -> datetime | None:
    """Read a timezone-less query bound as UTC so it compares with log stamps."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _parse_ts(raw: Any) -> datetime | None:
    if not isinstance(raw, str):
        return None
    try:
        return _as_utc(datetime.fromisoformat(raw.replace("Z", "+00:00")))
    except ValueError:
        return None


@router.get("/api/activity/copy/{session_id}/names", response_model=CopyNames)
def get_copy_names(session_id: str, world: WorldState = Depends(get_world)) -> CopyNames:
    """The games a copy skipped or failed, from its ``report.json``.

    An Activity entry carries the copy's ``session_id``; its report sits under
    the job's id, so the report is found by the session id it holds.
    """
    path = _find_report(world.data_dir / "copy-history", session_id)
    if path is None:
        raise JobNotFoundError(f"no copy report for session {session_id!r}")
    try:
        report = CopyReport.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CopyReportCorruptError(f"copy report unreadable: {session_id!r}: {exc!r}") from exc
    return CopyNames(skipped=_names(report.skipped), failed=_names(report.failed))


def _find_report(history: Path, session_id: str) -> Path | None:
    pattern = re.compile(rf'"session_id"\s*:\s*"{re.escape(session_id)}"')
    if not history.is_dir():
        return None
    for child in sorted(history.iterdir(), reverse=True):
        path = child / "report.json"
        try:
            with path.open("r", encoding="utf-8", errors="replace") as fh:
                head = fh.read(_REPORT_HEAD_BYTES)
        except OSError:
            continue
        if pattern.search(head):
            return path
    return None


def _names(outcomes: tuple[CopyOutcome, ...]) -> tuple[CopyName, ...]:
    return tuple(
        CopyName(short_name=o.short_name, role=o.role, status=o.status, error=o.error)
        for o in outcomes
    )

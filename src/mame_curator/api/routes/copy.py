"""R20-R27 — dry-run, start, pause/resume/abort, SSE status, history."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sse_starlette.sse import EventSourceResponse

from mame_curator.api.errors import CopyReportCorruptError, JobNotFoundError
from mame_curator.api.jobs import JobManager, check_playlist_conflict
from mame_curator.api.routes._deps import get_jobs, get_world
from mame_curator.api.schemas import (
    CopyAbortRequest,
    CopyJobRequest,
    DryRunReport,
    HistoryItem,
    HistoryListing,
    JobAccepted,
    JobStatus,
)
from mame_curator.api.state import WorldState
from mame_curator.copy import (
    CopyPlan,
    CopyReport,
    preflight,
    resolve_bios_dependencies,
)

router = APIRouter()


def _build_plan(body: CopyJobRequest, world: WorldState) -> CopyPlan:
    machines = {
        short: world.machines[short] for short in body.selected_names if short in world.machines
    }
    return CopyPlan(
        winners=body.selected_names,
        machines=machines,
        bios_chain=dict(world.bios_chain),
        chd_required=world.chd_required,
        source_dir=world.config.paths.source_roms,
        dest_dir=world.config.paths.dest_roms,
        conflict_strategy=body.conflict_strategy,
        append_decisions=dict(body.append_decisions),
    )


@router.post("/api/copy/dry-run", response_model=DryRunReport)
def dry_run(
    body: CopyJobRequest,
    world: WorldState = Depends(get_world),
) -> DryRunReport:
    plan = _build_plan(body, world)
    pre = preflight(plan)
    bios_set, _warnings = resolve_bios_dependencies(plan.winners, dict(world.bios_chain))
    counts = {
        "selected": len(plan.winners),
        "bios": len(bios_set),
        "missing_source": len(pre.missing_source),
        "already_copied": len(pre.already_copied),
        "new": len(plan.winners) - len(pre.already_copied) - len(pre.missing_source),
    }
    summary = {
        "dest_writable": pre.dest_writable,
        "free_space_gap_bytes": pre.free_space_gap_bytes,
        "existing_playlist": pre.existing_playlist,
    }
    return DryRunReport(counts=counts, summary=summary)


@router.post("/api/copy/start", response_model=JobAccepted)
async def start_copy(
    body: CopyJobRequest,
    world: WorldState = Depends(get_world),
    jobs: JobManager = Depends(get_jobs),
) -> JobAccepted:
    plan = _build_plan(body, world)
    check_playlist_conflict(plan)
    job = await jobs.start(plan, world)
    return JobAccepted(job_id=job.id)


@router.post("/api/copy/pause", response_model=JobStatus)
async def pause_copy(jobs: JobManager = Depends(get_jobs)) -> JobStatus:
    return await jobs.pause()


@router.post("/api/copy/resume", response_model=JobStatus)
async def resume_copy(jobs: JobManager = Depends(get_jobs)) -> JobStatus:
    return await jobs.resume()


@router.post("/api/copy/abort", response_model=JobStatus)
async def abort_copy(body: CopyAbortRequest, jobs: JobManager = Depends(get_jobs)) -> JobStatus:
    return await jobs.abort(recycle_partial=body.recycle_partial)


@router.get("/api/copy/status")
async def copy_status(jobs: JobManager = Depends(get_jobs)) -> EventSourceResponse:
    if jobs.current is None:
        raise JobNotFoundError("no active copy job")

    async def event_stream() -> Any:
        async for ev in jobs.events():
            yield {"data": ev.model_dump_json()}

    return EventSourceResponse(event_stream())


@router.get("/api/copy/history", response_model=HistoryListing)
def list_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    world: WorldState = Depends(get_world),
) -> HistoryListing:
    base = world.data_dir / "copy-history"
    items: list[HistoryItem] = []
    if base.exists():
        for child in sorted(base.iterdir(), reverse=True):
            report_file = child / "report.json"
            if not report_file.exists():
                continue
            try:
                report = CopyReport.model_validate_json(report_file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            items.append(
                HistoryItem(
                    job_id=child.name,
                    started_at=report.started_at,
                    finished_at=report.finished_at,
                    status=report.status,
                    succeeded=len(report.succeeded),
                    failed=len(report.failed),
                    bytes_copied=report.bytes_copied,
                )
            )
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return HistoryListing(
        items=tuple(items[start:end]),
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/api/copy/history/{job_id}/report", response_model=CopyReport)
def get_history_report(job_id: str, world: WorldState = Depends(get_world)) -> CopyReport:
    path = world.data_dir / "copy-history" / job_id / "report.json"
    if not path.exists():
        raise JobNotFoundError(f"history report not found: {job_id!r}")
    # FP09 A2: validate against the CopyReport schema on egress so a corrupt
    # or truncated report.json (manual edit, partial write) doesn't leak
    # malformed JSON to clients. Spec line 167 requires the typed response.
    # FP09 Cluster R M1: distinct error code for corrupt-but-existing reports
    # ("filesystem rot" signal) vs unknown id (404) — operators debugging at
    # 3 AM need to tell those failure modes apart.
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CopyReportCorruptError(f"history report unreadable: {job_id!r}: {exc!r}") from exc
    try:
        return CopyReport.model_validate_json(text)
    except ValueError as exc:
        raise CopyReportCorruptError(f"history report corrupt: {job_id!r}: {exc!r}") from exc

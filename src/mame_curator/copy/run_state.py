"""A copy run's running record, and the report and activity events built from it."""

from __future__ import annotations

import logging
import secrets
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from mame_curator.copy.activity import append_activity, record_copy_error, short_error_message
from mame_curator.copy.types import (
    ActivityEvent,
    ActivityEventType,
    CopyAbortedDetails,
    CopyFinishedDetails,
    CopyOutcome,
    CopyPlan,
    CopyReport,
    CopyReportStatus,
    CopyStartedDetails,
    OverwriteRecord,
    PlanSummary,
    RecycleRecord,
    ReportSummary,
)

logger = logging.getLogger(__name__)


def new_session_id() -> str:
    """A sortable, unique id for one copy run."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ-") + secrets.token_hex(4)


def make_plan_summary(plan: CopyPlan, bios_count: int) -> PlanSummary:
    """The plan facts the report and the `copy_started` event carry."""
    return PlanSummary(
        winners_count=len(plan.winners),
        bios_count=bios_count,
        conflict_strategy=plan.conflict_strategy,
        source_dir=plan.source_dir,
        dest_dir=plan.dest_dir,
    )


@dataclass
class RunState:
    """What a run has done so far, kept so a crash can still be reported.

    mame-curator-1157: the outcome lists are the run's own lists, filled in
    place, so they hold every file finished before an exception.
    """

    started_at: datetime
    session_id: str
    plan_summary: PlanSummary | None = None
    bios_set: frozenset[str] = frozenset()
    started: bool = False  # `copy_started` is in the activity log
    warnings: list[str] = field(default_factory=list)
    succeeded: list[CopyOutcome] = field(default_factory=list)
    skipped: list[CopyOutcome] = field(default_factory=list)
    failed: list[CopyOutcome] = field(default_factory=list)
    overwritten: list[OverwriteRecord] = field(default_factory=list)
    recycled: list[RecycleRecord] = field(default_factory=list)
    # Counted as files finish, so a cancel that recycles them keeps the total.
    bytes_copied: int = 0


def _by_name(outcomes: list[CopyOutcome]) -> tuple[CopyOutcome, ...]:
    return tuple(sorted(outcomes, key=lambda o: o.short_name))


def _build_report(
    plan: CopyPlan,
    state: RunState,
    plan_summary: PlanSummary,
    status: CopyReportStatus,
    finished_at: datetime,
    *,
    extra_warning: str | None = None,
) -> CopyReport:
    """The report of everything ``state`` holds; copy/spec.md § Sorting orders each tuple."""
    warnings = (*state.warnings, extra_warning) if extra_warning else tuple(state.warnings)
    return CopyReport(
        session_id=state.session_id,
        started_at=state.started_at,
        finished_at=finished_at,
        status=status,
        plan_summary=plan_summary,
        succeeded=_by_name(state.succeeded),
        skipped=_by_name(state.skipped),
        failed=_by_name(state.failed),
        overwritten=tuple(sorted(state.overwritten, key=lambda r: (r.old_short, r.new_short))),
        recycled=tuple(sorted(state.recycled, key=lambda r: str(r.original_path))),
        bios_included=tuple(sorted(state.bios_set)),
        # Winners the parser flags as needing a CHD: copied, but unplayable without it.
        chd_missing=tuple(sorted(w for w in plan.winners if w in plan.chd_required)),
        bytes_copied=state.bytes_copied,
        warnings=warnings,
    )


def log_started(
    plan: CopyPlan, state: RunState, plan_summary: PlanSummary, *, data_dir: Path
) -> None:
    """Write `copy_started` to the activity log; from here a crash is recorded."""
    append_activity(
        ActivityEvent(
            timestamp=state.started_at,
            event_type=ActivityEventType.COPY_STARTED,
            summary=f"copy started: {len(plan.winners)} winners + {len(state.bios_set)} BIOS",
            session_id=state.session_id,
            details=CopyStartedDetails(
                plan_summary=plan_summary,
                conflict_strategy=plan.conflict_strategy,
            ),
        ),
        log_path=data_dir / "activity.jsonl",
    )
    state.started = True


def record_crash(
    state: RunState,
    exc: Exception,
    *,
    plan: CopyPlan,
    data_dir: Path,
    on_crash: Callable[[CopyReport], None] | None,
) -> None:
    """Log the crash to the activity log and build its report. Never raises."""
    record_copy_error(
        exc,
        session_id=state.session_id,
        recycled_count=len(state.recycled),
        log_path=data_dir / "activity.jsonl",
    )
    if on_crash is None or state.plan_summary is None:
        return
    try:
        report = _build_report(
            plan,
            state,
            state.plan_summary,
            CopyReportStatus.ERROR,
            datetime.now(UTC),
            extra_warning=f"stopped because of an error: {short_error_message(exc)}",
        )
        on_crash(report)
    except Exception:
        logger.exception("could not hand on the report of a crashed copy")


def _aborted_event(
    state: RunState, status: CopyReportStatus, finished_at: datetime
) -> ActivityEvent:
    return ActivityEvent(
        timestamp=finished_at,
        event_type=ActivityEventType.COPY_ABORTED,
        summary=f"copy aborted: {status.value.lower()}",
        session_id=state.session_id,
        details=CopyAbortedDetails(reason=status.value, recycled_count=len(state.recycled)),
    )


def _finished_event(
    state: RunState, status: CopyReportStatus, finished_at: datetime
) -> ActivityEvent:
    return ActivityEvent(
        timestamp=finished_at,
        event_type=ActivityEventType.COPY_FINISHED,
        summary=(
            f"copy {status.value.lower()}: {len(state.succeeded)} ok, "
            f"{len(state.skipped)} skipped, {len(state.failed)} failed"
        ),
        session_id=state.session_id,
        details=CopyFinishedDetails(
            report_summary=ReportSummary(
                succeeded_count=len(state.succeeded),
                skipped_count=len(state.skipped),
                failed_count=len(state.failed),
                bytes_copied=state.bytes_copied,
            )
        ),
    )


def finish_early(
    plan: CopyPlan,
    state: RunState,
    plan_summary: PlanSummary,
    status: CopyReportStatus,
    *,
    data_dir: Path,
) -> CopyReport:
    """End a run before any file was copied: an empty report and `copy_aborted`."""
    finished_at = datetime.now(UTC)
    report = _build_report(plan, state, plan_summary, status, finished_at)
    append_activity(
        _aborted_event(state, status, finished_at), log_path=data_dir / "activity.jsonl"
    )
    return report


def finish_report(
    plan: CopyPlan,
    state: RunState,
    plan_summary: PlanSummary,
    *,
    cancelled: bool,
    data_dir: Path,
) -> CopyReport:
    """Build the run's report and log `copy_finished`, or `copy_aborted` on a cancel."""
    finished_at = datetime.now(UTC)
    if cancelled:
        status = CopyReportStatus.CANCELLED
    elif state.failed:
        status = CopyReportStatus.PARTIAL_FAILURE
    else:
        status = CopyReportStatus.OK

    report = _build_report(plan, state, plan_summary, status, finished_at)
    if status in (CopyReportStatus.OK, CopyReportStatus.PARTIAL_FAILURE):
        event = _finished_event(state, status, finished_at)
    else:
        event = _aborted_event(state, status, finished_at)
    append_activity(event, log_path=data_dir / "activity.jsonl")
    return report

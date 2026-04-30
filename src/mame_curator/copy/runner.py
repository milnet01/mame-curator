"""Top-level orchestrator: run a CopyPlan, return a CopyReport."""

from __future__ import annotations

import logging
import secrets
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from mame_curator.copy.activity import append_activity
from mame_curator.copy.bios import resolve_bios_dependencies
from mame_curator.copy.controller import CopyController
from mame_curator.copy.errors import CopyError, PlaylistError
from mame_curator.copy.executor import copy_one
from mame_curator.copy.playlist import read_lpl, write_lpl
from mame_curator.copy.preflight import preflight
from mame_curator.copy.recyclebin import recycle_file
from mame_curator.copy.types import (
    ActivityEvent,
    ActivityEventType,
    AppendDecision,
    ConflictStrategy,
    CopyAbortedDetails,
    CopyFinishedDetails,
    CopyOutcome,
    CopyOutcomeStatus,
    CopyPlan,
    CopyReport,
    CopyReportStatus,
    CopyStartedDetails,
    OverwriteRecord,
    PlanSummary,
    PlaylistEntry,
    RecycleRecord,
    ReportSummary,
)

logger = logging.getLogger(__name__)


def _new_session_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ-") + secrets.token_hex(4)


def _make_plan_summary(plan: CopyPlan, bios_count: int) -> PlanSummary:
    return PlanSummary(
        winners_count=len(plan.winners),
        bios_count=bios_count,
        conflict_strategy=plan.conflict_strategy,
        source_dir=plan.source_dir,
        dest_dir=plan.dest_dir,
    )


def _existing_basenames(items: list[dict[str, str]]) -> set[str]:
    out = set()
    for it in items:
        path = it.get("path", "")
        if path:
            out.add(Path(path).name)
    return out


def run_copy(
    plan: CopyPlan,
    *,
    controller: CopyController | None = None,
    on_progress: Callable[[str, int, int], None] | None = None,
) -> CopyReport:
    """Execute a CopyPlan; return a CopyReport. See spec.md for the full contract."""
    started_at = datetime.now(UTC)
    session_id = _new_session_id()
    ctl = controller or CopyController()

    bios_set, bios_warnings = resolve_bios_dependencies(plan.winners, plan.bios_chain)
    plan_summary = _make_plan_summary(plan, len(bios_set))

    # Activity: copy_started.
    append_activity(
        ActivityEvent(
            timestamp=started_at,
            event_type=ActivityEventType.COPY_STARTED,
            summary=f"copy started: {len(plan.winners)} winners + {len(bios_set)} BIOS",
            session_id=session_id,
            details=CopyStartedDetails(
                plan_summary=plan_summary,
                conflict_strategy=plan.conflict_strategy,
            ),
        ),
        log_path=Path("data/activity.jsonl"),
    )

    pre = preflight(plan)
    warnings: list[str] = [f"{w.name}: {w.kind}" for w in bios_warnings]

    # Playlist conflict resolution. CANCEL is a safety-rail for genuine
    # conflicts; an idempotent rerun (every winner-zip already at dest with
    # matching size+mtime, AND no extra zips at dest beyond winners + bios)
    # is not a conflict — proceed as no-op so the design § 6.4 idempotency
    # contract holds without requiring the user to specify `--conflict append`.
    if (
        pre.existing_playlist
        and not plan.dry_run
        and plan.conflict_strategy is ConflictStrategy.CANCEL
    ):
        all_winners_idempotent = set(pre.already_copied) >= set(plan.winners)
        if not all_winners_idempotent:
            return _finalize(
                plan=plan,
                started_at=started_at,
                session_id=session_id,
                status=CopyReportStatus.CANCELLED_PLAYLIST_CONFLICT,
                plan_summary=plan_summary,
                bios_set=bios_set,
                warnings=warnings,
            )

    succeeded: list[CopyOutcome] = []
    skipped: list[CopyOutcome] = []
    failed: list[CopyOutcome] = []
    overwritten: list[OverwriteRecord] = []
    recycled: list[RecycleRecord] = []
    bytes_copied = 0

    # Build the file list: winners first (preserves "winner" role), then BIOS.
    # Typed as Literal so CopyOutcome.role narrows without `# type: ignore`.
    work: list[tuple[str, Literal["winner", "bios"]]] = [
        (w, "winner") for w in sorted(plan.winners)
    ]
    work += [(b, "bios") for b in sorted(bios_set)]

    # Read existing playlist items if APPEND.
    # A failed read (corrupt or legacy 6-line format per spec § "read_lpl
    # input scope") falls back to empty-but-warns rather than silently
    # discarding the user's old playlist; the warning surfaces in
    # CopyReport.warnings and is logged.
    existing_items: list[dict[str, str]] = []
    if pre.existing_playlist and plan.conflict_strategy is ConflictStrategy.APPEND:
        try:
            existing_items = read_lpl(plan.dest_dir / "mame.lpl")
        except PlaylistError as exc:
            warnings.append(f"existing playlist could not be parsed (will be overwritten): {exc}")
            logger.warning("playlist parse failed; existing entries discarded: %s", exc)

    existing_basenames = _existing_basenames(existing_items)

    # Cancellation check before any work.
    if ctl.should_cancel():
        return _finalize(
            plan=plan,
            started_at=started_at,
            session_id=session_id,
            status=CopyReportStatus.CANCELLED,
            plan_summary=plan_summary,
            bios_set=bios_set,
            warnings=warnings,
            recycled=tuple(recycled),
        )

    for short, role in work:
        # Pause boundary.
        ctl.wait_if_paused()
        if ctl.should_cancel():
            break

        src = plan.source_dir / f"{short}.zip"
        dst = plan.dest_dir / f"{short}.zip"

        if not src.exists():
            skipped.append(
                CopyOutcome(
                    short_name=short,
                    role=role,
                    status=CopyOutcomeStatus.SKIPPED_MISSING_SOURCE,
                    src=src,
                    dst=dst,
                )
            )
            continue

        # APPEND + cross-version conflict handling.
        # The caller (CLI / API) pre-detects same-parent-group conflicts using
        # its cloneof_map and supplies one entry per conflict in
        # plan.append_decisions. Presence of `short` in the map IS the
        # conflict signal here — the runner does not re-derive it (no
        # cloneof_map at this layer; see spec § "Playlist conflict resolution").
        # Absent: the winner is added alongside existing entries.
        if (
            role == "winner"
            and plan.conflict_strategy is ConflictStrategy.APPEND
            and short in plan.append_decisions
        ):
            decision = plan.append_decisions[short]
            if decision is AppendDecision.KEEP_EXISTING:
                skipped.append(
                    CopyOutcome(
                        short_name=short,
                        role=role,
                        status=CopyOutcomeStatus.SKIPPED_EXISTING_VERSION,
                        src=src,
                        dst=dst,
                    )
                )
                continue
            # REPLACE / REPLACE_AND_RECYCLE: identify which existing winner zip
            # this replaces (any same-parent existing entry — for the simple
            # case the playlist has one entry per parent group). Record an
            # OverwriteRecord so the report is complete.
            replaced_short: str | None = None
            for it in existing_items:
                ipath = Path(it.get("path", ""))
                # We don't have the cloneof_map here, so the only signal of
                # "same parent" is sharing a filename root: existing_basenames
                # contains every existing zip; treat any one whose stem isn't
                # also a winner as the replaced entry. This is a heuristic that
                # works for the v1 design (single winner per parent group).
                if ipath.stem not in plan.winners and ipath.name in existing_basenames:
                    replaced_short = ipath.stem
                    break
            if replaced_short is not None:
                overwritten.append(
                    OverwriteRecord(
                        parent=replaced_short,
                        old_short=replaced_short,
                        new_short=short,
                    )
                )
                if decision is AppendDecision.REPLACE_AND_RECYCLE:
                    old_zip = plan.dest_dir / f"{replaced_short}.zip"
                    if old_zip.exists():
                        try:
                            new_path = recycle_file(
                                old_zip,
                                reason="REPLACE_AND_RECYCLE",
                                session_id=session_id,
                            )
                            recycled.append(
                                RecycleRecord(
                                    original_path=old_zip,
                                    recycled_path=new_path,
                                    reason="REPLACE_AND_RECYCLE",
                                )
                            )
                        except CopyError as exc:
                            warnings.append(f"recycle of {old_zip.name} failed: {exc}")

        if plan.dry_run:
            # Pretend success without writing.
            succeeded.append(
                CopyOutcome(
                    short_name=short,
                    role=role,
                    status=CopyOutcomeStatus.SUCCEEDED,
                    src=src,
                    dst=dst,
                    bytes=src.stat().st_size,
                )
            )
            bytes_copied += src.stat().st_size
            if on_progress is not None:
                on_progress(short, src.stat().st_size, src.stat().st_size)
            continue

        per_file_progress: Callable[[int, int], None] | None = None
        if on_progress is not None:

            def make_cb(name: str) -> Callable[[int, int], None]:
                def cb(done: int, total: int) -> None:
                    on_progress(name, done, total)

                return cb

            per_file_progress = make_cb(short)

        try:
            outcome = copy_one(src, dst, short_name=short, role=role, progress=per_file_progress)
        except Exception as exc:
            failed.append(
                CopyOutcome(
                    short_name=short,
                    role=role,
                    status=CopyOutcomeStatus.FAILED,
                    src=src,
                    dst=dst,
                    error=str(exc),
                )
            )
            continue

        if outcome.status is CopyOutcomeStatus.SUCCEEDED:
            succeeded.append(outcome)
            bytes_copied += outcome.bytes
            if on_progress is not None and per_file_progress is None:
                # Emit a single completion event when no chunk callback was used.
                on_progress(short, outcome.bytes, outcome.bytes)
        elif outcome.status is CopyOutcomeStatus.SKIPPED_IDEMPOTENT:
            skipped.append(outcome)
            if on_progress is not None:
                on_progress(short, outcome.bytes, outcome.bytes)

    # OVERWRITE with delete_existing_zips: recycle every existing dest zip
    # except the ones we just wrote.
    if (
        plan.conflict_strategy is ConflictStrategy.OVERWRITE
        and plan.delete_existing_zips
        and not plan.dry_run
    ):
        wrote = {o.dst.name for o in succeeded}
        for existing in plan.dest_dir.glob("*.zip"):
            if existing.name in wrote:
                continue
            new_path = recycle_file(
                existing,
                reason="OVERWRITE_DELETE_EXISTING",
                session_id=session_id,
            )
            recycled.append(
                RecycleRecord(
                    original_path=existing,
                    recycled_path=new_path,
                    reason="OVERWRITE_DELETE_EXISTING",
                )
            )

    # Write playlist (skip when dry-run or cancelled-mid-flight).
    cancelled_mid = ctl.should_cancel()
    if not plan.dry_run and not cancelled_mid:
        # Build entries: every successfully-present winner gets an entry.
        entries: list[PlaylistEntry] = []
        winner_set = set(plan.winners)
        # Entries from this run.
        present_basenames: set[str] = set()
        for o in (*succeeded, *skipped):
            if o.role != "winner":
                continue
            machine = plan.machines.get(o.short_name)
            if machine is None:
                continue
            entries.append(
                PlaylistEntry(
                    short_name=o.short_name,
                    description=machine.description,
                    abs_path=o.dst.resolve(),
                )
            )
            present_basenames.add(o.dst.name)

        # APPEND: also keep existing entries that aren't being replaced.
        if plan.conflict_strategy is ConflictStrategy.APPEND and existing_items:
            for it in existing_items:
                ipath = Path(it.get("path", ""))
                if ipath.name in present_basenames:
                    # Already in our entries.
                    continue
                # Same-short-name overlap → keep existing entry as-is.
                # Different-short-name in same group → overwrite handled by
                # the existing-replaced logic; here we simply append.
                if ipath.name not in {f"{w}.zip" for w in winner_set}:
                    entries.append(
                        PlaylistEntry(
                            short_name=ipath.stem,
                            description=str(it.get("label", ipath.stem)),
                            abs_path=ipath,
                        )
                    )

        write_lpl(plan.dest_dir / "mame.lpl", entries)

    finished_at = datetime.now(UTC)
    if cancelled_mid:
        status = CopyReportStatus.CANCELLED
    elif failed:
        status = CopyReportStatus.PARTIAL_FAILURE
    else:
        status = CopyReportStatus.OK

    chd_missing = tuple(sorted(short for short in plan.winners if short in plan.chd_required))

    report = CopyReport(
        session_id=session_id,
        started_at=started_at,
        finished_at=finished_at,
        status=status,
        plan_summary=plan_summary,
        succeeded=tuple(sorted(succeeded, key=lambda o: o.short_name)),
        skipped=tuple(sorted(skipped, key=lambda o: o.short_name)),
        failed=tuple(sorted(failed, key=lambda o: o.short_name)),
        overwritten=tuple(overwritten),
        recycled=tuple(recycled),
        bios_included=tuple(sorted(bios_set)),
        chd_missing=chd_missing,
        bytes_copied=bytes_copied,
        warnings=tuple(warnings),
    )

    # Activity: copy_finished or copy_aborted.
    if status in (CopyReportStatus.OK, CopyReportStatus.PARTIAL_FAILURE):
        append_activity(
            ActivityEvent(
                timestamp=finished_at,
                event_type=ActivityEventType.COPY_FINISHED,
                summary=(
                    f"copy {status.value.lower()}: {len(succeeded)} ok, "
                    f"{len(skipped)} skipped, {len(failed)} failed"
                ),
                session_id=session_id,
                details=CopyFinishedDetails(
                    report_summary=ReportSummary(
                        succeeded_count=len(succeeded),
                        skipped_count=len(skipped),
                        failed_count=len(failed),
                        bytes_copied=bytes_copied,
                    )
                ),
            ),
            log_path=Path("data/activity.jsonl"),
        )
    else:
        append_activity(
            ActivityEvent(
                timestamp=finished_at,
                event_type=ActivityEventType.COPY_ABORTED,
                summary=f"copy aborted: {status.value.lower()}",
                session_id=session_id,
                details=CopyAbortedDetails(
                    reason=status.value,
                    recycled_count=len(recycled),
                ),
            ),
            log_path=Path("data/activity.jsonl"),
        )

    return report


def _finalize(
    *,
    plan: CopyPlan,
    started_at: datetime,
    session_id: str,
    status: CopyReportStatus,
    plan_summary: PlanSummary,
    bios_set: frozenset[str],
    warnings: list[str],
    recycled: tuple[RecycleRecord, ...] = (),
) -> CopyReport:
    finished_at = datetime.now(UTC)
    chd_missing = tuple(sorted(short for short in plan.winners if short in plan.chd_required))
    report = CopyReport(
        session_id=session_id,
        started_at=started_at,
        finished_at=finished_at,
        status=status,
        plan_summary=plan_summary,
        bios_included=tuple(sorted(bios_set)),
        chd_missing=chd_missing,
        recycled=recycled,
        warnings=tuple(warnings),
    )
    append_activity(
        ActivityEvent(
            timestamp=finished_at,
            event_type=ActivityEventType.COPY_ABORTED,
            summary=f"copy aborted: {status.value.lower()}",
            session_id=session_id,
            details=CopyAbortedDetails(reason=status.value, recycled_count=len(recycled)),
        ),
        log_path=Path("data/activity.jsonl"),
    )
    return report

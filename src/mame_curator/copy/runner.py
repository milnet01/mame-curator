"""Top-level orchestrator: run a CopyPlan, return a CopyReport."""

from __future__ import annotations

import functools
import logging
import secrets
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from mame_curator.copy.activity import append_activity
from mame_curator.copy.bios import resolve_bios_dependencies
from mame_curator.copy.controller import CopyController
from mame_curator.copy.errors import CopyError, PlaylistError, RecycleError
from mame_curator.copy.executor import copy_one
from mame_curator.copy.playlist import read_lpl, write_lpl
from mame_curator.copy.preflight import preflight
from mame_curator.copy.recyclebin import recycle_file
from mame_curator.copy.types import (
    ActivityEvent,
    ActivityEventType,
    AppendDecisionKind,
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


def _chd_missing(plan: CopyPlan) -> tuple[str, ...]:
    return tuple(sorted(short for short in plan.winners if short in plan.chd_required))


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
    # FP08 R1 (Cluster R): quote w.name via repr() — the BIOS short-name
    # flows from DAT data (user-controlled). Same threat model as FP08 A1
    # at runner.py:240; missed by FP08's initial `warnings.append(f"...")`
    # grep because this site uses the list-comprehension form.
    warnings: list[str] = [f"{w.name!r}: {w.kind}" for w in bios_warnings]

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

    # Names being replaced — from caller-supplied AppendDecision.replaces.
    # Used both to drive the recycle path and to prune the existing-entry
    # carry-over when building mame.lpl.
    replaced_shorts: set[str] = {
        d.replaces
        for d in plan.append_decisions.values()
        if d.kind in (AppendDecisionKind.REPLACE, AppendDecisionKind.REPLACE_AND_RECYCLE)
        and d.replaces is not None
    }

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
        # its cloneof_map and supplies `AppendDecision(kind=..., replaces=...)`
        # in plan.append_decisions. Presence of `short` in the map IS the
        # conflict signal; `replaces` names which existing entry is targeted.
        # Absent: the winner is added alongside existing entries.
        if (
            role == "winner"
            and plan.conflict_strategy is ConflictStrategy.APPEND
            and short in plan.append_decisions
        ):
            decision = plan.append_decisions[short]
            if decision.kind is AppendDecisionKind.KEEP_EXISTING:
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
            # REPLACE / REPLACE_AND_RECYCLE: caller specifies which existing
            # entry is replaced via `replaces`. Without it, no record is
            # emitted (the winner still copies normally below).
            if decision.replaces is not None:
                replaced_short = decision.replaces
                overwritten.append(OverwriteRecord(old_short=replaced_short, new_short=short))
                if decision.kind is AppendDecisionKind.REPLACE_AND_RECYCLE:
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
                            # FP08 A1: quote old_zip.name via repr() — the
                            # basename embeds replaced_short which flows from
                            # AppendDecision.replaces (a DAT machine short
                            # name; user-data path). Same threat model as
                            # FP06 B3 / FP07 A4. The {exc} portion is a
                            # CopyError subclass that already repr-quotes
                            # any embedded path post-FP07 A4.
                            warnings.append(f"recycle of {old_zip.name!r} failed: {exc}")

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

        per_file_progress: Callable[[int, int], None] | None = (
            functools.partial(on_progress, short) if on_progress is not None else None
        )

        try:
            outcome = copy_one(src, dst, short_name=short, role=role, progress=per_file_progress)
        except (OSError, CopyError) as exc:
            # FP05 A3: narrowed from `except Exception`. CopyError is the
            # project's typed failure mode (`copy/spec.md` § Errors); OSError
            # is defense-in-depth for any path that doesn't transit
            # CopyExecutionError. MemoryError, RecursionError, and other
            # non-OSError Exceptions propagate — continuing the loop after
            # OOM is exactly wrong.
            logger.exception("copy_one(short=%s, role=%s) failed", short, role)
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

    # FP05 A1: cancel(recycle_partial=True) recycles every successfully-copied
    # file from the current session. Spec § Pause/Resume/Cancel: "every
    # successfully-copied file from the current session is moved to recycle
    # … one `copy_aborted` activity event with `details.recycled_count = N`."
    # Both winner and bios outcomes are session-owned (recycle is keyed on
    # session_id; the user can restore a partial run end-to-end).
    cancelled_mid = ctl.should_cancel()
    if cancelled_mid and ctl.recycle_partial and not plan.dry_run:
        # Closing-review R1: use the project-default `data/recycle/` root,
        # matching the OVERWRITE_DELETE_EXISTING and REPLACE_AND_RECYCLE call
        # sites elsewhere in this runner. The earlier dest-local recycle path
        # would split recycle entries across two roots (project-local from
        # other branches; dest-local from cancel-partial) — `purge_recycle`
        # only knows the project default.
        for outcome in tuple(succeeded):
            try:
                new_path = recycle_file(
                    outcome.dst,
                    reason="CANCELLED_RECYCLE_PARTIAL",
                    session_id=session_id,
                )
            except (OSError, RecycleError):
                logger.exception(
                    "recycle_file(short=%s) failed during cancel-with-partial",
                    outcome.short_name,
                )
                continue
            recycled.append(
                RecycleRecord(
                    original_path=outcome.dst,
                    recycled_path=new_path,
                    reason="CANCELLED_RECYCLE_PARTIAL",
                )
            )
        # Files have been moved out of dst; drop them from `succeeded` so
        # the report doesn't claim files that no longer exist at the
        # destination.
        succeeded = []

    # Write playlist (skip when dry-run or cancelled-mid-flight).
    if not plan.dry_run and not cancelled_mid:
        # Build entries: only winners that are *definitely present at dst*
        # (SUCCEEDED or SKIPPED_IDEMPOTENT) — see spec § "Which winners
        # become entries". SKIPPED_MISSING_SOURCE / SKIPPED_EXISTING_VERSION
        # / FAILED outcomes have no file at `dst` and must not get an entry.
        entries: list[PlaylistEntry] = []
        winner_set = set(plan.winners)
        present_basenames: set[str] = set()
        present_statuses = {
            CopyOutcomeStatus.SUCCEEDED,
            CopyOutcomeStatus.SKIPPED_IDEMPOTENT,
        }
        for o in (*succeeded, *skipped):
            if o.role != "winner":
                continue
            if o.status not in present_statuses:
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

        # APPEND: keep existing entries that aren't being replaced and aren't
        # already-written winners.
        if plan.conflict_strategy is ConflictStrategy.APPEND and existing_items:
            replaced_basenames = {f"{s}.zip" for s in replaced_shorts}
            winner_basenames = {f"{w}.zip" for w in winner_set}
            for it in existing_items:
                # FP05 L5: skip entries with empty/missing path; otherwise
                # `Path("")` resolves to `Path(".")` and gets carried into
                # `mame.lpl` as an entry pointing at the dest dir itself.
                raw_path = it.get("path", "")
                if not raw_path:
                    continue
                ipath = Path(raw_path)
                if ipath.name in present_basenames:
                    continue
                if ipath.name in replaced_basenames:
                    continue
                if ipath.name in winner_basenames:
                    # Same-short overlap covered by the winner outcome above.
                    continue
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
        chd_missing=_chd_missing(plan),
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
    report = CopyReport(
        session_id=session_id,
        started_at=started_at,
        finished_at=finished_at,
        status=status,
        plan_summary=plan_summary,
        bios_included=tuple(sorted(bios_set)),
        chd_missing=_chd_missing(plan),
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

"""Top-level orchestrator: run a CopyPlan, return a CopyReport.

The run's record and its report are in `run_state.py`, the playlist's entries
in `run_playlist.py`, and the two end-of-run recycle passes in `run_recycle.py`.
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from mame_curator.copy.bios import resolve_bios_dependencies
from mame_curator.copy.controller import CopyController
from mame_curator.copy.errors import CopyError, UnsafeShortNameError
from mame_curator.copy.executor import copy_one
from mame_curator.copy.paths import is_safe_short_name, zip_path
from mame_curator.copy.playlist import write_lpl
from mame_curator.copy.preflight import preflight
from mame_curator.copy.recyclebin import recycle_file
from mame_curator.copy.run_playlist import (
    build_playlist_entries,
    existing_playlist,
    should_cancel_for_playlist_conflict,
)
from mame_curator.copy.run_recycle import recycle_partial_copy, recycle_unwritten_zips
from mame_curator.copy.run_state import (
    RunState,
    finish_early,
    finish_report,
    log_started,
    make_plan_summary,
    new_session_id,
    record_crash,
)
from mame_curator.copy.types import (
    AppendDecision,
    AppendDecisionKind,
    ConflictStrategy,
    CopyOutcome,
    CopyOutcomeStatus,
    CopyPlan,
    CopyReport,
    CopyReportStatus,
    OverwriteRecord,
    RecycleRecord,
)

logger = logging.getLogger(__name__)

# Typed as Literal so CopyOutcome.role narrows without `# type: ignore`.
_Role = Literal["winner", "bios"]
_Progress = Callable[[str, int, int], None]


def run_copy(
    plan: CopyPlan,
    *,
    controller: CopyController | None = None,
    on_progress: _Progress | None = None,
    data_dir: Path = Path("data"),
    on_crash: Callable[[CopyReport], None] | None = None,
) -> CopyReport:
    """Execute a CopyPlan; return a CopyReport. See spec.md for the full contract.

    mame-curator-1157: an unexpected exception after `copy_started` adds a
    `copy_aborted` event and hands an `ERROR` report of the files done so far
    to ``on_crash``; then the exception propagates unchanged.
    """
    state = RunState(started_at=datetime.now(UTC), session_id=new_session_id())
    try:
        return _run_copy(
            plan,
            ctl=controller or CopyController(),
            on_progress=on_progress,
            data_dir=data_dir,
            state=state,
        )
    except Exception as exc:
        if state.started:
            record_crash(state, exc, plan=plan, data_dir=data_dir, on_crash=on_crash)
        raise


def _run_copy(
    plan: CopyPlan,
    *,
    ctl: CopyController,
    on_progress: _Progress | None,
    data_dir: Path,
    state: RunState,
) -> CopyReport:
    bios_set, bios_warnings = resolve_bios_dependencies(plan.winners, plan.bios_chain)
    plan_summary = make_plan_summary(plan, len(bios_set))
    state.plan_summary, state.bios_set = plan_summary, bios_set

    # mame-curator-1152: before copy_started, so a refused playlist leaves no
    # started copy in the activity log and no file touched.
    pre = preflight(plan)
    kept_playlist = existing_playlist(plan, pre)
    log_started(plan, state, plan_summary, data_dir=data_dir)

    # FP08 R1 (Cluster R): quote w.name via repr() — the BIOS short-name
    # flows from DAT data (user-controlled).
    state.warnings.extend(f"{w.name!r}: {w.kind}" for w in bios_warnings)

    # DS02 A4: CANCEL idempotency guard extracted; see helper docstring.
    if should_cancel_for_playlist_conflict(plan, pre):
        status = CopyReportStatus.CANCELLED_PLAYLIST_CONFLICT
        return finish_early(plan, state, plan_summary, status, data_dir=data_dir)
    if ctl.should_cancel():  # cancelled before any work
        return finish_early(
            plan, state, plan_summary, CopyReportStatus.CANCELLED, data_dir=data_dir
        )

    # Winners first (preserves the "winner" role), then BIOS.
    work: list[tuple[str, _Role]] = [(w, "winner") for w in sorted(plan.winners)]
    work += [(b, "bios") for b in sorted(bios_set)]
    for short, role in work:
        ctl.wait_if_paused()  # pause boundary
        if ctl.should_cancel():
            break
        _copy_item(plan, short, role, state=state, on_progress=on_progress, data_dir=data_dir)

    # A cancel means no OVERWRITE clear-out.
    if (
        plan.conflict_strategy is ConflictStrategy.OVERWRITE
        and plan.delete_existing_zips
        and not plan.dry_run
        and not ctl.should_cancel()
    ):
        recycle_unwritten_zips(plan, state, data_dir=data_dir)

    cancelled_mid = ctl.should_cancel()
    if cancelled_mid and ctl.recycle_partial and not plan.dry_run:
        recycle_partial_copy(state, data_dir=data_dir)

    # Write playlist (skip when dry-run or cancelled-mid-flight).
    if not plan.dry_run and not cancelled_mid:
        # Only replacements that arrived are recorded, so only their old
        # entries leave the playlist (mame-curator-1230).
        replaced = frozenset(r.old_short for r in state.overwritten)
        old_items = kept_playlist["items"] if kept_playlist is not None else []
        entries, kept = build_playlist_entries(
            plan, state.succeeded, state.skipped, old_items, replaced
        )
        write_lpl(plan.playlist_file, entries, kept=kept, base=kept_playlist)

    return finish_report(plan, state, plan_summary, cancelled=cancelled_mid, data_dir=data_dir)


def _record_unfinished(
    bucket: list[CopyOutcome], outcome: CopyOutcome, on_progress: _Progress | None
) -> None:
    """Record a file that was skipped or failed, and tick it done.

    mame-curator-1103: a skipped or failed file reports one done == total
    tick so a progress consumer counts it as processed and the counter can
    reach files_total.
    """
    bucket.append(outcome)
    if on_progress is not None:
        on_progress(outcome.short_name, 0, 0)


def _copy_item(
    plan: CopyPlan,
    short: str,
    role: _Role,
    *,
    state: RunState,
    on_progress: _Progress | None,
    data_dir: Path,
) -> None:
    """Copy, skip or fail one file of the run, recording its outcome in ``state``."""
    try:
        src, dst = zip_path(plan.source_dir, short), zip_path(plan.dest_dir, short)
    except UnsafeShortNameError as exc:
        failure = CopyOutcome(
            short_name=short,
            role=role,
            status=CopyOutcomeStatus.FAILED,
            src=plan.source_dir,
            dst=plan.dest_dir,
            error=str(exc),
        )
        _record_unfinished(state.failed, failure, on_progress)
        return

    def skip(status: CopyOutcomeStatus) -> None:
        outcome = CopyOutcome(short_name=short, role=role, status=status, src=src, dst=dst)
        _record_unfinished(state.skipped, outcome, on_progress)

    if not src.exists():
        skip(CopyOutcomeStatus.SKIPPED_MISSING_SOURCE)
        return

    decision = _append_decision(plan, short, role)
    if decision is not None and decision.kind is AppendDecisionKind.KEEP_EXISTING:
        skip(CopyOutcomeStatus.SKIPPED_EXISTING_VERSION)
        return

    if plan.dry_run:
        # Pretend success without writing.
        try:
            size = src.stat().st_size
        except FileNotFoundError:  # gone since the exists() check (mame-curator-1230)
            skip(CopyOutcomeStatus.SKIPPED_MISSING_SOURCE)
            return
        state.succeeded.append(
            CopyOutcome(
                short_name=short,
                role=role,
                status=CopyOutcomeStatus.SUCCEEDED,
                src=src,
                dst=dst,
                bytes=size,
            )
        )
        state.bytes_copied += size
        if on_progress is not None:
            on_progress(short, size, size)
        arrived = True
    else:
        arrived = _copy_file(short, role, src, dst, state=state, on_progress=on_progress)

    # The old version goes only once the new one is in place, so a failed
    # copy never loses the game (mame-curator-1230).
    if decision is not None and arrived:
        _replace_existing(plan, short, decision, state=state, data_dir=data_dir)


def _append_decision(plan: CopyPlan, short: str, role: _Role) -> AppendDecision | None:
    """The caller's decision for a winner that conflicts with the APPEND playlist.

    The caller (CLI / API) pre-detects same-parent-group conflicts using its
    cloneof_map and supplies `AppendDecision(kind=..., replaces=...)` in
    plan.append_decisions. Presence of `short` in the map IS the conflict
    signal; `replaces` names which existing entry is targeted. Absent: the
    winner is added alongside existing entries.
    """
    if role != "winner" or plan.conflict_strategy is not ConflictStrategy.APPEND:
        return None
    return plan.append_decisions.get(short)


def _replace_existing(
    plan: CopyPlan,
    short: str,
    decision: AppendDecision,
    *,
    state: RunState,
    data_dir: Path,
) -> None:
    """REPLACE / REPLACE_AND_RECYCLE: record the replaced entry, recycle its zip if asked.

    Without `replaces`, no record is made (the winner still copies normally).
    """
    if decision.replaces is None:
        return
    replaced_short = decision.replaces
    state.overwritten.append(OverwriteRecord(old_short=replaced_short, new_short=short))
    if not is_safe_short_name(replaced_short):
        state.warnings.append(f"not recycling {replaced_short!r}: not a plain game name")
        return
    if decision.kind is not AppendDecisionKind.REPLACE_AND_RECYCLE:
        return
    old_zip = zip_path(plan.dest_dir, replaced_short)
    if not old_zip.exists() or plan.dry_run:
        return
    try:
        new_path = recycle_file(
            old_zip,
            reason="REPLACE_AND_RECYCLE",
            session_id=state.session_id,
            recycle_root=data_dir / "recycle",
        )
    except (OSError, CopyError) as exc:
        # mame-curator-1192: OSError too, as the OVERWRITE recycle site
        # catches — _session_lock can raise a raw PermissionError, which must
        # not stop the copy. FP08 A1: quote old_zip.name via repr() — the
        # basename embeds replaced_short which flows from
        # AppendDecision.replaces (a DAT machine short name; user-data path).
        state.warnings.append(f"recycle of {old_zip.name!r} failed: {exc}")
        return
    state.recycled.append(
        RecycleRecord(original_path=old_zip, recycled_path=new_path, reason="REPLACE_AND_RECYCLE")
    )


def _copy_file(
    short: str,
    role: _Role,
    src: Path,
    dst: Path,
    *,
    state: RunState,
    on_progress: _Progress | None,
) -> bool:
    """Copy one file for real; a copy error fails that file and the run goes on.

    Returns whether the file is now at ``dst`` (copied, or already current).
    """
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
        failure = CopyOutcome(
            short_name=short,
            role=role,
            status=CopyOutcomeStatus.FAILED,
            src=src,
            dst=dst,
            error=str(exc),
        )
        _record_unfinished(state.failed, failure, on_progress)
        return False

    if outcome.status is CopyOutcomeStatus.SUCCEEDED:
        state.succeeded.append(outcome)
        state.bytes_copied += outcome.bytes
        return True
    if outcome.status is CopyOutcomeStatus.SKIPPED_IDEMPOTENT:
        state.skipped.append(outcome)
        if on_progress is not None:
            on_progress(short, outcome.bytes, outcome.bytes)
        return True
    # The source went missing after the runner's exists() check; it was left
    # out of the report altogether before (mame-curator-1230).
    _record_unfinished(state.skipped, outcome, on_progress)
    return False

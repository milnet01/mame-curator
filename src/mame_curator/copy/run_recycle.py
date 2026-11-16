"""The two recycle passes that end a copy run: OVERWRITE's clear-out and a cancel's undo."""

from __future__ import annotations

import logging
from pathlib import Path

from mame_curator.copy.errors import CopyError, RecycleError
from mame_curator.copy.recyclebin import recycle_file
from mame_curator.copy.run_state import RunState
from mame_curator.copy.types import CopyOutcome, CopyOutcomeStatus, CopyPlan, RecycleRecord

logger = logging.getLogger(__name__)


def recycle_unwritten_zips(plan: CopyPlan, state: RunState, *, data_dir: Path) -> None:
    """OVERWRITE with delete_existing_zips: recycle every dest zip this run did not write."""
    # Idempotently skipped files are this run's files too (already
    # present and current); recycling them would leave the new
    # playlist pointing at missing zips.
    wrote = {o.dst.name for o in state.succeeded}
    wrote |= {o.dst.name for o in state.skipped if o.status is CopyOutcomeStatus.SKIPPED_IDEMPOTENT}
    for existing in plan.dest_dir.glob("*.zip"):
        if existing.name in wrote:
            continue
        try:
            new_path = recycle_file(
                existing,
                reason="OVERWRITE_DELETE_EXISTING",
                session_id=state.session_id,
                recycle_root=data_dir / "recycle",
            )
        except (OSError, CopyError) as exc:
            # The copies are done; keep the playlist and the report.
            state.warnings.append(f"recycle of {existing.name!r} failed: {exc}")
            continue
        state.recycled.append(
            RecycleRecord(
                original_path=existing,
                recycled_path=new_path,
                reason="OVERWRITE_DELETE_EXISTING",
            )
        )


def recycle_partial_copy(state: RunState, *, data_dir: Path) -> None:
    """Undo a cancelled run: recycle every file it copied, then forget them.

    FP05 A1: cancel(recycle_partial=True) recycles every successfully-copied
    file from the current session. Spec § Pause/Resume/Cancel: "every
    successfully-copied file from the current session is moved to recycle
    … one `copy_aborted` activity event with `details.recycled_count = N`."
    Both winner and bios outcomes are session-owned (recycle is keyed on
    session_id; the user can restore a partial run end-to-end).
    """
    # Closing-review R1: use the project-default `data/recycle/` root,
    # matching the OVERWRITE_DELETE_EXISTING and REPLACE_AND_RECYCLE call
    # sites. A dest-local recycle path would split recycle entries across
    # two roots — `purge_recycle` only knows the project default.
    stayed: list[CopyOutcome] = []
    for outcome in tuple(state.succeeded):
        try:
            new_path = recycle_file(
                outcome.dst,
                reason="CANCELLED_RECYCLE_PARTIAL",
                session_id=state.session_id,
                recycle_root=data_dir / "recycle",
            )
        except (OSError, RecycleError) as exc:
            logger.exception(
                "recycle_file(short=%s) failed during cancel-with-partial",
                outcome.short_name,
            )
            # Still at the destination, so still in the report, and said so
            # (mame-curator-1230). repr: the name comes from DAT data.
            stayed.append(outcome)
            state.warnings.append(f"recycle of {outcome.dst.name!r} failed: {exc}")
            continue
        state.recycled.append(
            RecycleRecord(
                original_path=outcome.dst,
                recycled_path=new_path,
                reason="CANCELLED_RECYCLE_PARTIAL",
            )
        )
    # The recycled files are no longer at dst; only the ones that stayed
    # remain in `succeeded`.
    state.succeeded[:] = stayed

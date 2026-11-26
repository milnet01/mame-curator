"""The two recycle passes that end a copy run: OVERWRITE's clear-out and a cancel's undo."""

from __future__ import annotations

import logging
from pathlib import Path

from mame_curator.copy.errors import CopyError
from mame_curator.copy.recyclebin import recycle_file
from mame_curator.copy.run_state import RunState
from mame_curator.copy.types import CopyOutcome, CopyOutcomeStatus, CopyPlan, RecycleRecord

logger = logging.getLogger(__name__)


def recycle_and_record(path: Path, reason: str, state: RunState, *, data_dir: Path) -> bool:
    """Recycle ``path`` and record it in ``state``; return whether it moved.

    A failure becomes a report warning and the run goes on: the copies it is
    tidying up after are done. OSError too, because the session lock can
    raise a raw PermissionError (mame-curator-1192). repr: the name comes
    from DAT data.
    """
    try:
        new_path = recycle_file(
            path, reason=reason, session_id=state.session_id, recycle_root=data_dir / "recycle"
        )
    except (OSError, CopyError) as exc:
        logger.warning("recycle of %s failed (%s): %s", path, reason, exc)
        state.warnings.append(f"recycle of {path.name!r} failed: {exc}")
        return False
    state.recycled.append(RecycleRecord(original_path=path, recycled_path=new_path, reason=reason))
    return True


def recycle_unwritten_zips(plan: CopyPlan, state: RunState, *, data_dir: Path) -> None:
    """OVERWRITE with delete_existing_zips: recycle every dest zip this run did not write."""
    # Idempotently skipped files are this run's files too (already
    # present and current); recycling them would leave the new
    # playlist pointing at missing zips.
    wrote = {o.dst.name for o in state.succeeded}
    wrote |= {o.dst.name for o in state.skipped if o.status is CopyOutcomeStatus.SKIPPED_IDEMPOTENT}
    for existing in plan.dest_dir.glob("*.zip"):
        if existing.name not in wrote:
            recycle_and_record(existing, "OVERWRITE_DELETE_EXISTING", state, data_dir=data_dir)


def recycle_partial_copy(state: RunState, *, data_dir: Path) -> None:
    """Undo a cancelled run: recycle every file it copied, winners and BIOS alike.

    copy/spec.md § Pause / resume / cancel. A file that could not be recycled
    is still at the destination, so it stays in ``succeeded`` (mame-curator-1230).
    """
    stayed: list[CopyOutcome] = [
        outcome
        for outcome in tuple(state.succeeded)
        if not recycle_and_record(
            outcome.dst, "CANCELLED_RECYCLE_PARTIAL", state, data_dir=data_dir
        )
    ]
    state.succeeded[:] = stayed

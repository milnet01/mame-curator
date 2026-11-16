"""The playlist check a copy job passes before it starts."""

from __future__ import annotations

from mame_curator.api.errors import PlaylistConflictCancelledError, PlaylistUnreadableError
from mame_curator.copy import ConflictStrategy, CopyPlan, PlaylistError, read_lpl


def check_playlist_conflict(plan: CopyPlan) -> None:
    """Pre-flight: raise if CANCEL would abort or APPEND cannot read the playlist.

    The API answers here rather than from the worker so the refusal is the
    start's own error, before any file is touched.
    """
    if not plan.playlist_file.exists():
        return
    if plan.conflict_strategy is ConflictStrategy.APPEND:
        try:
            read_lpl(plan.playlist_file)
        except PlaylistError as exc:
            raise PlaylistUnreadableError(str(exc)) from exc
        return
    if plan.conflict_strategy is not ConflictStrategy.CANCEL:
        return
    # Only raise if not idempotent — let run_copy handle the no-op case.
    all_present = all((plan.dest_dir / f"{w}.zip").exists() for w in plan.winners)
    if not all_present:
        raise PlaylistConflictCancelledError(
            f"existing playlist at {str(plan.playlist_file)!r}; "
            "use APPEND or OVERWRITE conflict strategy"
        )

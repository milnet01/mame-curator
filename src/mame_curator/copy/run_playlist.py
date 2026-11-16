"""Which entries a copy run's `mame.lpl` gets, and what an APPEND copy keeps."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mame_curator.copy.errors import PlaylistError
from mame_curator.copy.playlist import read_lpl, read_lpl_document
from mame_curator.copy.types import (
    ConflictStrategy,
    CopyOutcome,
    CopyOutcomeStatus,
    CopyPlan,
    PlaylistEntry,
    PreflightResult,
)


def playlist_holds_only_winners(plan: CopyPlan) -> bool:
    """Does every entry of the existing playlist name one of the plan's winners?

    A CANCEL re-run rewrites the playlist with the winners alone, so it is a
    no-op only when this holds (mame-curator-1230). A playlist that cannot be
    read does not.
    """
    try:
        items = read_lpl(plan.playlist_file)
    except PlaylistError:
        return False
    winners = set(plan.winners)
    return all(Path(it.get("path", "")).stem in winners for it in items)


def should_cancel_for_playlist_conflict(plan: CopyPlan, pre: PreflightResult) -> bool:
    """True iff CANCEL strategy + existing playlist + the run is not a no-op.

    A no-op re-run (design § 6.4) has every winner already at dest (matching
    size+mtime) and a playlist naming only winners; such a rerun proceeds
    without asking for ``--conflict append``.
    """
    if not (
        pre.existing_playlist
        and not plan.dry_run
        and plan.conflict_strategy is ConflictStrategy.CANCEL
    ):
        return False
    every_winner_present = set(pre.already_copied) >= set(plan.winners)
    return not (every_winner_present and playlist_holds_only_winners(plan))


def existing_playlist(plan: CopyPlan, pre: PreflightResult) -> dict[str, Any] | None:
    """The destination playlist an APPEND copy keeps, settings and items; else None.

    A playlist that cannot be read raises ``PlaylistError``: APPEND promises
    to keep those entries, so the copy must not replace them.
    """
    if pre.existing_playlist and plan.conflict_strategy is ConflictStrategy.APPEND:
        return read_lpl_document(plan.playlist_file)
    return None


def build_playlist_entries(
    plan: CopyPlan,
    succeeded: list[CopyOutcome],
    skipped: list[CopyOutcome],
    existing_items: list[dict[str, Any]],
    replaced_shorts: frozenset[str],
) -> tuple[list[PlaylistEntry], list[dict[str, Any]]]:
    """Compose mame.lpl: ``(new entries, old items kept unchanged)``.

    Only winners *definitely present at dst* become entries (SUCCEEDED or
    SKIPPED_IDEMPOTENT); SKIPPED_MISSING_SOURCE / SKIPPED_EXISTING_VERSION
    / FAILED outcomes have no file at ``dst`` per spec § "Which winners
    become entries". For APPEND, an old item is kept unless a present winner
    has its file name, or replaced it; ``replaced_shorts`` names only
    replacements that arrived (mame-curator-1230).
    """
    entries: list[PlaylistEntry] = []
    present_basenames: set[str] = set()
    present_statuses = {CopyOutcomeStatus.SUCCEEDED, CopyOutcomeStatus.SKIPPED_IDEMPOTENT}
    for o in (*succeeded, *skipped):
        if o.role != "winner" or o.status not in present_statuses:
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

    kept: list[dict[str, Any]] = []
    if plan.conflict_strategy is ConflictStrategy.APPEND:
        gone = present_basenames | {f"{s}.zip" for s in replaced_shorts}
        for it in existing_items:
            # FP05 L5: skip empty paths; Path("") resolves to Path(".") and
            # would carry the dest dir itself into mame.lpl.
            raw_path = it.get("path", "")
            if raw_path and Path(raw_path).name not in gone:
                kept.append(it)
    return entries, kept

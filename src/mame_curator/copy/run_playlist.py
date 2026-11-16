"""Which entries a copy run's `mame.lpl` gets, and what an APPEND copy keeps."""

from __future__ import annotations

from pathlib import Path

from mame_curator.copy.playlist import read_lpl
from mame_curator.copy.types import (
    AppendDecisionKind,
    ConflictStrategy,
    CopyOutcome,
    CopyOutcomeStatus,
    CopyPlan,
    PlaylistEntry,
    PreflightResult,
)


def should_cancel_for_playlist_conflict(plan: CopyPlan, pre: PreflightResult) -> bool:
    """True iff CANCEL strategy + existing playlist + not fully idempotent.

    Idempotent rerun = every winner already at dest (matching size+mtime) AND
    no extra zips at dest beyond winners + bios. Per design § 6.4 we want
    such a rerun to proceed as a no-op without requiring the user to
    re-invoke with ``--conflict append``.
    """
    if not (
        pre.existing_playlist
        and not plan.dry_run
        and plan.conflict_strategy is ConflictStrategy.CANCEL
    ):
        return False
    return not (set(pre.already_copied) >= set(plan.winners))


def resolve_conflicts(
    plan: CopyPlan, pre: PreflightResult
) -> tuple[list[dict[str, str]], frozenset[str]]:
    """Return (existing_items, replaced_shorts) for an APPEND copy.

    ``existing_items`` is the destination playlist's pre-existing
    entries (carried forward by ``write_lpl``), or ``[]`` for non-APPEND
    paths. A playlist that cannot be read raises ``PlaylistError``: APPEND
    promises to keep those entries, so the copy must not replace them.
    ``replaced_shorts`` is the set of names targeted by REPLACE /
    REPLACE_AND_RECYCLE decisions.
    """
    existing_items: list[dict[str, str]] = []
    if pre.existing_playlist and plan.conflict_strategy is ConflictStrategy.APPEND:
        existing_items = read_lpl(plan.playlist_file)
    replaced_shorts = frozenset(
        d.replaces
        for d in plan.append_decisions.values()
        if d.kind in (AppendDecisionKind.REPLACE, AppendDecisionKind.REPLACE_AND_RECYCLE)
        and d.replaces is not None
    )
    return existing_items, replaced_shorts


def build_playlist_entries(
    plan: CopyPlan,
    succeeded: list[CopyOutcome],
    skipped: list[CopyOutcome],
    existing_items: list[dict[str, str]],
    replaced_shorts: frozenset[str],
) -> list[PlaylistEntry]:
    """Compose the final mame.lpl entry list for write_lpl.

    Only winners *definitely present at dst* become entries (SUCCEEDED or
    SKIPPED_IDEMPOTENT); SKIPPED_MISSING_SOURCE / SKIPPED_EXISTING_VERSION
    / FAILED outcomes have no file at ``dst`` per spec § "Which winners
    become entries". For APPEND, pre-existing entries are carried forward
    unless they are being replaced or overlap a same-name winner.
    """
    entries: list[PlaylistEntry] = []
    winner_set = set(plan.winners)
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

    if plan.conflict_strategy is ConflictStrategy.APPEND and existing_items:
        replaced_basenames = {f"{s}.zip" for s in replaced_shorts}
        winner_basenames = {f"{w}.zip" for w in winner_set}
        for it in existing_items:
            # FP05 L5: skip empty paths; Path("") resolves to Path(".") and
            # would carry the dest dir itself into mame.lpl.
            raw_path = it.get("path", "")
            if not raw_path:
                continue
            ipath = Path(raw_path)
            if (
                ipath.name in present_basenames
                or ipath.name in replaced_basenames
                or ipath.name in winner_basenames
            ):
                continue
            entries.append(
                PlaylistEntry(
                    short_name=ipath.stem,
                    description=str(it.get("label", ipath.stem)),
                    abs_path=ipath,
                )
            )
    return entries

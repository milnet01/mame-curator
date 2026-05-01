"""Frozen Pydantic types for the copy module.

Every public input/output surface is a frozen Pydantic model with
`extra="forbid"` per `coding-standards.md` § 3 (no implicit-Optional,
no surprise fields). Sorting on every tuple field is canonical so
the report is byte-identical across reruns (tested via `test_copy_idempotent`).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Discriminator

from mame_curator.parser.listxml import BIOSChainEntry
from mame_curator.parser.models import Machine


class ConflictStrategy(StrEnum):
    """Top-level strategy when an existing playlist is detected at preflight."""

    APPEND = "APPEND"
    OVERWRITE = "OVERWRITE"
    CANCEL = "CANCEL"


class AppendDecisionKind(StrEnum):
    """Variant of `AppendDecision` (the enum half of the tagged union)."""

    KEEP_EXISTING = "KEEP_EXISTING"
    REPLACE = "REPLACE"
    REPLACE_AND_RECYCLE = "REPLACE_AND_RECYCLE"


class AppendDecision(BaseModel):
    """Per-game decision when APPEND mode hits a cross-version conflict.

    `replaces` is the short-name of the existing playlist entry that this
    decision targets — required for `REPLACE` / `REPLACE_AND_RECYCLE`,
    ignored for `KEEP_EXISTING`. Caller-supplied so the runner does not
    have to heuristic-match (the prior heuristic broke on multi-conflict
    sessions; FP02 widened the API per `copy/spec.md` § Playlist conflict
    resolution).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: AppendDecisionKind
    replaces: str | None = None


class CopyOutcomeStatus(StrEnum):
    """Per-file outcome status (succeeded / skipped / failed variants)."""

    SUCCEEDED = "SUCCEEDED"
    SKIPPED_IDEMPOTENT = "SKIPPED_IDEMPOTENT"
    SKIPPED_MISSING_SOURCE = "SKIPPED_MISSING_SOURCE"
    SKIPPED_EXISTING_VERSION = "SKIPPED_EXISTING_VERSION"
    FAILED = "FAILED"


class CopyReportStatus(StrEnum):
    """Whole-session outcome status returned by `run_copy`."""

    OK = "OK"
    CANCELLED = "CANCELLED"
    CANCELLED_PLAYLIST_CONFLICT = "CANCELLED_PLAYLIST_CONFLICT"
    PARTIAL_FAILURE = "PARTIAL_FAILURE"


class BIOSResolutionWarning(BaseModel):
    """Non-fatal advisory from the BIOS chain walk."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str
    kind: Literal["missing_from_listxml"]


class CopyOutcome(BaseModel):
    """Frozen per-file copy result (winner or BIOS)."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    short_name: str
    role: Literal["winner", "bios"]
    status: CopyOutcomeStatus
    src: Path
    dst: Path
    bytes: int = 0
    error: str | None = None


class OverwriteRecord(BaseModel):
    """Record of an APPEND replace event (cross-version winner swap).

    `(old_short, new_short)` only — the runner has no `cloneof_map` and so
    cannot reliably name the parent. Pre-FP02 the model carried a `parent`
    field that always equalled `old_short`; that was misleading and was
    dropped per ROADMAP § FP02 Tier 2 #1.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    old_short: str
    new_short: str


class RecycleRecord(BaseModel):
    """Record of a file moved into `data/recycle/`."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    original_path: Path
    recycled_path: Path
    reason: str


class PlanSummary(BaseModel):
    """Compact CopyPlan view embedded in activity events + report."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    winners_count: int
    bios_count: int
    conflict_strategy: ConflictStrategy
    source_dir: Path
    dest_dir: Path


class ReportSummary(BaseModel):
    """Compact CopyReport view embedded in activity events."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    succeeded_count: int
    skipped_count: int
    failed_count: int
    bytes_copied: int


class PlaylistEntry(BaseModel):
    """One playlist entry destined for `mame.lpl`."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    short_name: str
    description: str
    abs_path: Path


class PreflightResult(BaseModel):
    """Aggregated findings from the source/destination filesystem checks."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    missing_source: tuple[str, ...] = ()
    dest_writable: bool = True
    free_space_gap_bytes: int = 0
    existing_playlist: bool = False
    already_copied: tuple[str, ...] = ()


class CopyPlan(BaseModel):
    """Frozen input to `run_copy`: winners + machines + dirs + strategy."""

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)
    winners: tuple[str, ...]
    machines: dict[str, Machine]
    bios_chain: dict[str, BIOSChainEntry]
    chd_required: frozenset[str] = frozenset()
    source_dir: Path
    dest_dir: Path
    conflict_strategy: ConflictStrategy = ConflictStrategy.CANCEL
    append_decisions: dict[str, AppendDecision] = {}
    delete_existing_zips: bool = False
    dry_run: bool = False


class CopyReport(BaseModel):
    """Frozen output of `run_copy`: per-file outcomes + summary stats."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    session_id: str
    started_at: datetime
    finished_at: datetime
    status: CopyReportStatus
    plan_summary: PlanSummary
    succeeded: tuple[CopyOutcome, ...] = ()
    skipped: tuple[CopyOutcome, ...] = ()
    failed: tuple[CopyOutcome, ...] = ()
    overwritten: tuple[OverwriteRecord, ...] = ()
    recycled: tuple[RecycleRecord, ...] = ()
    bios_included: tuple[str, ...] = ()
    chd_missing: tuple[str, ...] = ()
    bytes_copied: int = 0
    warnings: tuple[str, ...] = ()


# Activity log event types --------------------------------------------------


class ActivityEventType(StrEnum):
    """Closed enum of activity-log event types."""

    COPY_STARTED = "copy_started"
    COPY_FINISHED = "copy_finished"
    COPY_ABORTED = "copy_aborted"
    OVERRIDE_SET = "override_set"
    SESSION_ACTIVATED = "session_activated"
    INI_REFRESHED = "ini_refreshed"
    APP_UPDATED = "app_updated"
    FILE_RECYCLED = "file_recycled"
    RECYCLE_PURGED = "recycle_purged"


class CopyStartedDetails(BaseModel):
    """`copy_started` event payload."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    event_type: Literal[ActivityEventType.COPY_STARTED] = ActivityEventType.COPY_STARTED
    plan_summary: PlanSummary
    conflict_strategy: ConflictStrategy


class CopyFinishedDetails(BaseModel):
    """`copy_finished` event payload."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    event_type: Literal[ActivityEventType.COPY_FINISHED] = ActivityEventType.COPY_FINISHED
    report_summary: ReportSummary


class CopyAbortedDetails(BaseModel):
    """`copy_aborted` event payload."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    event_type: Literal[ActivityEventType.COPY_ABORTED] = ActivityEventType.COPY_ABORTED
    reason: str
    recycled_count: int = 0


class OverrideSetDetails(BaseModel):
    """`override_set` event payload (Phase 2 emitter)."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    event_type: Literal[ActivityEventType.OVERRIDE_SET] = ActivityEventType.OVERRIDE_SET
    parent: str
    winner: str


class SessionActivatedDetails(BaseModel):
    """`session_activated` event payload (Phase 2 emitter)."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    event_type: Literal[ActivityEventType.SESSION_ACTIVATED] = ActivityEventType.SESSION_ACTIVATED
    session_name: str


class IniRefreshedDetails(BaseModel):
    """`ini_refreshed` event payload (Phase 7 emitter)."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    event_type: Literal[ActivityEventType.INI_REFRESHED] = ActivityEventType.INI_REFRESHED
    ini_name: str
    sha256_old: str
    sha256_new: str


class AppUpdatedDetails(BaseModel):
    """`app_updated` event payload (Phase 7 emitter)."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    event_type: Literal[ActivityEventType.APP_UPDATED] = ActivityEventType.APP_UPDATED
    version_old: str
    version_new: str


class FileRecycledDetails(BaseModel):
    """`file_recycled` event payload."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    event_type: Literal[ActivityEventType.FILE_RECYCLED] = ActivityEventType.FILE_RECYCLED
    path: str
    reason: str


class RecyclePurgedDetails(BaseModel):
    """`recycle_purged` event payload."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    event_type: Literal[ActivityEventType.RECYCLE_PURGED] = ActivityEventType.RECYCLE_PURGED
    dirs_purged: int
    bytes_freed: int


ActivityDetails = Annotated[
    CopyStartedDetails
    | CopyFinishedDetails
    | CopyAbortedDetails
    | OverrideSetDetails
    | SessionActivatedDetails
    | IniRefreshedDetails
    | AppUpdatedDetails
    | FileRecycledDetails
    | RecyclePurgedDetails,
    Discriminator("event_type"),
]


class ActivityEvent(BaseModel):
    """One line of `data/activity.jsonl`; tagged-union via `event_type`."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    timestamp: datetime
    event_type: ActivityEventType
    summary: str
    session_id: str
    details: ActivityDetails

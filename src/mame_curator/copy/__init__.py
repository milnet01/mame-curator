"""Phase 3 — Copy, BIOS resolution, RetroArch playlist writer.

Public API surface — see spec.md for the full contract.
"""

from mame_curator.copy.activity import append_activity, read_activity
from mame_curator.copy.bios import resolve_bios_dependencies
from mame_curator.copy.controller import CopyController, CopyControlState
from mame_curator.copy.errors import (
    BIOSResolutionError,
    CopyError,
    CopyExecutionError,
    PlaylistError,
    PreflightError,
    RecycleError,
)
from mame_curator.copy.executor import copy_one
from mame_curator.copy.playlist import read_lpl, write_lpl
from mame_curator.copy.preflight import preflight
from mame_curator.copy.recyclebin import purge_recycle, recycle_file
from mame_curator.copy.runner import run_copy
from mame_curator.copy.types import (
    ActivityEvent,
    ActivityEventType,
    AppendDecision,
    BIOSResolutionWarning,
    ConflictStrategy,
    CopyOutcome,
    CopyOutcomeStatus,
    CopyPlan,
    CopyReport,
    CopyReportStatus,
    OverwriteRecord,
    PlanSummary,
    PlaylistEntry,
    PreflightResult,
    RecycleRecord,
    ReportSummary,
)

__all__ = [
    "ActivityEvent",
    "ActivityEventType",
    "AppendDecision",
    "BIOSResolutionError",
    "BIOSResolutionWarning",
    "ConflictStrategy",
    "CopyControlState",
    "CopyController",
    "CopyError",
    "CopyExecutionError",
    "CopyOutcome",
    "CopyOutcomeStatus",
    "CopyPlan",
    "CopyReport",
    "CopyReportStatus",
    "OverwriteRecord",
    "PlanSummary",
    "PlaylistEntry",
    "PlaylistError",
    "PreflightError",
    "PreflightResult",
    "RecycleError",
    "RecycleRecord",
    "ReportSummary",
    "append_activity",
    "copy_one",
    "preflight",
    "purge_recycle",
    "read_activity",
    "read_lpl",
    "recycle_file",
    "resolve_bios_dependencies",
    "run_copy",
    "write_lpl",
]

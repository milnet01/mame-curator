"""Copy-pipeline request/response models — extracted from schemas.py by DS02 A5.

Re-exported from ``mame_curator.api.schemas`` so existing
``from mame_curator.api.schemas import CopyJobRequest, ...`` callers keep
working unchanged.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from mame_curator.copy.types import (
    AppendDecision,
    ConflictStrategy,
    CopyOutcomeStatus,
    CopyReportStatus,
)

# mame-curator-1225: bounds on user-controlled memory, as ValidateRequest has.
# The count sits above any MAME set, because the guide sends the whole list;
# 64 characters is ValidateRequest's per-name cap.
_MAX_COPY_NAMES = 100_000
_ShortName = Annotated[str, Field(max_length=64)]


class CopyJobRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    selected_names: Annotated[tuple[_ShortName, ...], Field(max_length=_MAX_COPY_NAMES)]
    conflict_strategy: ConflictStrategy = ConflictStrategy.CANCEL
    append_decisions: Annotated[
        dict[_ShortName, AppendDecision], Field(max_length=_MAX_COPY_NAMES)
    ] = Field(default_factory=dict)


class DryRunReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    counts: dict[str, int]
    summary: dict[str, Any]


class JobAccepted(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    job_id: str


JobState = Literal["running", "paused", "terminating", "finished", "aborted"]


class JobStatus(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    job_id: str
    state: JobState
    started_at: datetime
    files_done: int
    files_total: int
    bytes_done: int
    bytes_total: int


class JobEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    event: Literal[
        "job_started",
        "file_started",
        "file_progress",
        "file_finished",
        "paused",
        "resumed",
        "bios_warning",
        "job_finished",
        "job_aborted",
    ]
    payload: dict[str, Any]
    ts: datetime


class CopyAbortRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    recycle_partial: bool = False


class CopyName(BaseModel):
    """One game or BIOS file a copy skipped or failed (mame-curator-1199)."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    short_name: str
    role: Literal["winner", "bios"]
    status: CopyOutcomeStatus
    error: str | None = None


class CopyNames(BaseModel):
    """The names behind a copy's skipped and failed counts in Activity."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    skipped: tuple[CopyName, ...] = ()
    failed: tuple[CopyName, ...] = ()


class HistoryItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    job_id: str
    started_at: datetime
    finished_at: datetime
    status: CopyReportStatus
    succeeded: int
    failed: int
    bytes_copied: int


class HistoryListing(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[HistoryItem, ...]
    page: int
    page_size: int
    total: int


class ActivityPage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[dict[str, Any], ...]
    page: int
    page_size: int
    total: int

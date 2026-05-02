"""Pydantic wire-models for the API.

Every model is ``frozen=True, extra="forbid"`` per project convention. Where a
type comes from ``parser/`` / ``filter/`` / ``copy/`` we re-export rather than
re-declare; see ``docs/specs/P04.md`` § Schemas.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mame_curator.copy.types import (
    AppendDecision,
    ConflictStrategy,
    CopyReportStatus,
)
from mame_curator.filter.config import FilterConfig
from mame_curator.filter.sessions import Session
from mame_curator.filter.types import TiebreakerHit
from mame_curator.parser.models import Machine

# ---------------------------------------------------------------------------
# Config schema
# ---------------------------------------------------------------------------


class PathsConfig(BaseModel):
    """The ``paths:`` section of ``config.yaml``.

    Includes both the real-data paths used by the copy pipeline AND the
    reference-data paths the lifespan parses on startup. The latter are
    grouped here (rather than under a dedicated ``reference_files:`` block)
    to mirror ``config.example.yaml`` as it ships and the conftest fixture.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    source_roms: Path
    source_dat: Path
    dest_roms: Path
    retroarch_playlist: Path
    catver: Path | None = None
    languages: Path | None = None
    bestgames: Path | None = None
    mature: Path | None = None
    series: Path | None = None
    listxml: Path | None = None


class ServerConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    host: str = "127.0.0.1"
    port: int = 8080
    open_browser_on_start: bool = True


class FsConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    granted_roots: tuple[Path, ...] = ()


class MediaConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    fetch_videos: bool = False
    cache_dir: Path = Path("./data/media-cache")


class UiConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    theme: Literal["dark", "light", "double_dragon", "pacman", "sf2", "neogeo"] = "dark"
    layout: Literal["masonry", "list", "covers", "grouped"] = "masonry"
    default_sort: Literal["name", "year", "manufacturer", "rating"] = "name"
    show_alternatives_indicator: bool = True
    cards_per_row_hint: Literal["auto", 4, 5, 6, 8] = "auto"


class UpdatesConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    channel: Literal["stable", "dev"] = "stable"
    check_on_startup: bool = True
    ini_check_on_startup: bool = True


class AppConfig(BaseModel):
    """Top-level config.yaml schema."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    paths: PathsConfig
    server: ServerConfig = ServerConfig()
    filters: FilterConfig = FilterConfig()
    media: MediaConfig = MediaConfig()
    ui: UiConfig = UiConfig()
    updates: UpdatesConfig = UpdatesConfig()
    fs: FsConfig = FsConfig()

    @model_validator(mode="before")
    @classmethod
    def _merge_picker_into_filters(cls, data: Any) -> Any:
        """YAML alias: ``picker:`` keys merge into ``filters:`` (single FilterConfig)."""
        if not isinstance(data, dict):
            return data
        picker = data.pop("picker", None) if isinstance(data.get("picker"), dict) else None
        if picker is not None:
            filters = data.get("filters") or {}
            if not isinstance(filters, dict):
                filters = {}
            merged = {**filters, **picker}
            data["filters"] = merged
        return data


# ---------------------------------------------------------------------------
# Games + metadata
# ---------------------------------------------------------------------------


class Badge(StrEnum):
    CONTESTED = "contested"
    OVERRIDDEN = "overridden"
    CHD_MISSING = "chd_missing"
    BIOS_MISSING = "bios_missing"
    HAS_NOTES = "has_notes"


class GameCard(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    short_name: str
    description: str
    year: int | None
    manufacturer: str | None
    publisher: str | None
    developer: str | None
    badges: tuple[Badge, ...]


class GamesPage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[GameCard, ...]
    page: int
    page_size: int
    total: int


class GameDetail(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    short_name: str
    machine: Machine
    category: str | None
    languages: tuple[str, ...]
    bestgames_tier: str | None
    mature: bool
    chd_required: bool
    badges: tuple[Badge, ...]
    override: str | None
    parent: str


class Alternatives(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[GameCard, ...]


class Explanation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    short_name: str
    parent: str
    candidates: tuple[str, ...]
    hits: tuple[TiebreakerHit, ...]


class Notes(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    notes: str = Field(max_length=4096)


class Stats(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    by_genre: dict[str, int]
    by_decade: dict[str, int]
    by_publisher: dict[str, int]
    by_driver_status: dict[str, int]
    total_bytes: int


# ---------------------------------------------------------------------------
# Overrides + sessions
# ---------------------------------------------------------------------------


class OverridesEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    parent: str
    winner: str


class OverridesView(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    entries: dict[str, str]
    warnings: tuple[str, ...] = ()


class SessionsListing(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    active: str | None
    sessions: dict[str, Session]


class SessionUpsertRequest(BaseModel):
    """Body for R11 POST /api/sessions.

    The ``name`` regex is enforced in the route handler (raising
    ``SessionNameInvalidError``) rather than via a Pydantic ``Field(pattern=...)``
    so the wire-level error code is ``session_name_invalid`` rather than the
    generic ``validation_error``.

    FP11 § G3: frozen=True flipped on to match the rest of `schemas.py`.
    The route handler reads `body.name` / `body.session` and never mutates,
    so the freeze is purely a consistency fix — every public input/output
    surface in this module is `frozen=True, extra="forbid"`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str
    session: Session


# ---------------------------------------------------------------------------
# Config snapshots / export-import
# ---------------------------------------------------------------------------


class Snapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str
    ts: datetime
    files: tuple[str, ...]


class SnapshotsListing(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[Snapshot, ...]


class ConfigExportBundle(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    config: dict[str, Any]
    overrides: dict[str, Any]
    sessions: dict[str, Any]
    notes: dict[str, str]


class AppConfigResponse(BaseModel):
    """``AppConfig`` plus the ``restart_required`` flag returned by R15."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    paths: PathsConfig
    server: ServerConfig
    filters: FilterConfig
    media: MediaConfig
    ui: UiConfig
    updates: UpdatesConfig
    fs: FsConfig
    restart_required: bool = False


# ---------------------------------------------------------------------------
# Copy
# ---------------------------------------------------------------------------


class CopyJobRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    selected_names: tuple[str, ...]
    conflict_strategy: ConflictStrategy = ConflictStrategy.CANCEL
    append_decisions: dict[str, AppendDecision] = Field(default_factory=dict)


class DryRunReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    counts: dict[str, int]
    summary: dict[str, Any]


class JobAccepted(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    job_id: str


class JobStatus(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    job_id: str
    state: Literal["running", "paused", "terminating", "finished", "aborted"]
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


# ---------------------------------------------------------------------------
# Activity
# ---------------------------------------------------------------------------


class ActivityPage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[dict[str, Any], ...]
    page: int
    page_size: int
    total: int


# ---------------------------------------------------------------------------
# Filesystem
# ---------------------------------------------------------------------------


class FsEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str
    path: str
    is_dir: bool
    size: int | None
    mtime: datetime


class FsListing(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    path: str
    entries: tuple[FsEntry, ...]
    parent: str | None


class FsPath(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    path: str


class FsAllowedRoot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str
    path: str
    source: Literal["config", "granted"]


class FsAllowedRoots(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    roots: tuple[FsAllowedRoot, ...]


class FsDriveRoots(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    roots: tuple[str, ...]


class FsGrantRootRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    path: str


# ---------------------------------------------------------------------------
# Setup / updates stubs
# ---------------------------------------------------------------------------


class SetupPathStatus(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    path: str
    exists: bool
    readable: bool
    writable: bool
    dat_parses: bool | None = None


class SetupPaths(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source_roms: SetupPathStatus
    source_dat: SetupPathStatus
    dest_roms: SetupPathStatus


class SetupReferenceStatus(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    path: str
    exists: bool


class SetupReferenceFiles(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    catver: SetupReferenceStatus
    languages: SetupReferenceStatus
    bestgames: SetupReferenceStatus
    mature: SetupReferenceStatus
    series: SetupReferenceStatus
    listxml: SetupReferenceStatus


class SetupCheck(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    config_present: bool
    paths: SetupPaths
    reference_files: SetupReferenceFiles


class AppUpdateInfo(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    current_version: str
    latest_version: str | None
    update_available: bool


class UpdatesCheck(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    app: AppUpdateInfo
    ini: tuple[Any, ...] = ()


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------


class HelpTopic(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    slug: str
    title: str


class HelpIndex(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    topics: tuple[HelpTopic, ...]


class HelpContent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    slug: str
    title: str
    html: str


# ---------------------------------------------------------------------------
# Notes-write request
# ---------------------------------------------------------------------------


class NotesPutRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    notes: str = Field(max_length=4096)


# ---------------------------------------------------------------------------
# Override-post request
# ---------------------------------------------------------------------------


class OverridePostRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    parent: str
    winner: str


# ---------------------------------------------------------------------------
# Session activate request (empty body)
# ---------------------------------------------------------------------------


class EmptyBody(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

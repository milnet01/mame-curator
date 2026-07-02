"""Pydantic wire-models for the API.

Every model is ``frozen=True, extra="forbid"`` per project convention. Where a
type comes from ``parser/`` / ``filter/`` / ``copy/`` we re-export rather than
re-declare; see ``docs/specs/P04.md`` § Schemas.

**DS02 A5 — file split.** This module now holds only the Config schema +
small per-route request bodies. Games / Overrides / Copy / Activity /
Filesystem / Setup / Help models live in sibling modules and are
re-exported below so existing
``from mame_curator.api.schemas import GameCard, ...`` callers keep
working unchanged.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from mame_curator.filter.config import FilterConfig
from mame_curator.media import Kind  # P10 chunk 9 — source-chain kind vocabulary

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
    # FP19: optional RetroArch invocation paths for the in-app "Launch"
    # button. Both must be set for the launch route to succeed; absent
    # configuration → POST /api/games/{name}/launch returns 422.
    retroarch: Path | None = None
    retroarch_core: Path | None = None


class LaunchResponse(BaseModel):
    """FP19: outcome of POST /api/games/{name}/launch."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    pid: int
    rom_path: str
    argv: tuple[str, ...]


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
    # P10 chunk 4 — ArcadeDB scraper rate-limit knob. Default 30 req/min;
    # the public service has no documented hard cap but is a hobby site,
    # so we cap ourselves at a courteous rate. Configurable so ops can
    # tune without a spec rev if upstream policy changes.
    arcadedb_rate_limit_per_min: int = 30
    # P10 chunk 6 — MobyGames lookup rate-limit knob. MobyGames documents
    # 360 req/hr for free accounts; 5 req/min (= 300/hr) leaves a 60%
    # margin. Configurable for users on a higher-tier key.
    mobygames_rate_limit_per_min: int = 5
    # P10 chunk 7 — the fallback source order. First tried first; a source
    # not listed is disabled (no chain entry); an unknown name logs a
    # one-time WARNING and is skipped. Users reorder to change priority.
    # "libretro" is always appended as the baseline even if omitted here.
    sources: tuple[str, ...] = (
        "libretro",
        "progettoSnaps",
        "arcadeDB",
        "wikipediaImage",
        "mobyGames",
    )


# P10 chunk 9 — media source readiness surface (GET /api/media/sources) +
# secret write (PUT /api/media/sources/{name}/secret).
class SourceReadinessRow(BaseModel):
    """Per-source readiness for the Settings → Media tab."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str
    enabled: bool  # True iff disabled_reason is None
    in_chain: bool  # True iff name appears in config.media.sources
    kinds: tuple[Kind, ...]  # sorted(source.kinds) — frozenset has no order
    license_compatible: bool
    disabled_reason: str | None  # non-None iff !enabled
    needs_config: bool  # True for value-paste sources (currently mobyGames)


class SourceReadiness(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    sources: tuple[SourceReadinessRow, ...]


class SourceSecret(BaseModel):
    """Request body for PUT /api/media/sources/{name}/secret."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    secret: str = Field(min_length=1)  # empty / whitespace-only → 422 before any write

    @field_validator("secret", mode="before")
    @classmethod
    def _strip_secret(cls, v: object) -> object:
        # Keys are pasted; a trailing newline or surrounding spaces would be
        # written verbatim to the 0600 dotfile and break the upstream auth
        # header. Strip first — a whitespace-only paste then fails min_length=1
        # → 422 (before any write). (FP33 L4)
        return v.strip() if isinstance(v, str) else v


class UiConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    theme: Literal["dark", "light", "double_dragon", "pacman", "sf2", "neogeo"] = "dark"
    layout: Literal["masonry", "list", "covers", "grouped"] = "masonry"
    default_sort: Literal["name", "year", "manufacturer", "rating"] = "name"
    show_alternatives_indicator: bool = True
    cards_per_row_hint: Literal["auto", 4, 5, 6, 8] = "auto"
    cart_clear_on_copy: Literal["always", "on_success", "never"] = "on_success"


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


class AppConfigPatch(BaseModel):
    """FP21-N: typed PATCH body for ``/api/config``.

    Per P04 spec lines 645-657. Each section is optional and accepts a
    ``dict[str, Any]`` (the section's own validation runs on the merged
    full ``AppConfig`` after ``deep_merge``). ``extra="forbid"`` rejects
    unknown top-level keys so typos / malicious sections never reach the
    merge step. Combined with ``deep_merge``'s ``_MERGE_MAX_DEPTH`` cap
    this closes the bare-dict-ingestion DoS surface.
    """

    model_config = ConfigDict(extra="forbid")
    paths: dict[str, Any] | None = None
    server: dict[str, Any] | None = None
    filters: dict[str, Any] | None = None
    picker: dict[str, Any] | None = None
    media: dict[str, Any] | None = None
    ui: dict[str, Any] | None = None
    updates: dict[str, Any] | None = None
    fs: dict[str, Any] | None = None

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
# Per-route request bodies (small singletons).
# ---------------------------------------------------------------------------


class NotesPutRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    notes: str = Field(max_length=4096)


class OverridePostRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    parent: str
    winner: str


class EmptyBody(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# ---------------------------------------------------------------------------
# Filesystem / Setup / Updates / Help — re-exported from sibling modules.
# Extracted by FP24-EE; further sibling-modules added in DS02 A5.
# ---------------------------------------------------------------------------

from mame_curator.api.schemas_copy import (  # noqa: E402
    ActivityPage,
    CopyAbortRequest,
    CopyJobRequest,
    DryRunReport,
    HistoryItem,
    HistoryListing,
    JobAccepted,
    JobEvent,
    JobStatus,
)
from mame_curator.api.schemas_fs import (  # noqa: E402
    FsAllowedRoot,
    FsAllowedRoots,
    FsDriveRoots,
    FsEntry,
    FsGrantRootRequest,
    FsListing,
    FsPath,
)
from mame_curator.api.schemas_games import (  # noqa: E402
    Alternatives,
    Badge,
    Explanation,
    GameCard,
    GameDetail,
    GamesPage,
    LibraryFacets,
    Notes,
    Stats,
    ValidateRequest,
    ValidateResponse,
)
from mame_curator.api.schemas_overrides import (  # noqa: E402
    OverridesEntry,
    OverridesView,
    SessionsListing,
    SessionUpsertRequest,
    StatePostRequest,
    StateView,
)
from mame_curator.api.schemas_setup import (  # noqa: E402
    AppUpdateInfo,
    HelpContent,
    HelpIndex,
    HelpTopic,
    SetupCheck,
    SetupPaths,
    SetupPathStatus,
    SetupReferenceFiles,
    SetupReferenceStatus,
    UpdatesCheck,
)

# Explicit __all__ so mypy --strict's no_implicit_reexport flags this
# module as a public re-export point. Existing callers of
# `from mame_curator.api.schemas import SetupCheck, GameCard, ...`
# keep working unchanged.
__all__ = (
    "ActivityPage",
    "Alternatives",
    "AppConfig",
    "AppConfigPatch",
    "AppConfigResponse",
    "AppUpdateInfo",
    "Badge",
    "ConfigExportBundle",
    "CopyAbortRequest",
    "CopyJobRequest",
    "DryRunReport",
    "EmptyBody",
    "Explanation",
    "FsAllowedRoot",
    "FsAllowedRoots",
    "FsConfig",
    "FsDriveRoots",
    "FsEntry",
    "FsGrantRootRequest",
    "FsListing",
    "FsPath",
    "GameCard",
    "GameDetail",
    "GamesPage",
    "HelpContent",
    "HelpIndex",
    "HelpTopic",
    "HistoryItem",
    "HistoryListing",
    "JobAccepted",
    "JobEvent",
    "JobStatus",
    "LaunchResponse",
    "LibraryFacets",
    "MediaConfig",
    "Notes",
    "NotesPutRequest",
    "OverridePostRequest",
    "OverridesEntry",
    "OverridesView",
    "PathsConfig",
    "ServerConfig",
    "SessionUpsertRequest",
    "SessionsListing",
    "SetupCheck",
    "SetupPathStatus",
    "SetupPaths",
    "SetupReferenceFiles",
    "SetupReferenceStatus",
    "Snapshot",
    "SnapshotsListing",
    "StatePostRequest",
    "StateView",
    "Stats",
    "UiConfig",
    "UpdatesCheck",
    "UpdatesConfig",
    "ValidateRequest",
    "ValidateResponse",
)

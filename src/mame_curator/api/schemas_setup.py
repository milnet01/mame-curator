"""Setup / updates / help wire-models.

FP24-EE: extracted out of ``schemas.py`` (over the 500-line hard cap
per coding-standards § 2). ``schemas.py`` re-exports these names so
existing ``from mame_curator.api.schemas import SetupCheck`` callers
keep working.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

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
    """Setup-check response model.

    FP24-BB: the derived ``listxml_available`` boolean was removed —
    no consumer ever used it because ListxmlBanner re-derives the
    file-missing vs parsed-empty distinction from the raw fields to
    pick a different body for each.

    FP22-A: ``retroarch_configured`` is the AND of ``paths.retroarch``
    and ``paths.retroarch_core`` both being non-null. The frontend
    Launch button (FP19) gates on this so a misconfigured user sees
    a disabled button and inline pointer to Settings → Paths instead
    of a 422 toast after click. The Setup banner mirrors the same
    bit for at-a-glance config state.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    config_present: bool
    paths: SetupPaths
    reference_files: SetupReferenceFiles
    cloneof_map_size: int
    retroarch_configured: bool


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

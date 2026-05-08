"""Filesystem-picker wire-models.

FP24-EE: extracted out of ``schemas.py`` (over the 500-line hard cap
per coding-standards § 2). ``schemas.py`` re-exports these names so
existing ``from mame_curator.api.schemas import FsEntry`` callers
keep working.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


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

"""R35 (setup-check) + R36 (updates-check)."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends

from mame_curator import __version__
from mame_curator.api.routes._deps import get_world
from mame_curator.api.schemas import (
    AppUpdateInfo,
    SetupCheck,
    SetupPaths,
    SetupPathStatus,
    SetupReferenceFiles,
    SetupReferenceStatus,
    UpdatesCheck,
)
from mame_curator.api.state import WorldState
from mame_curator.parser import ParserError, parse_dat

router = APIRouter()


def _probe_path(path: Path, *, kind: str, writable: bool = False) -> SetupPathStatus:
    exists = path.exists()
    readable = exists and os.access(path, os.R_OK)
    is_writable = exists and writable and os.access(path, os.W_OK)
    return SetupPathStatus(path=str(path), exists=exists, readable=readable, writable=is_writable)


def _probe_dat(path: Path) -> SetupPathStatus:
    base = _probe_path(path, kind="file")
    parses: bool | None = None
    if base.exists and base.readable:
        try:
            parse_dat(path)
            parses = True
        except ParserError:
            parses = False
    return base.model_copy(update={"dat_parses": parses})


def _probe_ref(path: Path | None) -> SetupReferenceStatus:
    if path is None:
        return SetupReferenceStatus(path="", exists=False)
    return SetupReferenceStatus(path=str(path), exists=path.exists())


@router.get("/api/setup/check", response_model=SetupCheck)
def setup_check(world: WorldState = Depends(get_world)) -> SetupCheck:
    p = world.config.paths
    return SetupCheck(
        config_present=True,
        paths=SetupPaths(
            source_roms=_probe_path(p.source_roms, kind="dir"),
            source_dat=_probe_dat(p.source_dat),
            dest_roms=_probe_path(p.dest_roms, kind="dir", writable=True),
        ),
        reference_files=SetupReferenceFiles(
            catver=_probe_ref(p.catver),
            languages=_probe_ref(p.languages),
            bestgames=_probe_ref(p.bestgames),
            mature=_probe_ref(p.mature),
            series=_probe_ref(p.series),
            listxml=_probe_ref(p.listxml),
        ),
    )


@router.get("/api/updates/check", response_model=UpdatesCheck)
def updates_check() -> UpdatesCheck:
    return UpdatesCheck(
        app=AppUpdateInfo(
            current_version=__version__,
            latest_version=None,
            update_available=False,
        ),
        ini=(),
    )

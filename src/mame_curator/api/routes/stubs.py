"""R35 (setup-check). R36 (updates-check) moved to ``routes/updates.py``."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends

from mame_curator.api.fs import validate_fs_path
from mame_curator.api.routes._deps import get_world
from mame_curator.api.schemas import (
    DatCheck,
    SetupCheck,
    SetupPaths,
    SetupPathStatus,
    SetupReferenceFiles,
    SetupReferenceStatus,
)
from mame_curator.api.state import WorldState, file_stamp
from mame_curator.parser import ParserError, check_dat_start, parse_dat

router = APIRouter()


def _probe_path(path: Path, *, kind: str, writable: bool = False) -> SetupPathStatus:
    """Probe a path's existence + access bits, gated on ``kind``.

    FP24-CC: ``kind`` now drives an ``is_dir`` / ``is_file`` check so
    a file at a directory path (or vice versa) reports ``exists=False``
    rather than masquerading as valid. The parameter was previously
    discarded silently.
    """
    if kind == "dir":
        exists = path.is_dir()
    elif kind == "file":
        exists = path.is_file()
    else:  # pragma: no cover — guarded by the typed callers below.
        raise ValueError(f"_probe_path: unsupported kind {kind!r}")
    readable = exists and os.access(path, os.R_OK)
    is_writable = exists and writable and os.access(path, os.W_OK)
    return SetupPathStatus(path=str(path), exists=exists, readable=readable, writable=is_writable)


# mame-curator-1172: the last probe's answer, keyed by `file_stamp`, so a DAT
# the world did not load (setup mode) is not re-read on every check either.
_last_probe: tuple[tuple[str, int, int], bool] | None = None


def _dat_parses(path: Path, world: WorldState) -> bool:
    """Does the DAT at ``path`` parse? Read it only if it changed since last asked.

    mame-curator-1172: a full parse per check read the game list twice when
    the setup wizard finished, and again on every later check.
    """
    global _last_probe
    stamp = file_stamp(path)
    if stamp is not None and stamp == world.dat_stamp:
        return True
    if stamp is not None and _last_probe is not None and _last_probe[0] == stamp:
        return _last_probe[1]
    try:
        parse_dat(path)
        parses = True
    except ParserError:
        parses = False
    except OSError:  # No scratch space to unzip it: may pass next time, so not kept.
        return False
    if stamp is not None:
        _last_probe = (stamp, parses)
    return parses


def _probe_dat(path: Path, world: WorldState) -> SetupPathStatus:
    base = _probe_path(path, kind="file")
    parses: bool | None = None
    if base.exists and base.readable:
        parses = _dat_parses(path, world)
    return base.model_copy(update={"dat_parses": parses})


def _probe_ref(path: Path | None) -> SetupReferenceStatus:
    if path is None:
        return SetupReferenceStatus(path="", exists=False)
    return SetupReferenceStatus(path=str(path), exists=path.exists())


@router.get("/api/setup/check", response_model=SetupCheck)
def setup_check(world: WorldState = Depends(get_world)) -> SetupCheck:
    p = world.config.paths
    listxml_status = _probe_ref(p.listxml)
    cloneof_map_size = len(world.cloneof_map)
    retroarch_configured = p.retroarch is not None and p.retroarch_core is not None
    return SetupCheck(
        config_present=True,
        paths=SetupPaths(
            source_roms=_probe_path(p.source_roms, kind="dir"),
            source_dat=_probe_dat(p.source_dat, world),
            dest_roms=_probe_path(p.dest_roms, kind="dir", writable=True),
        ),
        reference_files=SetupReferenceFiles(
            catver=_probe_ref(p.catver),
            languages=_probe_ref(p.languages),
            bestgames=_probe_ref(p.bestgames),
            mature=_probe_ref(p.mature),
            series=_probe_ref(p.series),
            listxml=listxml_status,
        ),
        cloneof_map_size=cloneof_map_size,
        retroarch_configured=retroarch_configured,
        setup_required=world.setup_required,
    )


@router.get("/api/setup/dat-check", response_model=DatCheck)
def dat_check(path: str, world: WorldState = Depends(get_world)) -> DatCheck:
    """mame-curator-1208: the wizard's list step refuses another file at once.

    Only where the picker may look. Reads up to the first machine, so it is
    quick; a file broken further on is still found by the save.
    """
    requested = validate_fs_path(path, world.allowed_roots)
    try:
        check_dat_start(requested)
    except ParserError:
        return DatCheck(path=str(requested), parses=False)
    return DatCheck(path=str(requested), parses=True)

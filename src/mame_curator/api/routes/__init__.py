"""Mounts every domain router onto a single top-level APIRouter."""

from __future__ import annotations

from fastapi import APIRouter

from mame_curator.api.routes import (
    activity,
    config,
    copy,
    curate,
    fs,
    games,
    media,
    stubs,
)
from mame_curator.api.routes import (
    help as help_,
)

router = APIRouter()
router.include_router(games.router)
router.include_router(curate.router)
router.include_router(config.router)
router.include_router(copy.router)
router.include_router(activity.router)
router.include_router(fs.router)
router.include_router(stubs.router)
router.include_router(help_.router)
router.include_router(media.router)

__all__ = ["router"]

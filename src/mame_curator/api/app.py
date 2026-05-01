"""FastAPI factory + lifespan.

Per ``docs/specs/P04.md`` § Lifespan + ``app.state`` model.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from mame_curator.api.errors import install_handlers
from mame_curator.api.jobs import JobManager
from mame_curator.api.routes import router as api_router
from mame_curator.api.state import build_world

logger = logging.getLogger(__name__)


def create_app(config_path: Path) -> FastAPI:
    """Build a configured FastAPI application instance."""
    config_path = Path(config_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        world = build_world(config_path)
        app.state.world = world
        app.state.job = JobManager(history_dir=world.data_dir / "copy-history")
        try:
            yield
        finally:
            jm: JobManager = app.state.job
            current = jm.current
            if current is not None:
                current.controller.cancel()
                current.thread.join(timeout=5.0)

    app = FastAPI(title="MAME Curator", version="0.0.1", lifespan=lifespan)
    install_handlers(app)
    app.include_router(api_router)
    return app

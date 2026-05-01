"""FastAPI factory + lifespan.

Per ``docs/specs/P04.md`` § Lifespan + ``app.state`` model.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
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
        # FP09 B4: shared httpx.AsyncClient for the media proxy. Per-request
        # AsyncClient creation triggers a fresh TLS handshake on every R39
        # request — 50 thumbnails per browse view → 50 handshakes against
        # `raw.githubusercontent.com`. One client, reused, amortizes TLS
        # negotiation across the connection-pool lifetime (the default httpx
        # client is HTTP/1.1 with keep-alive; HTTP/2 multiplexing requires
        # `httpx[http2]` extras + `http2=True` and is a P05 concern).
        # P05: 10s timeout moves from per-call (was inline in routes/media.py)
        # to client construction so fetch_with_cache(...) inherits it without
        # a per-call timeout= argument.
        app.state.media_client = httpx.AsyncClient(timeout=10.0)
        try:
            yield
        finally:
            await app.state.media_client.aclose()
            jm: JobManager = app.state.job
            current = jm.current
            if current is not None:
                current.controller.cancel()
                current.thread.join(timeout=5.0)

    app = FastAPI(title="MAME Curator", version="0.0.1", lifespan=lifespan)
    install_handlers(app)
    app.include_router(api_router)
    return app

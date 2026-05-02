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
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from mame_curator.api.errors import install_handlers
from mame_curator.api.jobs import JobManager
from mame_curator.api.routes import router as api_router
from mame_curator.api.state import build_world

logger = logging.getLogger(__name__)

# `src/mame_curator/api/app.py` → parents[3] = repo root.
_FRONTEND_DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"


class _SPAStaticFiles(StaticFiles):
    """`StaticFiles` that serves `index.html` for any 404 — react-router fallback.

    Vanilla `StaticFiles(html=True)` only serves `index.html` when the
    request hits a directory; deep SPA links like `/sessions/foo` 404. The
    SPA contract is "any non-API URL renders the SPA shell and the router
    decides what to show," so we catch the 404 from `super().get_response`
    and re-issue against `index.html`. Consumers that want a real 404
    (asset under `/assets/...` that doesn't exist) still see it because
    the ``api_router`` is mounted before this, and within the static dir
    `/assets/missing.js` will resolve to a 404 from this method's
    fallback as well — but that's by design, since the SPA boots and
    react-router shows its in-app NotFound view.
    """

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise
            return await super().get_response("index.html", scope)


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
        # FP10 A1: follow_redirects=True so a libretro CDN 301/302 transits
        # transparently instead of surfacing as MediaFetchError("upstream 301").
        app.state.media_client = httpx.AsyncClient(timeout=10.0, follow_redirects=True)
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
    # Mount the SPA bundle on / when `frontend/dist/` is present (production
    # path). The mount is registered AFTER the API router so /api/* and
    # /media/* routes keep precedence; the catch-all only fires on a
    # non-API request. `html=True` makes /<anything> fall back to
    # index.html so react-router's client-side routes resolve.
    if _FRONTEND_DIST.is_dir():
        app.mount(
            "/",
            _SPAStaticFiles(directory=_FRONTEND_DIST, html=True),
            name="frontend",
        )
    return app

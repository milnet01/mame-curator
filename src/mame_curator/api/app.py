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
    """`StaticFiles` that serves `index.html` for path-shaped 404s only.

    Vanilla `StaticFiles(html=True)` only serves `index.html` when the
    request resolves to a directory; deep SPA links like `/sessions/foo`
    return 404. The SPA contract is "any non-API, non-asset URL renders
    the SPA shell and the router decides what to show," so we catch
    the 404 from `super().get_response` and re-issue against
    `index.html` — BUT only for path-shaped URLs.

    Carve-outs (FP11 § A2 — must NOT cascade to `index.html`):

    - `api/`, `media/` — typo'd or unrouted API paths must surface as
      a real 404 so the frontend's zod validator distinguishes
      "missing route" from "shape mismatch". A 200 + HTML for
      `/api/sesions/foo` masks routing bugs.
    - `assets/` — a missing asset under the bundle MUST 404 visibly.
      Returning `index.html` makes the browser parse HTML as JS and
      throw `Uncaught SyntaxError: Unexpected token '<'`, breaking
      SPA boot opaquely with no clue in DevTools.

    Anything else (`/sessions/foo`, `/help/topic-x`, `/`) hits the
    fallback, the SPA boots, react-router renders the right view.
    """

    _NO_FALLBACK_PREFIXES = ("api/", "media/", "assets/")

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise
            # Starlette joins the URL path against the on-disk directory
            # using `os.path`, which normalises separators to the host's
            # native form. On Windows that's `\\`, so a naive
            # `path.startswith("api/")` misses `api\typo`. Normalise back
            # to forward slashes for the prefix check (the underlying
            # 404 was raised by Starlette's resolver, which already
            # handled the OS-side normalisation; we only need a
            # uniform string for the carve-out comparison).
            posix_path = path.replace("\\", "/")
            if posix_path.startswith(self._NO_FALLBACK_PREFIXES):
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

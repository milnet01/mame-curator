"""Static-file mount for the SPA bundle.

P06 step 9: ``api/app.py`` mounts ``frontend/dist/`` at ``/`` when the
directory exists (production path). The mount is conditional and lazy —
in dev mode, ``frontend/dist/`` is absent and the developer runs the
Vite dev server on :5173.

Tests verify both halves of the conditional plus the precedence rule
(API routes outrank the catch-all mount).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient


def _mount_names(app: Any) -> list[str]:
    """Return the names of every Mount route on the app, top-to-bottom."""
    from starlette.routing import Mount

    return [r.name for r in app.routes if isinstance(r, Mount) and r.name]


def test_static_mount_absent_when_dist_missing(
    monkeypatch: pytest.MonkeyPatch,
    config_file: Path,
    fake_home: Path,
) -> None:
    """Without frontend/dist/, no `frontend` mount is registered."""
    from mame_curator.api import app as app_module
    from mame_curator.api import create_app

    monkeypatch.setattr(app_module, "_FRONTEND_DIST", Path("/nonexistent-frontend-dist"))
    rebuilt = create_app(config_file)
    assert "frontend" not in _mount_names(rebuilt)


def test_static_mount_registered_and_serves_index(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    config_file: Path,
    fake_home: Path,
) -> None:
    """With a stub frontend/dist/, the mount serves index.html on GET /.

    Builds a minimal stub (one ``index.html``), points the module-level
    ``_FRONTEND_DIST`` at it, rebuilds the app, and asserts the mount
    serves the stub body. Also asserts the existing /api/health endpoint
    still wins precedence over the catch-all mount.
    """
    stub = tmp_path / "frontend" / "dist"
    stub.mkdir(parents=True)
    sentinel_html = "<!doctype html><title>P06 stub</title>"
    (stub / "index.html").write_text(sentinel_html, encoding="utf-8")

    from mame_curator.api import app as app_module
    from mame_curator.api import create_app

    monkeypatch.setattr(app_module, "_FRONTEND_DIST", stub)
    rebuilt = create_app(config_file)
    assert "frontend" in _mount_names(rebuilt)

    with TestClient(rebuilt) as client:
        # GET /  → SPA index.
        spa = client.get("/")
        assert spa.status_code == 200
        assert "P06 stub" in spa.text

        # GET /unknown/route → react-router fallback (html=True).
        fallback = client.get("/unknown/spa/route")
        assert fallback.status_code == 200
        assert "P06 stub" in fallback.text

        # GET /api/* still routes to the API, not the mount.
        # /api/games is the canonical R01 route and does not require a job.
        api = client.get("/api/games?page=1&page_size=1")
        assert api.status_code == 200
        # Response shape is the GamesPage envelope, not the SPA HTML.
        body = api.json()
        assert "items" in body
        assert "total" in body

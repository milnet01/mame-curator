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


def test_undefined_api_path_returns_404_not_spa_html(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    config_file: Path,
    fake_home: Path,
) -> None:
    """FP11 § A2: undefined /api/* must 404, NOT cascade to index.html.

    Without the prefix carve-out, a typo'd `/api/sesions/foo` would
    fall through the SPA mount and return 200 + HTML, masking a real
    routing bug. The frontend's zod validator rejects HTML as JSON
    and the user sees a generic toast — drift between contract and
    behaviour.
    """
    stub = tmp_path / "frontend" / "dist"
    stub.mkdir(parents=True)
    (stub / "index.html").write_text("<!doctype html><title>SPA</title>", encoding="utf-8")

    from mame_curator.api import app as app_module
    from mame_curator.api import create_app

    monkeypatch.setattr(app_module, "_FRONTEND_DIST", stub)
    rebuilt = create_app(config_file)
    with TestClient(rebuilt) as client:
        # Each of these is either an unrouted /api or /media path. The
        # exact 4xx code varies (router 404 vs media-kind 400) — what
        # matters is "NOT 200 + SPA HTML cascade".
        for path in (
            "/api/typo",
            "/api/games/typo/notes/extra",
            "/media/x",  # too few path segments — router 404
            "/media/x/y/z",  # too many path segments — router 404
        ):
            r = client.get(path)
            assert 400 <= r.status_code < 500, (
                f"{path}: expected 4xx (no SPA cascade), got {r.status_code}"
            )
            assert "<html" not in r.text.lower(), (
                f"{path}: SPA HTML cascaded — fix _SPAStaticFiles carve-out"
            )


def test_missing_asset_returns_404_not_spa_html(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    config_file: Path,
    fake_home: Path,
) -> None:
    """FP11 § A2: GET /assets/missing.js MUST 404, never serve index.html.

    If the SPA fallback returns index.html for missing assets, the
    browser parses HTML as JS → `Uncaught SyntaxError: Unexpected
    token '<'` → opaque SPA boot failure with no clue what went
    wrong.
    """
    stub = tmp_path / "frontend" / "dist"
    (stub / "assets").mkdir(parents=True)
    (stub / "index.html").write_text("<!doctype html><title>SPA</title>", encoding="utf-8")
    (stub / "assets" / "real.js").write_text("// real asset", encoding="utf-8")

    from mame_curator.api import app as app_module
    from mame_curator.api import create_app

    monkeypatch.setattr(app_module, "_FRONTEND_DIST", stub)
    rebuilt = create_app(config_file)
    with TestClient(rebuilt) as client:
        # Real asset still serves.
        ok = client.get("/assets/real.js")
        assert ok.status_code == 200
        assert "real asset" in ok.text

        # Missing asset 404s (does NOT cascade to index.html).
        missing = client.get("/assets/missing.js")
        assert missing.status_code == 404
        assert "<html" not in missing.text.lower()

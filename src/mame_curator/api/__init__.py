"""HTTP API surface for MAME Curator (Phase 4 — in flight).

Public surface (per `docs/specs/P04.md`):

- ``create_app(config) -> FastAPI`` — application factory.
- ``JobManager`` — singleton owning the in-flight copy job.
- ``ApiException`` + per-domain subclasses — typed errors rendered into the
  ``ApiErrorBody`` wire envelope by the FastAPI exception handler.

Implementation lands in P04 Step 4. The current shape exists so Step-3
tests can import the planned surface; every callable raises
``NotImplementedError("P04 — not yet implemented")`` until Step 4.
"""

from __future__ import annotations

from mame_curator.api.app import create_app

__all__ = ["create_app"]

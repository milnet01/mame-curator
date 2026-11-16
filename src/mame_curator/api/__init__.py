"""HTTP API for MAME Curator.

The package exports one name, ``create_app(config_path, *, bind_host=None)``,
the application factory. Other pieces are imported from their own modules,
for example ``JobManager`` from ``api.jobs`` and ``ApiException`` from
``api.errors``. The contract is ``api/spec.md``.
"""

from __future__ import annotations

from mame_curator.api.app import create_app

__all__ = ["create_app"]

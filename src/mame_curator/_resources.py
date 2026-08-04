"""Where bundled data files live, source checkout or frozen bundle.

PyInstaller unpacks the bundle into a temporary extraction root and
points `sys._MEIPASS` at it, so any path computed from `__file__`'s
position in the *source* tree resolves outside the bundle. Every lookup
of a shipped data file goes through `bundle_root()` instead.

See `docs/specs/mame-curator-1095-desktop-bundles.md` § 4.3.
"""

from __future__ import annotations

import sys
from pathlib import Path


def bundle_root() -> Path:
    """The extraction root when frozen, else the repository root."""
    if getattr(sys, "frozen", False):
        # Set by PyInstaller under both one-file and one-dir, and absent
        # from `sys`'s type stubs because it exists only in a bundle.
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    # `src/mame_curator/_resources.py` → parents[2] = repo root.
    return Path(__file__).resolve().parents[2]


def frontend_dist() -> Path:
    """The built SPA. Absent in a dev checkout that has not run `npm build`."""
    return bundle_root() / "frontend" / "dist"

"""Top-level pytest configuration.

Subdirectory ``conftest.py`` files (``tests/parser/``, ``tests/filter/``)
add per-suite fixtures; this top-level file handles shared environment
setup that must run before any subordinate ``conftest.py`` imports
resolve.
"""

from __future__ import annotations

# Force Qt's offscreen QPA platform before anything imports QApplication.
# MAME_Curator is a CLI tool today and doesn't pull in Qt, but adding
# the safe default here makes it impossible for a future Qt-using
# test (or a transitive import) to flash a real window onto the
# desktop hosting the test runner. `setdefault` lets a CI override
# (e.g. QT_QPA_PLATFORM=minimal) still win.
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

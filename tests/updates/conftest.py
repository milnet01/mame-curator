"""Shared fixtures for ``tests/updates/`` tests."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _no_sleep(no_sleep: None) -> None:
    """Autouse the shared ``no_sleep`` fixture (``tests/conftest.py``) across the
    whole updates suite.

    Both ``refresh_inis`` (test_ini) and ``refresh-snaps`` (test_snaps) drive
    the ``downloads`` retry-backoff path, so neither should actually sleep.
    Was a byte-identical per-file passthrough in both modules
    (mame-curator-1054f).
    """

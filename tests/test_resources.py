"""Tests for `mame_curator._resources` (mame-curator-1095 INV-11).

`bundle_root()` is the single place that knows whether this process is a
PyInstaller bundle or a source checkout, so both branches are exercised
here by monkeypatching the two attributes PyInstaller sets.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


def test_frontend_dist_follows_meipass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """INV-11, frozen half — the SPA is looked up inside the extraction root.

    PyInstaller sets `sys.frozen` and `sys._MEIPASS` under both one-file
    and one-dir; neither exists in a source run, hence `raising=False`.
    """
    from mame_curator._resources import bundle_root, frontend_dist

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert bundle_root() == tmp_path
    assert frontend_dist() == tmp_path / "frontend" / "dist"


def test_bundle_root_is_repo_root_when_not_frozen(monkeypatch: pytest.MonkeyPatch) -> None:
    """INV-11, source half — the repository root.

    Identified by a marker file rather than by restating the module's own
    `parents[...]` count, which would pass for any arithmetic.
    """
    from mame_curator._resources import bundle_root, frontend_dist

    monkeypatch.delattr(sys, "frozen", raising=False)

    root = bundle_root()
    assert (root / "pyproject.toml").is_file()
    assert frontend_dist() == root / "frontend" / "dist"

"""Tests for `mame_curator._atomic.atomic_write_text` (FP05 C2 + C3)."""

from __future__ import annotations

import errno
import os
from pathlib import Path

import pytest


def test_atomic_write_text_cleans_tmp_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C2 — when `os.replace` raises mid-write, the helper must clean the
    `.tmp` sibling so a subsequent run doesn't see a stale half-written
    file. The `try/finally` cleanup is the load-bearing line."""
    from mame_curator._atomic import atomic_write_text

    target = tmp_path / "report.json"

    def _fail(*_args: object, **_kwargs: object) -> None:
        raise OSError(errno.EIO, "synthetic disk error")

    monkeypatch.setattr(os, "replace", _fail)

    with pytest.raises(OSError):
        atomic_write_text(target, "should-never-land")

    # No `.tmp` leftover anywhere in the parent directory.
    leftovers = [p for p in tmp_path.iterdir() if p.suffix == ".tmp" or ".tmp" in p.name]
    assert leftovers == [], f"unexpected .tmp leftovers: {leftovers}"
    # The target itself must not have been created either.
    assert not target.exists()


def test_atomic_write_text_exdev_raises_typed_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C3 — `os.replace` raising EXDEV (cross-filesystem rename, e.g.
    target resolves through a symlink across mount points) must be
    re-raised with EXDEV identifiable. The current implementation lets
    raw OSError(EXDEV) escape; the helper should distinguish EXDEV from
    a generic OSError so callers can present a meaningful error."""
    from mame_curator._atomic import atomic_write_text

    target = tmp_path / "report.json"

    def _exdev(*_args: object, **_kwargs: object) -> None:
        raise OSError(errno.EXDEV, "Invalid cross-device link")

    monkeypatch.setattr(os, "replace", _exdev)

    with pytest.raises(OSError) as excinfo:
        atomic_write_text(target, "doesnt-matter")
    assert excinfo.value.errno == errno.EXDEV


def test_atomic_write_text_round_trip(tmp_path: Path) -> None:
    """Sanity check: golden path writes the text and leaves no tmp."""
    from mame_curator._atomic import atomic_write_text

    target = tmp_path / "config.json"
    atomic_write_text(target, '{"hello": "world"}\n')
    assert target.read_text() == '{"hello": "world"}\n'
    leftovers = [p for p in tmp_path.iterdir() if ".tmp" in p.name]
    assert leftovers == []

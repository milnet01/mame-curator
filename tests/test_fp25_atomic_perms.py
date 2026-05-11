"""FP25-D: ``_atomic.atomic_write_*`` perm-mode parity (0o644 not 0o600).

Pre-FP25-D, ``tempfile.NamedTemporaryFile`` creates the tmp file with mode
``0o600`` (owner-only read/write). ``os.replace`` then moves the tmp's
inode onto the target path, so the final file is also ``0o600``.
``copy/activity.py``'s ``os.open(..., 0o644)`` produces world-readable
files. The mismatch means RetroArch playlists, recyclebin manifests,
config.yaml snapshots, and overrides.yaml are owner-only readable while
activity.jsonl is world-readable — confusing and brittle for users who
inspect or share the data directory.

FP25-D pins the helper at ``0o644`` via ``os.fchmod(tmp.fileno(), 0o644)``
before the close+replace step. Skipped on Windows where POSIX mode bits
don't apply (only the read-only bit, which neither side sets).
"""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

import pytest

from mame_curator._atomic import atomic_write_bytes, atomic_write_text

_WINDOWS = sys.platform == "win32"


@pytest.mark.skipif(_WINDOWS, reason="POSIX mode bits don't apply on Windows")
def test_fp25_d_atomic_write_text_creates_0o644_file(tmp_path: Path) -> None:
    """``atomic_write_text`` lands the target at mode ``0o644``.

    Parity with ``copy/activity.py``'s ``os.open(..., 0o644)`` so every
    file the project writes under ``data/`` is consistently world-
    readable.
    """
    target = tmp_path / "config.yaml"
    atomic_write_text(target, "key: value\n")
    mode = stat.S_IMODE(target.stat().st_mode)
    assert mode == 0o644, f"expected 0o644 for parity with activity.py, got {oct(mode)}"


@pytest.mark.skipif(_WINDOWS, reason="POSIX mode bits don't apply on Windows")
def test_fp25_d_atomic_write_bytes_creates_0o644_file(tmp_path: Path) -> None:
    """``atomic_write_bytes`` lands the target at mode ``0o644`` too."""
    target = tmp_path / "snap.bin"
    atomic_write_bytes(target, b"binary data")
    mode = stat.S_IMODE(target.stat().st_mode)
    assert mode == 0o644, f"expected 0o644 for parity with activity.py, got {oct(mode)}"


@pytest.mark.skipif(_WINDOWS, reason="POSIX mode bits don't apply on Windows")
def test_fp25_d_perms_are_not_inherited_from_existing_target(tmp_path: Path) -> None:
    """Re-writing an existing file resets perms to ``0o644``.

    Documents the deliberate trade-off: a user who ran ``chmod 600
    config.yaml`` would see the file's mode reset by the next
    PATCH /api/config. The choice prioritises consistent perms across
    the project's data directory over preserving user customisation.
    """
    target = tmp_path / "config.yaml"
    target.write_text("initial: value\n")
    os.chmod(target, 0o600)
    assert stat.S_IMODE(target.stat().st_mode) == 0o600

    atomic_write_text(target, "key: value\n")
    mode = stat.S_IMODE(target.stat().st_mode)
    assert mode == 0o644

"""Tests for project-internal recycle bin (`data/recycle/`)."""

from __future__ import annotations

import time
from datetime import timedelta
from pathlib import Path

from mame_curator.copy import purge_recycle, recycle_file


def test_recycle_moves_file_into_timestamped_dir(tmp_path: Path) -> None:
    """Recycled file lands in `<recycle_root>/<session_id>/<original-name>`."""
    src = tmp_path / "sf2.zip"
    src.write_bytes(b"some content")
    recycle_root = tmp_path / "recycle"

    new_path = recycle_file(
        src, reason="REPLACE_AND_RECYCLE", session_id="01HZZ", recycle_root=recycle_root
    )
    assert new_path.exists()
    assert new_path.name == "sf2.zip"
    assert new_path.parent.parent == recycle_root
    # Source removed (move, not copy).
    assert not src.exists()


def test_recycle_writes_manifest(tmp_path: Path) -> None:
    """manifest.json beside recycled file records reason + session_id."""
    src = tmp_path / "sf2.zip"
    src.write_bytes(b"x")
    recycle_root = tmp_path / "recycle"
    new_path = recycle_file(
        src, reason="REPLACE_AND_RECYCLE", session_id="01HZZ", recycle_root=recycle_root
    )
    manifest = new_path.parent / "manifest.json"
    assert manifest.exists()
    text = manifest.read_text(encoding="utf-8")
    assert "REPLACE_AND_RECYCLE" in text
    assert "01HZZ" in text


def test_recycle_retention_purges_old_entries(tmp_path: Path) -> None:
    """purge_recycle removes subdirs older than the threshold."""
    recycle_root = tmp_path / "recycle"
    recycle_root.mkdir()
    # Old subdir (40 days ago).
    old_dir = recycle_root / "2026-03-21T00-00-00Z"
    old_dir.mkdir()
    (old_dir / "old.zip").write_bytes(b"old")
    # Force mtime back 40 days.
    old_time = time.time() - 40 * 86400
    import os as _os

    _os.utime(old_dir, (old_time, old_time))
    _os.utime(old_dir / "old.zip", (old_time, old_time))

    # Fresh subdir (today).
    fresh_dir = recycle_root / "2026-04-30T12-00-00Z"
    fresh_dir.mkdir()
    (fresh_dir / "fresh.zip").write_bytes(b"fresh")

    dirs_purged, bytes_freed = purge_recycle(
        older_than=timedelta(days=30), recycle_root=recycle_root
    )
    assert dirs_purged == 1
    assert bytes_freed >= 3  # b"old" is 3 bytes plus directory overhead
    assert not old_dir.exists()
    assert fresh_dir.exists()


def test_recycle_retention_keeps_everything_when_threshold_exceeded(tmp_path: Path) -> None:
    """Threshold larger than oldest entry purges nothing."""
    recycle_root = tmp_path / "recycle"
    recycle_root.mkdir()
    sub = recycle_root / "2026-04-29T00-00-00Z"
    sub.mkdir()
    (sub / "a.zip").write_bytes(b"a")

    dirs_purged, bytes_freed = purge_recycle(
        older_than=timedelta(days=365), recycle_root=recycle_root
    )
    assert dirs_purged == 0
    assert bytes_freed == 0
    assert sub.exists()


def test_recycle_idempotent_timestamp_collision(tmp_path: Path) -> None:
    """Two recycle calls in the same second don't clobber each other."""
    src1 = tmp_path / "a.zip"
    src1.write_bytes(b"a")
    src2 = tmp_path / "b.zip"
    src2.write_bytes(b"b")
    recycle_root = tmp_path / "recycle"

    p1 = recycle_file(src1, reason="x", session_id="s", recycle_root=recycle_root)
    p2 = recycle_file(src2, reason="x", session_id="s", recycle_root=recycle_root)
    # Both files exist after both calls.
    assert p1.exists() and p1.read_bytes() == b"a"
    assert p2.exists() and p2.read_bytes() == b"b"

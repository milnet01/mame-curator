"""A config-only snapshot must not delete files it never captured.

Every PATCH /api/config snapshots config.yaml alone into data/snapshots/,
and restoring any snapshot passes four targets (config, overrides,
sessions, notes). restore_snapshot deleted every target the snapshot
lacked, so restoring a routine settings snapshot wiped the user's
overrides, sessions and notes.
"""

from __future__ import annotations

from pathlib import Path

from mame_curator.api.persist import restore_snapshot, snapshot_files


def test_restoring_a_config_only_snapshot_keeps_the_other_files(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    overrides = tmp_path / "overrides.yaml"
    config.write_text("old: 1\n", encoding="utf-8")
    overrides.write_text("overrides: {pacman: puckman}\n", encoding="utf-8")
    snap_dir = tmp_path / "snapshots"

    snap_id = snapshot_files(snap_dir, {"config.yaml": config})
    config.write_text("new: 2\n", encoding="utf-8")
    restore_snapshot(snap_dir, snap_id, {"config.yaml": config, "overrides.yaml": overrides})

    assert config.read_text(encoding="utf-8") == "old: 1\n"
    assert overrides.read_text(encoding="utf-8") == "overrides: {pacman: puckman}\n"


def test_a_file_absent_when_snapshotted_is_still_removed(tmp_path: Path) -> None:
    """The original intent survives: a target the snapshot CAPTURED as absent
    is removed on restore, so the restore reverts cleanly."""
    config = tmp_path / "config.yaml"
    sessions = tmp_path / "sessions.yaml"
    config.write_text("a: 1\n", encoding="utf-8")
    snap_dir = tmp_path / "snapshots"

    snap_id = snapshot_files(snap_dir, {"config.yaml": config, "sessions.yaml": sessions})
    sessions.write_text("sessions: {}\n", encoding="utf-8")
    restore_snapshot(snap_dir, snap_id, {"config.yaml": config, "sessions.yaml": sessions})

    assert not sessions.exists()


def test_an_older_snapshot_without_a_covers_record_deletes_nothing(tmp_path: Path) -> None:
    """Snapshots written before the covers record are read as covering only
    the files they hold, so restoring one cannot delete anything else."""
    snap_dir = tmp_path / "snapshots"
    (snap_dir / "old").mkdir(parents=True)
    (snap_dir / "old" / "config.yaml").write_text("old: 1\n", encoding="utf-8")
    config = tmp_path / "config.yaml"
    notes = tmp_path / "notes.json"
    config.write_text("new: 2\n", encoding="utf-8")
    notes.write_text("{}", encoding="utf-8")

    restore_snapshot(snap_dir, "old", {"config.yaml": config, "notes.json": notes})

    assert config.read_text(encoding="utf-8") == "old: 1\n"
    assert notes.exists()


def test_the_covers_record_is_not_listed_as_a_file(tmp_path: Path) -> None:
    from mame_curator.api.persist import list_snapshots

    config = tmp_path / "config.yaml"
    config.write_text("a: 1\n", encoding="utf-8")
    snapshot_files(tmp_path / "snapshots", {"config.yaml": config})

    (entry,) = list_snapshots(tmp_path / "snapshots")
    assert entry["files"] == ("config.yaml",)

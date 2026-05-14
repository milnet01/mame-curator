"""Tests for project-internal recycle bin (`data/recycle/`)."""

from __future__ import annotations

import time
from datetime import timedelta
from pathlib import Path

import pytest

from mame_curator.copy import purge_recycle, recycle_file
from mame_curator.copy.types import ActivityEvent, ActivityEventType


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
    """``<basename>.manifest.json`` beside the recycled file records the metadata.

    FP21-D: per-file manifest naming (was a single ``manifest.json`` that
    multiple files in the same session-dir overwrote).
    """
    src = tmp_path / "sf2.zip"
    src.write_bytes(b"x")
    recycle_root = tmp_path / "recycle"
    new_path = recycle_file(
        src, reason="REPLACE_AND_RECYCLE", session_id="01HZZ", recycle_root=recycle_root
    )
    manifest = new_path.parent / "sf2.zip.manifest.json"
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


def test_fp21_d_per_file_manifests_dont_collide(tmp_path: Path) -> None:
    """FP21-D: recycling two files into the same session dir produces TWO
    manifests, one per file. Pre-fix the second call's ``manifest.json``
    overwrote the first, silently losing the first file's metadata.
    """
    src1 = tmp_path / "a.zip"
    src1.write_bytes(b"a")
    src2 = tmp_path / "b.zip"
    src2.write_bytes(b"b")
    recycle_root = tmp_path / "recycle"

    p1 = recycle_file(src1, reason="r1", session_id="s", recycle_root=recycle_root)
    p2 = recycle_file(src2, reason="r2", session_id="s", recycle_root=recycle_root)
    # Both files land in the SAME parent directory (no -1 / -2 counter
    # because the basenames differ).
    assert p1.parent == p2.parent
    # And each has its own manifest, distinct from the other.
    m1 = p1.parent / "a.zip.manifest.json"
    m2 = p1.parent / "b.zip.manifest.json"
    assert m1.exists() and m2.exists()
    assert "r1" in m1.read_text(encoding="utf-8")
    assert "r2" in m2.read_text(encoding="utf-8")


def test_fp21_d_source_intact_when_manifest_write_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FP21-D: write-manifest-then-move ordering means the source file is
    NEVER moved if the manifest write fails. Pre-fix used move-then-write
    with a rollback envelope (FP25-C); on rollback failure the source was
    orphaned. With write-first, the source is intact under any failure.
    """

    def failing_atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
        raise OSError("simulated ENOSPC")

    monkeypatch.setattr("mame_curator.copy.recyclebin.atomic_write_text", failing_atomic_write_text)

    src = tmp_path / "sf2.zip"
    src.write_bytes(b"original content")
    recycle_root = tmp_path / "recycle"

    with pytest.raises(Exception, match="manifest"):
        recycle_file(src, reason="x", session_id="s", recycle_root=recycle_root)

    # Source untouched — no rollback path was needed because the file
    # never moved.
    assert src.exists() and src.read_bytes() == b"original content"
    # No half-written state inside the recycle tree.
    target_dir = recycle_root / "s"
    if target_dir.exists():
        assert list(target_dir.iterdir()) == []


def test_fp21_f_purge_uses_manifest_recycled_at_over_dir_mtime(
    tmp_path: Path,
) -> None:
    """FP21-F: ``purge_recycle`` decides eligibility from
    ``manifest['recycled_at']``, not from directory mtime which advances
    on every new file added.

    Setup: recycle a file (writes manifest with NOW as recycled_at),
    then **artificially advance the dir mtime backwards** to a value 40
    days ago. Pre-fix the dir-mtime check would mark the dir purgeable;
    post-fix the manifest's NOW timestamp keeps it.
    """
    import os as _os

    recycle_root = tmp_path / "recycle"
    src = tmp_path / "sf2.zip"
    src.write_bytes(b"x")
    new_path = recycle_file(src, reason="x", session_id="s", recycle_root=recycle_root)
    target_dir = new_path.parent

    # Push BOTH dir and manifest mtimes back 40 days so dir-mtime would
    # decide purge eligible — but recycled_at inside the manifest is
    # still today.
    old_time = time.time() - 40 * 86400
    for child in target_dir.rglob("*"):
        _os.utime(child, (old_time, old_time))
    _os.utime(target_dir, (old_time, old_time))

    dirs_purged, bytes_freed = purge_recycle(
        older_than=timedelta(days=30), recycle_root=recycle_root
    )
    assert dirs_purged == 0, (
        "manifest's recycled_at is today; mtime backdating must not trigger purge"
    )
    assert bytes_freed == 0
    assert target_dir.exists()


# ---------------------------------------------------------------------------
# FP27 A3 — recyclebin activity-log events
#
# `copy/spec.md:266` promises:
#   "Each `recycle_file` call appends one `file_recycled` event to
#   `data/activity.jsonl`; each `purge_recycle` call appends one
#   `recycle_purged` event."
#
# At HEAD: `recycle_file` and `purge_recycle` perform their FS work and
# return, but never write to the activity log. The Activity UI tab is
# the user's only window onto what got recycled and when, so the
# missing audit trail is a half-shipped contract per the
# 2026-05-14 indie-review.
#
# A3 wires the existing `append_activity(event, log_path)` writer at
# `copy/activity.py:50` into both functions. The activity log path is
# derived from `recycle_root.parent / "activity.jsonl"` so a custom
# recycle_root naturally drives a sibling activity log (and the default
# `data/recycle/` recycle_root drives `data/activity.jsonl` —
# matching the design promise).
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason="FP27 T1b — A3 implementation not yet landed; this test stays "
    "RED until copy/recyclebin.py wires append_activity.",
    strict=True,
)
def test_recycle_file_appends_file_recycled_activity_event(tmp_path: Path) -> None:
    """FP27 A3 — `recycle_file(...)` appends one `FILE_RECYCLED` event
    line to the per-data-dir activity log.

    Pre-fix: no append happens; activity.jsonl absent → fails.
    Post-fix: exactly one event line is present; parses to an
    `ActivityEvent` whose outer + inner `event_type` are both
    `FILE_RECYCLED`, whose `session_id` matches the call's
    session_id, and whose `details.path` + `details.reason` carry the
    recycle call's path + reason.
    """
    data_dir = tmp_path / "data"
    recycle_root = data_dir / "recycle"
    activity_log = data_dir / "activity.jsonl"

    src = tmp_path / "sf2.zip"
    src.write_bytes(b"some bytes")

    new_path = recycle_file(
        src,
        reason="REPLACE_AND_RECYCLE",
        session_id="01ABC123",
        recycle_root=recycle_root,
    )
    assert new_path.exists()  # baseline (existing FS contract).

    assert activity_log.exists(), (
        "FP27 A3 — recycle_file must append a FILE_RECYCLED event to "
        f"{activity_log!s}; see `docs/specs/FP27.md` § A3."
    )
    lines = [ln for ln in activity_log.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1, (
        f"FP27 A3 — expected exactly one event line, got {len(lines)}: {lines!r}"
    )

    event = ActivityEvent.model_validate_json(lines[0])
    assert event.event_type == ActivityEventType.FILE_RECYCLED
    assert event.details.event_type == ActivityEventType.FILE_RECYCLED
    assert event.session_id == "01ABC123"
    # Inner FileRecycledDetails fields (verified against copy/types.py:286).
    assert event.details.path == str(src), (
        f"details.path expected {src!s}, got {event.details.path!r}"
    )
    assert event.details.reason == "REPLACE_AND_RECYCLE"


@pytest.mark.xfail(
    reason="FP27 T1b — A3 implementation not yet landed; this test stays "
    "RED until copy/recyclebin.py wires append_activity.",
    strict=True,
)
def test_purge_recycle_appends_recycle_purged_activity_event(tmp_path: Path) -> None:
    """FP27 A3 — `purge_recycle(...)` appends one `RECYCLE_PURGED`
    event line to the per-data-dir activity log.

    The event records the dir + byte counts that the function returns.
    `session_id` uses the sentinel `'_purge'` (purge isn't a session-
    scoped operation; the sentinel signals 'system action' to the
    Activity UI).
    """
    import os as _os

    data_dir = tmp_path / "data"
    recycle_root = data_dir / "recycle"
    activity_log = data_dir / "activity.jsonl"

    # Stage one recycled file dated 40 days ago so purge eats it.
    src = tmp_path / "old.zip"
    src.write_bytes(b"old bytes")
    new_path = recycle_file(
        src, reason="REPLACE_AND_RECYCLE", session_id="01OLD", recycle_root=recycle_root
    )
    target_dir = new_path.parent
    old_time = time.time() - 40 * 86400
    for child in target_dir.rglob("*"):
        _os.utime(child, (old_time, old_time))
    _os.utime(target_dir, (old_time, old_time))

    # Truncate the log so the recycle_file event from setup doesn't
    # pollute the purge assertion (the recycle wrote one FILE_RECYCLED
    # event; we only want to assert on the new RECYCLE_PURGED event).
    activity_log.write_text("", encoding="utf-8")

    dirs_purged, bytes_freed = purge_recycle(
        older_than=timedelta(days=30), recycle_root=recycle_root
    )
    assert dirs_purged == 1
    assert bytes_freed > 0  # at least the "old bytes" payload + manifest.

    assert activity_log.exists(), (
        "FP27 A3 — purge_recycle must append a RECYCLE_PURGED event to "
        f"{activity_log!s}; see `docs/specs/FP27.md` § A3."
    )
    lines = [ln for ln in activity_log.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1, (
        f"FP27 A3 — expected one RECYCLE_PURGED event, got {len(lines)}: {lines!r}"
    )

    event = ActivityEvent.model_validate_json(lines[0])
    assert event.event_type == ActivityEventType.RECYCLE_PURGED
    assert event.details.event_type == ActivityEventType.RECYCLE_PURGED
    # Sentinel session_id for system-scoped purge action.
    assert event.session_id == "_purge"
    assert event.details.dirs_purged == dirs_purged
    assert event.details.bytes_freed == bytes_freed

"""mame-curator-1230: the copy-run findings of the 2026-11-11 code review.

Each test names the finding it locks.
"""

from __future__ import annotations

import errno
import importlib
import json
import os
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from mame_curator.copy import executor, recyclebin, run_recycle, runner
from mame_curator.copy.errors import CopyExecutionError, RecycleError
from mame_curator.copy.run_state import RunState, finish_report, make_plan_summary
from mame_curator.copy.types import (
    AppendDecision,
    AppendDecisionKind,
    ConflictStrategy,
    CopyOutcome,
    CopyOutcomeStatus,
    CopyReportStatus,
    OverwriteRecord,
    RecycleRecord,
)
from tests.copy._runner_helpers import _machine, _plan
from tests.copy.conftest import _seed_existing_playlist

# `mame_curator.copy.preflight` the attribute is the function; this is the module.
preflight = importlib.import_module("mame_curator.copy.preflight")


def _src(tmp_path: Path, *names: str) -> Path:
    src = tmp_path / "src"
    src.mkdir(exist_ok=True)
    for name in names:
        (src / f"{name}.zip").write_bytes(name.encode() * 100)
    return src


def _dest(tmp_path: Path) -> Path:
    dest = tmp_path / "dest"
    dest.mkdir(exist_ok=True)
    return dest


def _items(dest: Path) -> list[dict[str, Any]]:
    return json.loads((dest / "mame.lpl").read_text(encoding="utf-8"))["items"]  # type: ignore[no-any-return]


# ---- CR-02-1: a narrowed CANCEL re-run --------------------------------------


def test_cancel_rerun_with_fewer_winners_keeps_the_playlist(tmp_path: Path) -> None:
    """CR-02-1: every winner present is not enough; the playlist holds others too."""
    src = _src(tmp_path, "kof94", "sf2")
    dest = _dest(tmp_path)
    for name in ("kof94", "sf2"):
        shutil.copy2(src / f"{name}.zip", dest / f"{name}.zip")
    _seed_existing_playlist(
        dest,
        [{"path": str(dest / f"{n}.zip"), "label": n} for n in ("kof94", "sf2")],
    )
    before = (dest / "mame.lpl").read_bytes()
    plan = _plan(
        winners=("kof94",),
        machines={"kof94": _machine("kof94")},
        bios_chain={},
        source_dir=src,
        dest_dir=dest,
    )

    report = runner.run_copy(plan, data_dir=tmp_path / "data")

    assert report.status is CopyReportStatus.CANCELLED_PLAYLIST_CONFLICT
    assert (dest / "mame.lpl").read_bytes() == before


def test_api_precheck_refuses_a_narrowed_cancel_rerun(tmp_path: Path) -> None:
    """CR-02-1: the API's own check answers the same way, before the worker starts."""
    from mame_curator.api.errors import PlaylistConflictCancelledError
    from mame_curator.api.job_preflight import check_playlist_conflict

    src = _src(tmp_path, "kof94", "sf2")
    dest = _dest(tmp_path)
    for name in ("kof94", "sf2"):
        shutil.copy2(src / f"{name}.zip", dest / f"{name}.zip")
    _seed_existing_playlist(
        dest, [{"path": str(dest / f"{n}.zip"), "label": n} for n in ("kof94", "sf2")]
    )
    plan = _plan(
        winners=("kof94",),
        machines={"kof94": _machine("kof94")},
        bios_chain={},
        source_dir=src,
        dest_dir=dest,
    )
    with pytest.raises(PlaylistConflictCancelledError):
        check_playlist_conflict(plan)


# ---- CR-02-4: APPEND keeps what it does not replace --------------------------


def test_append_keeps_an_entry_whose_winner_failed(tmp_path: Path) -> None:
    """CR-02-4: a same-name winner that did not arrive must not drop the old entry."""
    src = _src(tmp_path)  # no sf2.zip: the winner's copy is skipped
    dest = _dest(tmp_path)
    (dest / "sf2.zip").write_bytes(b"old")
    _seed_existing_playlist(dest, [{"path": str(dest / "sf2.zip"), "label": "Old SF2"}])
    plan = _plan(
        winners=("sf2",),
        machines={"sf2": _machine("sf2")},
        bios_chain={},
        source_dir=src,
        dest_dir=dest,
        conflict_strategy=ConflictStrategy.APPEND,
    )

    runner.run_copy(plan, data_dir=tmp_path / "data")

    assert [it["label"] for it in _items(dest)] == ["Old SF2"]


def test_append_carries_kept_entries_and_settings_unchanged(tmp_path: Path) -> None:
    """CR-02-4: a kept entry's core and CRC, and the playlist's own settings, survive."""
    src = _src(tmp_path, "kof94")
    dest = _dest(tmp_path)
    kept = {
        "path": str(dest / "sf2.zip"),
        "label": "Street Fighter II",
        "core_path": "/cores/mame_libretro.so",
        "core_name": "MAME",
        "crc32": "DEADBEEF|crc",
        "db_name": "MAME.lpl",
    }
    _seed_existing_playlist(dest, [kept])
    doc = json.loads((dest / "mame.lpl").read_text(encoding="utf-8"))
    doc["default_core_path"] = "/cores/mame_libretro.so"
    (dest / "mame.lpl").write_text(json.dumps(doc), encoding="utf-8")
    plan = _plan(
        winners=("kof94",),
        machines={"kof94": _machine("kof94")},
        bios_chain={},
        source_dir=src,
        dest_dir=dest,
        conflict_strategy=ConflictStrategy.APPEND,
    )

    runner.run_copy(plan, data_dir=tmp_path / "data")

    written = json.loads((dest / "mame.lpl").read_text(encoding="utf-8"))
    assert kept in written["items"]
    assert written["default_core_path"] == "/cores/mame_libretro.so"


# ---- CR-02-3: REPLACE_AND_RECYCLE waits for the new copy ---------------------


def test_replace_and_recycle_keeps_the_old_game_when_the_copy_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CR-02-3: the old zip was recycled before the copy, so a failure lost the game."""
    src = _src(tmp_path, "sf2ce")
    dest = _dest(tmp_path)
    (dest / "sf2.zip").write_bytes(b"old")
    _seed_existing_playlist(dest, [{"path": str(dest / "sf2.zip"), "label": "Old SF2"}])

    def failing_copy(src_path: Path, *_args: Any, **_kwargs: Any) -> Any:
        raise CopyExecutionError("disk full", path=src_path)

    monkeypatch.setattr(runner, "copy_one", failing_copy)
    plan = _plan(
        winners=("sf2ce",),
        machines={"sf2ce": _machine("sf2ce")},
        bios_chain={},
        source_dir=src,
        dest_dir=dest,
        conflict_strategy=ConflictStrategy.APPEND,
        append_decisions={
            "sf2ce": AppendDecision(kind=AppendDecisionKind.REPLACE_AND_RECYCLE, replaces="sf2")
        },
    )

    report = runner.run_copy(plan, data_dir=tmp_path / "data")

    assert (dest / "sf2.zip").read_bytes() == b"old"
    assert report.recycled == ()
    assert [it["label"] for it in _items(dest)] == ["Old SF2"]


# ---- RL-7: a partial-copy recycle that fails --------------------------------


def test_a_file_the_cancel_could_not_recycle_stays_in_the_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RL-7: it stays at the destination, so it stays in `succeeded`, with a warning."""
    dst = tmp_path / "dest" / "kof94.zip"
    state = RunState(started_at=datetime.now(UTC), session_id="s")
    state.succeeded.append(
        CopyOutcome(
            short_name="kof94",
            role="winner",
            status=CopyOutcomeStatus.SUCCEEDED,
            src=tmp_path / "kof94.zip",
            dst=dst,
            bytes=1,
        )
    )

    def refuse(path: Path, **_kwargs: Any) -> Path:
        raise RecycleError("locked", path=path)

    monkeypatch.setattr(run_recycle, "recycle_file", refuse)
    run_recycle.recycle_partial_copy(state, data_dir=tmp_path / "data")

    assert [o.short_name for o in state.succeeded] == ["kof94"]
    assert any("kof94.zip" in w for w in state.warnings)


# ---- RL-9: the report's records are sorted ----------------------------------


def test_report_records_are_sorted(tmp_path: Path) -> None:
    """RL-9: copy/spec.md says every tuple is sorted, recycle records by path."""
    plan = _plan(winners=(), machines={}, bios_chain={}, source_dir=tmp_path, dest_dir=tmp_path)
    state = RunState(started_at=datetime.now(UTC), session_id="s")
    state.overwritten += [
        OverwriteRecord(old_short="zz", new_short="zz2"),
        OverwriteRecord(old_short="aa", new_short="aa2"),
    ]
    state.recycled += [
        RecycleRecord(original_path=tmp_path / "z.zip", recycled_path=tmp_path / "r1", reason="x"),
        RecycleRecord(original_path=tmp_path / "a.zip", recycled_path=tmp_path / "r2", reason="x"),
    ]
    summary = make_plan_summary(plan, 0)

    report = finish_report(plan, state, summary, cancelled=False, data_dir=tmp_path / "data")

    assert [r.old_short for r in report.overwritten] == ["aa", "zz"]
    assert [r.original_path.name for r in report.recycled] == ["a.zip", "z.zip"]


# ---- RL-10: the crash report lists the CHD games -----------------------------


def test_crash_report_lists_chd_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """RL-10: the other two report builders set it; the crash one left it out."""
    src = _src(tmp_path, "kof94")
    dest = _dest(tmp_path)

    def crash(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("boom")

    monkeypatch.setattr(runner, "copy_one", crash)
    plan = _plan(
        winners=("kof94",),
        machines={"kof94": _machine("kof94")},
        bios_chain={},
        source_dir=src,
        dest_dir=dest,
    ).model_copy(update={"chd_required": frozenset({"kof94"})})
    seen: list[Any] = []

    with pytest.raises(RuntimeError):
        runner.run_copy(plan, data_dir=tmp_path / "data", on_crash=seen.append)

    assert seen[0].chd_missing == ("kof94",)


# ---- RL-11: BIOS already copied is not counted as needed ---------------------


def test_free_space_estimate_leaves_out_bios_already_copied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bios_chain: Any
) -> None:
    """RL-11: only winners were checked, so a present BIOS still counted as needed."""
    src = _src(tmp_path, "kof94", "neogeo")
    dest = _dest(tmp_path)
    monkeypatch.setattr(
        preflight.shutil, "disk_usage", lambda _p: shutil._ntuple_diskusage(10**9, 0, 10**9)
    )
    plan = _plan(
        winners=("kof94",),
        machines={"kof94": _machine("kof94")},
        bios_chain=bios_chain,
        source_dir=src,
        dest_dir=dest,
    )
    without_bios = preflight.preflight(plan).free_space_gap_bytes
    shutil.copy2(src / "neogeo.zip", dest / "neogeo.zip")
    with_bios = preflight.preflight(plan).free_space_gap_bytes

    assert with_bios - without_bios == (src / "neogeo.zip").stat().st_size


# ---- RL-12, CR-02-2, CR-02-6: copy_one ---------------------------------------


def test_copy_one_leaves_another_writers_tmp_alone(tmp_path: Path) -> None:
    """RL-12: a fixed `<dst>.tmp` name collides with a second run into the same folder."""
    src = _src(tmp_path, "kof94") / "kof94.zip"
    dest = _dest(tmp_path)
    other = dest / "kof94.zip.tmp"
    other.write_bytes(b"another run's half-written copy")

    executor.copy_one(src, dest / "kof94.zip", short_name="kof94", role="winner")

    assert other.read_bytes() == b"another run's half-written copy"


@pytest.mark.parametrize(("shift", "same"), [(1.5, True), (3600.0, True), (10.0, False)])
def test_idempotency_allows_fat_and_daylight_saving_shifts(
    tmp_path: Path, shift: float, same: bool
) -> None:
    """CR-02-2: FAT keeps 2-second times, and daylight saving moves them an hour."""
    src = _src(tmp_path, "kof94") / "kof94.zip"
    dst = _dest(tmp_path) / "kof94.zip"
    shutil.copy2(src, dst)
    st = src.stat()
    os.utime(dst, (st.st_atime, st.st_mtime + shift))

    assert executor._is_idempotent(src, dst) is same


@pytest.mark.parametrize(
    ("code", "copies"), [(errno.EINVAL, True), (errno.ENOTSUP, True), (errno.EIO, False)]
)
def test_copy_survives_a_filesystem_without_fsync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: int, copies: bool
) -> None:
    """CR-02-6: a filesystem that rejects fsync must not fail every copy; a disk error must."""
    src = _src(tmp_path, "kof94") / "kof94.zip"
    dst = _dest(tmp_path) / "kof94.zip"

    def no_fsync(_fd: int) -> None:
        raise OSError(code, os.strerror(code))

    monkeypatch.setattr("mame_curator.copy.executor.os.fsync", no_fsync)
    if copies:
        executor.copy_one(src, dst, short_name="kof94", role="winner")
        assert dst.read_bytes() == src.read_bytes()
    else:
        with pytest.raises(CopyExecutionError):
            executor.copy_one(src, dst, short_name="kof94", role="winner")


# ---- RL-13: a source that vanishes during a dry run ------------------------


def test_dry_run_skips_a_source_that_vanishes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RL-13: `src.stat()` was unguarded after the `exists()` check."""

    class _Vanishing(type(Path())):  # type: ignore[misc]
        def exists(self, *, follow_symlinks: bool = True) -> bool:
            return True

        def stat(self, *, follow_symlinks: bool = True) -> os.stat_result:
            raise FileNotFoundError(str(self))

    from mame_curator.copy.paths import zip_path as real_zip_path

    def vanishing_zip_path(root: Path, short: str) -> Path:
        path = real_zip_path(root, short)
        return _Vanishing(path) if root == plan.source_dir else path

    plan = _plan(
        winners=("kof94",),
        machines={"kof94": _machine("kof94")},
        bios_chain={},
        source_dir=_src(tmp_path, "kof94"),
        dest_dir=_dest(tmp_path),
        dry_run=True,
    )
    monkeypatch.setattr("mame_curator.copy.runner.zip_path", vanishing_zip_path)

    report = runner.run_copy(plan, data_dir=tmp_path / "data")

    assert [o.status for o in report.skipped] == [CopyOutcomeStatus.SKIPPED_MISSING_SOURCE]


# ---- CR-02-11, CR-02-8: the recycle bin -------------------------------------


def _cross_drive_move(fail_unlink_of_copy: bool, monkeypatch: pytest.MonkeyPatch) -> None:
    def move(src: str, dst: str) -> None:
        shutil.copy2(src, dst)  # the copy half of a cross-drive move
        raise OSError(errno.EACCES, "source could not be removed")

    monkeypatch.setattr("mame_curator.copy.recyclebin.shutil.move", move)
    if fail_unlink_of_copy:
        real_unlink = Path.unlink

        def unlink(self: Path, missing_ok: bool = False) -> None:
            if self.suffix == ".zip" and "recycle" in self.parts:
                raise OSError(errno.EACCES, "denied")
            real_unlink(self, missing_ok=missing_ok)

        monkeypatch.setattr(Path, "unlink", unlink)


def test_failed_cross_drive_recycle_leaves_no_orphan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CR-02-11: the copy at the recycle target was left with no manifest."""
    game = tmp_path / "dest" / "kof94.zip"
    game.parent.mkdir()
    game.write_bytes(b"game")
    _cross_drive_move(False, monkeypatch)

    with pytest.raises(RecycleError):
        recyclebin.recycle_file(game, reason="x", session_id="s", recycle_root=tmp_path / "recycle")

    assert game.read_bytes() == b"game"
    assert list((tmp_path / "recycle").rglob("*.zip")) == []


def test_an_orphan_that_cannot_be_removed_is_named(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CR-02-11: `recycled_orphan` was never set."""
    game = tmp_path / "dest" / "kof94.zip"
    game.parent.mkdir()
    game.write_bytes(b"game")
    _cross_drive_move(True, monkeypatch)

    with pytest.raises(RecycleError) as caught:
        recyclebin.recycle_file(game, reason="x", session_id="s", recycle_root=tmp_path / "recycle")

    assert caught.value.recycled_orphan is not None
    assert caught.value.recycled_orphan.name == "kof94.zip"


def test_purge_reads_a_manifest_time_with_no_time_zone(tmp_path: Path) -> None:
    """CR-02-8: a naive time made the comparison raise TypeError; it is read as UTC."""
    sub = tmp_path / "recycle" / "old-session"
    sub.mkdir(parents=True)
    (sub / "kof94.zip").write_bytes(b"x")
    old = (datetime.now(UTC) - timedelta(days=90)).replace(tzinfo=None).isoformat()
    (sub / "kof94.zip.manifest.json").write_text(json.dumps({"recycled_at": old}))

    dirs, _freed = recyclebin.purge_recycle(recycle_root=tmp_path / "recycle")

    assert dirs == 1


# ---- CR-02-7: the activity reader -------------------------------------------


def test_one_bad_byte_does_not_hide_the_activity_log(tmp_path: Path) -> None:
    """CR-02-7: the whole log was decoded as UTF-8, so one bad byte broke it."""
    from mame_curator.copy import append_activity, read_activity
    from mame_curator.copy.types import ActivityEvent, ActivityEventType, RecyclePurgedDetails

    log = tmp_path / "activity.jsonl"
    event = ActivityEvent(
        timestamp=datetime.now(UTC),
        event_type=ActivityEventType.RECYCLE_PURGED,
        summary="purged",
        session_id="",
        details=RecyclePurgedDetails(dirs_purged=1, bytes_freed=2),
    )
    append_activity(event, log_path=log)
    with log.open("ab") as fh:
        fh.write(b"\xff\xfe not utf-8\n")

    assert [e.summary for e in read_activity(log)] == ["purged"]


# ---- CR-05-10: file_finished once per file -----------------------------------


def test_file_finished_fires_once_per_file() -> None:
    """CR-05-10: a copy that reached 100% then failed ticked it finished twice."""
    from mame_curator.api.job_progress import ProgressSynthesizer

    sent: list[Any] = []

    class _Loop:
        def call_soon_threadsafe(self, fn: Any, event: Any) -> None:
            sent.append(event)

    from types import SimpleNamespace

    sink = SimpleNamespace(_emit=lambda _event: None)
    synth = ProgressSynthesizer(_Loop(), sink=sink)  # type: ignore[arg-type]
    synth("kof94", 10, 10)  # the last chunk lands
    synth("kof94", 0, 0)  # then the rename fails, and the failure ticks it done

    finished = [e for e in sent if e.event == "file_finished"]
    assert len(finished) == 1

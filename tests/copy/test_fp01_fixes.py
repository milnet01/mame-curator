"""Regression tests for FP01 Tier-1 / Tier-2 fixes against P03.

Each test pins a specific finding from the indie-review pass on
2026-04-30. Folder name `test_fp01_fixes.py` is intentional —
keeping the FP origin visible in the test layout per
`testing.md` § "tests anchor to external signals".
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from mame_curator.copy import (
    copy_one,
    recycle_file,
    run_copy,
)
from mame_curator.copy.errors import CopyError, CopyExecutionError, RecycleError
from mame_curator.copy.types import (
    AppendDecision,
    AppendDecisionKind,
    ConflictStrategy,
    CopyOutcomeStatus,
    CopyPlan,
    CopyReportStatus,
)
from mame_curator.parser.listxml import BIOSChainEntry
from mame_curator.parser.models import Machine


def _machine(short: str, desc: str | None = None) -> Machine:
    return Machine(name=short, description=desc or short, runnable=True)


# --- Tier 1 #2: KeyboardInterrupt cleanup ---------------------------------


def test_copy_one_cleans_tmp_on_keyboard_interrupt(
    source_dir: Path, dest_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Spec § Atomic copy step 6: KeyboardInterrupt mid-copy cleans up `.tmp`."""
    src = source_dir / "kof94.zip"
    dst = dest_dir / "kof94.zip"

    import shutil as _shutil

    from mame_curator.copy import executor

    def boom(_src: object, tmp_arg: object) -> None:
        # Partial-write the .tmp before raising.
        Path(str(tmp_arg)).write_bytes(b"PARTIAL")
        raise KeyboardInterrupt

    monkeypatch.setattr(_shutil, "copy2", boom)
    monkeypatch.setattr(executor, "shutil", _shutil)

    with pytest.raises(KeyboardInterrupt):
        copy_one(src, dst, short_name="kof94", role="winner")

    # Tmp removed by the try/finally in copy_one.
    assert not list(dest_dir.glob("*.tmp"))
    # Original dst (absent) still absent — never half-written.
    assert not dst.exists()


# --- Tier 1 #3: OverwriteRecord populated ---------------------------------


def _seed_existing_playlist(dest_dir: Path, items: list[dict[str, str]]) -> None:
    payload = {
        "version": "1.5",
        "default_core_path": "",
        "default_core_name": "",
        "label_display_mode": 0,
        "right_thumbnail_mode": 0,
        "left_thumbnail_mode": 0,
        "sort_mode": 0,
        "items": items,
    }
    (dest_dir / "mame.lpl").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_overwrite_record_populated_on_replace(
    source_dir: Path, dest_dir: Path, bios_chain: dict[str, BIOSChainEntry]
) -> None:
    """REPLACE / REPLACE_AND_RECYCLE paths must record one OverwriteRecord per replaced winner."""
    # Existing playlist contains sf2 (parent of sf2ce). Place the existing
    # zip at dest so REPLACE_AND_RECYCLE has something to recycle.
    (dest_dir / "sf2.zip").write_bytes(b"old sf2 content")
    _seed_existing_playlist(
        dest_dir,
        [
            {
                "path": str((dest_dir / "sf2.zip").resolve()),
                "label": "Street Fighter II",
                "core_path": "DETECT",
                "core_name": "DETECT",
                "crc32": "00000000|crc",
                "db_name": "MAME.lpl",
            }
        ],
    )

    plan = CopyPlan(
        winners=("sf2ce",),
        machines={"sf2ce": _machine("sf2ce", "Street Fighter II' - CE")},
        bios_chain=bios_chain,
        source_dir=source_dir,
        dest_dir=dest_dir,
        conflict_strategy=ConflictStrategy.APPEND,
        append_decisions={
            "sf2ce": AppendDecision(kind=AppendDecisionKind.REPLACE_AND_RECYCLE, replaces="sf2")
        },
    )
    report = run_copy(plan)
    assert report.status is CopyReportStatus.OK
    assert len(report.overwritten) == 1
    assert report.overwritten[0].old_short == "sf2"
    assert report.overwritten[0].new_short == "sf2ce"
    # The old sf2.zip was recycled (recorded in the report).
    assert any(r.original_path.name == "sf2.zip" for r in report.recycled)
    # The recycled file's content matches what we seeded (the OLD sf2).
    recycled_record = next(r for r in report.recycled if r.original_path.name == "sf2.zip")
    assert recycled_record.recycled_path.read_bytes() == b"old sf2 content"
    # A fresh sf2.zip lands at dest because sf2 is a BIOS dep of sf2ce —
    # source-copied after the recycle. Its content matches source, not the
    # old user-installed copy. (This is the design: BIOS deps are always
    # the source's version, not whatever was previously at dest.)
    assert (dest_dir / "sf2.zip").exists()
    assert (dest_dir / "sf2.zip").read_bytes() == (source_dir / "sf2.zip").read_bytes()


def test_overwrite_record_populated_on_plain_replace_no_recycle(
    source_dir: Path, dest_dir: Path, bios_chain: dict[str, BIOSChainEntry]
) -> None:
    """REPLACE (without _AND_RECYCLE) records overwrite but leaves old zip on disk."""
    (dest_dir / "sf2.zip").write_bytes(b"old sf2 content")
    _seed_existing_playlist(
        dest_dir,
        [
            {
                "path": str((dest_dir / "sf2.zip").resolve()),
                "label": "Street Fighter II",
                "core_path": "DETECT",
                "core_name": "DETECT",
                "crc32": "00000000|crc",
                "db_name": "MAME.lpl",
            }
        ],
    )
    plan = CopyPlan(
        winners=("sf2ce",),
        machines={"sf2ce": _machine("sf2ce")},
        bios_chain=bios_chain,
        source_dir=source_dir,
        dest_dir=dest_dir,
        conflict_strategy=ConflictStrategy.APPEND,
        append_decisions={"sf2ce": AppendDecision(kind=AppendDecisionKind.REPLACE, replaces="sf2")},
    )
    report = run_copy(plan)
    assert report.status is CopyReportStatus.OK
    # OverwriteRecord populated.
    assert len(report.overwritten) == 1
    assert report.overwritten[0].new_short == "sf2ce"
    # No recycle: per spec, plain REPLACE leaves old zip on disk.
    assert report.recycled == ()
    # New winner copied; sf2.zip exists (re-written as a BIOS dep from source).
    assert (dest_dir / "sf2ce.zip").exists()
    assert (dest_dir / "sf2.zip").exists()


def test_corrupt_existing_playlist_surfaces_warning(
    source_dir: Path, dest_dir: Path, bios_chain: dict[str, BIOSChainEntry]
) -> None:
    """A corrupt or legacy playlist surfaces a warning on the report (B-T2-3).

    Without this, the user's old playlist is silently overwritten — a real
    user-data risk caught in FP01 round-2 indie-review.
    """
    (dest_dir / "mame.lpl").write_text(
        "this is the legacy 6-line format which we do not support",
        encoding="utf-8",
    )
    plan = CopyPlan(
        winners=("kof94",),
        machines={"kof94": _machine("kof94")},
        bios_chain=bios_chain,
        source_dir=source_dir,
        dest_dir=dest_dir,
        conflict_strategy=ConflictStrategy.APPEND,
    )
    report = run_copy(plan)
    assert any("existing playlist could not be parsed" in w for w in report.warnings), (
        report.warnings
    )


def test_replace_keep_existing_skips_winner(
    source_dir: Path, dest_dir: Path, bios_chain: dict[str, BIOSChainEntry]
) -> None:
    """KEEP_EXISTING decision skips the new winner; nothing recycled."""
    _seed_existing_playlist(
        dest_dir,
        [
            {
                "path": str((dest_dir / "sf2.zip").resolve()),
                "label": "Street Fighter II",
                "core_path": "DETECT",
                "core_name": "DETECT",
                "crc32": "00000000|crc",
                "db_name": "MAME.lpl",
            }
        ],
    )
    plan = CopyPlan(
        winners=("sf2ce",),
        machines={"sf2ce": _machine("sf2ce")},
        bios_chain=bios_chain,
        source_dir=source_dir,
        dest_dir=dest_dir,
        conflict_strategy=ConflictStrategy.APPEND,
        append_decisions={"sf2ce": AppendDecision(kind=AppendDecisionKind.KEEP_EXISTING)},
    )
    report = run_copy(plan)
    assert report.status is CopyReportStatus.OK
    # New winner skipped, not copied.
    assert not (dest_dir / "sf2ce.zip").exists()
    # No overwritten / recycled records.
    assert report.overwritten == ()
    assert report.recycled == ()
    # Skipped with the right reason.
    assert any(
        o.short_name == "sf2ce" and o.status is CopyOutcomeStatus.SKIPPED_EXISTING_VERSION
        for o in report.skipped
    )


# --- Tier 1 #5: recycle collision logic -----------------------------------


def test_recycle_same_name_same_second_does_not_clobber(tmp_path: Path) -> None:
    """Two recycles of files named the same in the same second land in distinct dirs."""
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    same_name_a = tmp_path / "a" / "sf2.zip"
    same_name_a.write_bytes(b"AAA")
    same_name_b = tmp_path / "b" / "sf2.zip"
    same_name_b.write_bytes(b"BBB")
    recycle_root = tmp_path / "recycle"

    # Force both calls to use the same timestamp via a fixed datetime.
    fixed_now = datetime(2026, 4, 30, 12, 0, 0, tzinfo=UTC)
    with patch("mame_curator.copy.recyclebin.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_now
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        p1 = recycle_file(same_name_a, reason="x", session_id="s", recycle_root=recycle_root)
        p2 = recycle_file(same_name_b, reason="x", session_id="s", recycle_root=recycle_root)

    # Both files preserved with their original content; neither clobbered.
    assert p1.read_bytes() == b"AAA"
    assert p2.read_bytes() == b"BBB"
    # Distinct parent directories (the second got a -1 suffix).
    assert p1.parent != p2.parent


# --- Tier 2: FAILED branch coverage ---------------------------------------


def test_runner_records_failed_outcome_when_copy_one_raises(
    source_dir: Path, dest_dir: Path, bios_chain: dict[str, BIOSChainEntry]
) -> None:
    """A copy_one failure surfaces as a FAILED CopyOutcome and PARTIAL_FAILURE report."""
    plan = CopyPlan(
        winners=("kof94",),
        machines={"kof94": _machine("kof94")},
        bios_chain=bios_chain,
        source_dir=source_dir,
        dest_dir=dest_dir,
    )

    def boom(*args: object, **kwargs: object) -> None:
        raise CopyExecutionError("simulated failure", path=Path(str(args[0])))

    with patch("mame_curator.copy.runner.copy_one", side_effect=boom):
        report = run_copy(plan)

    assert report.status is CopyReportStatus.PARTIAL_FAILURE
    assert len(report.failed) >= 1
    assert all(o.status is CopyOutcomeStatus.FAILED for o in report.failed)
    assert any("simulated failure" in (o.error or "") for o in report.failed)


# --- Tier 2: OVERWRITE + delete_existing_zips coverage --------------------


def test_overwrite_with_delete_existing_zips_recycles_old_zips(
    source_dir: Path, dest_dir: Path, bios_chain: dict[str, BIOSChainEntry]
) -> None:
    """delete_existing_zips=True moves existing dest zips not in the new plan to recycle."""
    # Pre-existing zips at dest, none in the new plan.
    (dest_dir / "old1.zip").write_bytes(b"old1")
    (dest_dir / "old2.zip").write_bytes(b"old2")
    _seed_existing_playlist(dest_dir, [])

    plan = CopyPlan(
        winners=("kof94",),
        machines={"kof94": _machine("kof94")},
        bios_chain=bios_chain,
        source_dir=source_dir,
        dest_dir=dest_dir,
        conflict_strategy=ConflictStrategy.OVERWRITE,
        delete_existing_zips=True,
    )
    report = run_copy(plan)
    assert report.status is CopyReportStatus.OK
    recycled_names = {r.original_path.name for r in report.recycled}
    assert {"old1.zip", "old2.zip"} <= recycled_names
    # Old zips no longer at dest.
    assert not (dest_dir / "old1.zip").exists()
    assert not (dest_dir / "old2.zip").exists()


# --- Tier 3: errors __str__ round-trip ------------------------------------


def test_copy_error_str_renders_path_suffix() -> None:
    p = Path("/x/y.zip")
    err = CopyError("simulated", path=p)
    # FP07 A4: path is rendered via repr() to defend the single-line
    # error contract against control bytes in user-controlled paths.
    assert str(err) == f"simulated (path={p!r})"


def test_copy_error_str_without_path() -> None:
    err = CopyError("simulated")
    assert str(err) == "simulated"


# --- Tier 3: playlist error branches --------------------------------------


def test_read_lpl_raises_on_missing_file(tmp_path: Path) -> None:
    from mame_curator.copy.errors import PlaylistError
    from mame_curator.copy.playlist import read_lpl

    with pytest.raises(PlaylistError):
        read_lpl(tmp_path / "nope.lpl")


def test_read_lpl_raises_on_corrupt_json(tmp_path: Path) -> None:
    from mame_curator.copy.errors import PlaylistError
    from mame_curator.copy.playlist import read_lpl

    bad = tmp_path / "bad.lpl"
    bad.write_text("not json at all", encoding="utf-8")
    with pytest.raises(PlaylistError):
        read_lpl(bad)


def test_read_lpl_raises_when_items_not_list(tmp_path: Path) -> None:
    from mame_curator.copy.errors import PlaylistError
    from mame_curator.copy.playlist import read_lpl

    bad = tmp_path / "bad.lpl"
    bad.write_text(json.dumps({"items": "not-a-list"}), encoding="utf-8")
    with pytest.raises(PlaylistError):
        read_lpl(bad)


def test_recycle_raises_when_source_missing(tmp_path: Path) -> None:
    with pytest.raises(RecycleError):
        recycle_file(tmp_path / "nope.zip", reason="x", session_id="s")

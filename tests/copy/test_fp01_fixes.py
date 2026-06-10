"""Regression tests for FP01 Tier-1 / Tier-2 fixes against P03.

Each test pins a specific finding from the indie-review pass on
2026-04-30. Folder name `test_fp01_fixes.py` is intentional —
keeping the FP origin visible in the test layout per
`testing.md` § "tests anchor to external signals".
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from mame_curator.copy import run_copy
from mame_curator.copy.errors import CopyExecutionError
from mame_curator.copy.types import (
    AppendDecision,
    AppendDecisionKind,
    ConflictStrategy,
    CopyOutcomeStatus,
    CopyPlan,
    CopyReportStatus,
)
from mame_curator.parser.listxml import BIOSChainEntry

# FP31: `_machine` lifted to the shared `_runner_helpers` module (DS05
# Cluster B established the seam pattern). Was byte-for-byte duplicated
# here and in test_fp02_fixes.py + test_preflight.py.
# `_seed_existing_playlist` lifted to `conftest.py` (mame-curator-1054c) —
# it was duplicated in test_fp02_fixes.py too.
from tests.copy._runner_helpers import _machine
from tests.copy.conftest import _seed_existing_playlist

# --- Tier 1 #2: KeyboardInterrupt cleanup ---------------------------------
# DS04 T2.9: deleted `test_copy_one_cleans_tmp_on_keyboard_interrupt` — the
# equivalent test at `tests/copy/test_fp02_fixes.py:317` uses a `progress=`
# callback to trigger the interrupt and exercises the same `_chunked_copy`
# write path. Both paths funnel through `_chunked_copy` post-FP27-B1; one
# test is enough.


# --- Tier 1 #3: OverwriteRecord populated ---------------------------------


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
# DS04 T2.10: deleted `test_recycle_same_name_same_second_does_not_clobber`
# — the equivalent at `tests/copy/test_fp02_fixes.py:158` exercises a
# stronger `session_id`-distinguishing assertion, and the canonical
# `tests/copy/test_recyclebin.py:95` already pins the dir-uniqueness
# contract.


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
# DS04 T2.11: deleted `test_copy_error_str_renders_path_suffix` +
# `test_copy_error_str_without_path` — both subsumed by
# `tests/copy/test_errors.py:15-37`, which iterates over every
# `CopyError` subclass and additionally locks the FP07 A4 control-byte
# repr contract.

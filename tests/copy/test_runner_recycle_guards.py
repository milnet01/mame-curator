"""run_copy's recycle paths: failure, cancel and dry-run guards.

Each test pins a finding from review-code 2026-10-30
(docs/reviews/review-code-2026-10-30/lane-02-core-library.md).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mame_curator.copy import run_copy
from mame_curator.copy.controller import CopyController
from mame_curator.copy.errors import RecycleError
from mame_curator.copy.types import (
    AppendDecision,
    AppendDecisionKind,
    ConflictStrategy,
    CopyPlan,
    CopyReportStatus,
)
from mame_curator.parser.listxml import BIOSChainEntry
from tests.copy._runner_helpers import _machine
from tests.copy.conftest import _seed_existing_playlist


def _overwrite_plan(
    source_dir: Path, dest_dir: Path, bios_chain: dict[str, BIOSChainEntry]
) -> CopyPlan:
    return CopyPlan(
        winners=("kof94", "sf2"),
        machines={"kof94": _machine("kof94"), "sf2": _machine("sf2")},
        bios_chain=bios_chain,
        source_dir=source_dir,
        dest_dir=dest_dir,
        conflict_strategy=ConflictStrategy.OVERWRITE,
        delete_existing_zips=True,
    )


def test_overwrite_delete_recycle_failure_warns_and_still_writes_playlist(
    source_dir: Path,
    dest_dir: Path,
    bios_chain: dict[str, BIOSChainEntry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """#3: one old zip that cannot be recycled must not lose the playlist
    and the report after every copy is done; it becomes a warning."""
    (dest_dir / "old.zip").write_bytes(b"old")

    def _fail_recycle(path: Path, **_kw: object) -> Path:
        raise RecycleError("simulated recycle failure", path=path)

    monkeypatch.setattr("mame_curator.copy.runner.recycle_file", _fail_recycle)
    report = run_copy(_overwrite_plan(source_dir, dest_dir, bios_chain), data_dir=tmp_path)
    assert report.status is CopyReportStatus.OK
    assert (dest_dir / "mame.lpl").exists()
    assert (dest_dir / "old.zip").exists()
    assert any("'old.zip'" in w for w in report.warnings)


def test_overwrite_delete_skipped_after_cancel(
    source_dir: Path, dest_dir: Path, bios_chain: dict[str, BIOSChainEntry], tmp_path: Path
) -> None:
    """#8: a cancel mid-run means no recycling (spec § Pause / resume /
    cancel), so the OVERWRITE delete pass must not run."""
    (dest_dir / "old.zip").write_bytes(b"old")
    ctl = CopyController()

    def _cancel_after_first(short: str, done: int, total: int) -> None:
        if done == total:
            ctl.cancel(recycle_partial=False)

    report = run_copy(
        _overwrite_plan(source_dir, dest_dir, bios_chain),
        controller=ctl,
        on_progress=_cancel_after_first,
        data_dir=tmp_path,
    )
    assert report.status is CopyReportStatus.CANCELLED
    assert (dest_dir / "old.zip").exists()
    assert report.recycled == ()


def test_replace_and_recycle_is_a_no_op_on_dry_run(
    source_dir: Path, dest_dir: Path, bios_chain: dict[str, BIOSChainEntry], tmp_path: Path
) -> None:
    """#9: dry run means no writes, so REPLACE_AND_RECYCLE must not move
    the replaced zip."""
    old = dest_dir / "kof94a.zip"
    old.write_bytes(b"old")
    _seed_existing_playlist(dest_dir, [{"path": str(old.resolve()), "label": "KOF 94a"}])
    plan = CopyPlan(
        winners=("kof94",),
        machines={"kof94": _machine("kof94")},
        bios_chain=bios_chain,
        source_dir=source_dir,
        dest_dir=dest_dir,
        conflict_strategy=ConflictStrategy.APPEND,
        append_decisions={
            "kof94": AppendDecision(kind=AppendDecisionKind.REPLACE_AND_RECYCLE, replaces="kof94a")
        },
        dry_run=True,
    )
    report = run_copy(plan, data_dir=tmp_path)
    assert old.exists()
    assert report.recycled == ()

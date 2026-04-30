"""End-to-end tests for `run_copy` orchestrator."""

from __future__ import annotations

import json
import threading
from pathlib import Path

from mame_curator.copy import (
    CopyController,
    run_copy,
)
from mame_curator.copy.types import (
    AppendDecision,
    ConflictStrategy,
    CopyOutcomeStatus,
    CopyPlan,
    CopyReportStatus,
)
from mame_curator.parser.listxml import BIOSChainEntry
from mame_curator.parser.models import Machine


def _machine(short: str, desc: str | None = None) -> Machine:
    return Machine(name=short, description=desc or short, runnable=True)


def _plan(
    *,
    winners: tuple[str, ...],
    machines: dict[str, Machine],
    bios_chain: dict[str, BIOSChainEntry],
    source_dir: Path,
    dest_dir: Path,
    conflict_strategy: ConflictStrategy = ConflictStrategy.CANCEL,
    append_decisions: dict[str, AppendDecision] | None = None,
    delete_existing_zips: bool = False,
    dry_run: bool = False,
) -> CopyPlan:
    return CopyPlan(
        winners=winners,
        machines=machines,
        bios_chain=bios_chain,
        source_dir=source_dir,
        dest_dir=dest_dir,
        conflict_strategy=conflict_strategy,
        append_decisions=append_decisions or {},
        delete_existing_zips=delete_existing_zips,
        dry_run=dry_run,
    )


# --- Dry-run -------------------------------------------------------------


def test_copy_dry_run_no_writes(
    source_dir: Path, dest_dir: Path, bios_chain: dict[str, BIOSChainEntry]
) -> None:
    """Dry-run leaves dest dir untouched."""
    plan = _plan(
        winners=("kof94",),
        machines={"kof94": _machine("kof94")},
        bios_chain=bios_chain,
        source_dir=source_dir,
        dest_dir=dest_dir,
        dry_run=True,
    )
    report = run_copy(plan)
    assert report.status is CopyReportStatus.OK
    # No files created.
    assert list(dest_dir.iterdir()) == []
    # Report still shows what would have happened.
    assert report.plan_summary.winners_count == 1
    assert "neogeo" in report.bios_included


# --- Apply (golden path) -------------------------------------------------


def test_copy_apply_succeeds_and_writes_files(
    source_dir: Path, dest_dir: Path, bios_chain: dict[str, BIOSChainEntry]
) -> None:
    """Full apply: winner + transitive BIOS deps land at dest, plus mame.lpl."""
    plan = _plan(
        winners=("kof94",),
        machines={"kof94": _machine("kof94", "The King of Fighters '94")},
        bios_chain=bios_chain,
        source_dir=source_dir,
        dest_dir=dest_dir,
    )
    report = run_copy(plan)
    assert report.status is CopyReportStatus.OK
    # Winner zip copied.
    assert (dest_dir / "kof94.zip").exists()
    # BIOS deps copied (neogeo + euro + us; all also in source fixture).
    assert (dest_dir / "neogeo.zip").exists()
    # Playlist written.
    lpl = dest_dir / "mame.lpl"
    assert lpl.exists()
    parsed = json.loads(lpl.read_text(encoding="utf-8"))
    assert parsed["items"][0]["label"] == "The King of Fighters '94"


def test_copy_handles_missing_source(
    tmp_path: Path, dest_dir: Path, bios_chain: dict[str, BIOSChainEntry]
) -> None:
    """Winner listed but .zip missing on disk → SKIPPED_MISSING_SOURCE; no crash."""
    src = tmp_path / "source"
    src.mkdir()
    # Only kof94 exists in source; ghost does not.
    (src / "kof94.zip").write_bytes(b"x" * 100)
    plan = _plan(
        winners=("kof94", "ghost"),
        machines={"kof94": _machine("kof94"), "ghost": _machine("ghost")},
        bios_chain=bios_chain,
        source_dir=src,
        dest_dir=dest_dir,
    )
    report = run_copy(plan)
    # ghost reported as skipped, kof94 succeeded.
    statuses = {o.short_name: o.status for o in (*report.succeeded, *report.skipped)}
    assert statuses["ghost"] is CopyOutcomeStatus.SKIPPED_MISSING_SOURCE
    assert statuses["kof94"] is CopyOutcomeStatus.SUCCEEDED


def test_copy_idempotent_rerun_skips_already_copied(
    source_dir: Path, dest_dir: Path, bios_chain: dict[str, BIOSChainEntry]
) -> None:
    """Re-running a clean apply is a no-op (everything SKIPPED_IDEMPOTENT)."""
    plan = _plan(
        winners=("kof94",),
        machines={"kof94": _machine("kof94")},
        bios_chain=bios_chain,
        source_dir=source_dir,
        dest_dir=dest_dir,
    )
    run_copy(plan)
    second = run_copy(plan)
    assert second.status is CopyReportStatus.OK
    assert all(o.status is CopyOutcomeStatus.SKIPPED_IDEMPOTENT for o in second.skipped)
    assert second.succeeded == ()


def test_copy_report_completeness(
    source_dir: Path, dest_dir: Path, bios_chain: dict[str, BIOSChainEntry]
) -> None:
    """Every winner-or-BIOS appears in exactly one of succeeded/skipped/failed."""
    plan = _plan(
        winners=("kof94", "sf2ce"),
        machines={"kof94": _machine("kof94"), "sf2ce": _machine("sf2ce")},
        bios_chain=bios_chain,
        source_dir=source_dir,
        dest_dir=dest_dir,
    )
    report = run_copy(plan)
    expected = {"kof94", "sf2ce", "neogeo", "euro", "us", "sf2", "cps1bios"}
    actual = {o.short_name for o in (*report.succeeded, *report.skipped, *report.failed)}
    assert actual == expected
    # Disjoint.
    assert (
        len({o.short_name for o in report.succeeded} & {o.short_name for o in report.skipped}) == 0
    )


def test_copy_progress_callback_emits_per_file(
    source_dir: Path, dest_dir: Path, bios_chain: dict[str, BIOSChainEntry]
) -> None:
    """N copy operations → N progress events (one per file)."""
    plan = _plan(
        winners=("kof94",),
        machines={"kof94": _machine("kof94")},
        bios_chain=bios_chain,
        source_dir=source_dir,
        dest_dir=dest_dir,
    )
    file_events: list[str] = []

    def on_progress(short: str, done: int, total: int) -> None:
        if done == total:  # one event per file when done==total
            file_events.append(short)

    run_copy(plan, on_progress=on_progress)
    # 1 winner + 3 BIOS = 4 files.
    assert len(file_events) == 4


# --- Playlist conflict ----------------------------------------------------


def test_existing_playlist_append_no_conflict(
    source_dir: Path, dest_dir: Path, bios_chain: dict[str, BIOSChainEntry]
) -> None:
    """Append mode adds new games without disturbing existing entries."""
    # Pre-existing playlist with one entry.
    existing = {
        "version": "1.5",
        "default_core_path": "",
        "default_core_name": "",
        "label_display_mode": 0,
        "right_thumbnail_mode": 0,
        "left_thumbnail_mode": 0,
        "sort_mode": 0,
        "items": [
            {
                "path": str((dest_dir / "preexisting.zip").resolve()),
                "label": "Pre-existing Game",
                "core_path": "DETECT",
                "core_name": "DETECT",
                "crc32": "00000000|crc",
                "db_name": "MAME.lpl",
            }
        ],
    }
    (dest_dir / "mame.lpl").write_text(json.dumps(existing, indent=2), encoding="utf-8")

    plan = _plan(
        winners=("kof94",),
        machines={"kof94": _machine("kof94", "KoF '94")},
        bios_chain=bios_chain,
        source_dir=source_dir,
        dest_dir=dest_dir,
        conflict_strategy=ConflictStrategy.APPEND,
    )
    report = run_copy(plan)
    assert report.status is CopyReportStatus.OK
    parsed = json.loads((dest_dir / "mame.lpl").read_text(encoding="utf-8"))
    labels = [item["label"] for item in parsed["items"]]
    assert "Pre-existing Game" in labels
    assert "KoF '94" in labels


def test_existing_playlist_overwrite_discards_old(
    source_dir: Path, dest_dir: Path, bios_chain: dict[str, BIOSChainEntry]
) -> None:
    """Overwrite discards the entire existing playlist."""
    (dest_dir / "mame.lpl").write_text(json.dumps({"items": [{"label": "old"}]}), encoding="utf-8")
    plan = _plan(
        winners=("kof94",),
        machines={"kof94": _machine("kof94", "KoF '94")},
        bios_chain=bios_chain,
        source_dir=source_dir,
        dest_dir=dest_dir,
        conflict_strategy=ConflictStrategy.OVERWRITE,
    )
    report = run_copy(plan)
    assert report.status is CopyReportStatus.OK
    parsed = json.loads((dest_dir / "mame.lpl").read_text(encoding="utf-8"))
    labels = [item["label"] for item in parsed["items"]]
    assert "old" not in labels
    assert "KoF '94" in labels


def test_existing_playlist_cancel_makes_no_writes(
    source_dir: Path, dest_dir: Path, bios_chain: dict[str, BIOSChainEntry]
) -> None:
    """Cancel strategy when playlist exists → CANCELLED_PLAYLIST_CONFLICT, no writes."""
    (dest_dir / "mame.lpl").write_text('{"items": []}', encoding="utf-8")
    plan = _plan(
        winners=("kof94",),
        machines={"kof94": _machine("kof94")},
        bios_chain=bios_chain,
        source_dir=source_dir,
        dest_dir=dest_dir,
        conflict_strategy=ConflictStrategy.CANCEL,
    )
    report = run_copy(plan)
    assert report.status is CopyReportStatus.CANCELLED_PLAYLIST_CONFLICT
    # No new zips copied.
    assert not (dest_dir / "kof94.zip").exists()


# --- Pause / resume / cancel ----------------------------------------------


def test_pause_holds_at_file_boundary(
    source_dir: Path, dest_dir: Path, bios_chain: dict[str, BIOSChainEntry]
) -> None:
    """A pause before the first file holds the worker; resume completes."""
    plan = _plan(
        winners=("kof94",),
        machines={"kof94": _machine("kof94")},
        bios_chain=bios_chain,
        source_dir=source_dir,
        dest_dir=dest_dir,
    )
    controller = CopyController()
    controller.pause()

    done = threading.Event()
    result: dict[str, object] = {}

    def runner() -> None:
        result["report"] = run_copy(plan, controller=controller)
        done.set()

    t = threading.Thread(target=runner, daemon=True)
    t.start()
    # Worker is paused; nothing copied yet.
    assert not done.wait(timeout=0.2)
    assert not (dest_dir / "kof94.zip").exists()

    controller.resume()
    assert done.wait(timeout=5.0)
    t.join(timeout=5.0)
    assert (dest_dir / "kof94.zip").exists()


def test_cancel_with_keep_partial(
    source_dir: Path, dest_dir: Path, bios_chain: dict[str, BIOSChainEntry]
) -> None:
    """Cancel mid-session keeps already-copied files (default)."""
    plan = _plan(
        winners=("kof94", "sf2ce"),
        machines={"kof94": _machine("kof94"), "sf2ce": _machine("sf2ce")},
        bios_chain=bios_chain,
        source_dir=source_dir,
        dest_dir=dest_dir,
    )
    controller = CopyController()
    # Cancel immediately; runner should bail out quickly.
    controller.cancel(recycle_partial=False)
    report = run_copy(plan, controller=controller)
    assert report.status is CopyReportStatus.CANCELLED
    # Anything already copied stays put — but with cancel-before-start there
    # may be nothing copied. The contract: not deleted.
    assert report.recycled == ()

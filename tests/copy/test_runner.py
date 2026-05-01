"""End-to-end tests for `run_copy` orchestrator."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

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


# DS01 — Cluster A and B tests below


def test_cancel_after_first_winner_keeps_partial(
    tmp_path: Path,
    bios_chain: dict[str, BIOSChainEntry],
) -> None:
    """B2 — strengthens `test_cancel_with_keep_partial` to exercise mid-session
    cancel rather than cancel-before-start. Two winners; cancel fires from the
    progress callback the moment the first winner finishes copying. Assertion:
    first winner's dst survives intact; second winner's dst was never written.

    Uses a per-test source dir with ≥1 MiB zips so `_chunked_copy` actually
    fires (the shared `source_dir` fixture writes ~600 B zips that go through
    `shutil.copy2` instead, bypassing the chunk-progress path entirely).
    """
    src = tmp_path / "src"
    src.mkdir()
    payload = b"X" * (2 * 1024 * 1024)  # 2 MiB > _CHUNK (1 MiB)
    (src / "kof94.zip").write_bytes(payload)
    (src / "sf2ce.zip").write_bytes(payload)
    # BIOS deps: kof94's chain (neogeo + biossets) + sf2ce's chain (sf2 + cps1bios).
    for name in ("neogeo", "euro", "us", "sf2", "cps1bios"):
        (src / f"{name}.zip").write_bytes(payload)
    dest = tmp_path / "dest"
    dest.mkdir()

    plan = _plan(
        winners=("kof94", "sf2ce"),
        machines={"kof94": _machine("kof94"), "sf2ce": _machine("sf2ce")},
        bios_chain=bios_chain,
        source_dir=src,
        dest_dir=dest,
    )
    controller = CopyController()
    cancelled: list[bool] = []

    def on_progress(short: str, done: int, total: int) -> None:
        if not cancelled and short == "kof94" and done == total:
            cancelled.append(True)
            controller.cancel(recycle_partial=False)

    report = run_copy(plan, controller=controller, on_progress=on_progress)

    assert report.status is CopyReportStatus.CANCELLED
    assert (dest / "kof94.zip").exists(), "first winner dst must survive cancel"
    assert (dest / "kof94.zip").stat().st_size == len(payload)
    assert not (dest / "sf2ce.zip").exists(), "second winner must not have been started"


def test_runner_logs_exception_on_copy_one_failure(
    source_dir: Path,
    dest_dir: Path,
    bios_chain: dict[str, BIOSChainEntry],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A5 — when `copy_one` raises, the runner currently swallows the
    traceback and only `str(exc)` reaches `CopyOutcome.error`. The fix is
    `logger.exception(...)` immediately inside the `except Exception` block
    at `runner.py:258`, so the full stack frame survives in logs.
    """
    import logging

    from mame_curator.copy import executor

    # Use OSError (typed family) so the FP05 A3-narrowed except clause
    # `except (OSError, CopyError)` catches it. RuntimeError post-A3
    # propagates by design (e.g. MemoryError must not be swallowed).
    def _boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("synthetic failure for A5 test")

    monkeypatch.setattr(executor, "copy_one", _boom)
    # The runner imports `copy_one` at module level via `from .executor import
    # copy_one`; patching the executor module also requires patching the
    # runner's own binding.
    from mame_curator.copy import runner as runner_module

    monkeypatch.setattr(runner_module, "copy_one", _boom)

    plan = _plan(
        winners=("kof94",),
        machines={"kof94": _machine("kof94")},
        bios_chain=bios_chain,
        source_dir=source_dir,
        dest_dir=dest_dir,
    )

    with caplog.at_level(logging.ERROR, logger="mame_curator.copy.runner"):
        report = run_copy(plan)

    # Outcome is recorded as FAILED with the exception string.
    assert any(
        o.error is not None and "synthetic failure" in (o.error or "") for o in report.failed
    )
    # `logger.exception` always attaches `exc_info`; `logger.error` does not.
    # This pins the call as `.exception(...)` rather than `.error(...)` —
    # without it the traceback is silently swallowed (the bug DS01 A5 fixed).
    runner_records = [rec for rec in caplog.records if rec.name == "mame_curator.copy.runner"]
    assert runner_records, "runner did not log the exception"
    assert all(rec.exc_info is not None for rec in runner_records), (
        "logger must use .exception() so traceback survives in logs"
    )
    # The exception's class + message are reachable via exc_info.
    assert any(
        rec.exc_info is not None and "synthetic failure" in str(rec.exc_info[1])
        for rec in runner_records
    )


# FP05 — cluster A1 + A3 tests below


def test_cancel_recycle_partial_recycles_winner_and_bios(
    tmp_path: Path,
    bios_chain: dict[str, BIOSChainEntry],
) -> None:
    """A1 — `controller.cancel(recycle_partial=True)` after a winner *and*
    its BIOS file have completed must move BOTH to `data/recycle/<session_id>/`.

    Spec: `copy/spec.md` § Pause/Resume/Cancel — "every successfully-copied
    file from the current session is moved to recycle". This test pins the
    "every file" wording: winner and bios both, not just winner.
    """
    src = tmp_path / "src"
    src.mkdir()
    payload = b"X" * (2 * 1024 * 1024)  # 2 MiB > _CHUNK so progress fires
    # kof94's chain is neogeo (romof) + euro + us (biossets).
    for name in ("kof94", "neogeo", "euro", "us"):
        (src / f"{name}.zip").write_bytes(payload)
    dest = tmp_path / "dest"
    dest.mkdir()

    plan = _plan(
        winners=("kof94",),
        machines={"kof94": _machine("kof94")},
        bios_chain=bios_chain,
        source_dir=src,
        dest_dir=dest,
    )
    controller = CopyController()
    triggered: list[bool] = []

    def on_progress(short: str, done: int, total: int) -> None:
        # Cancel only after at least the winner + first BIOS have completed.
        if (
            not triggered
            and done == total
            and short in ("euro", "us")  # second-or-later BIOS finished
        ):
            triggered.append(True)
            controller.cancel(recycle_partial=True)

    report = run_copy(plan, controller=controller, on_progress=on_progress)
    assert report.status is CopyReportStatus.CANCELLED

    # Both winner and at least one bios should be in the recycled set.
    # `RecycleRecord` carries `original_path`; the short-name is the
    # filename stem.
    recycled_shorts = {r.original_path.stem for r in report.recycled}
    assert "kof94" in recycled_shorts, "winner must be recycled per 'every file' contract"
    assert recycled_shorts & {"neogeo", "euro", "us"}, (
        "at least one BIOS file must be recycled per 'every file' contract"
    )
    # Originals at dst no longer exist (move, not copy).
    assert not (dest / "kof94.zip").exists()
    # Recycled files land in the project-default recycle root (matches
    # other recycle call sites). Verify via the report's RecycleRecord
    # paths — they're absolute and point at the actual on-disk locations.
    for r in report.recycled:
        assert r.recycled_path.exists(), f"recycled file missing: {r.recycled_path}"


def test_runner_propagates_memoryerror(
    source_dir: Path,
    dest_dir: Path,
    bios_chain: dict[str, BIOSChainEntry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A3 — `MemoryError` raised from `copy_one` must propagate, not land
    in `report.failed`. Continuing the loop after OOM is exactly wrong;
    the bare `except Exception` swallows MemoryError today."""
    from mame_curator.copy import runner as runner_module

    def _oom(*_args: object, **_kwargs: object) -> None:
        raise MemoryError("synthetic OOM")

    monkeypatch.setattr(runner_module, "copy_one", _oom)
    plan = _plan(
        winners=("kof94",),
        machines={"kof94": _machine("kof94")},
        bios_chain=bios_chain,
        source_dir=source_dir,
        dest_dir=dest_dir,
    )

    with pytest.raises(MemoryError):
        run_copy(plan)

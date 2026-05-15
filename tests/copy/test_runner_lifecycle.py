"""Pause / resume / cancel / DS01 / FP05 tests for `run_copy` orchestrator.

Extracted from `tests/copy/test_runner.py` during DS05 Cluster B to
keep both files under the 500-line hard cap. The split seam mirrors
the original file's `# --- Pause / resume / cancel ---` section
header. `_machine` / `_plan` factory helpers live in
`tests/copy/_runner_helpers.py` (sibling module, leading underscore =
not a test file).
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from mame_curator.copy import CopyController, run_copy
from mame_curator.copy.types import CopyReportStatus
from mame_curator.parser.listxml import BIOSChainEntry

from ._runner_helpers import _machine, _plan

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

    # Use OSError (typed family) so the FP05 A3-narrowed except clause
    # `except (OSError, CopyError)` catches it. RuntimeError post-A3
    # propagates by design (e.g. MemoryError must not be swallowed).
    def _boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("synthetic failure for A5 test")

    # `runner` imports `copy_one` at module level via `from .executor
    # import copy_one`, so the load-bearing patch target is the runner
    # module's binding — not the executor's. (DS04 T1.7 removed a
    # parallel patch on `executor.copy_one` that never fired.)
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

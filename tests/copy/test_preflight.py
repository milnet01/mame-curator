"""Tests for `preflight`."""

from __future__ import annotations

from pathlib import Path

import pytest

from mame_curator.copy import preflight
from mame_curator.copy.types import ConflictStrategy, CopyPlan
from mame_curator.parser.listxml import BIOSChainEntry

# FP31: `_machine` lifted to the shared `_runner_helpers` module.
from tests.copy._runner_helpers import _machine


def _plan(
    *,
    winners: tuple[str, ...],
    source_dir: Path,
    dest_dir: Path,
    bios_chain: dict[str, BIOSChainEntry] | None = None,
) -> CopyPlan:
    return CopyPlan(
        winners=winners,
        machines={w: _machine(w) for w in winners},
        bios_chain=bios_chain or {},
        source_dir=source_dir,
        dest_dir=dest_dir,
        conflict_strategy=ConflictStrategy.CANCEL,
    )


def test_preflight_clean_plan_returns_empty_findings(source_dir: Path, dest_dir: Path) -> None:
    plan = _plan(winners=("kof94", "sf2"), source_dir=source_dir, dest_dir=dest_dir)
    result = preflight(plan)
    assert result.missing_source == ()
    assert result.dest_writable is True
    assert result.existing_playlist is False
    assert result.already_copied == ()


def test_preflight_detects_missing_source_zips(tmp_path: Path, dest_dir: Path) -> None:
    """Winner with no .zip in source is recorded in missing_source."""
    src = tmp_path / "source"
    src.mkdir()
    (src / "kof94.zip").write_bytes(b"x")
    plan = _plan(winners=("kof94", "ghost"), source_dir=src, dest_dir=dest_dir)
    result = preflight(plan)
    assert result.missing_source == ("ghost",)


def test_preflight_detects_existing_playlist(source_dir: Path, dest_dir: Path) -> None:
    (dest_dir / "mame.lpl").write_text('{"items": []}', encoding="utf-8")
    plan = _plan(winners=("kof94",), source_dir=source_dir, dest_dir=dest_dir)
    result = preflight(plan)
    assert result.existing_playlist is True


def test_preflight_detects_idempotent_already_copied(source_dir: Path, dest_dir: Path) -> None:
    """An identical (size+mtime) zip already at dest is recorded."""
    import shutil

    shutil.copy2(source_dir / "kof94.zip", dest_dir / "kof94.zip")
    plan = _plan(winners=("kof94",), source_dir=source_dir, dest_dir=dest_dir)
    result = preflight(plan)
    assert "kof94" in result.already_copied


def test_fp21_e_preflight_total_needed_includes_bios_chain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FP21-E: ``preflight`` accounts for BIOS-chain zips when computing
    ``free_space_gap_bytes``. Pre-fix ``total_needed`` summed only
    ``plan.winners`` zips; ``run_copy`` actually transfers
    ``winners | bios_set`` so the free-space estimate was systematically
    under-counted by the BIOS chain's size — a 50 MB neogeo BIOS missing
    from the estimate could mean "preflight OK" then mid-copy ENOSPC.

    Real ``shutil.disk_usage`` is replaced with a deterministic stub so
    concurrent filesystem activity (other tests, OS-side I/O) can't
    perturb the delta. We only care that the BIOS bytes change the
    answer — not how much real disk is free.
    """
    import shutil as _shutil

    src = tmp_path / "source"
    src.mkdir()
    dest = tmp_path / "dest"
    dest.mkdir()
    (src / "kof94.zip").write_bytes(b"x" * 1000)
    (src / "neogeo.zip").write_bytes(b"y" * 100_000)

    FIXED_FREE = 10 * 1024 * 1024  # 10 MB headroom; deterministic between calls

    def fake_disk_usage(_path: object) -> object:
        # ``shutil._ntuple_diskusage`` is the precise named-tuple type;
        # SimpleNamespace satisfies the only attribute preflight reads.
        from types import SimpleNamespace

        return SimpleNamespace(total=FIXED_FREE * 2, used=FIXED_FREE, free=FIXED_FREE)

    monkeypatch.setattr(_shutil, "disk_usage", fake_disk_usage)

    plan_with_bios = _plan(
        winners=("kof94",),
        source_dir=src,
        dest_dir=dest,
        bios_chain={"kof94": BIOSChainEntry(romof="neogeo")},
    )
    plan_no_bios = _plan(
        winners=("kof94",),
        source_dir=src,
        dest_dir=dest,
        bios_chain={},
    )

    result_with = preflight(plan_with_bios)
    result_no = preflight(plan_no_bios)

    # With BIOS: total_needed = 1000 + 100_000 = 101_000
    # No BIOS:    total_needed = 1000
    # gap = FIXED_FREE - total_needed → delta = exactly 100_000.
    delta = result_no.free_space_gap_bytes - result_with.free_space_gap_bytes
    assert delta == 100_000, (
        f"BIOS zip's 100KB must show as a 100KB drop in free_space_gap_bytes; "
        f"observed delta={delta}"
    )


def test_fp21_e_preflight_total_needed_subtracts_already_copied(
    tmp_path: Path, source_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FP21-E: ``preflight`` subtracts already-copied bytes from
    ``total_needed`` so a re-run on a fully-idempotent set reports a
    meaningful free-space gap (not a phantom shortfall).

    Two-run gap-difference check (mirrors the BIOS-chain test above): with
    ``shutil.disk_usage`` pinned to a fixed free value, the only thing that
    moves ``free_space_gap_bytes`` between the two runs is whether kof94 is
    already at dest. The delta must equal exactly kof94's size — a stronger
    claim than the old ``gap >= -sf2_size`` lower bound, which passed even if
    the already-copied subtraction were dropped (mame-curator-1055g).
    """
    import shutil as _shutil

    # dest_present has kof94 already copied (→ already_copied, not needed);
    # dest_absent is empty (→ kof94 must be copied, counts toward total).
    dest_present = tmp_path / "dest_present"
    dest_present.mkdir()
    dest_absent = tmp_path / "dest_absent"
    dest_absent.mkdir()
    _shutil.copy2(source_dir / "kof94.zip", dest_present / "kof94.zip")

    FIXED_FREE = 10 * 1024 * 1024  # deterministic between the two calls

    def fake_disk_usage(_path: object) -> object:
        from types import SimpleNamespace

        return SimpleNamespace(total=FIXED_FREE * 2, used=FIXED_FREE, free=FIXED_FREE)

    monkeypatch.setattr(_shutil, "disk_usage", fake_disk_usage)

    result_present = preflight(
        _plan(winners=("kof94", "sf2"), source_dir=source_dir, dest_dir=dest_present)
    )
    result_absent = preflight(
        _plan(winners=("kof94", "sf2"), source_dir=source_dir, dest_dir=dest_absent)
    )
    assert "kof94" in result_present.already_copied
    assert "kof94" not in result_absent.already_copied

    kof94_size = (source_dir / "kof94.zip").stat().st_size
    # present: total_needed = sf2; absent: total_needed = sf2 + kof94.
    # gap = FIXED_FREE - total_needed → the already-copied kof94 lifts the gap
    # by exactly its size.
    delta = result_present.free_space_gap_bytes - result_absent.free_space_gap_bytes
    assert delta == kof94_size, (
        f"already-copied kof94 ({kof94_size} bytes) must lift free_space_gap "
        f"by exactly its size; observed delta={delta}"
    )


def test_preflight_dest_writable_false_when_dest_missing_and_uncreatable(tmp_path: Path) -> None:
    """Non-existent dest under a non-writable parent → dest_writable=False."""
    # Use a path that cannot exist as a directory (a file pretending to be a dir).
    blocker = tmp_path / "blocker"
    blocker.write_bytes(b"x")
    dest = blocker / "nested"  # Cannot create — blocker is a file
    src = tmp_path / "source"
    src.mkdir()
    plan = _plan(winners=(), source_dir=src, dest_dir=dest)
    result = preflight(plan)
    assert result.dest_writable is False

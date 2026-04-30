"""Tests for `preflight`."""

from __future__ import annotations

from pathlib import Path

from mame_curator.copy import preflight
from mame_curator.copy.types import ConflictStrategy, CopyPlan
from mame_curator.parser.listxml import BIOSChainEntry
from mame_curator.parser.models import Machine


def _machine(short: str, desc: str = "") -> Machine:
    return Machine(name=short, description=desc or short, runnable=True)


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

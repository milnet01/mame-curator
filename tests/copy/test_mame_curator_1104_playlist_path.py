"""mame-curator-1104 — the playlist goes where ``CopyPlan.playlist_path`` says.

Observed 2026-09-26: with ``paths.retroarch_playlist`` set outside
``paths.dest_roms``, ``mame.lpl`` appeared in the ROM folder and not at the
configured path. ``run_copy``, ``preflight`` and the APPEND reader all
hard-coded ``plan.dest_dir / "mame.lpl"``, so the setting did nothing.

Pre-fix: ``CopyPlan`` has no ``playlist_path`` field and forbids extras, so
building the plan raises ``ValidationError``.
"""

from __future__ import annotations

import json
from pathlib import Path

from mame_curator.copy import preflight, run_copy
from mame_curator.copy.types import ConflictStrategy, CopyPlan, CopyReportStatus
from mame_curator.parser.listxml import BIOSChainEntry

from ._runner_helpers import _machine


def _plan(
    source_dir: Path,
    dest_dir: Path,
    bios_chain: dict[str, BIOSChainEntry],
    playlist: Path | None,
    strategy: ConflictStrategy = ConflictStrategy.CANCEL,
) -> CopyPlan:
    return CopyPlan(
        winners=("kof94",),
        machines={"kof94": _machine("kof94", "KoF '94")},
        bios_chain=bios_chain,
        source_dir=source_dir,
        dest_dir=dest_dir,
        playlist_path=playlist,
        conflict_strategy=strategy,
    )


def _labels(path: Path) -> list[str]:
    return [item["label"] for item in json.loads(path.read_text(encoding="utf-8"))["items"]]


def test_playlist_written_to_playlist_path_not_dest(
    source_dir: Path, dest_dir: Path, bios_chain: dict[str, BIOSChainEntry], tmp_path: Path
) -> None:
    playlist = tmp_path / "playlists" / "mame.lpl"
    playlist.parent.mkdir()
    report = run_copy(_plan(source_dir, dest_dir, bios_chain, playlist))
    assert report.status is CopyReportStatus.OK
    assert _labels(playlist) == ["KoF '94"]
    assert not (dest_dir / "mame.lpl").exists(), "playlist must not land in the ROM folder"


def test_playlist_path_defaults_to_dest_mame_lpl(
    source_dir: Path, dest_dir: Path, bios_chain: dict[str, BIOSChainEntry]
) -> None:
    """No playlist_path (the CLI has no config) keeps the old location."""
    run_copy(_plan(source_dir, dest_dir, bios_chain, None))
    assert _labels(dest_dir / "mame.lpl") == ["KoF '94"]


def test_preflight_and_append_use_playlist_path(
    source_dir: Path, dest_dir: Path, bios_chain: dict[str, BIOSChainEntry], tmp_path: Path
) -> None:
    playlist = tmp_path / "playlists" / "mame.lpl"
    playlist.parent.mkdir()
    old = {"items": [{"path": str(dest_dir / "old.zip"), "label": "Old Game"}]}
    playlist.write_text(json.dumps(old), encoding="utf-8")

    plan = _plan(source_dir, dest_dir, bios_chain, playlist, ConflictStrategy.APPEND)
    assert preflight(plan).existing_playlist is True

    run_copy(plan)
    assert _labels(playlist) == ["KoF '94", "Old Game"]

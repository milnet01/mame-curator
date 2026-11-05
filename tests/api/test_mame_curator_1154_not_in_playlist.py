"""mame-curator-1154 — the dry run counts games on the drive but not in the playlist.

A copy stopped part way keeps its files and writes no playlist. The guide's
Check step then saw every game as already copied and hid Start, so nothing
could ever add those games to the playlist. ``counts.not_in_playlist`` is the
games already at the destination that no playlist entry names, read from the
playlist actually there (spec mame-curator-1144 § 4.4, INV-8).
"""

from __future__ import annotations

import json
import shutil
import struct
from pathlib import Path
from typing import Any

import zstandard

from mame_curator.copy import run_copy
from mame_curator.copy.playlist import read_lpl
from mame_curator.copy.types import ConflictStrategy, CopyPlan
from mame_curator.parser.models import Machine

GAMES = ["pacman", "pacmanf"]


def _request(strategy: str = "APPEND") -> dict[str, Any]:
    return {"selected_names": GAMES, "conflict_strategy": strategy, "append_decisions": {}}


def _put_on_drive(source_dir: Path, dest_dir: Path) -> None:
    """What a stopped copy leaves: the files, at the size and time a rerun skips."""
    for short in GAMES:
        shutil.copy2(source_dir / f"{short}.zip", dest_dir / f"{short}.zip")


def _playlist_json(dest_dir: Path, shorts: list[str]) -> bytes:
    items = [{"path": str(dest_dir / f"{s}.zip"), "label": s} for s in shorts]
    return json.dumps({"version": "1.5", "items": items}).encode()


def _rzip(data: bytes) -> bytes:
    """RetroArch's compressed playlist: one zstd chunk (see test_mame_curator_1174)."""
    block = zstandard.ZstdCompressor().compress(data)
    header = b"#RZIPv\x02#" + struct.pack("<IQ", len(data), len(data))
    return header + struct.pack("<I", len(block)) + block


def _counts(client: Any, strategy: str = "APPEND") -> dict[str, int]:
    response = client.post("/api/copy/dry-run", json=_request(strategy))
    assert response.status_code == 200, response.text
    counts: dict[str, int] = response.json()["counts"]
    return counts


def test_no_playlist_counts_every_game_on_the_drive(
    client: Any, source_dir: Path, dest_dir: Path
) -> None:
    _put_on_drive(source_dir, dest_dir)

    counts = _counts(client)

    assert counts["already_copied"] == 2
    assert counts["new"] == 0
    assert counts["not_in_playlist"] == 2


def test_counts_only_the_games_the_playlist_does_not_name(
    client: Any, source_dir: Path, dest_dir: Path
) -> None:
    _put_on_drive(source_dir, dest_dir)
    (dest_dir / "mame.lpl").write_bytes(_playlist_json(dest_dir, ["pacman"]))

    assert _counts(client)["not_in_playlist"] == 1


def test_reads_retroarchs_compressed_playlist(
    client: Any, source_dir: Path, dest_dir: Path
) -> None:
    _put_on_drive(source_dir, dest_dir)
    (dest_dir / "mame.lpl").write_bytes(_rzip(_playlist_json(dest_dir, GAMES)))

    assert _counts(client)["not_in_playlist"] == 0


def test_a_game_not_yet_copied_is_not_counted(client: Any, dest_dir: Path) -> None:
    """A new game is the copy's to add; this count is for files already there."""
    counts = _counts(client)

    assert counts["new"] == 2
    assert counts["not_in_playlist"] == 0


def test_an_unreadable_playlist_is_refused_as_the_start_refuses_it(
    client: Any, source_dir: Path, dest_dir: Path
) -> None:
    _put_on_drive(source_dir, dest_dir)
    (dest_dir / "mame.lpl").write_bytes(b"not a playlist")

    dry = client.post("/api/copy/dry-run", json=_request())
    start = client.post("/api/copy/start", json=_request())

    assert dry.status_code == start.status_code == 409, dry.text
    assert dry.json()["code"] == start.json()["code"] == "playlist_unreadable"


def test_an_unreadable_playlist_does_not_stop_an_overwrite_dry_run(
    client: Any, source_dir: Path, dest_dir: Path
) -> None:
    """OVERWRITE never reads the old playlist, so neither does its dry run."""
    _put_on_drive(source_dir, dest_dir)
    (dest_dir / "mame.lpl").write_bytes(b"not a playlist")

    assert _counts(client, "OVERWRITE")["not_in_playlist"] == 2


def test_an_append_start_writes_games_already_on_the_drive(
    source_dir: Path, dest_dir: Path, tmp_path: Path
) -> None:
    """What Start does for these games: every one ends up in the playlist."""
    _put_on_drive(source_dir, dest_dir)
    plan = CopyPlan(
        winners=tuple(GAMES),
        machines={s: Machine(name=s, description=s, runnable=True) for s in GAMES},
        bios_chain={},
        source_dir=source_dir,
        dest_dir=dest_dir,
        conflict_strategy=ConflictStrategy.APPEND,
    )

    run_copy(plan, data_dir=tmp_path / "data")

    named = {Path(item["path"]).name for item in read_lpl(dest_dir / "mame.lpl")}
    assert named == {"pacman.zip", "pacmanf.zip"}

"""mame-curator-1104 — the API copies to the configured ``retroarch_playlist``.

Settings → Paths and ``setup`` both collect ``paths.retroarch_playlist``,
but ``_build_plan`` never passed it on, so the playlist was written to
``dest_roms/mame.lpl`` and the CANCEL conflict check looked there too.

Pre-fix: the plan built by ``_build_plan`` has no ``playlist_path``.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from mame_curator.api.errors import PlaylistConflictCancelledError
from mame_curator.api.jobs import check_playlist_conflict
from mame_curator.api.routes.copy import _build_plan
from mame_curator.api.schemas_copy import CopyJobRequest
from mame_curator.api.state import WorldState


def _world(tmp_path: Path) -> tuple[WorldState, Path]:
    dest = tmp_path / "roms"
    dest.mkdir()
    playlist = tmp_path / "playlists" / "mame.lpl"
    playlist.parent.mkdir()
    paths = SimpleNamespace(
        source_roms=tmp_path / "src", dest_roms=dest, retroarch_playlist=playlist
    )
    # Only the attributes _build_plan reads; a real WorldState needs parsed
    # DAT/listxml/INI state this test has no use for.
    world = SimpleNamespace(
        machines={}, bios_chain={}, chd_required=frozenset(), config=SimpleNamespace(paths=paths)
    )
    return cast(WorldState, world), playlist


def test_build_plan_carries_configured_playlist_path(tmp_path: Path) -> None:
    world, playlist = _world(tmp_path)
    plan = _build_plan(CopyJobRequest(selected_names=("pacman",)), world)
    assert plan.playlist_path == playlist


def test_cancel_conflict_checks_configured_playlist(tmp_path: Path) -> None:
    world, playlist = _world(tmp_path)
    plan = _build_plan(CopyJobRequest(selected_names=("pacman",)), world)

    # A stray mame.lpl in the ROM folder is not the configured playlist.
    (tmp_path / "roms" / "mame.lpl").write_text('{"items": []}', encoding="utf-8")
    check_playlist_conflict(plan)

    playlist.write_text('{"items": []}', encoding="utf-8")
    with pytest.raises(PlaylistConflictCancelledError):
        check_playlist_conflict(plan)

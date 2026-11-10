"""mame-curator-1208 — ``GET /api/setup/dat-check`` answers for the wizard's list step."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from tests.api.conftest import PARSER_FIXTURES


def test_a_game_list_parses(client: Any, fake_home: Path) -> None:
    dat = fake_home / "mame.xml"
    shutil.copy(PARSER_FIXTURES / "mini.dat.xml", dat)
    reply = client.get("/api/setup/dat-check", params={"path": str(dat)})
    assert reply.status_code == 200
    assert reply.json() == {"path": str(dat), "parses": True}


def test_another_file_does_not(client: Any, fake_home: Path) -> None:
    notes = fake_home / "notes.xml"
    notes.write_text("<not a game list")
    reply = client.get("/api/setup/dat-check", params={"path": str(notes)})
    assert reply.status_code == 200
    assert reply.json()["parses"] is False


def test_it_looks_only_where_the_picker_may(client: Any, fake_home: Path) -> None:
    reply = client.get("/api/setup/dat-check", params={"path": "/etc/hostname"})
    assert reply.status_code == 403
    assert reply.json()["code"] == "fs_sandboxed"

"""mame-curator-1146 — picture choices in Backup export, import and restore.

Per ``docs/specs/mame-curator-1146-picture-choice.md`` §4.7 and INV-10. The
test config's only media source is ``libretro``, which covers every kind, so
a save needs no fake source; a save fetches nothing.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

_CHOICE = {"source": "libretro", "kind": "title"}


def _data(config_file: Path) -> Path:
    return config_file.parent / "data"


def _choose(client: Any, kind: str = "title") -> None:
    reply = client.put("/api/games/pacman/picture", json={"source": "libretro", "kind": kind})
    assert reply.status_code == 200, reply.text


def _picture(client: Any) -> object:
    items = client.get("/api/games/pacman/alternatives").json()["items"]
    return next(c for c in items if c["short_name"] == "pacman")["picture"]


def _targets(config_file: Path) -> list[Path]:
    base = config_file.parent
    return [
        config_file,
        base / "overrides.yaml",
        base / "sessions.yaml",
        _data(config_file) / "notes.json",
        _data(config_file) / "pictures.json",
    ]


def _bytes(paths: list[Path]) -> list[bytes | None]:
    return [p.read_bytes() if p.exists() else None for p in paths]


def test_export_leaves_pictures_out_when_there_are_none(client: Any) -> None:
    body = client.post("/api/config/export").json()
    assert "pictures" not in body
    # A null inside config stays, so the bundle keeps every value it held.
    assert "retroarch" in body["config"]["paths"]
    assert body["config"]["paths"]["retroarch"] is None


def test_export_holds_the_choices_when_there_are_some(client: Any) -> None:
    _choose(client)
    body = client.post("/api/config/export").json()
    assert body["pictures"] == {"pictures": {"pacman": _CHOICE}}
    assert body["config"]["paths"]["retroarch"] is None


def test_a_backup_with_choices_restores_them(client: Any) -> None:
    _choose(client)
    bundle = client.post("/api/config/export").json()
    assert client.delete("/api/games/pacman/picture").status_code == 200
    assert client.post("/api/config/import", json=bundle).status_code == 200
    assert _picture(client) == _CHOICE


def test_importing_a_backup_from_before_choices_clears_them(client: Any, config_file: Path) -> None:
    pre_1146 = client.post("/api/config/export").json()
    assert set(pre_1146) == {"config", "overrides", "sessions", "notes"}
    _choose(client)
    held = (_data(config_file) / "pictures.json").read_bytes()
    reply = client.post("/api/config/import", json=pre_1146)
    assert reply.status_code == 200, reply.text
    assert _picture(client) is None
    stored = json.loads((_data(config_file) / "pictures.json").read_text())
    assert stored == {"pictures": {}}
    # The snapshot taken first keeps the choices.
    snapshots = _data(config_file) / "snapshots"
    assert held in [p.read_bytes() for p in snapshots.glob("*/pictures.json")]


def test_an_invalid_pictures_entry_is_refused_and_changes_no_file(
    client: Any, config_file: Path
) -> None:
    _choose(client)
    bundle = client.post("/api/config/export").json()
    bundle["config"]["ui"]["theme"] = "light"
    bundle["notes"] = {"pacman": "changed"}
    bundle["pictures"] = {"pictures": {"pacman": {"source": "esde"}}}
    targets = _targets(config_file)
    before = _bytes(targets)

    reply = client.post("/api/config/import", json=bundle)

    assert reply.status_code == 422
    assert reply.json()["code"] == "config_invalid"
    assert "invalid pictures" in reply.json()["detail"]
    assert _bytes(targets) == before


def test_restore_puts_back_pictures_from_a_snapshot_that_covers_them(
    client: Any, config_file: Path
) -> None:
    _choose(client, "title")
    _choose(client, "snap")  # snapshots the file holding the title choice
    snaps = sorted((_data(config_file) / "snapshots").glob("*/pictures.json"))
    assert snaps
    reply = client.post(f"/api/config/snapshots/{snaps[-1].parent.name}/restore")
    assert reply.status_code == 200, reply.text
    assert _picture(client) == _CHOICE


def test_restore_of_a_snapshot_from_before_choices_leaves_them(
    client: Any, config_file: Path
) -> None:
    old = _data(config_file) / "snapshots" / "20200101T000000_000000Z"
    old.mkdir(parents=True)
    shutil.copy(config_file, old / "config.yaml")
    covered = ["config.yaml", "notes.json", "overrides.yaml", "sessions.yaml", "state.yaml"]
    (old / ".covers.json").write_text(json.dumps(covered))
    _choose(client)
    pictures = _data(config_file) / "pictures.json"
    before = pictures.read_bytes()

    reply = client.post(f"/api/config/snapshots/{old.name}/restore")

    assert reply.status_code == 200, reply.text
    assert pictures.read_bytes() == before
    assert _picture(client) == _CHOICE

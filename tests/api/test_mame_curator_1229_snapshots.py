"""mame-curator-1229: settings snapshots, backups and notes (2026-11-11 review).

Each test names the finding it locks.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from mame_curator.api import persist
from tests.api.conftest import LOCAL_URL

# ---- CR-05-4, CR-05-9, CR-06-2: snapshot_files ------------------------------


def test_a_file_that_failed_to_read_is_not_covered(tmp_path: Path) -> None:
    """CR-05-4: covering it would make a later restore delete the live file."""
    good = tmp_path / "config.yaml"
    good.write_text("a: 1\n", encoding="utf-8")
    unreadable = tmp_path / "notes.json"
    unreadable.mkdir()  # exists, but read_bytes raises

    snap_id = persist.snapshot_files(
        tmp_path / "snapshots", {"config.yaml": good, "notes.json": unreadable}
    )

    covers = json.loads((tmp_path / "snapshots" / snap_id / ".covers.json").read_text())
    assert covers == ["config.yaml"]


def test_pruning_spares_the_snapshot_just_taken(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CR-05-9: after a clock change the new id can sort oldest of all."""
    monkeypatch.setattr(persist, "MAX_SNAPSHOTS", 2)
    snapshots = tmp_path / "snapshots"
    for name in ("29990101T000000_000000Z", "29990102T000000_000000Z"):
        (snapshots / name).mkdir(parents=True)
    # Not config.yaml, which the newest-config rule would spare on its own.
    src = tmp_path / "pictures.json"
    src.write_text("{}", encoding="utf-8")

    snap_id = persist.snapshot_files(snapshots, {"pictures.json": src})

    assert (snapshots / snap_id).is_dir()


def test_pruning_keeps_the_newest_config_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CR-06-2: picture (and other) saves must not push out every config snapshot."""
    monkeypatch.setattr(persist, "MAX_SNAPSHOTS", 2)
    snapshots = tmp_path / "snapshots"
    config = tmp_path / "config.yaml"
    config.write_text("a: 1\n", encoding="utf-8")
    pictures = tmp_path / "pictures.json"
    pictures.write_text("{}", encoding="utf-8")

    config_snap = persist.snapshot_files(snapshots, {"config.yaml": config})
    for _ in range(3):
        persist.snapshot_files(snapshots, {"pictures.json": pictures})

    assert (snapshots / config_snap / "config.yaml").is_file()


# ---- RR-05-2: one list of the user's files ----------------------------------


def test_update_snapshot_covers_every_user_file(app_started: Any) -> None:
    """RR-05-2: the update rollback left out pictures.json."""
    from mame_curator.api.routes.updates import _snapshot_targets

    world = app_started.state.world
    assert set(_snapshot_targets(world)) == {
        "config.yaml",
        "overrides.yaml",
        "sessions.yaml",
        "notes.json",
        "state.yaml",
        "pictures.json",
    }


# ---- CR-06-1: a backup from a newer version ---------------------------------


def test_import_drops_keys_this_version_does_not_know(client: Any) -> None:
    """CR-06-1: as load_app_config does, so a newer backup still imports."""
    bundle = client.post("/api/config/export").json()
    bundle["config"]["a_key_from_a_newer_version"] = True
    response = client.post("/api/config/import", json=bundle)
    assert response.status_code == 200, response.text


# ---- RL-25, RR-04-6: a corrupt notes.json in a snapshot ---------------------


def test_restore_sets_aside_a_snapshot_notes_file_that_does_not_load(
    client: Any, config_file: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """RL-25: it restored as empty notes, silently. Now it is kept and logged."""
    data = config_file.parent / "data"
    snap = data / "snapshots" / "20260101T000000_000000Z"
    snap.mkdir(parents=True)
    (snap / "notes.json").write_text("{not json", encoding="utf-8")
    (snap / ".covers.json").write_text('["notes.json"]', encoding="utf-8")

    with caplog.at_level("WARNING", logger="mame_curator.api.notes"):
        response = client.post("/api/config/snapshots/20260101T000000_000000Z/restore")

    assert response.status_code == 200, response.text
    kept = list(data.glob("notes.json.unreadable-*"))
    assert [p.read_text(encoding="utf-8") for p in kept] == ["{not json"]
    assert any("moved to" in r.getMessage() for r in caplog.records)


# ---- CR-05-5: a corrupt notes.json at start-up ------------------------------


@pytest.fixture
def notes_file(config_file: Path) -> Path:
    path = config_file.parent / "data" / "notes.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _started(app: Any) -> Iterator[TestClient]:
    with TestClient(app, base_url=LOCAL_URL) as c:
        yield c


@pytest.mark.parametrize("body", ["{not json", "[1, 2, 3]"])
def test_unreadable_notes_are_kept_aside_not_overwritten(
    app: Any, notes_file: Path, body: str
) -> None:
    """CR-05-5: the next note save used to overwrite the old file."""
    notes_file.write_text(body, encoding="utf-8")
    for c in _started(app):
        assert c.put("/api/games/pacman/notes", json={"notes": "new"}).status_code == 200

    kept = list(notes_file.parent.glob("notes.json.unreadable-*"))
    assert len(kept) == 1
    assert kept[0].read_text(encoding="utf-8") == body
    assert json.loads(notes_file.read_text(encoding="utf-8")) == {"pacman": "new"}


# ---- CR-07-12: a hand-edited note over the limit ----------------------------


def test_an_over_long_hand_edited_note_still_opens(app: Any, notes_file: Path) -> None:
    """CR-07-12: GET failed response validation with a 500."""
    notes_file.write_text(json.dumps({"pacman": "x" * 5000}), encoding="utf-8")
    for c in _started(app):
        response = c.get("/api/games/pacman/notes")
        assert response.status_code == 200
        assert len(response.json()["notes"]) == 4096
    # Shown cut, but the file keeps the whole note until the user saves it.
    assert len(json.loads(notes_file.read_text(encoding="utf-8"))["pacman"]) == 5000


# ---- CR-04-6: refresh-inis keeps a copy before it rewrites config.yaml ------


def test_refresh_inis_snapshots_the_config_before_rewriting_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CR-04-6: the rewrite drops comments; a snapshot keeps the file as it was."""
    from mame_curator.cli import build_parser, run
    from mame_curator.updates.ini import INIRefreshReport

    config = tmp_path / "config.yaml"
    original = "# my own comment\npaths: {}\n"
    config.write_text(original, encoding="utf-8")

    async def fake_refresh(*, dest_dir: Path, client: Any) -> INIRefreshReport:
        return INIRefreshReport(updated=["catver.ini"])

    monkeypatch.setattr("mame_curator.updates.refresh_inis", fake_refresh)
    args = build_parser().parse_args(
        ["refresh-inis", "--dest", str(tmp_path / "inis"), "--config", str(config)]
    )
    assert run(args) == 0

    kept = list((tmp_path / "data" / "snapshots").glob("*/config.yaml"))
    assert [p.read_text(encoding="utf-8") for p in kept] == [original]

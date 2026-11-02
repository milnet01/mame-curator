"""mame-curator-1132 and the mame-curator-1145 review, Group 4: snapshots and import."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from mame_curator.api.persist import MAX_SNAPSHOTS, restore_snapshot, write_json_atomic

_SNAP_ID = "20200101T000000_000000Z"
WRITE_JSON = "mame_curator.api.routes.config.write_json_atomic"


def _snapshot(config_file: Path, name: str = _SNAP_ID) -> Path:
    snap = config_file.parent / "data" / "snapshots" / name
    snap.mkdir(parents=True)
    shutil.copy(config_file, snap / "config.yaml")
    return snap


# --- the id format ------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_id",
    ["%2e%2e", "..%5C..%5Cx", "20200101T000000_000000Z%0A", "not-a-snapshot", "%2e"],
)
def test_a_snapshot_id_out_of_format_is_not_found(
    client: Any, config_file: Path, bad_id: str
) -> None:
    """Before the fix, `..` read data/ as a snapshot and answered 200."""
    _snapshot(config_file)
    # data/ holds a config.yaml that would be restored if `..` got through.
    planted = config_file.parent / "data" / "config.yaml"
    planted.write_text("not: [a config", encoding="utf-8")
    before = config_file.read_bytes()

    reply = client.post(f"/api/config/snapshots/{bad_id}/restore")

    assert reply.status_code == 404, reply.text
    assert reply.json()["code"] == "snapshot_not_found"
    assert config_file.read_bytes() == before


def test_a_directory_in_the_id_format_restores(client: Any, config_file: Path) -> None:
    _snapshot(config_file)

    assert client.post(f"/api/config/snapshots/{_SNAP_ID}/restore").status_code == 200


@pytest.mark.parametrize("bad_id", ["%2e%2e", "fake_job_id", "..%5Cx"])
def test_a_history_id_out_of_format_is_not_found(client: Any, tmp_path: Path, bad_id: str) -> None:
    """Before the fix, `..` read data/report.json and answered 502."""
    history = tmp_path / "data" / "copy-history"
    (history / "fake_job_id").mkdir(parents=True)
    (history / "fake_job_id" / "report.json").write_text("{bad", encoding="utf-8")
    (tmp_path / "data" / "report.json").write_text("{bad", encoding="utf-8")

    reply = client.get(f"/api/copy/history/{bad_id}/report")

    assert reply.status_code == 404, reply.text
    assert reply.json()["code"] == "job_not_found"


# --- the prune ----------------------------------------------------------------


def test_restoring_the_oldest_snapshot_at_the_cap_keeps_it(client: Any, config_file: Path) -> None:
    oldest = _snapshot(config_file)
    snapshots = oldest.parent
    for i in range(1, MAX_SNAPSHOTS):
        (snapshots / f"20200102T000000_{i:06d}Z").mkdir()
    next_oldest = snapshots / "20200102T000000_000001Z"

    reply = client.post(f"/api/config/snapshots/{oldest.name}/restore")

    assert reply.status_code == 200, reply.text
    assert oldest.is_dir()
    # The undo snapshot is new, so another one went to stay within the cap.
    assert not next_oldest.exists()
    assert sum(p.is_dir() for p in snapshots.iterdir()) == MAX_SNAPSHOTS


# --- a snapshot that will not load ---------------------------------------------


@pytest.mark.parametrize(
    "spoil",
    [
        pytest.param(lambda s: (s / "overrides.yaml").write_bytes(b"caf\xe9: 1\n"), id="overrides"),
        pytest.param(lambda s: (s / "config.yaml").write_text("paths: {}\n"), id="older-schema"),
        pytest.param(lambda s: (s / "config.yaml").write_text("not: [yaml"), id="not-yaml"),
    ],
)
def test_a_snapshot_that_will_not_load_is_a_clear_refusal(
    client: Any, config_file: Path, spoil: Any
) -> None:
    overrides = config_file.parent / "overrides.yaml"
    overrides.write_text("overrides: {}\n", encoding="utf-8")
    before = config_file.read_bytes()
    snap = _snapshot(config_file)
    spoil(snap)

    reply = client.post(f"/api/config/snapshots/{snap.name}/restore")

    assert reply.status_code == 422, reply.text
    assert reply.json()["code"] == "snapshot_unusable"
    assert snap.name in reply.json()["detail"]
    assert config_file.read_bytes() == before
    assert overrides.read_text(encoding="utf-8") == "overrides: {}\n"


def test_a_restore_that_fails_while_copying_puts_the_files_back(
    client: Any, config_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = restore_snapshot
    calls: list[str] = []

    def fail_first(snapshots_dir: Path, snap_id: str, targets: Any) -> None:
        calls.append(snap_id)
        if len(calls) == 1:
            targets["config.yaml"].write_text("half: written\n", encoding="utf-8")
            raise OSError("disk trouble")
        real(snapshots_dir, snap_id, targets)

    monkeypatch.setattr("mame_curator.api.routes.config.restore_snapshot", fail_first)
    before = config_file.read_bytes()
    snap = _snapshot(config_file)

    reply = client.post(f"/api/config/snapshots/{snap.name}/restore")

    assert reply.status_code == 422, reply.text
    assert reply.json()["code"] == "snapshot_unusable"
    assert config_file.read_bytes() == before


def test_a_snapshot_with_a_key_this_version_dropped_still_restores(
    client: Any, config_file: Path
) -> None:
    """The older-schema cases load_app_config already migrates are not refused."""
    snap = _snapshot(config_file)
    data = yaml.safe_load((snap / "config.yaml").read_text(encoding="utf-8"))
    data["retired_section"] = {"a": 1}
    data["picker"] = {"prefer_parent_over_clone": False}
    (snap / "config.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")

    reply = client.post(f"/api/config/snapshots/{snap.name}/restore")

    assert reply.status_code == 200, reply.text
    assert reply.json()["filters"]["prefer_parent_over_clone"] is False


# --- import ---------------------------------------------------------------------


def test_import_folds_picker_as_the_config_loader_does(client: Any) -> None:
    bundle = client.post("/api/config/export").json()
    bundle["config"]["picker"] = {"prefer_parent_over_clone": False}

    reply = client.post("/api/config/import", json=bundle)

    assert reply.status_code == 200, reply.text
    assert reply.json()["filters"]["prefer_parent_over_clone"] is False


def test_import_refuses_a_picker_that_is_not_a_mapping(client: Any) -> None:
    bundle = client.post("/api/config/export").json()
    bundle["config"]["picker"] = "soon"

    reply = client.post("/api/config/import", json=bundle)

    assert reply.status_code == 422, reply.text
    assert reply.json()["code"] == "config_invalid"


def test_import_refuses_a_nul_path(client: Any) -> None:
    bundle = client.post("/api/config/export").json()
    bundle["config"]["paths"]["dest_roms"] = "/a\u0000b"

    reply = client.post("/api/config/import", json=bundle)

    assert reply.status_code == 422, reply.text
    assert [f["type"] for f in reply.json()["fields"]] == ["path_invalid"]


def test_import_refuses_one_folder_for_games_and_destination(client: Any) -> None:
    bundle = client.post("/api/config/export").json()
    bundle["config"]["paths"]["dest_roms"] = bundle["config"]["paths"]["source_roms"]

    reply = client.post("/api/config/import", json=bundle)

    assert reply.status_code == 422, reply.text
    assert [f["type"] for f in reply.json()["fields"]] == ["same_folder"]


def test_import_of_a_backup_from_another_machine_still_works(client: Any, tmp_path: Path) -> None:
    """Versioning-overrides item 2: a kept backup's folders may not exist here."""
    bundle = client.post("/api/config/export").json()
    bundle["config"]["paths"]["source_roms"] = str(tmp_path / "another-machine" / "roms")

    assert client.post("/api/config/import", json=bundle).status_code == 200


def test_import_leaves_no_marker_file(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """Nothing reads a marker, so none is written, not even mid-import."""
    seen: list[str] = []
    data_dir = client.app.state.world.data_dir
    real = write_json_atomic

    def spy(path: Path, data: Any) -> None:
        seen.extend(p.name for p in data_dir.iterdir())
        real(path, data)

    monkeypatch.setattr(WRITE_JSON, spy)
    bundle = client.post("/api/config/export").json()

    assert client.post("/api/config/import", json=bundle).status_code == 200
    assert seen, "the spy never ran"
    assert "import.in_progress" not in seen


def test_an_import_that_fails_part_way_puts_the_files_back(
    client: Any, config_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = config_file.read_bytes()
    bundle = client.post("/api/config/export").json()
    bundle["config"]["ui"]["theme"] = "light"

    def full_disk(path: Path, data: Any) -> None:
        raise OSError("no space left")

    monkeypatch.setattr(WRITE_JSON, full_disk)

    with pytest.raises(OSError, match="no space left"):
        client.post("/api/config/import", json=bundle)

    assert config_file.read_bytes() == before


# --- a symlinked config ------------------------------------------------------------


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks need privilege on Windows")
def test_save_and_restore_keep_a_symlinked_config(tmp_path: Path, config_file: Path) -> None:
    """Both write paths: the atomic helper on save, the promote step on restore."""
    from fastapi.testclient import TestClient

    from mame_curator.api import create_app

    real_dir = tmp_path / "dotfiles"
    real_dir.mkdir()
    real = real_dir / "config.yaml"
    shutil.move(config_file, real)
    config_file.symlink_to(real)

    home = tmp_path / "fake_home"
    home.mkdir()
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("HOME", str(home))
        mp.setenv("USERPROFILE", str(home))
        with TestClient(create_app(config_file)) as client:
            assert client.patch("/api/config", json={"ui": {"theme": "light"}}).status_code == 200
            assert config_file.is_symlink()
            assert yaml.safe_load(real.read_text(encoding="utf-8"))["ui"]["theme"] == "light"

            snap = next(p for p in (tmp_path / "data" / "snapshots").iterdir())
            assert client.post(f"/api/config/snapshots/{snap.name}/restore").status_code == 200
            assert config_file.is_symlink()
            assert yaml.safe_load(real.read_text(encoding="utf-8"))["ui"]["theme"] == "dark"

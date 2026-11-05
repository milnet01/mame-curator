"""mame-curator-1145 — what a save, restore or import in setup mode replies, and
what it refuses. The save itself is `test_setup_mode.py`.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient

from mame_curator.api import create_app
from mame_curator.api.fs import compose_allowlist
from mame_curator.api.state import build_world
from mame_curator.filter import OverridesError, load_overrides

SAME_FOLDER_WORDS = "Please choose a different folder from the one holding your games."


def _set_paths(config_file: Path, **paths: str) -> None:
    data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    data["paths"].update(paths)
    config_file.write_text(yaml.safe_dump(data), encoding="utf-8")


@pytest.fixture
def setup_client(config_file: Path, tmp_path: Path, fake_home: Path) -> Iterator[Any]:
    """A client whose app started in setup mode: the DAT path is absent."""
    _set_paths(config_file, source_dat=str(tmp_path / "does-not-exist.xml"))
    with TestClient(create_app(config_file)) as client:
        yield client


@pytest.fixture
def broken_dat(tmp_path: Path) -> Path:
    path = tmp_path / "broken.dat.xml"
    path.write_text("<mame><machine name='pacman'", encoding="utf-8")
    return path


def _in_setup(client: Any) -> bool:
    answer: bool = client.get("/api/setup/check").json()["setup_required"]
    return answer


def _new_snapshot(config_file: Path, name: str = "20200101T000000_000000Z") -> Path:
    """A snapshot of the config as it stands, which the test then edits."""
    snap = config_file.parent / "data" / "snapshots" / name
    snap.mkdir(parents=True)
    shutil.copy(config_file, snap / "config.yaml")
    return snap


# --- setup_ended ------------------------------------------------------------


def test_setup_ended_says_the_save_ended_setup_mode(setup_client: Any, mini_dat: Path) -> None:
    """INV-8's trigger: only the reply to the save that ended it."""
    first = setup_client.patch("/api/config", json={"paths": {"source_dat": str(mini_dat)}})
    assert first.json()["setup_ended"] is True
    assert first.json()["restart_required"] is False

    second = setup_client.patch("/api/config", json={"ui": {"theme": "light"}})
    assert second.json()["setup_ended"] is False
    assert setup_client.get("/api/config").json()["setup_ended"] is False


def test_setup_ended_false_when_setup_mode_stays_on(setup_client: Any, broken_dat: Path) -> None:
    reply = setup_client.patch("/api/config", json={"paths": {"source_dat": str(broken_dat)}})
    assert reply.json()["setup_ended"] is False
    assert reply.json()["restart_required"] is True


def test_one_save_can_end_setup_mode_and_change_the_server(
    setup_client: Any, mini_dat: Path
) -> None:
    """The two fields say two things: a reply can hold both."""
    reply = setup_client.patch(
        "/api/config",
        json={"paths": {"source_dat": str(mini_dat)}, "server": {"port": 8765}},
    )
    assert reply.json()["setup_ended"] is True
    assert reply.json()["restart_required"] is True


def test_setup_ended_false_outside_setup_mode(client: Any) -> None:
    reply = client.patch("/api/config", json={"ui": {"theme": "light"}})
    assert reply.status_code == 200, reply.text
    assert reply.json()["setup_ended"] is False


# --- restart_required survives a refetch ------------------------------------


def test_get_keeps_the_restart_prompt_after_a_kept_save(
    setup_client: Any, broken_dat: Path
) -> None:
    """INV-2: returning to the window refetches, and the prompt must stay."""
    assert setup_client.get("/api/config").json()["restart_required"] is False
    setup_client.patch("/api/config", json={"paths": {"source_dat": str(broken_dat)}})
    assert setup_client.get("/api/config").json()["restart_required"] is True


def test_get_clears_the_restart_prompt_once_setup_mode_ends(
    setup_client: Any, broken_dat: Path, mini_dat: Path
) -> None:
    setup_client.patch("/api/config", json={"paths": {"source_dat": str(broken_dat)}})
    setup_client.patch("/api/config", json={"paths": {"source_dat": str(mini_dat)}})
    assert setup_client.get("/api/config").json()["restart_required"] is False


def test_get_keeps_the_restart_prompt_after_a_server_change(client: Any) -> None:
    client.patch("/api/config", json={"server": {"port": 8765}})
    assert client.get("/api/config").json()["restart_required"] is True
    # A later save that does not touch the server must not hide it either.
    later = client.patch("/api/config", json={"ui": {"theme": "light"}})
    assert later.json()["restart_required"] is True
    same_again = client.patch("/api/config", json={"ui": {"theme": "light"}})
    assert same_again.json()["restart_required"] is True


def test_no_restart_prompt_once_the_server_settings_are_back(client: Any) -> None:
    port = client.get("/api/config").json()["server"]["port"]
    client.patch("/api/config", json={"server": {"port": 8765}})
    client.patch("/api/config", json={"server": {"port": port}})
    assert client.get("/api/config").json()["restart_required"] is False


# --- restore and import (INV-15) --------------------------------------------


def test_restore_in_setup_mode_retries_the_dat(
    setup_client: Any, config_file: Path, mini_dat: Path
) -> None:
    snap = _new_snapshot(config_file)
    _set_paths(snap / "config.yaml", source_dat=str(mini_dat))

    reply = setup_client.post(f"/api/config/snapshots/{snap.name}/restore")

    assert reply.status_code == 200, reply.text
    assert reply.json()["setup_ended"] is True
    assert reply.json()["restart_required"] is False
    assert _in_setup(setup_client) is False
    assert setup_client.get("/api/games").json()["total"] > 0


def test_restore_of_an_unreadable_dat_keeps_setup_mode_and_says_so(
    setup_client: Any, config_file: Path, broken_dat: Path
) -> None:
    snap = _new_snapshot(config_file)
    _set_paths(snap / "config.yaml", source_dat=str(broken_dat))

    reply = setup_client.post(f"/api/config/snapshots/{snap.name}/restore")

    assert reply.status_code == 200, reply.text
    assert reply.json()["setup_ended"] is False
    assert reply.json()["restart_required"] is True
    assert _in_setup(setup_client) is True


def _bundle_naming(client: Any, dat: Path) -> dict[str, Any]:
    bundle: dict[str, Any] = client.post("/api/config/export").json()
    bundle["config"]["paths"]["source_dat"] = str(dat)
    return bundle


def test_import_in_setup_mode_retries_the_dat(setup_client: Any, mini_dat: Path) -> None:
    reply = setup_client.post("/api/config/import", json=_bundle_naming(setup_client, mini_dat))

    assert reply.status_code == 200, reply.text
    assert reply.json()["setup_ended"] is True
    assert reply.json()["restart_required"] is False
    assert _in_setup(setup_client) is False
    assert setup_client.get("/api/games").json()["total"] > 0


def test_import_of_an_unreadable_dat_keeps_setup_mode_and_says_so(
    setup_client: Any, broken_dat: Path
) -> None:
    reply = setup_client.post("/api/config/import", json=_bundle_naming(setup_client, broken_dat))

    assert reply.status_code == 200, reply.text
    assert reply.json()["setup_ended"] is False
    assert reply.json()["restart_required"] is True
    assert _in_setup(setup_client) is True


def test_restore_with_undecodable_notes_reads_them_as_none(client: Any, config_file: Path) -> None:
    snap = _new_snapshot(config_file)
    (snap / "notes.json").write_bytes(b'{"pacman": "caf\xe9"}')

    reply = client.post(f"/api/config/snapshots/{snap.name}/restore")

    assert reply.status_code == 200, reply.text


def test_restore_and_import_do_not_retry_outside_setup_mode(
    client: Any, config_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def must_not_run(world: Any) -> Any:
        raise AssertionError("retried outside setup mode")

    monkeypatch.setattr("mame_curator.api.routes.config.retry_setup", must_not_run)
    snap = _new_snapshot(config_file)
    assert client.post(f"/api/config/snapshots/{snap.name}/restore").json()["setup_ended"] is False
    bundle = client.post("/api/config/export").json()
    assert client.post("/api/config/import", json=bundle).json()["setup_ended"] is False


# --- a bad file during the retry (INV-4) ------------------------------------


@pytest.mark.parametrize(
    "relative",
    ["overrides.yaml", "sessions.yaml", "data/state.yaml"],
)
def test_undecodable_file_keeps_setup_mode_not_a_500(
    setup_client: Any, config_file: Path, mini_dat: Path, relative: str
) -> None:
    bad = config_file.parent / relative
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_bytes(b"caf\xe9: 1\n")

    reply = setup_client.patch("/api/config", json={"paths": {"source_dat": str(mini_dat)}})

    assert reply.status_code == 200, reply.text
    assert reply.json()["restart_required"] is True
    assert reply.json()["paths"]["source_dat"] == str(mini_dat)
    assert _in_setup(setup_client) is True


def test_undecodable_notes_do_not_stop_the_games_loading(
    setup_client: Any, config_file: Path, mini_dat: Path
) -> None:
    """Notes are optional: a bad file reads as none, as bad JSON already does."""
    notes = config_file.parent / "data" / "notes.json"
    notes.parent.mkdir(parents=True, exist_ok=True)
    notes.write_bytes(b'{"pacman": "caf\xe9"}')

    reply = setup_client.patch("/api/config", json={"paths": {"source_dat": str(mini_dat)}})

    assert reply.status_code == 200, reply.text
    assert reply.json()["setup_ended"] is True


def test_undecodable_overrides_raise_the_typed_error(tmp_path: Path) -> None:
    bad = tmp_path / "overrides.yaml"
    bad.write_bytes(b"caf\xe9: 1\n")
    with pytest.raises(OverridesError, match="UTF-8"):
        load_overrides(bad)


def test_unexpected_failure_in_the_retry_leaves_the_running_config_saved(
    setup_client: Any, mini_dat: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def blows_up(world: Any) -> Any:
        raise RuntimeError("not one of the expected failures")

    monkeypatch.setattr("mame_curator.api.routes.config.retry_setup", blows_up)
    with pytest.raises(RuntimeError):
        setup_client.patch("/api/config", json={"paths": {"source_dat": str(mini_dat)}})

    assert setup_client.get("/api/config").json()["paths"]["source_dat"] == str(mini_dat)


# --- the stored INI preview -------------------------------------------------


def test_retry_that_ends_setup_mode_clears_the_stored_preview(
    setup_client: Any, mini_dat: Path
) -> None:
    """A preview from the empty library must not be applied over the games."""
    setup_client.app.state.ini_staged = object()

    setup_client.patch("/api/config", json={"paths": {"source_dat": str(mini_dat)}})

    assert setup_client.app.state.ini_staged is None
    assert setup_client.post("/api/updates/ini/apply").status_code == 409


def test_retry_that_keeps_setup_mode_keeps_the_stored_preview(
    setup_client: Any, broken_dat: Path
) -> None:
    staged = object()
    setup_client.app.state.ini_staged = staged
    setup_client.patch("/api/config", json={"paths": {"source_dat": str(broken_dat)}})
    assert setup_client.app.state.ini_staged is staged


# --- paths that are refused -------------------------------------------------


@pytest.mark.parametrize("key", ["source_dat", "catver", "listxml"])
def test_nul_path_is_refused_in_setup_mode(setup_client: Any, config_file: Path, key: str) -> None:
    before = config_file.read_text(encoding="utf-8")

    reply = setup_client.patch("/api/config", json={"paths": {key: "/a\u0000b"}})

    assert reply.status_code == 422, reply.text
    assert reply.json()["fields"][0]["loc"] == f"paths.{key}"
    assert reply.json()["fields"][0]["type"] == "path_invalid"
    assert config_file.read_text(encoding="utf-8") == before


def test_config_already_holding_a_nul_path_still_starts(
    config_file: Path, fake_home: Path, tmp_path: Path
) -> None:
    """How the bad path once reached the disk: the next start must not die."""
    _set_paths(config_file, source_dat="/a\u0000b/list.xml")
    world = build_world(config_file)
    assert world.setup_required is True
    assert compose_allowlist(world.config)


def test_granted_root_holding_a_nul_is_skipped(config_file: Path, fake_home: Path) -> None:
    world = build_world(config_file)
    fs = world.config.fs.model_copy(update={"granted_roots": ("/a\u0000b",)})
    assert compose_allowlist(world.config.model_copy(update={"fs": fs}))


def test_same_folder_is_refused_with_the_plain_sentence(client: Any) -> None:
    paths = client.get("/api/config").json()["paths"]

    reply = client.patch("/api/config", json={"paths": {"dest_roms": paths["source_roms"]}})

    assert reply.status_code == 422, reply.text
    field = reply.json()["fields"][0]
    assert field["loc"] == "paths.dest_roms"
    assert field["msg"] == SAME_FOLDER_WORDS
    # Not "path_": the page shows a path_ type as "could not be found".
    assert not field["type"].startswith("path_")


@pytest.mark.skipif(os.name == "nt", reason="symlinks need elevation on Windows")
def test_same_folder_through_a_symlink_is_refused(client: Any, tmp_path: Path) -> None:
    paths = client.get("/api/config").json()["paths"]
    link = tmp_path / "games-by-another-name"
    link.symlink_to(paths["source_roms"], target_is_directory=True)

    reply = client.patch("/api/config", json={"paths": {"dest_roms": str(link)}})

    assert reply.status_code == 422, reply.text
    assert reply.json()["fields"][0]["msg"] == SAME_FOLDER_WORDS


def test_a_config_already_naming_one_folder_twice_loads_and_saves(
    config_file: Path, fake_home: Path
) -> None:
    """Nothing refuses it on load, nor on a save leaving those two paths alone."""
    data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    _set_paths(config_file, dest_roms=data["paths"]["source_roms"])

    with TestClient(create_app(config_file)) as client:
        assert client.get("/api/games").status_code == 200
        reply = client.patch("/api/config", json={"ui": {"theme": "light"}})
        assert reply.status_code == 200, reply.text
        # Moving one of the two, onto a third folder, is a repair and passes.
        third = config_file.parent / "third"
        third.mkdir()
        repair = client.patch("/api/config", json={"paths": {"dest_roms": str(third)}})
        assert repair.status_code == 200, repair.text


# --- a snapshot that will not load (INV-16) ---------------------------------


def test_restore_that_will_not_load_puts_the_files_back(client: Any, config_file: Path) -> None:
    overrides = config_file.parent / "overrides.yaml"
    overrides.write_text("overrides: {}\n", encoding="utf-8")
    before = config_file.read_bytes()
    snap = _new_snapshot(config_file)
    (snap / "overrides.yaml").write_bytes(b"caf\xe9: 1\n")
    _set_paths(snap / "config.yaml", dest_roms=str(config_file.parent))

    reply = client.post(f"/api/config/snapshots/{snap.name}/restore")

    assert reply.status_code == 422, reply.text
    assert reply.json()["code"] == "snapshot_unusable"
    assert overrides.read_text(encoding="utf-8") == "overrides: {}\n"
    assert config_file.read_bytes() == before
    # The next save starts from what the running app holds, and matches the disk.
    assert client.patch("/api/config", json={"ui": {"theme": "light"}}).status_code == 200


# --- the setup check --------------------------------------------------------


def test_setup_check_survives_an_os_error_reading_the_dat(
    client: Any, mini_dat: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_scratch_space(path: Path) -> Any:
        raise OSError("no space left on device")

    # A DAT the world did not load, so the check has to read it
    # (mame-curator-1172 answers from the world for the one it loaded).
    other = tmp_path / "other.dat.xml"
    other.write_bytes(mini_dat.read_bytes())
    saved = client.patch("/api/config", json={"paths": {"source_dat": str(other)}})
    assert saved.status_code == 200, saved.text
    monkeypatch.setattr("mame_curator.api.routes.stubs.parse_dat", no_scratch_space)
    reply = client.get("/api/setup/check")
    assert reply.status_code == 200, reply.text
    assert reply.json()["paths"]["source_dat"]["dat_parses"] is False

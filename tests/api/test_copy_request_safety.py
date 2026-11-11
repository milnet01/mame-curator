"""mame-curator-1145 review, Group 4: what a copy request may name.

Every name reaches a path, so the routes refuse a name the library does not
hold, and a copy in setup mode, before any file or playlist is touched.
`tests/copy/test_short_name_containment.py` holds the second line.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient

from mame_curator.api import create_app
from tests.api.conftest import LOCAL_URL

_ROUTES = ("/api/copy/dry-run", "/api/copy/start")


@pytest.fixture
def outside(tmp_path: Path) -> Path:
    """A folder beside source and destination, which no name may reach."""
    folder = tmp_path / "outside"
    folder.mkdir()
    (folder / "secret.zip").write_bytes(b"secret")
    return folder


def _wait_for_job(client: Any) -> None:
    for _ in range(500):
        if client.app.state.job.current is None:
            return
        time.sleep(0.01)
    raise AssertionError("copy job did not finish in time")


@pytest.mark.parametrize("route", _ROUTES)
@pytest.mark.parametrize(
    "name",
    ["../outside/secret", "pacman/../../outside/secret", "..", "", "no_such_game"],
)
def test_a_name_the_library_does_not_hold_is_refused(
    client: Any, outside: Path, route: str, name: str
) -> None:
    reply = client.post(route, json={"selected_names": [name], "conflict_strategy": "OVERWRITE"})

    assert reply.status_code == 422, reply.text
    assert reply.json()["code"] == "copy_names_unknown"
    assert [f["msg"] for f in reply.json()["fields"]] == [name]
    assert client.app.state.job.replayable is None


@pytest.mark.parametrize("route", _ROUTES)
def test_an_absolute_name_is_refused(client: Any, outside: Path, route: str) -> None:
    name = str(outside / "secret")

    reply = client.post(route, json={"selected_names": [name], "conflict_strategy": "OVERWRITE"})

    assert reply.status_code == 422, reply.text
    # A long path trips the 64-character name cap first (mame-curator-1225).
    assert reply.json()["code"] in {"copy_names_unknown", "validation_error"}


def test_one_stale_name_refuses_the_whole_copy_and_says_which(
    client: Any, dest_dir: Path, source_dir: Path
) -> None:
    (source_dir / "gone.zip").write_bytes(b"old")

    reply = client.post(
        "/api/copy/start",
        json={"selected_names": ["pacman", "gone"], "conflict_strategy": "OVERWRITE"},
    )

    assert reply.status_code == 422, reply.text
    assert [f["msg"] for f in reply.json()["fields"]] == ["gone"]
    assert "gone" in reply.json()["detail"]
    assert client.app.state.job.replayable is None
    assert not (dest_dir / "pacman.zip").exists()


def test_a_long_list_of_stale_names_stays_a_short_reply(client: Any) -> None:
    names = [f"gone{i}" for i in range(500)]

    reply = client.post("/api/copy/dry-run", json={"selected_names": names})

    assert reply.status_code == 422, reply.text
    assert len(reply.json()["fields"]) == 20
    assert "500" in reply.json()["detail"]


@pytest.mark.parametrize("route", _ROUTES)
def test_a_replaces_outside_the_library_is_refused(
    client: Any, outside: Path, tmp_path: Path, route: str
) -> None:
    """Measured before the fix: this moved outside/secret.zip into the recycle bin."""
    reply = client.post(
        route,
        json={
            "selected_names": ["pacman"],
            "conflict_strategy": "APPEND",
            "append_decisions": {
                "pacman": {"kind": "REPLACE_AND_RECYCLE", "replaces": "../outside/secret"},
            },
        },
    )

    assert reply.status_code == 422, reply.text
    assert reply.json()["code"] == "copy_names_unknown"
    _wait_for_job(client)
    assert (outside / "secret.zip").read_bytes() == b"secret"


def test_names_the_library_holds_still_copy(client: Any, dest_dir: Path) -> None:
    reply = client.post(
        "/api/copy/start",
        json={"selected_names": ["pacman"], "conflict_strategy": "OVERWRITE"},
    )

    assert reply.status_code == 200, reply.text
    _wait_for_job(client)
    assert (dest_dir / "pacman.zip").exists()


# --- setup mode --------------------------------------------------------------


@pytest.fixture
def setup_client(config_file: Path, tmp_path: Path, fake_home: Path) -> Iterator[Any]:
    """A client whose app started in setup mode: the DAT path is absent."""
    data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    data["paths"]["source_dat"] = str(tmp_path / "does-not-exist.xml")
    config_file.write_text(yaml.safe_dump(data), encoding="utf-8")
    with TestClient(create_app(config_file), base_url=LOCAL_URL) as client:
        yield client


@pytest.mark.parametrize("route", _ROUTES)
@pytest.mark.parametrize("strategy", ["OVERWRITE", "APPEND"])
def test_a_copy_in_setup_mode_is_refused_and_leaves_the_playlist(
    setup_client: Any, dest_dir: Path, route: str, strategy: str
) -> None:
    playlist = dest_dir / "mame.lpl"
    before = b'{"version": "1.5", "items": [{"path": "/roms/kept.zip", "label": "Kept"}]}'
    playlist.write_bytes(before)

    reply = setup_client.post(
        route, json={"selected_names": ["pacman"], "conflict_strategy": strategy}
    )

    assert reply.status_code == 409, reply.text
    assert reply.json()["code"] == "copy_setup_required"
    _wait_for_job(setup_client)
    assert setup_client.app.state.job.replayable is None
    assert playlist.read_bytes() == before


# --- an empty selection (mame-curator-1182) -----------------------------------


@pytest.mark.parametrize("route", _ROUTES)
@pytest.mark.parametrize("strategy", ["OVERWRITE", "APPEND"])
def test_an_empty_selection_is_refused_and_leaves_the_playlist(
    client: Any, dest_dir: Path, route: str, strategy: str
) -> None:
    """Measured before the fix: OVERWRITE with no names answered 200 and
    rewrote the playlist with nothing in it."""
    playlist = dest_dir / "mame.lpl"
    before = b'{"version": "1.5", "items": [{"path": "/roms/kept.zip", "label": "Kept"}]}'
    playlist.write_bytes(before)

    reply = client.post(route, json={"selected_names": [], "conflict_strategy": strategy})

    assert reply.status_code == 422, reply.text
    assert reply.json()["code"] == "copy_nothing_selected"
    _wait_for_job(client)
    assert client.app.state.job.replayable is None
    assert playlist.read_bytes() == before

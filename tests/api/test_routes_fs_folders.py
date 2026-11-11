"""mame-curator-1169 — POST /api/fs/folders makes one folder inside an allowed root.

Per ``src/mame_curator/api/spec.md`` § Filesystem sandbox, "New folder".
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def granted(client: Any, tmp_path: Path) -> Path:
    """A folder the app is allowed to use."""
    root = tmp_path / "granted"
    root.mkdir()
    assert client.post("/api/fs/allowed-roots", json={"path": str(root)}).status_code == 200
    return root


def test_makes_the_folder_and_returns_its_path(client: Any, granted: Path) -> None:
    response = client.post("/api/fs/folders", json={"parent": str(granted), "name": "Arcade"})
    assert response.status_code == 200
    made = granted / "Arcade"
    assert made.is_dir()
    assert Path(response.json()["path"]) == made.resolve()


def test_a_name_of_255_utf8_bytes_is_allowed(client: Any, granted: Path) -> None:
    name = "é" * 127 + "a"  # 255 bytes
    response = client.post("/api/fs/folders", json={"parent": str(granted), "name": name})
    assert response.status_code == 200
    assert (granted / name).is_dir()


def test_outside_every_allowed_root_is_refused(client: Any, tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    response = client.post("/api/fs/folders", json={"parent": str(outside), "name": "x"})
    assert response.status_code == 403
    assert response.json()["code"] == "fs_sandboxed"
    assert not (outside / "x").exists()


def test_a_missing_parent_is_not_made(client: Any, granted: Path) -> None:
    parent = granted / "missing"
    response = client.post("/api/fs/folders", json={"parent": str(parent), "name": "x"})
    assert response.status_code == 404
    assert not parent.exists()


@pytest.mark.parametrize(
    "name",
    [
        "",
        ".",
        "..",
        "a/b",
        "a\\b",
        "a\x00b",
        "trailing.",
        "trailing ",
        "é" * 128,  # 256 bytes
    ],
)
def test_a_name_that_cannot_be_one_folder_here_is_refused(
    client: Any, granted: Path, name: str
) -> None:
    response = client.post("/api/fs/folders", json={"parent": str(granted), "name": name})
    assert response.status_code == 400
    assert response.json()["code"] == "fs_path_invalid"
    assert list(granted.iterdir()) == []


def test_a_name_cannot_climb_out_of_the_allowed_root(client: Any, granted: Path) -> None:
    response = client.post("/api/fs/folders", json={"parent": str(granted), "name": "../escaped"})
    assert response.status_code == 400
    assert not (granted.parent / "escaped").exists()


def test_a_name_that_is_not_utf8_is_refused(client: Any, granted: Path) -> None:
    # A lone surrogate is valid JSON but cannot be written as UTF-8.
    raw = json.dumps({"parent": str(granted), "name": "\ud800"})
    response = client.post(
        "/api/fs/folders", content=raw, headers={"content-type": "application/json"}
    )
    assert response.status_code == 400
    assert response.json()["code"] == "fs_path_invalid"
    assert list(granted.iterdir()) == []


@pytest.mark.parametrize("kind", ["folder", "file"])
def test_a_name_already_there_is_refused(client: Any, granted: Path, kind: str) -> None:
    there = granted / "Arcade"
    if kind == "folder":
        there.mkdir()
    else:
        there.write_text("x")
    response = client.post("/api/fs/folders", json={"parent": str(granted), "name": "Arcade"})
    assert response.status_code == 409
    assert response.json()["code"] == "fs_folder_exists"


def test_a_folder_the_system_will_not_make_is_said(
    client: Any, granted: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(self: Path, *args: object, **kwargs: object) -> None:
        raise PermissionError(13, "Permission denied", str(self))

    monkeypatch.setattr(Path, "mkdir", refuse)
    response = client.post("/api/fs/folders", json={"parent": str(granted), "name": "x"})
    assert response.status_code == 400
    assert response.json()["code"] == "fs_path_invalid"

"""mame-curator-1175 / CR-06-4 — a granted folder that disappears can still be removed.

Per ``src/mame_curator/api/spec.md`` § Filesystem sandbox, "Missing grants"
and "Revoke".
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def gone(client: Any, tmp_path: Path) -> dict[str, Any]:
    """A folder granted, then deleted outside the app, then the world rebuilt.

    CR-06-4: the rebuild (here, another grant) drops the deleted folder from
    the sandbox, which is when it could no longer be found to revoke.
    """
    folder = tmp_path / "usb-stick"
    folder.mkdir()
    reply = client.post("/api/fs/allowed-roots", json={"path": str(folder)}).json()
    root = next(r for r in reply["roots"] if r["path"] == str(folder.resolve()))
    folder.rmdir()
    other = tmp_path / "other"
    other.mkdir()
    assert client.post("/api/fs/allowed-roots", json={"path": str(other)}).status_code == 200
    return {"folder": folder, "root": root}


def test_every_reply_says_which_grants_are_missing(client: Any, tmp_path: Path) -> None:
    folder = tmp_path / "kept"
    folder.mkdir()
    granted = client.post("/api/fs/allowed-roots", json={"path": str(folder)})
    assert granted.json()["missing"] == []
    assert client.get("/api/fs/allowed-roots").json()["missing"] == []


def test_a_deleted_folder_is_listed_as_missing_not_allowed(
    client: Any, gone: dict[str, Any]
) -> None:
    body = client.get("/api/fs/allowed-roots").json()
    assert gone["root"] in body["missing"]
    assert all(r["id"] != gone["root"]["id"] for r in body["roots"])


def test_a_missing_grant_can_be_removed_by_its_id(client: Any, gone: dict[str, Any]) -> None:
    response = client.delete(f"/api/fs/allowed-roots/{gone['root']['id']}")
    assert response.status_code == 200
    assert response.json()["missing"] == []
    # Removed for good: the folder coming back does not bring the grant back.
    gone["folder"].mkdir()
    body = client.get("/api/fs/allowed-roots").json()
    assert all(r["id"] != gone["root"]["id"] for r in body["roots"] + body["missing"])


def test_a_missing_grant_left_alone_works_again_when_its_folder_returns(
    client: Any, gone: dict[str, Any]
) -> None:
    gone["folder"].mkdir()
    body = client.get("/api/fs/allowed-roots").json()
    assert gone["root"] in body["roots"]
    assert body["missing"] == []

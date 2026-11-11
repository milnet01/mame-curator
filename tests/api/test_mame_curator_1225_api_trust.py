"""mame-curator-1225 — what the web service trusts.

Each test locks one finding from the 2026-11-11 code review (ids in the
docstrings). Contract: ``api/spec.md`` § Cross-site guard, § Filesystem
sandbox and § Config persistence + snapshots.
"""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from mame_curator.api.origin_guard import OriginGuard
from mame_curator.api.schemas import CopyJobRequest

# ---- CR-05-2: the Host check covers every request ---------------------------


async def _ok(_: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


def _guarded() -> TestClient:
    inner = Starlette(routes=[Route("/x", _ok, methods=["GET", "POST"])])
    return TestClient(OriginGuard(inner), base_url="http://127.0.0.1")


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_a_rebound_name_is_refused_without_browser_headers(method: str) -> None:
    """CR-05-2: an old browser sends neither Origin nor Sec-Fetch-Site."""
    r = _guarded().request(method, "/x", headers={"host": "evil.example"})
    assert r.status_code == 403
    assert r.json()["code"] == "cross_site_blocked"


@pytest.mark.parametrize("host", ["127.0.0.1:8080", "localhost:8080", "[::1]:8080", "10.0.0.5"])
def test_a_local_name_or_address_passes_without_browser_headers(host: str) -> None:
    assert _guarded().get("/x", headers={"host": host}).status_code == 200


# ---- CR-06-3: only the folder picker grants folder access --------------------


def test_backup_restore_keeps_the_current_folder_grants(client: Any, tmp_path: Path) -> None:
    """CR-06-3, user decision 2026-11-11: a restore never grants folder access."""
    bundle = client.post("/api/config/export").json()
    bundle["config"]["fs"] = {"granted_roots": [str(tmp_path)]}
    assert client.post("/api/config/import", json=bundle).status_code == 200
    assert client.get("/api/config").json()["fs"]["granted_roots"] == []
    roots = {r["path"] for r in client.get("/api/fs/allowed-roots").json()["roots"]}
    assert str(tmp_path.resolve()) not in roots


def test_a_settings_save_cannot_grant_folder_access(client: Any, tmp_path: Path) -> None:
    """CR-06-3: PATCH /api/config must not add a grant past the picker's prompt."""
    r = client.patch("/api/config", json={"fs": {"granted_roots": [str(tmp_path)]}})
    assert r.status_code == 422
    assert client.get("/api/config").json()["fs"]["granted_roots"] == []


# ---- CR-06-5: session names match whole --------------------------------------


def test_import_refuses_a_session_name_ending_in_a_newline(client: Any) -> None:
    bundle = client.post("/api/config/export").json()
    bundle["sessions"]["sessions"]["good\n"] = {"include_genres": ["Shooter*"]}
    r = client.post("/api/config/import", json=bundle)
    assert r.status_code == 422
    assert r.json()["code"] == "session_name_invalid"


def test_save_refuses_a_session_name_ending_in_a_newline(client: Any) -> None:
    r = client.post(
        "/api/sessions", json={"name": "good\n", "session": {"include_genres": ["Shooter*"]}}
    )
    assert r.status_code == 422
    assert r.json()["code"] == "session_name_invalid"


# ---- CR-06-7: the DAT check reads files only ---------------------------------


@pytest.mark.skipif(sys.platform == "win32", reason="named pipes made by mkfifo are POSIX-only")
def test_dat_check_does_not_hang_on_a_named_pipe(client: Any, fake_home: Path) -> None:
    """CR-06-7: opening a FIFO for reading blocks until a writer appears."""
    fifo = fake_home / "pipe.xml"
    os.mkfifo(fifo)
    answer: dict[str, Any] = {}
    worker = threading.Thread(
        target=lambda: answer.update(
            r=client.get("/api/setup/dat-check", params={"path": str(fifo)})
        )
    )
    worker.start()
    worker.join(timeout=5)
    hung = worker.is_alive()
    if hung:  # free the blocked reader so the suite can finish
        os.close(os.open(fifo, os.O_WRONLY | os.O_NONBLOCK))
        worker.join(timeout=5)
    assert not hung, "dat-check blocked on a named pipe"
    assert answer["r"].json()["parses"] is False


# ---- CR-06-8: the help index stays inside the help folder --------------------


def test_help_index_skips_a_link_that_leaves_the_help_folder(
    client: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    help_dir = tmp_path / "help"
    help_dir.mkdir()
    (help_dir / "intro.md").write_text("# Intro\n", encoding="utf-8")
    outside = tmp_path / "secret.md"
    outside.write_text("# Secret title\n", encoding="utf-8")
    try:
        (help_dir / "leak.md").symlink_to(outside)
    except OSError:
        pytest.skip("this system cannot make symlinks")
    monkeypatch.setenv("MAME_CURATOR_HELP_DIR", str(help_dir))
    slugs = [t["slug"] for t in client.get("/api/help/index").json()["topics"]]
    assert slugs == ["intro"]


# ---- CR-07-8: a copy request is size-capped ----------------------------------


def test_copy_request_caps_each_name() -> None:
    with pytest.raises(ValidationError):
        CopyJobRequest(selected_names=("x" * 65,))


def test_copy_request_caps_the_name_count() -> None:
    """Above any MAME set, so the guide's copy-everything path still fits."""
    CopyJobRequest(selected_names=("pacman",) * 100_000)
    with pytest.raises(ValidationError):
        CopyJobRequest(selected_names=("pacman",) * 100_001)


def test_copy_request_caps_the_append_decisions() -> None:
    keep = {"kind": "KEEP_EXISTING"}
    with pytest.raises(ValidationError):
        CopyJobRequest.model_validate(
            {"selected_names": ["pacman"], "append_decisions": {"x" * 65: keep}}
        )
    with pytest.raises(ValidationError):
        CopyJobRequest.model_validate(
            {
                "selected_names": ["pacman"],
                "append_decisions": {f"g{i}": keep for i in range(100_001)},
            }
        )

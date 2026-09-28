"""mame-curator-1010 §4.2-§4.4 — the check, apply and rollback routes.

GitHub is always an ``httpx.MockTransport`` here: no test reaches the network.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest

import mame_curator.api.routes.updates as routes
from mame_curator import __version__
from tests.updates.gitrepo import Recorder, git, make_clone

ASSET_BODY = b"bundle bytes"


class FakeGitHub:
    """Serves the latest-release answer and one asset; counts API requests."""

    def __init__(self, tag: str = "v9.9.0") -> None:
        self.tag = tag
        self.status = 200
        self.api_requests = 0

    def release(self) -> dict[str, Any]:
        version = self.tag.removeprefix("v")
        return {
            "tag_name": self.tag,
            "body": "## Added\n- a thing",
            "html_url": f"https://example.test/releases/{self.tag}",
            "assets": [
                {
                    "name": f"MAME_Curator-{version}-x86_64.AppImage",
                    "browser_download_url": "https://example.test/asset",
                    "digest": "sha256:" + hashlib.sha256(ASSET_BODY).hexdigest(),
                }
            ],
        }

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.github.com":
            self.api_requests += 1
            if self.status != 200:
                return httpx.Response(self.status, content=b"rate limited")
            return httpx.Response(200, content=json.dumps(self.release()))
        return httpx.Response(200, content=ASSET_BODY)


@pytest.fixture
def gh(client: Any) -> FakeGitHub:
    fake = FakeGitHub()
    client.app.state.updates_client = httpx.AsyncClient(transport=httpx.MockTransport(fake))
    return fake


def _kind(monkeypatch: pytest.MonkeyPatch, kind: str) -> None:
    monkeypatch.setattr(routes, "install_kind", lambda: kind)


def test_check_reports_the_latest_release(
    client: Any, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch
) -> None:
    _kind(monkeypatch, "git")
    body = client.get("/api/updates/check").json()
    assert body["ini"] == []
    app = body["app"]
    assert app["current_version"] == __version__
    assert app["latest_version"] == "9.9.0"
    assert app["update_available"] and app["can_apply"]
    assert app["install_kind"] == "git"
    assert "<h2>Added</h2>" in app["notes_html"]
    assert app["release_url"].endswith("v9.9.0")
    assert app["check_error"] is None


def test_check_is_cached_for_an_hour(
    client: Any, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INV-3."""
    _kind(monkeypatch, "git")
    client.get("/api/updates/check")
    client.get("/api/updates/check")
    assert gh.api_requests == 1
    client.get("/api/updates/check", params={"refresh": "true"})
    assert gh.api_requests == 2


def test_check_failure_is_reported_not_raised(
    client: Any, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INV-4."""
    _kind(monkeypatch, "git")
    gh.status = 403
    response = client.get("/api/updates/check")
    assert response.status_code == 200
    app = response.json()["app"]
    assert app["update_available"] is False
    assert "403" in app["check_error"]


def test_package_install_cannot_apply(
    client: Any, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INV-10."""
    _kind(monkeypatch, "package")
    assert client.get("/api/updates/check").json()["app"]["can_apply"] is False
    response = client.post("/api/updates/apply")
    assert response.status_code == 409
    assert response.json()["code"] == "update_not_supported"


def test_bundle_apply_downloads_beside_itself(
    client: Any, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _kind(monkeypatch, "bundle")
    folder = tmp_path / "apps"
    folder.mkdir()
    monkeypatch.setattr(
        routes, "bundle_target", lambda v: (f"MAME_Curator-{v}-x86_64.AppImage", folder)
    )
    response = client.post("/api/updates/apply")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["install_kind"] == "bundle"
    assert Path(body["downloaded_path"]).read_bytes() == ASSET_BODY
    # A bundle never offers a rollback or a pending restart.
    app = client.get("/api/updates/check").json()["app"]
    assert not app["rollback_available"] and not app["restart_pending"]


@pytest.mark.skipif(sys.platform == "win32", reason="drives git; POSIX-only")
def test_git_apply_records_then_rolls_back(
    client: Any, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _kind(monkeypatch, "git")
    repo = make_clone(tmp_path / "git")
    gh.tag = "v1.1.0"
    state = client.app.state
    state.update_repo, state.update_run = repo, Recorder()
    state.started_commit = git(repo, "rev-parse", "HEAD")
    world = state.world

    response = client.post("/api/updates/apply")
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["from_version"], body["to_version"]) == (__version__, "1.1.0")
    assert body["restart_required"] and body["snapshot_id"]
    assert (world.data_dir / "snapshots" / body["snapshot_id"]).is_dir()
    record = json.loads((world.data_dir / "update-state.json").read_text())
    assert record["to_commit"] == git(repo, "rev-parse", "v1.1.0")
    assert "app_updated" in (world.data_dir / "activity.jsonl").read_text()

    app = client.get("/api/updates/check").json()["app"]
    assert app["restart_pending"] and app["rollback_available"]

    rolled = client.post("/api/updates/rollback")
    assert rolled.status_code == 200, rolled.text
    assert git(repo, "rev-parse", "HEAD") == git(repo, "rev-parse", "v1.0.0")
    app = client.get("/api/updates/check").json()["app"]
    # This process still runs the commit it started on, which rollback restored.
    assert not app["restart_pending"] and not app["rollback_available"]

    again = client.post("/api/updates/rollback")
    assert again.status_code == 409
    assert again.json()["code"] == "update_nothing_to_roll_back"


@pytest.mark.skipif(sys.platform == "win32", reason="drives git; POSIX-only")
def test_git_apply_error_carries_its_code(
    client: Any, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _kind(monkeypatch, "git")
    repo = make_clone(tmp_path / "git")
    (repo / "a.txt").write_text("edited")
    gh.tag = "v1.1.0"
    client.app.state.update_repo, client.app.state.update_run = repo, Recorder()
    response = client.post("/api/updates/apply")
    assert response.status_code == 409
    assert response.json()["code"] == "update_dirty_tree"


@pytest.mark.skipif(sys.platform == "win32", reason="drives git; POSIX-only")
def test_error_detail_is_one_line(
    client: Any, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """api/spec.md § Error envelope — git's multi-line refusal keeps detail one line."""
    _kind(monkeypatch, "git")
    repo = make_clone(tmp_path / "git")
    (repo / "b.txt").write_text("in the way")
    gh.tag = "v1.1.0"
    client.app.state.update_repo, client.app.state.update_run = repo, Recorder()
    body = client.post("/api/updates/apply").json()
    assert body["code"] == "update_merge_refused"
    assert "\n" not in body["detail"]
    assert body["detail"].startswith("git refused the merge: error:")

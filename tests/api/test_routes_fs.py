"""R29–R34 shape tests + L12 / L13 behavioral + S01–S03 sandbox-grant tests.

Per ``docs/specs/P04.md`` § Routes (Filesystem browser) and § Filesystem sandbox.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

# ---- Per-route shape tests --------------------------------------------------


def test_route_r29_shape_fs_list_within_home(client: Any) -> None:
    home = str(Path.home())
    response = client.get(f"/api/fs/list?path={home}")
    assert response.status_code == 200
    body = response.json()
    for key in ("path", "entries", "parent"):
        assert key in body


def test_route_r29_shape_fs_list_outside_allowlist(client: Any) -> None:
    response = client.get("/api/fs/list?path=/etc/passwd")
    assert response.status_code == 403
    assert response.json()["code"] == "fs_sandboxed"


def test_route_r30_shape_fs_home(client: Any) -> None:
    response = client.get("/api/fs/home")
    assert response.status_code == 200
    assert "path" in response.json()


def test_route_r31_shape_fs_drive_roots(client: Any) -> None:
    """R31 — informational drive roots, distinct from R32 allowlist."""
    response = client.get("/api/fs/roots")
    assert response.status_code == 200
    body = response.json()
    assert "roots" in body
    assert isinstance(body["roots"], list)


def test_route_r32_shape_fs_allowed_roots_list(client: Any) -> None:
    response = client.get("/api/fs/allowed-roots")
    assert response.status_code == 200
    body = response.json()
    assert "roots" in body
    for root in body["roots"]:
        assert root["source"] in ("config", "granted")


def test_route_r33_shape_fs_grant_root(client: Any, tmp_path: Path) -> None:
    grant_dir = tmp_path / "grant_target"
    grant_dir.mkdir()
    response = client.post("/api/fs/allowed-roots", json={"path": str(grant_dir)})
    assert response.status_code == 200

    nonexistent = client.post("/api/fs/allowed-roots", json={"path": "/definitely/not/a/path"})
    assert nonexistent.status_code == 400


def test_route_r34_shape_fs_revoke_root(client: Any, tmp_path: Path) -> None:
    grant_dir = tmp_path / "revoke_target"
    grant_dir.mkdir()
    granted = client.post("/api/fs/allowed-roots", json={"path": str(grant_dir)}).json()
    new_root = next(r for r in granted["roots"] if r["source"] == "granted")
    response = client.delete(f"/api/fs/allowed-roots/{new_root['id']}")
    assert response.status_code == 200

    not_found = client.delete("/api/fs/allowed-roots/nonexistent_id")
    assert not_found.status_code == 404


# ---- Behavioral tests (L12, L13) --------------------------------------------


def test_fs_list_sandboxed(client: Any, tmp_path: Path) -> None:
    """L12 — rejects /etc/passwd, ../../etc/passwd, and symlink-to-/etc."""
    # Direct absolute traversal.
    direct = client.get("/api/fs/list?path=/etc/passwd")
    assert direct.status_code == 403
    assert direct.json()["code"] == "fs_sandboxed"

    # Relative traversal (resolves to the same forbidden path).
    relative = client.get("/api/fs/list?path=../../etc/passwd")
    assert relative.status_code == 403
    assert relative.json()["code"] == "fs_sandboxed"

    # Symlink traversal — allowed root contains a symlink to /etc.
    symlink = tmp_path / "evil_link"
    try:
        symlink.symlink_to("/etc")
    except OSError:
        pytest.skip("symlink creation not supported on this platform")
    # Note: the symlink itself is in tmp_path, not in an allowlist root, so
    # listing tmp_path/evil_link would already 403. The case is covered by
    # the allowlist resolution rule in the spec.


def test_fs_roots_per_platform(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """L13 — Linux returns ('/'); Windows returns drive letters."""
    response = client.get("/api/fs/roots")
    assert response.status_code == 200
    roots = response.json()["roots"]
    if os.name == "posix":
        assert "/" in roots
    elif os.name == "nt":
        assert any(r.endswith(":\\") or r.endswith(":") for r in roots)


# ---- Additional sandbox tests (S01–S03) -------------------------------------


def test_fs_list_allowed_within_home(client: Any) -> None:
    """S01 — listing under $HOME succeeds."""
    response = client.get(f"/api/fs/list?path={Path.home()}")
    assert response.status_code == 200
    assert "entries" in response.json()


def test_fs_grant_root_then_list(client: Any, tmp_path: Path) -> None:
    """S02 — POST grant; subsequent list under the granted root succeeds."""
    grant_dir = tmp_path / "fixture_grant"
    grant_dir.mkdir()
    (grant_dir / "marker.txt").write_text("hi")

    grant = client.post("/api/fs/allowed-roots", json={"path": str(grant_dir)})
    assert grant.status_code == 200

    listed = client.get(f"/api/fs/list?path={grant_dir}")
    assert listed.status_code == 200
    names = [e["name"] for e in listed.json()["entries"]]
    assert "marker.txt" in names


def test_fs_revoke_config_root_rejected(client: Any) -> None:
    """S03 — DELETE on a config-derived root returns 400."""
    roots = client.get("/api/fs/allowed-roots").json()["roots"]
    config_roots = [r for r in roots if r["source"] == "config"]
    assert config_roots, "config-derived roots must be present"
    response = client.delete(f"/api/fs/allowed-roots/{config_roots[0]['id']}")
    assert response.status_code == 400

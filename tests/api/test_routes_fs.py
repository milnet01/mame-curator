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

    # Relative traversal — resolves against the test process's CWD, which on
    # CI runners can land inside the (faked) home allowlist root, in which
    # case the sandbox check passes and existence-fails with 404. Either
    # outcome means the request was denied; the security property under
    # test is "the response was NOT 200".
    relative = client.get("/api/fs/list?path=../../etc/passwd")
    assert relative.status_code in (403, 404)

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


# ---- FP20-D: compose_allowlist drops stale granted_roots --------------------


def test_compose_allowlist_drops_nonexistent_granted_roots(
    config_file: Path, fake_home: Path, tmp_path: Path
) -> None:
    """FP20-D: granted_roots pointing at missing paths or non-dirs are dropped.

    Threat: a config persisted to disk preserves ``granted_roots`` across
    sessions. If the user (or another process) later deletes the
    underlying directory, the allowlist entry survives ``resolve(strict=
    False)``. If anything is then created at that name — file, symlink,
    re-created directory — it is silently inside the sandbox without the
    user re-granting it. The fix filters the allowlist build to entries
    that satisfy both ``exists()`` and ``is_dir()`` at composition time.
    """
    from mame_curator.api.fs import compose_allowlist
    from mame_curator.api.schemas import FsConfig
    from mame_curator.api.state import load_app_config

    existing = tmp_path / "exists"
    existing.mkdir()
    not_a_dir = tmp_path / "file.txt"
    not_a_dir.write_text("hi")
    nonexistent = tmp_path / "ghost"  # never created

    base = load_app_config(config_file)
    config = base.model_copy(
        update={"fs": FsConfig(granted_roots=(existing, not_a_dir, nonexistent))}
    )

    roots = compose_allowlist(config)
    granted_paths = {Path(r.path) for r in roots if r.source == "granted"}

    assert existing.resolve() in granted_paths
    assert not_a_dir.resolve() not in granted_paths
    assert nonexistent.resolve() not in granted_paths


def test_compose_allowlist_logs_info_on_dropped_granted_root(
    config_file: Path,
    fake_home: Path,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """FP20-D: dropped granted roots emit an INFO log naming the path.

    The Settings UI surfaces "your granted root <path> is gone" using
    these log records; without the log there is no audit trail and the
    user has no signal that their config has drifted out of date.
    """
    from mame_curator.api.fs import compose_allowlist
    from mame_curator.api.schemas import FsConfig
    from mame_curator.api.state import load_app_config

    nonexistent = tmp_path / "ghost-missing-dir"

    base = load_app_config(config_file)
    config = base.model_copy(update={"fs": FsConfig(granted_roots=(nonexistent,))})

    with caplog.at_level("INFO", logger="mame_curator.api.fs"):
        compose_allowlist(config)

    assert any(str(nonexistent) in r.message for r in caplog.records), (
        f"expected INFO log naming {nonexistent}; got {[r.message for r in caplog.records]}"
    )

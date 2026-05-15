"""R35 (setup-check) + R36 (updates-check) shape tests.

Per ``docs/specs/P04.md`` § Stub endpoints.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


def test_route_r35_shape_setup_check(client: Any) -> None:
    response = client.get("/api/setup/check")
    assert response.status_code == 200
    body = response.json()
    for key in ("config_present", "paths", "reference_files"):
        assert key in body
    for path_key in ("source_roms", "source_dat", "dest_roms"):
        assert path_key in body["paths"]


def test_route_r36_shape_updates_check(client: Any) -> None:
    response = client.get("/api/updates/check")
    assert response.status_code == 200
    body = response.json()
    assert "app" in body
    assert "ini" in body
    assert body["ini"] == [], "P04 stub: ini list always empty"

    app = body["app"]
    assert "current_version" in app
    assert app["latest_version"] is None, "P04 stub: latest_version always null"
    assert app["update_available"] is False


def test_setup_check_cloneof_map_size_and_listxml_status(client: Any) -> None:
    """P15 § 4.3.1: /api/setup/check exposes cloneof_map_size and the
    raw listxml status under reference_files.

    FP24-BB: the derived ``listxml_available`` boolean was removed —
    the ListxmlBanner re-derives `file missing` vs `parsed empty`
    from the raw fields so it can pick a different body for each.
    cloneof_map_size is the literal len(world.cloneof_map).

    The api_listxml fixture maps pacmanf → pacman, so cloneof_map_size
    >= 1 and reference_files.listxml.exists is True.
    """
    resp = client.get("/api/setup/check")
    assert resp.status_code == 200
    body = resp.json()
    assert "listxml_available" not in body
    assert body["cloneof_map_size"] >= 1
    assert body["reference_files"]["listxml"]["exists"] is True


def test_setup_check_retroarch_configured_false_by_default(client: Any) -> None:
    """FP22-A: ``retroarch_configured`` is the AND of ``paths.retroarch``
    and ``paths.retroarch_core`` both being non-null.

    The default ``config_file`` fixture sets neither, so the field is
    ``False``. Drives the Launch-button gate (FP22-B) and the Setup
    banner RetroArch line (FP22-C) on the frontend.
    """
    resp = client.get("/api/setup/check")
    assert resp.status_code == 200
    body = resp.json()
    assert body["retroarch_configured"] is False


def test_app_state_has_world_lock(client: Any) -> None:
    """FP20-C: ``app.state.world_lock`` is an asyncio.Lock that mutating
    routes (patch_config, restore_config_snapshot, import_config,
    fs_grant_root, fs_revoke_root) must acquire before any
    ``read-merge-write-snapshot-set_world`` block.

    Without the lock, two concurrent PATCHes (frontend slider autosave
    under retry) read the same base ``world.config``, each compute a
    merged config, and the later writer overwrites the earlier — losing
    one user edit silently. P04 spec lines 104-115 mandate the lock.
    """
    import asyncio

    # The lifespan runs inside the TestClient context (entered by the
    # fixture), so app.state.world_lock is populated by the time we
    # query it through client.app.
    lock = client.app.state.world_lock
    assert isinstance(lock, asyncio.Lock)


def _write_config_with_retroarch(
    tmp_path: Path,
    config_file: Path,
    *,
    retroarch: Path | None,
    retroarch_core: Path | None,
) -> Path:
    """Splice ``retroarch`` / ``retroarch_core`` into the ``paths:`` block.

    The conftest config_file fixture intentionally omits both. Tests that
    need them rewrite the YAML rather than re-implementing the whole
    fixture.
    """
    src = config_file.read_text()
    extras = ""
    if retroarch is not None:
        extras += f"  retroarch: {retroarch}\n"
    if retroarch_core is not None:
        extras += f"  retroarch_core: {retroarch_core}\n"
    rewritten = src.replace("\nserver:\n", f"{extras}\nserver:\n", 1)
    out = tmp_path / "config_with_retroarch.yaml"
    out.write_text(rewritten)
    return out


@pytest.mark.parametrize(
    "has_retroarch, has_core, expected",
    [
        (True, False, False),
        (False, True, False),
        (True, True, True),
    ],
    ids=["retroarch_only", "core_only", "both_set"],
)
def test_setup_check_retroarch_configured(
    tmp_path: Path,
    config_file: Path,
    fake_home: Path,
    has_retroarch: bool,
    has_core: bool,
    expected: bool,
) -> None:
    """FP22-A: ``retroarch_configured`` is true only when both
    ``retroarch`` and ``retroarch_core`` are set — the launch route
    requires both. DS04 T1.13 parametrized two original tests + added
    the missing ``core_only`` case for completeness.
    """
    from fastapi.testclient import TestClient

    from mame_curator.api import create_app

    binary: Path | None = None
    if has_retroarch:
        binary = tmp_path / "retroarch"
        binary.write_text("#!/bin/sh\nexit 0\n")
        binary.chmod(0o755)
    core: Path | None = None
    if has_core:
        core = tmp_path / "mame_libretro.so"
        core.write_text("")

    cfg = _write_config_with_retroarch(tmp_path, config_file, retroarch=binary, retroarch_core=core)
    with TestClient(create_app(cfg)) as c:
        body = c.get("/api/setup/check").json()
    assert body["retroarch_configured"] is expected

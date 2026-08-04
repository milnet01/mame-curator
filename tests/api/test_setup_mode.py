"""mame-curator-1095 — degraded start when the DAT is unreadable.

Per ``docs/specs/mame-curator-1095-desktop-bundles.md`` § 4.2. A bundled
app whose configured ``source_dat`` is missing or corrupt must still
start: the Settings page is the only place the path can be corrected,
and it is unreachable when the lifespan aborts.

INV-7 (missing DAT) and INV-8 (malformed DAT) are stated separately
because the two take different paths through ``parse_dat`` — a fixture
that only deletes the file passes against a catch narrowed to
``FileNotFoundError``.

The degrade tests assert the world is *usable*, not merely machine-less:
a degrade that returns a half-built world moves the crash from the
lifespan to the first request.

Starting is necessary but not sufficient — INV-9 and INV-10 cover the
other half, the save that ends setup mode: the missing DAT must not veto
the PATCH that fixes it, and the fix must ask for the restart that
re-parses it.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from mame_curator.api.state import WorldState, build_world, replace_world


def _config_with_dat(config_file: Path, dat: Path) -> Path:
    """Rewrite ``config_file``'s ``source_dat:`` to point at ``dat``."""
    text = config_file.read_text(encoding="utf-8")
    patched, count = re.subn(r"(?m)^  source_dat: .*$", f"  source_dat: {dat}", text)
    assert count == 1, "config fixture no longer has exactly one source_dat line"
    config_file.write_text(patched, encoding="utf-8")
    return config_file


def _assert_usable_setup_world(world: WorldState) -> None:
    """Every field populated, empty rather than absent — not a half-built world."""
    assert world.setup_required is True
    assert world.machines == {}
    assert world.bytes_by_machine == {}
    assert world.filter_result.winners == ()
    assert world.allowed_roots  # allowlist still composed from config.paths
    assert world.ctx is not None
    assert world.data_dir == world.config_path.parent / "data"


@pytest.fixture
def setup_mode_client(config_file: Path, tmp_path: Path, fake_home: Path) -> Iterator[Any]:
    """A client whose app started in setup mode — the DAT path is absent.

    Built here rather than from the shared ``app`` fixture because the
    config must be rewritten *before* ``create_app`` runs: setup mode is
    decided once, during the lifespan.
    """
    from fastapi.testclient import TestClient

    from mame_curator.api import create_app

    _config_with_dat(config_file, tmp_path / "does-not-exist.xml")
    with TestClient(create_app(config_file)) as client:
        yield client


def test_missing_dat_starts_in_setup_mode(config_file: Path, tmp_path: Path) -> None:
    """INV-7 — an absent ``source_dat`` degrades instead of raising."""
    path = _config_with_dat(config_file, tmp_path / "does-not-exist.xml")

    _assert_usable_setup_world(build_world(path))


def test_malformed_dat_starts_in_setup_mode(config_file: Path, tmp_path: Path) -> None:
    """INV-8 — a DAT that exists but is not parseable degrades too."""
    broken = tmp_path / "broken.dat.xml"
    broken.write_text("<mame><machine name='pacman'", encoding="utf-8")

    _assert_usable_setup_world(build_world(_config_with_dat(config_file, broken)))


def test_world_swap_preserves_setup_mode(config_file: Path, tmp_path: Path) -> None:
    """``setup_required`` follows ``machines`` through a world swap.

    ``replace_world`` names every field explicitly, so the default would
    silently clear setup mode on the first ``PATCH /api/config`` while the
    library stayed empty — the SPA would then see a configured app with no
    games rather than one still in setup.
    """
    world = build_world(_config_with_dat(config_file, tmp_path / "does-not-exist.xml"))

    assert replace_world(base=world, notes={"pacman": "note"}).setup_required is True


def test_patch_persists_while_only_dat_missing(setup_mode_client: Any) -> None:
    """INV-9 — the missing ``source_dat`` must not veto an unrelated save.

    Every other path check stays fatal; only ``source_dat`` is skipped, and
    only while setup mode is on. Without this the user can never save the
    change that ends setup mode — including changes with nothing to do with
    paths, like this theme switch.
    """
    response = setup_mode_client.patch("/api/config", json={"ui": {"theme": "light"}})

    assert response.status_code == 200, response.text
    assert setup_mode_client.get("/api/config").json()["ui"]["theme"] == "light"


def test_dat_change_requests_restart(setup_mode_client: Any, mini_dat: Path) -> None:
    """INV-10 — correcting the DAT path asks for the restart that reloads it.

    ``replace_world`` does not re-parse the DAT, so without the prompt the
    user fixes the path, sees no complaint, and the library stays empty.
    """
    response = setup_mode_client.patch("/api/config", json={"paths": {"source_dat": str(mini_dat)}})

    assert response.status_code == 200, response.text
    assert response.json()["restart_required"] is True

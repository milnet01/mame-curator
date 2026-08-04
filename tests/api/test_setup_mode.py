"""mame-curator-1095 — degraded start when the DAT is unreadable.

Per ``docs/specs/mame-curator-1095-desktop-bundles.md`` § 4.2. A bundled
app whose configured ``source_dat`` is missing or corrupt must still
start: the Settings page is the only place the path can be corrected,
and it is unreachable when the lifespan aborts.

INV-7 (missing DAT) and INV-8 (malformed DAT) are stated separately
because the two take different paths through ``parse_dat`` — a fixture
that only deletes the file passes against a catch narrowed to
``FileNotFoundError``.

Both tests assert the world is *usable*, not merely machine-less: a
degrade that returns a half-built world moves the crash from the
lifespan to the first request.
"""

from __future__ import annotations

import re
from pathlib import Path

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

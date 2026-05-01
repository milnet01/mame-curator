"""Shared fixtures for copy/ tests."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from mame_curator.parser.listxml import BIOSChainEntry, parse_listxml_bios_chain
from mame_curator.parser.models import Machine

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def bios_chain() -> dict[str, BIOSChainEntry]:
    """Parsed BIOS chain map from the fixture listxml."""
    return parse_listxml_bios_chain(FIXTURES / "listxml_bios.xml")


@pytest.fixture
def machine_kof94() -> Machine:
    return Machine(
        name="kof94",
        description="The King of Fighters '94 (Set 1)",
        is_bios=False,
        is_device=False,
        is_mechanical=False,
        runnable=True,
    )


@pytest.fixture
def machine_sf2ce() -> Machine:
    return Machine(
        name="sf2ce",
        description="Street Fighter II' - Champion Edition (World 920313)",
        is_bios=False,
        is_device=False,
        is_mechanical=False,
        runnable=True,
    )


@pytest.fixture
def make_zip(tmp_path: Path) -> Callable[..., Path]:
    """Factory: create a fake zip file with given content; returns the Path."""

    def _make(
        name: str, content: bytes = b"PK\x05\x06" + b"\0" * 18, in_dir: Path | None = None
    ) -> Path:
        target_dir = in_dir or tmp_path
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / name
        path.write_bytes(content)
        return path

    return _make


@pytest.fixture(scope="module")
def source_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Source directory with kof94, kof94a, sf2, sf2ce, neogeo, cps1bios zips.

    Module-scoped: every consumer (`test_executor`, `test_fp02_fixes`, etc.)
    reads the fixture, never mutates its contents (writes target their own
    `dest_dir` or `monkeypatch.setattr(shutil, ...)`). Module scope avoids
    rebuilding eight zip files per test (verified via grep across
    `tests/copy/` 2026-05-01).
    """
    src = tmp_path_factory.mktemp("source_dir_shared")
    for name in (
        "kof94",
        "kof94a",
        "sf2",
        "sf2ce",
        "neogeo",
        "cps1bios",
        "euro",
        "us",
    ):
        (src / f"{name}.zip").write_bytes(name.encode() * 100)
    return src


@pytest.fixture
def dest_dir(tmp_path: Path) -> Path:
    """Empty destination directory."""
    d = tmp_path / "dest"
    d.mkdir()
    return d

"""Shared fixtures for copy/ tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from mame_curator.parser.listxml import BIOSChainEntry, parse_listxml_bios_chain

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def bios_chain() -> dict[str, BIOSChainEntry]:
    """Parsed BIOS chain map from the fixture listxml.

    Module-scoped: the parsed result is treated as read-only by all
    ~25 consumer tests, and parsing a static fixture XML is wasted
    work to repeat per test (chunk-2 audit, 2026-05-18).
    """
    # `no-any-return` silences the pre-commit isolated mypy (which
    # can't resolve `mame_curator.parser.listxml` and infers `Any`
    # from the import); `unused-ignore` lets the CI mypy (which sees
    # the real `dict[str, BIOSChainEntry]` return) skip the
    # no-any-return check without complaining the ignore is unused.
    return parse_listxml_bios_chain(FIXTURES / "listxml_bios.xml")  # type: ignore[no-any-return, unused-ignore]


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

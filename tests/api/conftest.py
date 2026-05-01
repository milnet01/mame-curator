"""Shared fixtures for ``tests/api/``.

Reuses the existing parser / copy fixture data files (mini DAT, INIs, listxml)
so the API tests don't duplicate them. Only API-specific fixture data lives in
``tests/api/fixtures/``.

The ``app`` and ``client`` fixtures call ``mame_curator.api.create_app`` which,
during Step 3, raises ``NotImplementedError``. Tests using these fixtures
therefore fail at fixture-setup time — that is the desired red state. Step 4's
implementation makes them pass.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

PARSER_FIXTURES = Path(__file__).resolve().parents[1] / "parser" / "fixtures"
COPY_FIXTURES = Path(__file__).resolve().parents[1] / "copy" / "fixtures"
API_FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def mini_dat() -> Path:
    """6-machine DAT fixture (reused from parser tests)."""
    return PARSER_FIXTURES / "mini.dat.xml"


@pytest.fixture
def listxml() -> Path:
    """Listxml fixture with pacman/pacmanf cloneof + neogeo bios entries.

    The api/fixtures/api_listxml.xml fixture covers the mini DAT machines
    (pacman/pacmanf cloneof relationship) so the API tests' ``/api/games/
    pacman/explanation`` route returns a non-empty contested-group hit chain.
    """
    return API_FIXTURES / "api_listxml.xml"


@pytest.fixture
def catver_ini() -> Path:
    return PARSER_FIXTURES / "catver.ini"


@pytest.fixture
def languages_ini() -> Path:
    return PARSER_FIXTURES / "languages.ini"


@pytest.fixture
def bestgames_ini() -> Path:
    return PARSER_FIXTURES / "bestgames.ini"


@pytest.fixture
def mature_ini() -> Path:
    return PARSER_FIXTURES / "mature.ini"


@pytest.fixture
def series_ini() -> Path:
    return PARSER_FIXTURES / "series.ini"


@pytest.fixture
def source_dir(tmp_path: Path) -> Path:
    """Temporary source-rom directory with .zip files matching the mini DAT."""
    src = tmp_path / "src"
    src.mkdir()
    for short in ("pacman", "pacmanf", "neogeo", "z80", "3bagfull", "brokensim"):
        (src / f"{short}.zip").write_bytes(short.encode() * 100)
    return src


@pytest.fixture
def dest_dir(tmp_path: Path) -> Path:
    """Temporary destination directory (writable, empty)."""
    d = tmp_path / "dest"
    d.mkdir()
    return d


@pytest.fixture
def config_file(
    tmp_path: Path,
    mini_dat: Path,
    listxml: Path,
    catver_ini: Path,
    languages_ini: Path,
    bestgames_ini: Path,
    mature_ini: Path,
    series_ini: Path,
    source_dir: Path,
    dest_dir: Path,
) -> Path:
    """Write a config.yaml under tmp_path that points at all reference files.

    Per ``docs/specs/P04.md`` § AppConfig schema. The shape mirrors
    ``config.example.yaml`` at the repo root.
    """
    config_yaml = f"""
paths:
  source_roms: {source_dir}
  source_dat: {mini_dat}
  dest_roms: {dest_dir}
  retroarch_playlist: {dest_dir}/mame.lpl
  catver: {catver_ini}
  languages: {languages_ini}
  bestgames: {bestgames_ini}
  mature: {mature_ini}
  series: {series_ini}
  listxml: {listxml}

server:
  host: 127.0.0.1
  port: 8080
  open_browser_on_start: false

filters:
  drop_bios_devices_mechanical: true
  drop_categories: []
  drop_genres: []
  drop_publishers: []
  drop_developers: []
  drop_japanese_only_text: false
  drop_preliminary_emulation: true
  drop_chd_required: true
  drop_mature: false

  region_priority: ["World", "USA", "Europe", "Japan"]
  preferred_genres: []
  preferred_publishers: []
  preferred_developers: []
  prefer_parent_over_clone: true
  prefer_good_driver: true

ui:
  theme: dark
  layout: masonry

updates:
  channel: stable
  check_on_startup: false
  ini_check_on_startup: false

fs:
  granted_roots: []
"""
    path = tmp_path / "config.yaml"
    path.write_text(config_yaml.lstrip())
    return path


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Override ``Path.home()`` to a controlled subdir under ``tmp_path``.

    Without this, on Windows CI the system tmp lives under ``USERPROFILE``,
    so any pytest ``tmp_path``-derived directory is "already covered" by
    the home allowlist root that ``compose_allowlist`` adds — collapsing
    the grant tests to 409. Linux/macOS CI with ``HOME=/home/runner`` also
    catches relative paths like ``../../etc/passwd`` resolving back inside
    home, masking the sandbox check. Setting both ``HOME`` and
    ``USERPROFILE`` to a known subdir keeps the home root small and
    predictable for every test platform.
    """
    home = tmp_path / "fake_home"
    home.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    return home


@pytest.fixture
def app(config_file: Path, fake_home: Path) -> Any:
    """FastAPI application instance.

    The ``fake_home`` fixture must run BEFORE ``create_app`` — the latter
    calls ``compose_allowlist`` which calls ``Path.home()``.
    """
    from mame_curator.api import create_app

    return create_app(config_file)


@pytest.fixture
def client(app: Any) -> Iterator[Any]:
    """``fastapi.testclient.TestClient`` bound to the application instance."""
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c

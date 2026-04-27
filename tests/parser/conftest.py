"""Shared fixtures for parser tests."""

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def mini_dat() -> Path:
    """Path to the 6-machine mini DAT fixture."""
    return FIXTURES / "mini.dat.xml"


@pytest.fixture
def listxml_with_disks() -> Path:
    """Path to a tiny listxml fixture with one CHD-required machine."""
    return FIXTURES / "listxml_with_disks.xml"


@pytest.fixture
def catver_ini() -> Path:
    """Path to the catver.ini fixture."""
    return FIXTURES / "catver.ini"


@pytest.fixture
def languages_ini() -> Path:
    """Path to the languages.ini fixture."""
    return FIXTURES / "languages.ini"


@pytest.fixture
def bestgames_ini() -> Path:
    """Path to the bestgames.ini fixture."""
    return FIXTURES / "bestgames.ini"


@pytest.fixture
def mature_ini() -> Path:
    """Path to the mature.ini fixture."""
    return FIXTURES / "mature.ini"


@pytest.fixture
def series_ini() -> Path:
    """Path to the series.ini fixture."""
    return FIXTURES / "series.ini"

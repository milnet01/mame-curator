"""Shared fixtures for filter tests."""

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to the filter test fixtures directory."""
    return FIXTURES

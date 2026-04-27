"""Smoke test: the package imports and exposes a version."""

import mame_curator


def test_package_imports() -> None:
    """The package must be importable."""
    assert mame_curator is not None


def test_version_is_set() -> None:
    """__version__ is a non-empty string."""
    assert isinstance(mame_curator.__version__, str)
    assert len(mame_curator.__version__) > 0

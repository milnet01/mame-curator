"""Smoke test: the package imports and exposes a version."""

import mame_curator


def test_version_is_set() -> None:
    """``mame_curator`` imports cleanly and exposes a non-empty ``__version__``.

    FP31: collapsed prior `test_package_imports` (whose body was the
    tautological `assert mame_curator is not None`) into this test — the
    bare ``import`` at module top already proves importability, and any
    attribute lookup below proves the module object is real.
    """
    assert isinstance(mame_curator.__version__, str)
    assert len(mame_curator.__version__) > 0

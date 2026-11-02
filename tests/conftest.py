"""Top-level pytest configuration.

Subdirectory ``conftest.py`` files (``tests/parser/``, ``tests/filter/``)
add per-suite fixtures; this top-level file handles shared environment
setup that must run before any subordinate ``conftest.py`` imports
resolve.
"""

from __future__ import annotations

# Force Qt's offscreen QPA platform before anything imports QApplication.
# MAME_Curator is a CLI tool today and doesn't pull in Qt, but adding
# the safe default here makes it impossible for a future Qt-using
# test (or a transitive import) to flash a real window onto the
# desktop hosting the test runner. `setdefault` lets a CI override
# (e.g. QT_QPA_PLATFORM=minimal) still win.
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# mame-curator-1186: `data/` at the repo root is the user's real data when they
# run the app from a checkout. Absent in CI, which the snapshot treats as empty.
_USER_DATA = Path(__file__).resolve().parents[1] / "data"


def _snapshot(folder: Path) -> dict[str, tuple[int, int]]:
    """Map each name under `folder`, and `folder` itself, to its size and mtime."""
    found: dict[str, tuple[int, int]] = {}
    paths = [folder] if folder.exists() else []
    for root, dirs, files in os.walk(folder):
        paths += [Path(root, name) for name in (*dirs, *files)]
    for path in paths:
        try:
            info = path.lstat()
        except FileNotFoundError:  # Gone since the walk: the app may be running here.
            continue
        found[path.relative_to(folder.parent).as_posix()] = (info.st_size, info.st_mtime_ns)
    return found


# Taken as this file loads, so a write during collection counts too.
_USER_DATA_AT_START = _snapshot(_USER_DATA)


@pytest.fixture(autouse=True, scope="session")
def _user_data_stays_untouched() -> Iterator[None]:
    """Fail the run if anything in it changed the repo's `data/` folder."""
    yield
    now = _snapshot(_USER_DATA)
    changed = sorted(
        name
        for name in _USER_DATA_AT_START.keys() | now.keys()
        if _USER_DATA_AT_START.get(name) != now.get(name)
    )
    if changed:
        pytest.fail(
            "A test wrote into the repo's data/ folder, which holds the user's real "
            "data. Give the code under test a temp folder instead. Changed: "
            f"{', '.join(changed)}. The test this is reported against is only the last "
            "to run. If the app was running from this folder, it may be the writer.",
            pytrace=False,
        )


@pytest.fixture(autouse=True)
def _run_outside_the_repo(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Start each test in its own empty folder, away from the repo.

    The app's relative defaults (`run_copy`'s `Path("data")`, `./config.yaml`,
    `./data/media-cache`) then land here, not in the user's files.
    """
    monkeypatch.chdir(tmp_path_factory.mktemp("cwd"))


@pytest.fixture
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace ``mame_curator.downloads.asyncio.sleep`` with a no-op coroutine.

    Tests that exercise retry-backoff paths in ``downloads.download`` (and
    transitively ``updates.refresh_inis``) opt into this fixture so the
    backoff sleeps don't actually wait. Not autouse — only test modules
    that touch the retry path should request it.
    """

    async def _instant(*_args: Any, **_kwargs: Any) -> None:
        return None

    monkeypatch.setattr("mame_curator.downloads.asyncio.sleep", _instant)

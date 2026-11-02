"""mame-curator-1186: test runs must leave the repo's `data/` folder alone.

`data/` at the repo root is the user's real data when they run the app from a
checkout. Three things protect it, and this file proves each one:

- `tests/conftest.py` runs every test from an empty temp folder, so a relative
  default such as `run_copy`'s `Path("data")` lands there.
- `tests/conftest.py` fails the run if `data/` changed anyway, naming what did.
- The Playwright fixture config keeps everything it writes under its own folder.

The guard is checked by running a small pytest session of its own, on a copy of
the real `conftest.py`, in a temp folder that stands in for the repo.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from mame_curator.api.schemas import AppConfig

REPO_ROOT = Path(__file__).resolve().parents[1]

_DATA = 'data = Path(__file__).resolve().parents[1] / "data"\n'


def _run_child_session(root: Path, test_body: str) -> subprocess.CompletedProcess[str]:
    """Run one test, in a session under `root`, with the real conftest."""
    tests = root / "tests"
    tests.mkdir()
    shutil.copy(REPO_ROOT / "tests" / "conftest.py", tests / "conftest.py")
    (tests / "test_child.py").write_text(
        f"from pathlib import Path\n\n\ndef test_child():\n    {_DATA}    {test_body}\n",
        encoding="utf-8",
    )
    return subprocess.run(  # noqa: S603 — fixed argv: this interpreter, a temp folder of ours
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(tests)],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _seed_data(root: Path) -> None:
    (root / "data").mkdir()
    (root / "data" / "activity.jsonl").write_text("{}\n", encoding="utf-8")


def _path_values(value: Any) -> list[Path]:
    """Every `Path` inside a dumped config, however deep."""
    if isinstance(value, Path):
        return [value]
    if isinstance(value, dict):
        return [p for v in value.values() for p in _path_values(v)]
    if isinstance(value, list | tuple):
        return [p for v in value for p in _path_values(v)]
    return []


def test_every_test_runs_outside_the_repo() -> None:
    """A relative path in a test or in production code cannot reach the repo."""
    assert not Path.cwd().resolve().is_relative_to(REPO_ROOT)


@pytest.mark.parametrize(
    ("seeded", "test_body", "named"),
    [
        pytest.param(True, '(data / "new.zip").write_text("x")', "new.zip", id="adds-a-file"),
        pytest.param(
            True,
            '(data / "activity.jsonl").write_text("{}\\n{}\\n")',
            "activity.jsonl",
            id="changes-a-file",
        ),
        pytest.param(
            True, '(data / "activity.jsonl").unlink()', "activity.jsonl", id="removes-a-file"
        ),
        pytest.param(False, "data.mkdir()", "data", id="creates-the-folder"),
    ],
)
def test_the_guard_fails_the_run_and_names_what_changed(
    tmp_path: Path, seeded: bool, test_body: str, named: str
) -> None:
    if seeded:
        _seed_data(tmp_path)

    result = _run_child_session(tmp_path, test_body)

    output = result.stdout + result.stderr
    assert result.returncode == 1, output
    assert "wrote into the repo's data/ folder" in output
    assert named in output


@pytest.mark.parametrize("seeded", [True, False], ids=["data-present", "data-absent-as-in-ci"])
def test_the_guard_stays_quiet_when_data_is_untouched(tmp_path: Path, seeded: bool) -> None:
    if seeded:
        _seed_data(tmp_path)

    result = _run_child_session(tmp_path, "assert True")

    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "data").exists() is seeded


def test_a_relative_data_path_lands_in_the_temp_folder(tmp_path: Path) -> None:
    """The route the bug took: `Path("data")`, resolved against the working folder."""
    _seed_data(tmp_path)

    result = _run_child_session(
        tmp_path,
        'Path("data").mkdir(); Path("data/activity.jsonl").write_text("from a test")',
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "data" / "activity.jsonl").read_text(encoding="utf-8") == "{}\n"


def test_the_playwright_config_keeps_out_of_the_data_folder() -> None:
    """No gate runs frontend/e2e, so this is what stops the fixture drifting back.

    The server starts in the repo root, so a relative path resolves there, and
    an unset media folder falls back to `./data/...`.
    """
    fixture = REPO_ROOT / "frontend" / "e2e" / "fixtures" / "config.yaml"
    config = AppConfig.model_validate(yaml.safe_load(fixture.read_text(encoding="utf-8")))

    paths = _path_values(config.model_dump())

    assert paths
    inside = [p for p in paths if (REPO_ROOT / p).resolve().is_relative_to(REPO_ROOT / "data")]
    assert not inside

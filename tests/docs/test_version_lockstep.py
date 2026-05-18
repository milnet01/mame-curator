"""DS02 F2 — pyproject.toml and frontend/package.json versions match.

The frontend ships inside the same Python package distribution; both
files should report the same semver string so the next `/bump` recipe
rolls both atomically and `mame-curator --version` matches the
SettingsPage About-tab build label.

At HEAD pyproject is at 1.2.0; frontend/package.json is at 0.0.1 — a
4-minor-cycle drift that's the legacy of `package.json` being
scaffolded once and never re-touched. F2 makes them lockstep.

Test: read both files, parse the version strings, assert equal. The
test runs every CI cycle so a future bump that updates only one side
fails fast.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = REPO_ROOT / "pyproject.toml"
PACKAGE_JSON = REPO_ROOT / "frontend" / "package.json"

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.+-]+)?$")


def _pyproject_version() -> str:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    version = data["project"]["version"]
    # FP31: failure messages name the file + observed type so a regression
    # changing the field type produces a useful CI log instead of bare
    # "AssertionError".
    assert isinstance(version, str), (
        f"pyproject.toml [project].version expected str, got {type(version).__name__}: {version!r}"
    )
    return version


def _package_json_version() -> str:
    data = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
    version = data["version"]
    assert isinstance(version, str), (
        f"frontend/package.json .version expected str, got {type(version).__name__}: {version!r}"
    )
    return version


def test_pyproject_version_is_semver() -> None:
    """Sanity check the source-of-truth before comparing."""
    version = _pyproject_version()
    assert SEMVER_RE.match(version), f"pyproject version {version!r} is not semver"


def test_frontend_package_json_version_matches_pyproject() -> None:
    """Both files must report the same semver string."""
    py = _pyproject_version()
    js = _package_json_version()
    assert py == js, (
        f"version drift: pyproject.toml={py!r} but frontend/package.json={js!r}. "
        f"Update frontend/package.json to {py!r} and add a bump-recipe entry "
        f"so the next /bump rolls both."
    )

"""mame-curator-1106 — dev tools live in the `dev` dependency group.

A plain `uv sync` is an exact sync: it installs the default dependency
groups and uninstalls anything else, extras included. While the dev tools
were a `dev` extra, that command stripped mypy, ruff, pytest and
pytest-cov, and the next `uv run` failed in ways that read as broken code.
uv installs the `dev` group by default, so keeping the tools there makes
the plain command safe. This pins the tools to the group and keeps them
out of any extra.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_TOOLS = ("pytest", "pytest-cov", "ruff", "mypy")


def _names(specs: list[str]) -> set[str]:
    return {spec.split(">")[0].split("=")[0].split("[")[0].strip() for spec in specs}


def test_dev_tools_are_in_the_dev_dependency_group() -> None:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    extras = data["project"].get("optional-dependencies", {})
    assert "dev" not in extras, "dev tools belong in [dependency-groups], not an extra"
    group = _names(data.get("dependency-groups", {}).get("dev", []))
    missing = [tool for tool in _TOOLS if tool not in group]
    assert not missing, f"[dependency-groups].dev is missing {missing}"

"""DS03 — cross-pin coupling drift detector.

Three deps appear in BOTH `pyproject.toml` (resolved via `uv.lock`) AND
`.pre-commit-config.yaml` (hook rev). One env var (`GITLEAKS_VERSION`)
appears in BOTH GitHub workflow files AND `.pre-commit-config.yaml`. This
test makes those couplings CI-enforceable so a future bump that only
touches one side fires the gate.

Failure mode this test prevents (DS02-R2 shape): pre-commit and CI run
different versions of the same tool because a manifest bump didn't
propagate to the hook rev — local pre-commit passes, CI fails (or vice
versa), and the gap surfaces only after push.

See `docs/specs/DS03.md` §§ Cluster D + Tests to write first.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

_COUPLED_TOOLS: tuple[tuple[str, str], ...] = (
    ("ruff", "https://github.com/astral-sh/ruff-pre-commit"),
    ("mypy", "https://github.com/pre-commit/mirrors-mypy"),
    ("bandit", "https://github.com/PyCQA/bandit"),
)

_GITLEAKS_REPO = "https://github.com/gitleaks/gitleaks"
_GITLEAKS_RE = re.compile(r'GITLEAKS_VERSION:\s*"?([0-9][0-9.]*)"?')


def _read_uv_lock_versions() -> dict[str, str]:
    raw = (REPO_ROOT / "uv.lock").read_text(encoding="utf-8")
    data = tomllib.loads(raw)
    return {pkg["name"]: pkg["version"] for pkg in data.get("package", [])}


def _read_precommit_revs() -> dict[str, str]:
    raw = (REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    return {entry["repo"]: entry["rev"] for entry in data["repos"] if "rev" in entry}


def _normalise(rev: str) -> str:
    return rev.removeprefix("v")


@pytest.mark.parametrize(("tool", "repo"), _COUPLED_TOOLS)
def test_pyproject_pin_matches_precommit_rev(tool: str, repo: str) -> None:
    """Pre-commit hook rev MUST equal uv.lock's resolved version for ruff/mypy/bandit."""
    locked = _read_uv_lock_versions()
    revs = _read_precommit_revs()

    assert tool in locked, f"{tool} not present in uv.lock"
    assert repo in revs, f"pre-commit config missing repo {repo}"

    locked_version = locked[tool]
    rev_version = _normalise(revs[repo])
    assert rev_version == locked_version, (
        f"{tool}: uv.lock pins {locked_version} but .pre-commit-config.yaml "
        f"rev is {revs[repo]!r}. Bump one to match the other so local and CI "
        f"run the same tool version."
    )


def test_gitleaks_version_lockstep_across_ci_release_and_precommit() -> None:
    """`GITLEAKS_VERSION` in ci.yml + release.yml == pre-commit gitleaks rev."""
    ci_text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    release_text = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    ci_match = _GITLEAKS_RE.search(ci_text)
    release_match = _GITLEAKS_RE.search(release_text)
    assert ci_match, "ci.yml is missing GITLEAKS_VERSION env var"
    assert release_match, "release.yml is missing GITLEAKS_VERSION env var"

    ci_version = ci_match.group(1)
    release_version = release_match.group(1)
    revs = _read_precommit_revs()
    assert _GITLEAKS_REPO in revs, "pre-commit config missing gitleaks repo"
    rev_version = _normalise(revs[_GITLEAKS_REPO])

    assert ci_version == release_version == rev_version, (
        f"gitleaks version drift: ci.yml={ci_version!r}, release.yml="
        f"{release_version!r}, pre-commit rev={revs[_GITLEAKS_REPO]!r}. All "
        f"three must pin the exact same binary so local pre-commit, CI lint, "
        f"and release-stage scans never diverge."
    )

"""DS03 — no pre-release pins.

Coding-standards § 8: "No lock-pinning to bleeding-edge zero-x releases
unless essential. Pin to the most recent stable." This test makes that
rule CI-enforceable instead of aspirational.

Walks every pin string in `pyproject.toml`, `frontend/package.json`,
`.pre-commit-config.yaml`, and the `GITLEAKS_VERSION` env vars in both
GitHub workflow files. Asserts no entry carries a pre-release marker
(alpha / beta / rc / preview / next / dev) that PEP 440 or npm dist-tag
semantics would resolve to a non-stable build.

See `docs/specs/DS03.md` §§ Tests to write first.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

_PRE_RELEASE_RE = re.compile(r"(?i)(alpha|beta|rc|preview|next|dev)(\d|$|[.-])")


def _python_pins() -> list[tuple[str, str]]:
    raw = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    data = tomllib.loads(raw)
    pins: list[tuple[str, str]] = []
    for spec in data["project"].get("dependencies", []):
        pins.append((f"pyproject.toml [project.dependencies]:{spec}", spec))
    for extra, specs in data["project"].get("optional-dependencies", {}).items():
        for spec in specs:
            pins.append((f"pyproject.toml [optional-dependencies.{extra}]:{spec}", spec))
    return pins


def _frontend_pins() -> list[tuple[str, str]]:
    raw = (REPO_ROOT / "frontend" / "package.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    pins: list[tuple[str, str]] = []
    for group in ("dependencies", "devDependencies"):
        for name, version in data.get(group, {}).items():
            pins.append((f"frontend/package.json {group}.{name}:{version}", version))
    return pins


def _precommit_pins() -> list[tuple[str, str]]:
    raw = (REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    pins: list[tuple[str, str]] = []
    for entry in data["repos"]:
        if "rev" in entry:
            pins.append((f".pre-commit-config.yaml {entry['repo']}:{entry['rev']}", entry["rev"]))
    return pins


def _gitleaks_env_pins() -> list[tuple[str, str]]:
    pattern = re.compile(r'GITLEAKS_VERSION:\s*"?([0-9][0-9.]*)"?')
    pins: list[tuple[str, str]] = []
    for name in ("ci.yml", "release.yml"):
        path = REPO_ROOT / ".github" / "workflows" / name
        match = pattern.search(path.read_text(encoding="utf-8"))
        if match:
            value = match.group(1)
            pins.append((f".github/workflows/{name} GITLEAKS_VERSION:{value}", value))
    return pins


_MISSING_FILE_SENTINEL = "__missing__:"


def _all_pins() -> list[tuple[str, str]]:
    """Collect every pin string across the five manifests.

    Each reader is wrapped in ``try`` so a stripped CI image (where one of
    the workflow files is missing, say, because the runner is a docs-only
    job) emits a named skip-entry instead of an unhandled collection-time
    exception (test-audit FP04, 2026-05-18).
    """
    pins: list[tuple[str, str]] = []
    for reader in (_python_pins, _frontend_pins, _precommit_pins, _gitleaks_env_pins):
        try:
            pins.extend(reader())
        except FileNotFoundError as exc:
            # Sentinel entry: the test below converts these to pytest.skip
            # so the missing file shows up by name in the test report.
            pins.append((f"{_MISSING_FILE_SENTINEL}{reader.__name__}", str(exc)))
    return pins


@pytest.mark.parametrize(("label", "value"), _all_pins())
def test_pin_is_not_pre_release(label: str, value: str) -> None:
    """No pin string carries a PEP 440 / npm pre-release suffix."""
    if label.startswith(_MISSING_FILE_SENTINEL):
        pytest.skip(f"manifest reader skipped: {label[len(_MISSING_FILE_SENTINEL) :]} → {value}")
    match = _PRE_RELEASE_RE.search(value)
    assert match is None, (
        f"{label} appears to pin a pre-release ({match.group(0)!r}). "
        f"Coding-standards § 8 forbids bleeding-edge pre-release pins unless "
        f"essential — and 'essential' must be documented inline if so."
    )

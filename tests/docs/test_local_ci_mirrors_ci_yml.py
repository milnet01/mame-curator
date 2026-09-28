"""mame-curator-1129 — the local CI mirror runs exactly the checks ci.yml runs.

The local mirror promises "the same commands, in the same order" as
.github/workflows/ci.yml, and until this test nothing compared the two.
Compared: every check command, in order. Exempt on both sides: setup
(installing Python, dependencies or gitleaks), which each side does its own
way, and the local mirror's --docs branch, which ci.yml has no twin for.

The mirror is found by glob, not by name (tests/docs/test_posix_only_tests_
skip_on_win32.py flags a quoted shell-script name).
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
SETUP_STEPS = re.compile(r"^(Set up Python|Install )")
RUN_LINE = re.compile(r'^\s*run(?:_in\s+\S+)?\s+"[^"]*"\s+(.+)$')


def _norm(cmd: str) -> str:
    cmd = " ".join(cmd.split())
    # The mirror wraps a shell snippet in bash -c '...' to run it as one step.
    wrapped = re.fullmatch(r"bash -c '(.*)'", cmd)
    return wrapped.group(1) if wrapped else cmd


def _ci_commands() -> list[str]:
    workflow = yaml.safe_load((REPO / ".github" / "workflows" / "ci.yml").read_text())
    commands = []
    for job in workflow["jobs"].values():
        for step in job["steps"]:
            if "run" in step and not SETUP_STEPS.match(step.get("name", "")):
                commands.append(_norm(step["run"]))
    return commands


def _mirror_commands() -> list[str]:
    (mirror,) = sorted(REPO.glob("local-CI.*"))
    text = mirror.read_text(encoding="utf-8").replace("\\\n", " ")
    body = text[text.index("# --- Job 1") : text.index("# --- Summary")]
    return [_norm(m.group(1)) for line in body.splitlines() if (m := RUN_LINE.match(line))]


def test_local_ci_runs_the_same_checks_as_ci_yml_in_order() -> None:
    ci, mirror = _ci_commands(), _mirror_commands()
    assert ci, "no check steps parsed from ci.yml"
    assert mirror == ci

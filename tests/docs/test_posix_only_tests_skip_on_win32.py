"""A test that drives a POSIX shell must declare itself POSIX-only.

`local-CI.sh` mirrors every command `.github/workflows/ci.yml` runs, but it
runs them on ONE machine — it cannot reproduce CI's `windows-latest` /
`macos-latest` legs. That gap is real and inherent, so the guard has to be a
check the local run CAN make: any test module that shells out to `bash`,
`sh`, or a `.sh` script fails on the Windows runner (no `/usr/bin/env bash`)
unless it carries a `sys.platform == "win32"` skip.

Caught for real on 2026-08-03 (mame-curator-1088): `tests/tools/
test_run_sh_port.py` passed every local gate and reddened both Windows legs
with `FileNotFoundError: [WinError 2]`. This test is the local half of that
signal — it costs a source scrape, not a Windows runner.

Deliberately a source scrape rather than a runtime check: the failure it
prevents happens on a platform this suite never executes on, so there is
nothing to observe at runtime. Same shape as the other `tests/docs/`
guards.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_ROOT = REPO_ROOT / "tests"

# A module "drives a shell" if it names a POSIX shell binary or a .sh script
# in a subprocess-ish context. Deliberately broad — a false positive costs
# one skipif line; a false negative costs a red CI leg.
_SHELL_USE = re.compile(
    r"""["'](?:/usr/bin/env\s+)?(?:ba)?sh["']|\.sh["']|shutil\.which\(["'](?:ba)?sh["']\)""",
)
# Any of the three spellings that make the module (or a test in it) skip on
# Windows: a module-level `pytestmark`, a per-test decorator, or an explicit
# `pytest.skip` at import time.
_WIN32_GUARD = re.compile(r'sys\.platform\s*==\s*["\']win32["\']')


def _modules_driving_a_shell() -> list[Path]:
    hits = []
    for path in sorted(TESTS_ROOT.rglob("test_*.py")):
        text = path.read_text(encoding="utf-8")
        if _SHELL_USE.search(text):
            hits.append(path)
    return hits


def test_shell_driving_test_modules_skip_on_win32() -> None:
    """Every shell-driving test module carries a win32 skip."""
    unguarded = [
        path.relative_to(REPO_ROOT)
        for path in _modules_driving_a_shell()
        if not _WIN32_GUARD.search(path.read_text(encoding="utf-8"))
    ]
    assert not unguarded, (
        "these test modules drive a POSIX shell but have no "
        'sys.platform == "win32" skip, so they will fail on CI\'s '
        f"windows-latest runner: {[str(p) for p in unguarded]}. Add "
        "`pytestmark = pytest.mark.skipif(sys.platform == 'win32', "
        "reason=...)` — local-CI.sh cannot catch this for you."
    )


def test_guard_actually_matches_something() -> None:
    """The scan finds the known shell-driving module.

    Without this, a typo in `_SHELL_USE` turns the guard above into a test
    that passes because it inspects nothing — the failure mode every
    source-scrape check has.
    """
    found = {p.relative_to(REPO_ROOT).as_posix() for p in _modules_driving_a_shell()}
    assert "tests/tools/test_run_sh_port.py" in found, (
        f"_SHELL_USE no longer matches the known shell-driving module; found {found}"
    )

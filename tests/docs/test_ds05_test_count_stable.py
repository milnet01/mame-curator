"""DS05 — test-declaration count regression-lock for the seam splits.

State-pin test: counts top-level test declarations (`def test_…` in
pytest, `it(` in vitest) across the project's test trees and pins
the totals. DS05's seam splits move tests across files but never
delete them — if Step 4 silently drops a test via a typo'd import
or wrong filename pattern, this test fires.

The count is by **declaration**, not by collection (parametrize
expansions count once). Cluster A/B/C splits should leave both
counts unchanged: moving an `it(...)` from `SettingsPage.test.tsx`
to `SettingsPage_render.test.tsx` is +0 net.

Bump the pinned values explicitly in the same commit as any
intentional test addition or removal. The pin is the audit trail.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Pinned counts at DS05 Step 3 (pre-impl). Step 4's seam splits MUST
# preserve both numbers. Step 4 commits that touch test counts MUST
# bump these pins in the same commit, with a journal-cited reason.
EXPECTED_PYTEST_DECLARATIONS = 504
EXPECTED_VITEST_DECLARATIONS = 289

_PYTEST_DEF_RE = re.compile(r"^def test_", re.MULTILINE)
_VITEST_IT_RE = re.compile(r"^\s*it\s*\(", re.MULTILINE)


def _count_in_tree(root: Path, pattern: re.Pattern[str], suffixes: tuple[str, ...]) -> int:
    total = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in suffixes:
            continue
        # Skip __pycache__ + node_modules + build artifacts.
        if any(part in {"__pycache__", "node_modules", "dist", "coverage"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        total += len(pattern.findall(text))
    return total


def test_pytest_declaration_count_stable() -> None:
    """Top-level `def test_…` count across `tests/` matches the pin.

    DS05 splits MUST preserve this count. If Step 4 changes it,
    bump `EXPECTED_PYTEST_DECLARATIONS` in the same commit with a
    one-line reason in the commit body.
    """
    tests_root = REPO_ROOT / "tests"
    actual = _count_in_tree(tests_root, _PYTEST_DEF_RE, (".py",))
    assert actual == EXPECTED_PYTEST_DECLARATIONS, (
        f"pytest test-declaration count drifted: expected "
        f"{EXPECTED_PYTEST_DECLARATIONS}, found {actual}. If this is "
        "intentional (test added or removed), bump the pin in the "
        "same commit and reference the journal entry. If unintentional, "
        "a test was likely dropped by a typo'd import or filename rename."
    )


def test_vitest_declaration_count_stable() -> None:
    """Top-level `it(` count across `frontend/src` matches the pin.

    DS05 splits MUST preserve this count. Same pin-bump-with-reason
    discipline as the pytest counterpart.
    """
    frontend_root = REPO_ROOT / "frontend" / "src"
    actual = _count_in_tree(frontend_root, _VITEST_IT_RE, (".ts", ".tsx"))
    assert actual == EXPECTED_VITEST_DECLARATIONS, (
        f"vitest test-declaration count drifted: expected "
        f"{EXPECTED_VITEST_DECLARATIONS}, found {actual}. Same "
        "discipline as the pytest counterpart applies."
    )

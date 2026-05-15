"""DS05 — file-size cap regression-lock for the three seam-split targets.

State-pin test (RED pre-split, GREEN post-split) that names the
acceptable post-DS05 layout. Each cluster lists the resulting files
and their max line counts; the test fails until every file in the
list satisfies its cap.

The test also acts as a forward-defending gate: a future PR that
re-grows any of these files past its cap fires the same assertion.

See `docs/specs/DS05.md` §§ Cluster A/B/C for the seam rationale.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


# Cluster A — `frontend/src/pages/__tests__/SettingsPage.test.tsx` split.
#
# Post-DS05: the original file ≤ 500 (was 742); two new sibling files
# under the same 500 cap. Numbers are spec § Cluster A's target.
_CLUSTER_A = (
    ("frontend/src/pages/__tests__/SettingsPage.test.tsx", 500),
    ("frontend/src/pages/__tests__/SettingsPage_render.test.tsx", 500),
    ("frontend/src/pages/__tests__/SettingsPage_destructive_confirm.test.tsx", 500),
)

# Cluster B — `tests/copy/test_runner.py` split.
_CLUSTER_B = (
    ("tests/copy/test_runner.py", 500),
    ("tests/copy/test_runner_lifecycle.py", 500),
)

# Cluster C — `tests/parser/test_dat.py` split.
# Soft cap (300) for parser tests; 3-way split mandated by spec.
_CLUSTER_C = (
    ("tests/parser/test_dat_basic.py", 300),
    ("tests/parser/test_dat_security.py", 300),
    ("tests/parser/test_dat_validation.py", 300),
)

_ALL_TARGETS = _CLUSTER_A + _CLUSTER_B + _CLUSTER_C


# DS05 Step 3 RED batch — xfail-strict-false until Step 4 splits land.
# `strict=False` tolerates per-case XPASS as the clusters land
# incrementally; the marker is removed entirely when all four clusters
# are GREEN. Pattern mirrors FP27 Tier 1's per-batch xfail discipline.
_DS05_RED = pytest.mark.xfail(
    strict=False,
    reason="DS05 Step 3 RED batch — GREEN after Step 4 splits land.",
)


@_DS05_RED
@pytest.mark.parametrize(("rel_path", "max_lines"), _ALL_TARGETS)
def test_ds05_split_target_under_cap(rel_path: str, max_lines: int) -> None:
    """Every DS05 split target exists and respects its line cap."""
    path = REPO_ROOT / rel_path
    assert path.exists(), (
        f"DS05 split target missing: {rel_path}. "
        "Either the cluster's split has not landed yet (Step 4) "
        "or the file was renamed."
    )
    line_count = sum(1 for _ in path.read_text(encoding="utf-8").splitlines())
    assert line_count <= max_lines, (
        f"{rel_path} is {line_count} lines, over the DS05 cap of "
        f"{max_lines}. Either re-extract a seam or amend the spec."
    )


@_DS05_RED
@pytest.mark.parametrize(("rel_path", "_cap"), _ALL_TARGETS)
def test_ds05_split_target_has_test_bodies(rel_path: str, _cap: int) -> None:
    """No DS05 split target is an empty husk — each has at least one test."""
    path = REPO_ROOT / rel_path
    if not path.exists():
        pytest.skip(f"Split not yet landed: {rel_path}")
    text = path.read_text(encoding="utf-8")
    marker = "def test_" if rel_path.endswith(".py") else "it("
    assert marker in text, (
        f"{rel_path} contains no `{marker}` declarations — "
        "likely a botched move (file created but empty)."
    )

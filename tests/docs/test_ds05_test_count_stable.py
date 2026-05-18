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
#
# Bumped 2026-05-16 (DS03 Cluster D): +3 pytest declarations for the
# two new docs-tests landing in this commit (test_dep_pin_coupling +
# test_no_pre_release_pins). 504 → 507.
# Bumped 2026-05-17 (P14 chunk 1): +8 pytest declarations for the new
# tests/filter/test_review_state.py (6 spec-listed tests + 2
# coverage-gate tests to hit the filter/ ≥ 95% bar). 507 → 515.
# Bumped 2026-05-17 (P14 chunk 2): +1 pytest declaration for
# test_review_state_event_round_trip (ActivityEvent tagged-union
# extension). 515 → 516.
# Bumped 2026-05-17 (P14 chunk 3): +2 pytest declarations for the new
# tests/api/test_state.py (replace_world passive-swap + omit-default
# pass-through; INV-4). 516 → 518.
# Bumped 2026-05-17 (P14 chunk 4): +11 pytest declarations for the new
# tests/api/test_state_routes.py (POST happy + write effects,
# POST/DELETE error paths, GET, INV-5/8/13). 518 → 529.
# Bumped 2026-05-17 (P14 chunk 5): +5 pytest declarations for the
# per-request review_state filter on GET /api/games (INV-10 + stage
# composition). 529 → 534.
# Bumped 2026-05-17 (P14 chunk 6): +1 pytest declaration for the
# INV-12 frontend/backend pending-predicate parity contract test.
# 534 → 535.
# Bumped 2026-05-17 (P10 chunk 1 foundations): +5 pytest declarations
# split across `tests/media/test_rate_limit.py` (4 — burst-cap, refill,
# capacity-cap, error-hierarchy) and `tests/media/test_cache_text.py`
# (extra 1 not counted by the count regex since most are async and
# import-side; the net +5 reflects the 4 rate-limit `def test_*`
# declarations + 1 cache-text `def test_default_text_max_bytes_*`).
# 535 → 540.
# Bumped 2026-05-17 (P10 chunk 2 LibretroSource refactor): +4 pytest
# declarations in `tests/media/test_sources.py` — 4 sync (`url_for`
# three kinds / `disabled_reason` default / Protocol compliance via
# isinstance / ClassVars pin); the 5th test (`test_libretro_source_prepare_is_noop`)
# is async (`async def`) and so doesn't match the `^def test_` regex.
# 540 → 544.
# Bumped 2026-05-18 (test-audit fold-in): regex now also matches
# `async def test_…` declarations so silently-dropped async tests
# trigger the guard (37 async tests previously uncounted). One
# regression-pin test (`test_b6_no_op_patch_preserves_filter_result`
# in test_fp09_fixes.py) was deleted as a byte-for-byte duplicate of
# `test_filter_recompute_idempotent_under_no_op_patch` in
# test_routes_config.py — see commit body for the rationale.
# Net: 544 - 1 (delete) + 37 (newly counted async tests) = 580.
# Bumped 2026-05-18 (P10 chunk 3a): +9 declarations in
# tests/updates/test_snaps.py covering discovery, download, extraction,
# disk-space gate, force/no-force overwrite, url override, non-PNG skip,
# and the PACK_URL_PATTERN regression-lock. 580 → 589.
# Bumped 2026-05-18 (P10 chunk 3b): +10 declarations in
# tests/media/test_sources.py covering ProgettoSnapsSource — name/kinds/
# protocol-conformance, file:// URL on hit, None on miss, non-snap kinds
# rejected, disabled_reason on empty-dir + absent-dir, per-instance
# existence cache, no-op prepare. 589 → 599.
EXPECTED_PYTEST_DECLARATIONS = 599
# Bumped 2026-05-17 (P14 chunk 7): +3 vitest declarations for the new
# frontend/src/hooks/__tests__/useReviewState.test.tsx (optimistic
# update + rollback + clear). 289 → 292.
# Bumped 2026-05-17 (P14 chunk 9): +7 vitest declarations for the new
# frontend/src/hooks/__tests__/useGameGridFocus.test.tsx (FP21-T
# preservation + focusNextPending). 292 → 299.
# Bumped 2026-05-17 (P14 chunk 10): +1 vitest declaration for the new
# review-state badge tests in GameCard.test.tsx (an `it()` for the
# undefined-prop case; the `it.each` covering 3 states isn't counted
# by the `^\s*it\s*\(` regex). 299 → 300.
# Bumped 2026-05-17 (FP29): +4 vitest declarations in
# SettingsPage_render.test.tsx pinning the new RetroArch executable
# and core PathRows (banner pointed users to a UI that didn't render
# the two fields). 300 → 304.
EXPECTED_VITEST_DECLARATIONS = 304

# Match both ``def test_…`` and ``async def test_…`` so async tests can't
# be silently dropped by a typo'd import without firing this guard.
_PYTEST_DEF_RE = re.compile(r"^(?:async\s+)?def test_", re.MULTILINE)
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

# Cold-eyes review loop 1 — DS05 spec

**Reviewer:** general-purpose agent, dispatched 2026-05-15.
**Spec at time of review:** `docs/specs/DS05.md` rev 1 (initial draft).
**Verdict:** REVISE.
**Findings:** 7 (3 HIGH + 3 MED + 1 LOW).

## Findings

### HIGH

- HIGH at `docs/specs/DS05.md:116` — `renderSettings` helper does not exist; actual helper is `render` at `frontend/src/pages/__tests__/SettingsPage.test.tsx:14`.
- HIGH at `docs/specs/DS05.md:91` — Cluster A A1 seam premise wrong: FP12/FP13 markers span the whole file, not just the first 270 lines. Reframe by line range, not by FP## tag.
- HIGH at `docs/specs/DS05.md:272` — DS02 R2 lesson recommendation contradicts `docs/journal/DS02.md:111` — journal asked for permanent fix (pre-commit wiring or `make ci-local`); spec proposes ad-hoc manual checklist. Coding-standards § 0 rule 4 violation.

### MED

- MED at `docs/specs/DS05.md:94` — destructive-confirm cluster is 4 `it` blocks, not 5; ~83 lines, not ~95.
- MED at `docs/specs/DS05.md:285` — `tools/check_error_codes_sync.py` does not exist; referencing a non-existent script invites confusion.
- MED at `docs/specs/DS05.md:88` — `~40 it blocks` overstates by ~25%; actual count is ~33 (30 top-level + 3 nested).

### LOW

- LOW at `docs/specs/DS05.md:228` — Cluster C acceptance inconsistency: scope mandates 3-way split, acceptance says "and possibly `test_dat_basic.py`". Commit to 3-way unconditionally or rephrase scope.

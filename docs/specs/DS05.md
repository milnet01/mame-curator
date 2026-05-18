# DS05 — Test-file seam-split sweep

- **Status:** ✅ closed 2026-05-16 (tag `DS05-complete`; see `../journal/DS05.md`)
- **Stable ID:** [mame-curator-1037]
- **Kind:** refactor (test files only — no production-code changes)
- **Source:** three conditional follow-ups opened during DS04 close
  (`mame-curator-1034`, `mame-curator-1035`, `mame-curator-1036`).
  Each named a single test file over a coding-standards cap; this
  bundle folds all three into one sweep per the FP27 / FP28 / DS02
  precedent of consolidating similar work.
- **Theme:** three test files violate `coding-standards.md` § 2 file-
  size caps. The hard cap (500 lines) is breached by Clusters A + B.
  Cluster C is over the **backend-Python** soft cap (300 lines). Note:
  `coding-standards.md` § 2 does NOT explicitly state caps for test
  files — it caps backend Python (500/300) and frontend React
  (350/200). DS05 applies the same caps to tests because (i) Python
  test files share the same readability constraints as production
  Python (functions, imports, fixtures), and (ii) Python tests already
  enforced the 500 hard cap implicitly through DS04's parametrize
  collapses. Cluster D opens to add an explicit test-file cap row to
  `coding-standards.md` § 2 — see Cluster D acceptance below. Splits along stable seams; no test deletions, no
  rewrites of working test bodies, no fixture restructuring beyond
  what the split forces. The goal is a cleaner foundation — every
  test that runs today still runs after, identical name + identical
  body.
- **Dependencies:** DS04 ✅ (the audit that surfaced these three
  items), DS02 ✅ (the structural debt sweep this echoes).

## Out of scope (verified during Step 1)

Each cluster verifies the file is still over its cap at HEAD before
opening. Files that came down under-cap as a side-effect of earlier
work are dropped silently. The Step 1 verification:

```text
SettingsPage.test.tsx       742 lines  >500  ✓ in scope (A)
test_runner.py              526 lines  >500  ✓ in scope (B)
test_dat.py                 447 lines  >300  ✓ in scope (C — soft cap only)
```

All three confirmed at HEAD (2026-05-15). No items dropped.

## Deliberately not in scope

- **Fixture extraction across clusters.** Each cluster's split MAY
  hoist private fixtures into a sibling `conftest.py` if doing so
  is the natural way to keep the resulting files small. Cross-
  cluster fixture sharing (e.g. unifying `mini_dat` usage across
  `tests/parser/` and `tests/copy/`) is a separate refactor and
  not opened here.
- **Test-body rewrites.** Every test's body stays byte-for-byte
  identical after the split. Renames are allowed only when the
  test moves to a new file whose name carries the same intent
  (e.g. `test_copy_dry_run_no_writes` keeps its name when moved
  from `test_runner.py` to `test_runner_preflight.py`).
- **Coverage-gate adjustments.** The `copy/` ≥85% / `parser/` ≥90%
  module coverage gates stay where they are. The split shouldn't
  change either number — the same tests run.
- **DS02 A4's `copy/runner.py` follow-up.** That's a production-
  code split deferred to its own spec. DS05 only touches test
  files.

## Why a single bundled sweep

Each split in isolation is small (~250 lines of moves per file).
Together they share three risks the close-phase reviewer would
re-discover three times if shipped as three separate phases:

1. **Vitest / pytest collection scope.** Splitting a test file
   into N files makes N collection units. The closing audit
   verifies the project's test count holds across the split
   (no test silently dropped via stale import or typo'd path).
2. **Fixture-import drift.** Moving a test out of one file into
   another forces every fixture it uses to be importable from
   the new file. The simplest path is a per-directory
   `conftest.py`; one cluster will discover the pattern, the
   other two then trivially copy it.
3. **`tests/` layout discipline.** Three files moving at once
   needs one cold-eyes review pass on the resulting tree, not
   three.

Bundling also amortises the audit / indie-review token cost
(close-phase dispatches both regardless of cluster count).

## Scope

### Cluster A — `frontend/src/pages/__tests__/SettingsPage.test.tsx` (742 → ≤ 500)

**Seam (proposed; finalised at Step 4):** the file has ONE
top-level `describe('SettingsPage', () => …)` with ~30 flat `it`
blocks plus one nested `describe('DS02 D1 — tab state lives in
URL ?tab=', …)` carrying 3 more `it` blocks (~33 total `it`
declarations; parameterised `it.each` cases count as multiple
runs but one declaration). Each flat `it` block clicks into a
specific tab (Filters, Picker, Updates, Interface, Media, Paths,
Snapshots, Backup). Two natural seams, each named by **line
range** (not by FP## tag — FP12/FP13/P15 references span the
whole file, not the upper portion):

- **A1 — extract the upper-file tab-rendering tests
  (`SettingsPage.test.tsx:L72-L349`)** (~280 lines, covers the
  9-tab-headers render assertion + the `it.each` RetroArch
  Setup-banner parameter table at `SettingsPage.test.tsx:L122`
  + the Updates R36 banner test at L140 + Filters/Picker
  chip-list render-and-patch tests + Updates/Interface dropdown
  tests up through `cards_per_row_hint` integer-cast at L330)
  into `SettingsPage_render.test.tsx`. The exact end line
  (L349) is the closing brace of the `cards_per_row_hint`
  patch test; everything after is the destructive-confirm and
  routing-state tail. Imports come along; the bulk of the
  user-event-driven patch tests for tabs further down stay
  in the main file.
- **A2 — extract the destructive-DAT-confirm cluster**
  (`SettingsPage.test.tsx:L520-602`, ~83 lines, 4 `it` blocks
  covering destructive-confirm cancel / accept / revert / "does
  not patch on cancel") into
  `SettingsPage_destructive_confirm.test.tsx`. Stable cluster
  that doesn't share fixtures with the rest.

Combined, A1 + A2 lift ~363 lines, leaving the main file at
~380. Both new files come in well under 500.

If A1 + A2 don't both land cleanly (e.g. fixture coupling
forces a third move), Step 4 adopts a 3-way split along
`SettingsPage_tab_interactions.test.tsx` /
`SettingsPage_destructive_confirm.test.tsx` /
`SettingsPage_chrome.test.tsx` (chrome = header + restart-
required banner + URL state). The decision is made at Step 4
based on what the seams actually look like once the moves
begin; the spec mandates the outcome (every resulting file
≤ 500 lines, no test deleted, no test renamed), not the exact
file boundary.

**Reuse before rewriting (rule 3):** **two** shared fixtures need
co-housing, not one:

- The `render` wrapper at `SettingsPage.test.tsx:14` (a
  `@testing-library/react` override that injects router +
  query client).
- The 48-line `config: AppConfigResponse` literal at
  `SettingsPage.test.tsx:22-69` (a fully-populated AppConfig
  fixture every test reaches into).

Both must be import-reachable from `SettingsPage.test.tsx` +
`SettingsPage_render.test.tsx` + `SettingsPage_destructive_confirm.test.tsx`.
Step 4 picks ONE of:

- (a) Keep both in `SettingsPage.test.tsx`, export them as
  module-private named exports, import from the two new files.
- (b) Hoist both to
  `frontend/src/pages/__tests__/_settingsPageFixtures.tsx`
  (leading underscore = "not a test file, helper only"; `.tsx`
  because the `render` wrapper returns JSX),
  import from all three.

(b) is the slightly-cleaner option because it stops
`SettingsPage.test.tsx` from being a load-bearing fixture
source for its siblings; (a) is cheaper if Step 4's
intermediate state would otherwise need two commits (move
fixtures → move tests). The DS05 author leans (a) for the
single-commit story; final call deferred to Step 4 based on
the actual diff complexity.

### Cluster B — `tests/copy/test_runner.py` (526 → ≤ 500)

**Seam (proposed; finalised at Step 4):** the file has explicit
section headers:

```text
# --- Dry-run ---------------------                line 55
# --- Apply (golden path) ----------                line 79
# --- Playlist conflict -------------                line 189
# --- Pause / resume / cancel ------                line 274
# DS01 — Cluster A and B tests below                line 331
# FP05 — cluster A1 + A3 tests below                line 439
```

Two natural splits:

- **B1 — extract the Pause / resume / cancel + DS01 + FP05
  sections** (lines 274-525, ~250 lines) into
  `tests/copy/test_runner_lifecycle.py`. These tests share the
  `_runner_with_recyclebin` helper pattern; the new file gets
  its own `conftest.py` import or a sibling helper module.
- **B2 — main file retains** Dry-run + Apply + Playlist conflict
  (lines 1-273, ~270 lines).

After B1: main file ~280 lines, new file ~250 lines. Both well
under 500.

**Reuse before rewriting:** the file currently uses module-level
fixture functions imported from elsewhere. If the lifecycle tests
need any of them, they import from the existing path — no fixture
duplication.

### Cluster C — `tests/parser/test_dat.py` (447 → ≤ 300)

**Seam:** the file has ~30 test functions organised top-to-bottom
roughly in this order:

```text
L1-105    "happy-path" parsing (basic structure, parent/clone,
          bios/device flags, year, manufacturer, driver_status,
          roms, zip wrapper, no-xml, multiple-xmls, missing-file,
          malformed-xml)
L107-211  security tests (xxe external entity, billion_laughs
          internal entity, zip member size cap)
L212-415  validation tests (duplicate names, missing fields,
          biosset, corrupt zip, year out of range, empty rom,
          empty biosset, negative size, non-integer size, empty
          dat, wrong root, unknown driver status, zip-slip)
L417-447  "# ---- FP04 — parser hardening sweep ----" tail
```

The natural split is the three-way `basic / security / validation`
the roadmap names:

- **C1 — `tests/parser/test_dat_basic.py`** (~110 lines): the
  happy-path tests up to L105.
- **C2 — `tests/parser/test_dat_security.py`** (~105 lines):
  the security tests L107-211.
- **C3 — `tests/parser/test_dat_validation.py`** (~235 lines):
  the validation tests + FP04 hardening tail L212-447.

After: three files each ≤ 250, all under the 300 soft cap. The
spec commits to a 3-way split unconditionally; if Step 4
discovers a reason the basic vs validation split is uneven
(e.g. the basic file ends up at 80 lines while validation
hits 230), the threshold to drop to a 2-way split (merging
basic into validation) is **fewer than 4 top-level test
functions** in any resulting file. The check is
`grep -c '^def test_' tests/parser/test_dat_basic.py` — under 4,
merge into validation; 4 or more, keep the 3-way.

**Reuse before rewriting:** the `mini_dat` fixture is currently
in `tests/parser/conftest.py` (already module-scoped). All three
new files import it automatically via pytest's conftest scoping
— no fixture duplication needed.

## Tests to write first (Step 3)

Test-file seam-splits are mechanical and don't get conventional
unit tests (every existing test that imports the affected files
is its own regression test for the split). The Step 3 RED batch
here is **state-pin** / **regression-lock** in nature, not
TDD-design-driving — the tests don't drive a contract that
doesn't yet exist; they pin the file-tree post-condition that
Step 4 must achieve. Each one RED before any Step 4 move, GREEN
after the matching move.

Write **two test files** — 18 cases total (16 parametrize + 2
stable-count) — that pin the new layout in place:

1. **`tests/docs/test_file_size_caps.py`** (extend if it exists,
   else create): assert each of the cluster targets is under cap
   at HEAD. The same script will then defend the cap forever —
   if a future PR re-grows any of these files past the cap, the
   gate fires.
2. **`tests/docs/test_test_count_stable.py`** (new): cache the
   current test count (from `pytest --collect-only -q | tail -1`)
   into a file, then assert the count stays the same across the
   refactor. The point is to catch a test that silently dropped
   via stale import or typo.
3. **Per-cluster grep test (in the same file)**: for each new
   test file, assert it contains at least one `def test_…` (so an
   empty file from a botched move fails before the test suite
   even runs).

All three are RED before Step 4's first move, GREEN after the
last move.

## Acceptance criteria (all met at close 2026-05-16; see `../journal/DS05.md`)

### Cluster acceptance

- [x] **Cluster A** — `SettingsPage.test.tsx` +
  `SettingsPage_render.test.tsx` +
  `SettingsPage_destructive_confirm.test.tsx`; main file
  ≤ 500 lines (final 336); every original `it` block still runs; vitest
  count holds. Fixture-choice resolved Step 4 to option (b) —
  `_settingsPageFixtures.tsx` (journal § By cluster).
- [x] **Cluster B** — `test_runner.py` (241) + `test_runner_lifecycle.py`
  (277); both ≤ 500 lines; pytest count holds. Step 4 additionally
  added a `_runner_helpers.py` factory-helper module (44 lines) —
  see journal § By cluster.
- [x] **Cluster C** — `test_dat_basic.py` + `test_dat_security.py`
  + `test_dat_validation.py` (3-way split landed; 2-way fallback
  not taken); all ≤ 300 lines (112 / 121 / 252); pytest count holds.

### Whole-pass acceptance

- [x] All three file-size targets met (`wc -l` gate).
- [x] No test deleted: `pytest --collect-only` returns identical
  count before and after.
- [x] All five backend gates green
  (`uv run pytest && uv run ruff check && uv run ruff format
  --check && uv run mypy && uv run bandit -c pyproject.toml -r
  src`).
- [x] Frontend gates green (`cd frontend && npm test && npm run lint
  && npx tsc --noEmit`).
- [x] Coverage gates hold: `copy/` ≥85%, `parser/` ≥90%, frontend
  ≥70%, overall ≥85%.
- [x] `/audit` returns clean (the closing audit re-runs the
  file-size grep and pytest collection-stable test).
- [x] `/indie-review` returns clean (or only contract-clarification
  findings folded as Cluster R1).
- [x] CHANGELOG `[Unreleased]` updated; ROADMAP DS05 ticked ✅;
  three sub-items (1034/1035/1036) marked ✅ with reference to
  DS05; journal at `docs/journal/DS05.md`.
- [x] Tagged `DS05-complete` (annotated); push (repo is PUBLIC).

## Architecture notes

DS05 changes nothing user-visible:

- **No production code changes.** Only `tests/` and
  `frontend/src/**/__tests__/` files move.
- **No public API surface change.** No `__init__.py` modifications,
  no test-helper renames, no fixture reshuffles beyond what each
  cluster's split requires.
- **No conftest reshuffle.** Each cluster's `conftest.py` (where
  needed) only adds helpers that came from the file being split,
  imported back into the original location for tests that stay
  put.

The DS02 R2 lesson applies here: any test-helper script that
discovers files via a hardcoded list (e.g. `tools/check_*.py`)
needs auditing post-split. Step 5/6 closing audit explicitly
greps `tools/` for `PYTHON_SOURCES`-style tuples that might
miss the new file paths.

## Cluster D — Permanent fix for the DS02 R2 lesson

Per the DS02 R2 post-mortem at `docs/journal/DS02.md` § "What
was learned": `tools/check_api_types_sync.py` is a CI-only gate
not wired into pre-commit, which is why DS02 A5's split-tuple
miss went undetected locally and CI caught it after the
DS02-complete tag was pushed. The journal explicitly named the
permanent fix as **either** (a) wire the script into pre-commit
(< 1 s runtime) **or** (b) add a `make ci-local` recipe to
CLAUDE.md "Common commands". Coding-standards § 0 rule 4 ("no
workarounds without a root-cause fix") makes (a) or (b) the
required path, not "remember to run scripts manually before
each close".

DS05 adopts path (a): **wire `tools/check_api_types_sync.py`
into `.pre-commit-config.yaml` as a `local` hook**, scoped to
`pass_filenames: false` (the script discovers its own inputs
from the hardcoded `PYTHON_SOURCES` tuple) and `always_run:
true` (so it runs even when no Python files change — DS02 R2
proved a TS-side change can also flag the gate). The hook
runs the same script CI runs; failures fail the commit. The
gate then fires before every commit, not just CI.

(Path (b) was the alternative; path (a) is preferred because
it catches the failure before `git commit` returns, vs. a
Makefile target which still relies on the author remembering
to run it.)

This makes Cluster D a small but load-bearing addition to the
sweep — without it, the next test-file refactor that re-shuffles
sibling-module discovery will hit the same DS02-R2-shape bug.

### Cluster D acceptance

- [ ] **D1** — `.pre-commit-config.yaml` gains a local hook
  named `check-api-types-sync` running
  `python3 tools/check_api_types_sync.py` with
  `pass_filenames: false`, `always_run: true`, `language: system`.
  Pattern mirrors the existing `pytest-fast` hook at
  `.pre-commit-config.yaml` (the project's working precedent;
  no `types:` filter needed when `always_run: true` is set —
  that's redundant per `pre-commit` docs).
- [ ] **D1-test** — regression test for the hook itself: a
  pytest at `tests/tools/test_check_api_types_sync.py` that
  invokes `tools/check_api_types_sync.py` as a subprocess with
  a `tmp_path`-staged Python source listing a Pydantic model
  whose name does NOT appear in the canonical
  `frontend/src/api/types.ts`, asserts the script exits 1 and
  the offending model name appears in stderr. Pure
  subprocess + tmp_path; no side-channel mutation of the
  working tree or the real `PYTHON_SOURCES` tuple. Tests the
  script's drift-detection, not pre-commit-the-framework
  (the latter is upstream's responsibility).
- [ ] **D2** — `docs/standards/coding-standards.md` § 2
  extended with a one-line "Test files follow the same caps
  as the layer they live in (Python tests: 500/300; frontend
  test files: 500/300 — relaxed from the React component cap
  to acknowledge that test files don't carry render
  responsibilities). Test-file caps are explicit because §15
  applies the precedence rule across the whole document and
  the test-cap question was unresolved at DS04 close." This
  row makes DS05's whole-pass acceptance auditable against a
  named standard, not an implicit one.
- [ ] **D3** — `docs/journal/DS02.md` § "What was learned"
  updated to cross-reference DS05's Cluster D as the closing
  fix.

The full Step 8 "final five-gate green" still runs at close,
but Cluster D's hook means the gate has already fired before
every Cluster A/B/C commit lands locally — DS02's "CI catches
what local missed" pattern can't recur.

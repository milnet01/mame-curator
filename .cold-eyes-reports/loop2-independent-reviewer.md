# Cold-eyes review loop 2 — DS05 spec

**Reviewer:** independent loop-2 agent (no prior conversation context; loop 1 deliberately unread).
**Verdict:** REVISE.
**Findings:** 9 (2 HIGH + 4 MED + 3 LOW).

All citations verified against source-on-disk at HEAD (2026-05-15). Files
verified via `wc -l`, line ranges via `Read`, hook semantics via
`.pre-commit-config.yaml:55-62` (existing local hook pattern).

## Summary

The spec is competent and mostly accurate — line counts and section
markers in Clusters B and C check out exactly. Two HIGH issues need
fixing before Step 2: Cluster A's seam description conflates the
RetroArch `it.each` with the Updates banner test (different L122 vs
L140), and Cluster D's regression-test design (commit-a-broken-state-
then-clean-up) is a side-channel pattern that pollutes the local repo
and should be replaced by an in-process invocation of the script. Plus
a scope-creep concern: Cluster D was added in revision and arguably
belongs in its own FP## (Karpathy rule 9 push-back on complexity).

## Findings

### HIGH

- HIGH at `docs/specs/DS05.md:94` — Cluster A1's seam description
  ("covers the `it.each` Updates banner table + Filters/Picker
  chip-list tests…") conflates two distinct tests. The `it.each` at
  `frontend/src/pages/__tests__/SettingsPage.test.tsx:122` is for
  **RetroArch Setup-banner** (`/RetroArch: not configured|configured/`),
  not the Updates banner. The Updates banner `it` block is at
  `frontend/src/pages/__tests__/SettingsPage.test.tsx:140`
  (`renders the R36 update banner when updateInfo is provided`). The
  prose mis-attributes the `it.each` to Updates, which (a) misleads
  the Step-4 implementer about what's being moved and (b) hides the
  fact that the `it.each` produces **2** parameterized test entries
  in pytest/vitest `--collect-only` counts, which affects the
  "test_count_stable" gate. Fix: rewrite L94 prose to read "covers
  the RetroArch Setup-banner `it.each` table (L122-138, 2 parameterised
  cases) + the R36 update banner test (L140) + Filters/Picker chip-list
  tests + Updates/Interface dropdown render-and-patch pairs (through
  L349 — cards_per_row_hint patch ends at L349, not L341)."

- HIGH at `docs/specs/DS05.md:327` — Cluster D's regression-test
  design is unsound. "Commit a copy of a known-broken state … Clean
  up immediately after" is a side-channel pattern that (a) mutates
  the local repo state under the test, (b) requires the test to be
  ordered (a crash mid-test leaves a half-committed broken state),
  (c) doesn't work in CI (no commit to "clean up"), and (d) duplicates
  what pre-commit itself does. The script's contract is "exit 0 on
  parity, 1 on drift" — a fixture-based test is straightforward: in
  `tests/docs/test_check_api_types_sync_runs.py` (or extension),
  invoke `python3 tools/check_api_types_sync.py` via
  `subprocess.run` with a tmp_path-monkey-patched copy of
  `frontend/src/api/types.ts` that adds an unmirrored interface,
  assert exit code 1 and the expected diagnostic. No git plumbing,
  no commit. Fix: replace the "commit-and-revert" wording with a
  subprocess-based fixture test pattern that monkeypatches the
  inputs and asserts the script's exit code.

### MED

- MED at `docs/specs/DS05.md:288` — Cluster D scope creep. The spec
  opens (`docs/specs/DS05.md:5`) as a "refactor (test files only —
  no production-code changes)" sweep bundling three test-file
  splits. Cluster D modifies `.pre-commit-config.yaml` (not a test
  file), adds a new regression test, and updates `docs/journal/DS02.md`.
  This is a permanent infrastructure fix for a DS02 R2 lesson, not
  a test-file split. Karpathy global rule 9 (push back on
  complexity) and global rule 11 (stay in your lane) both argue
  for splitting Cluster D into its own one-line FP## ("wire
  check_api_types_sync.py into pre-commit"). The benefit of
  bundling (one close-phase audit instead of two) is small given
  Cluster D has zero overlap with A/B/C's test-moves; the cost is
  scope drift on a refactor labeled "test files only". Fix: either
  (a) re-scope the spec header at `docs/specs/DS05.md:5` to drop
  the "test files only" claim, **or** (b) extract Cluster D into a
  separate sibling spec.

- MED at `docs/specs/DS05.md:31` — Soft-cap framing on test files
  is asserted without authority. The spec says "the soft cap (300
  lines for test files, mirroring backend Python)" but
  `docs/standards/coding-standards.md:43` says "**Backend Python
  file size:** soft cap 300 / hard cap 500" — and at L44 says
  "**Frontend React component:** soft cap 200 / hard cap 350" —
  neither standard explicitly covers test files. The 300-line cap
  on `tests/parser/test_dat.py` (447 lines) is a spec invention
  ("mirroring backend Python"). This isn't unreasonable, but it
  should land in `coding-standards.md` first (or DS05 should
  explicitly add it under "Standards updated"), not be asserted as
  if already binding. Fix: add an explicit "this spec extends
  coding-standards § 2 file-size caps to cover `tests/**.py` at
  the same 300/500 thresholds as backend Python" note, OR cite a
  pre-existing standard if one exists at a path I missed.

- MED at `docs/specs/DS05.md:107` — Cluster A's "Combined, A1 + A2
  lift ~353 lines, leaving the main file at ~390 lines" arithmetic
  doesn't square with the shared `config` object. Spec at L120-127
  describes the shared `render` wrapper at
  `frontend/src/pages/__tests__/SettingsPage.test.tsx:14` but the
  L22-69 `const config: AppConfigResponse = {...}` (48 lines) is
  also shared across every test and is not addressed. Moving A1
  and A2 forces *either* duplicating those 48 lines into both new
  files (so each gets `config`) or extracting them to a sibling
  helper. The "≤500 lines" gate is comfortable so duplication is
  cheap, but the spec should name the decision. Fix: add a
  sentence at `docs/specs/DS05.md:127` explicitly stating that the
  `config: AppConfigResponse` fixture moves to the same shared
  location chosen for `render`.

- MED at `docs/specs/DS05.md:204` — Tests-first RED batch
  meaningfulness. The spec's three structural tests (file-size,
  test-count-stable, per-cluster grep) are useful but they don't
  RED *before* Step 4 in the conventional sense — they go RED
  only because the new test files don't exist yet (grep test
  fires) or because the old file is over cap (file-size test
  fires). They don't drive Step 4's design, only certify the
  end-state. This is fine for a mechanical refactor, but the
  spec should be explicit: "these are state-pinning tests, not
  TDD drivers — Step 4 is a mechanical move, not a design task."
  CLAUDE.md global rule 10 (reproduce-before-fix) doesn't apply
  here (no bug), so this is an honest framing nit, not a
  workflow violation. Fix: add a one-line clarifier at
  `docs/specs/DS05.md:206` distinguishing state-pin tests from
  TDD-driver tests.

### LOW

- LOW at `docs/specs/DS05.md:96` — Line range "L72-~341" is
  imprecise. Actual: A1's upper extent ends at L349 (close brace
  of the `cards_per_row_hint` patch test), not L341. L341-348 is
  the body of that test. The `~` qualifier acknowledges
  approximation, so this is a low-priority readability nit, but
  the implementer at Step 4 will want the exact number. Fix:
  change "L72-~341" to "L72-349" (precise).

- LOW at `docs/specs/DS05.md:325` — Hook config `types: [text]` is
  redundant when `always_run: true` is set. Per
  `.pre-commit-config.yaml:55-62`, the project's existing
  `pytest-fast` local hook uses `types: [python]` precisely
  because it does NOT set `always_run`. With `always_run: true`
  set, pre-commit runs the hook regardless of file-type filters.
  Functionally harmless but reads as cargo-culted. Fix: drop
  `types: [text]` from the Cluster D acceptance, OR drop
  `always_run: true` and keep `types: [text]` (latter is fine
  because the script's drift-detection wants to fire on any
  text-file change, including the TS side).

- LOW at `docs/specs/DS05.md:189` — Cluster C's 100-line fallback
  threshold ("neither file drops below 100 lines of net test
  bodies") is under-specified. "Net test bodies" excludes imports,
  fixtures, and section markers — but the spec doesn't define how
  to count. The implementer at Step 4 will need a rule
  ("`grep -c '^def test_'` ≥ 4" is a cleaner proxy). Fix: replace
  the "100 lines of net test bodies" rule with a count-based one
  ("each resulting file holds ≥ 4 `def test_…` declarations") so
  Step 4 is mechanical.

## Smallest delta to lift REVISE → APPROVE

1. Fix the two HIGH items: rewrite A1 prose to correctly attribute
   the `it.each` (and extend its line range to L349); replace
   Cluster D's "commit-and-revert" regression test with a
   subprocess-and-tmp-path-fixture pattern.
2. Resolve the MED scope question: either re-frame the spec header
   to drop "test files only" or extract Cluster D into a sibling
   FP##.
3. Add the soft-cap-on-test-files authority note (one sentence).
4. Name the shared `config` fixture's destination (one sentence).

Once those four are in, the spec is ready for user sign-off and
Step 2 (plan inlining). Clusters B and C in isolation are clean and
mechanical — most of the friction is in A's prose and D's design.

<!-- mame-roadmap-format: 1 -->

# MAME Curator — Roadmap

> **What this is.** A forward-looking queue of upcoming work for the
> MAME Curator project. Shipped work lives in
> [`CHANGELOG.md`](CHANGELOG.md); this file shows only what's next.
>
> **For non-technical readers (vibe coders welcome).** Each item has a
> `Layman:` line — one plain-English sentence describing what the
> change does for you, the user. You don't need to read past it.
>
> **Status emojis.** ✅ shipped · 🚧 in progress · 📋 planned ·
> 💭 considered (scope or feasibility still being thought through).
> The position of an item in a section is its priority (top first).
> The `[mame-curator-NNNN]` ID after the emoji is the item's identity
> — it never changes, even if the item moves or is reworded.
>
> **Theme emojis.** Each `###` section header carries one:
> 🎨 features · 🐛 bug fixes · ⚡ performance · 🔒 security ·
> 🧹 cleanup / debt · 🧰 dev experience · 📚 documentation ·
> 📦 packaging · 🔌 plugins / extensions · 🖥 platform ·
> 🔍 audit / review fold-ins.
>
> **Glance counts at a section heading** (the Ants Terminal viewer
> renders these automatically): `✅ N 🚧 N 📋 N 💭 N`.

---

## 1.3.0 — Hardening + housekeeping (target: 2026-Q2)

**Theme:** ship the deferred Tier 3 structural-debt sweep and bring
every dependency to its latest stable release. No user-visible
features; the goal is a cleaner foundation before the next feature
wave lands.

### 🧹 Cleanup / debt

- ✅ [mame-curator-1033] **DS04 — Test-suite quality sweep.**
  Triaged fold-in from the 5-lane test-suite audit 2026-05-15 on
  commit `06fe3b8` (post-FP27). 51 sub-fixes across three tiers:
  Tier 1 (14 items) clears dead-spec coverage (FP25-C rollback
  tests contradicting `copy/spec.md:260`), vitest prototype /
  global-state pollution leaks, unnecessary I/O (50k-line JSONL
  twice, 6 MiB string allocations, 2.5 s Playwright sleep,
  hardcoded `/tmp/` path with `# noqa: S108`), parametrize wins,
  one mis-located test file. Tier 2 (19 items) hoists `_machine`,
  `_plan`, `renderWithClient`, and a 47-line `config` fixture into
  shared conftest / helpers, deletes FP##-named duplicate tests
  subsumed by canonical module coverage, and fixes a Hypothesis
  empty-strategy. Tier 3 (13 items) drops redundant
  `afterEach(() => cleanup())` under auto-cleanup-on, fixes a11y
  query patterns, tags brittle tracemalloc tests `@pytest.mark.slow`.
  Layman: A spring-clean of the project's own tests — removing
  ones that test code that no longer exists, deleting duplicates,
  and pulling repeated boilerplate into shared helpers so future
  test-writing is faster. Nothing changes for you as a user.
  Kind: refactor.
  Lanes: backend tests, frontend tests, e2e tests.
  Source: test-audit-2026-05-15 (5 lanes: parser+filter / copy /
  api+media+downloads / frontend components+hooks+lib / frontend
  pages+e2e+strings).

- ✅ [mame-curator-1037] **DS05 — Test-file seam-split sweep.**
  Closed 2026-05-16 (`738b418..d9c6817`). 7 commits: opener +
  RED batch + 4 cluster splits + R1 closing-review fold-in.
  Spec converged on cold-eyes loop 2 (16 findings total folded);
  closing `/audit` clean (10/10 gates); closing `/indie-review`
  5/5 lanes PASS with 2 LOW spec-history nits. 605 backend +
  301 frontend tests green at close. See
  [`CHANGELOG.md`](CHANGELOG.md) for the per-cluster breakdown.
  Bundles three conditional follow-ups from DS04 (1034 / 1035 /
  1036) into a single sweep per the FP27 / FP28 / DS02 precedent
  of consolidating similar work. Four clusters at Step 1:
  Cluster A splits `SettingsPage.test.tsx` (742 → ≤500) into
  three files along an L72-L349 + L520-602 seam; Cluster B splits
  `tests/copy/test_runner.py` (526 → ≤500) into two files along
  the existing `# --- Section ---` headers; Cluster C splits
  `tests/parser/test_dat.py` (447 → ≤300) into three files along
  basic / security / validation; Cluster D wires
  `tools/check_api_types_sync.py` into `.pre-commit-config.yaml`
  as a permanent fix for the DS02 R2 lesson ("CI-only gate caught
  what local missed"), plus a one-line `coding-standards.md` § 2
  extension stating test-file caps explicitly. Two cold-eyes
  review loops converged on the current spec (loop 1: 3 HIGH +
  3 MED + 1 LOW folded; loop 2: 2 HIGH + 4 MED + 3 LOW folded).
  Layman: A tidy-up of three oversized test files (splitting
  them into smaller themed files) plus a permanent fix that
  prevents the next "CI catches what local missed" embarrassment.
  Nothing changes for you as a user; the same tests still run
  after, just organised across more files.
  Kind: refactor.
  Lanes: backend tests, frontend tests, build.
  Source: test-audit-2026-05-15 (1034/1035/1036) +
  DS02-R2-post-mortem (Cluster D).

- ✅ [mame-curator-1034] **`SettingsPage.test.tsx` seam-split** —
  closed in DS05 Cluster A (2026-05-16).

- ✅ [mame-curator-1035] **`tests/copy/test_runner.py` seam-split** —
  closed in DS05 Cluster B (2026-05-16).

- ✅ [mame-curator-1036] **`tests/parser/test_dat.py` split** —
  closed in DS05 Cluster C (2026-05-16).

- ✅ [mame-curator-1021] **DS02 — Tier 3 structural debt sweep.**
  Closed 2026-05-15 (`c0a6ad6..eb000e4`). 18 sub-bullets across 7
  clusters + 3 closing-review corrections (Cluster R1) shipped across
  4 commits. Spec converged on cold-eyes loop 2 (0 residual findings);
  583 backend + 301 frontend tests green at close. See
  [`CHANGELOG.md`](CHANGELOG.md) for the per-bullet breakdown.
  Sweeps the Tier 3 fold-in from the 2026-05-04 multi-agent review:
  five files over the hard-cap split into smaller modules, hardcoded
  UI strings pulled into `strings.ts`, accessibility polish
  (skip-to-main link, `aria-label`s on landmarks, `aria-live` on
  loading states), Settings-tab URL state via `useSearchParams`, and
  documentation drift in `parser/spec.md` + `copy/spec.md`.
  Scope expanded 2026-05-14 with the new sweep's Tier 3 additions
  (roving-tabindex `.focus()`, duplicate `<h1>` on Help page,
  markdown heading-level remap, `<article>` / `<aside>` landmark
  labels, `revision_key_of` memoization in picker, `total_bytes`
  cache in `WorldState`, `AlternativesDrawer` + `CopyModal` inside
  `ErrorBoundary`, `ConfirmationDialog` render-time throw → dev
  assert, `NotesEditor` save-on-blur cleanup) plus the matching
  `/debt-sweep` mechanical drift (16 sites lacking inline
  `# type: ignore` / `# noqa` reasons per coding-standards § 1,
  stale `CHANGELOG.md` versioning-policy paragraph, frontend
  `package.json` version lockstep break vs `pyproject.toml`).
  Layman: A tidy-up of code that's grown messy enough to slow future
  features down — splitting oversized files, removing dead branches,
  pulling hardcoded UI strings into the central translations file.
  Nothing changes for you as a user.
  Kind: refactor.
  Lanes: backend, frontend, docs.
  Source: indie-review-2026-05-04 Tier 3 + indie-review-2026-05-14
  Tier 3 + debt-sweep-2026-05-14 mechanical drift.

- ✅ [mame-curator-1025] **DS03 — Dependency freshness sweep.**
  Closed 2026-05-16 (`1916cd7..f9be074`). 8 clusters + R1 closing-
  review fold-in across 10 commits. Python pins (Cluster A) +
  frontend pins (B) + GitHub Actions GITLEAKS_VERSION (C) +
  pre-commit hook revs with cross-pin coupling test (D) +
  engines.node 20→24 LTS (E) + transitive lockfile refresh
  including opportunistic mypy 1→2 (F) + new frontend-lint-types-
  test CI job (G) + pnpm→npm spec corrections (H) + R1 (7
  closing-review fixes). Two new docs-tests
  (`test_dep_pin_coupling.py`, `test_no_pre_release_pins.py`)
  CI-enforce the cross-pin invariants. Deferred to follow-up
  phases: pydantic v3, fastapi 1.0, react 20, vite 9, upload/
  download-artifact v5+, gh-release v3, pre-commit-hooks v6,
  @types/node v25 — all major-version breakers per the spec's
  non-breaking-only rule.
  Walks every entry in `pyproject.toml`, `frontend/package.json`,
  and `.github/workflows/ci.yml`, comparing the pinned version
  against the current latest stable. Ships a single coordinated
  bump commit so the CI matrix re-runs once for the whole set
  instead of dep-by-dep.
  Layman: A one-time pass to make sure every library the project
  depends on is on its latest stable release. Catches things like
  "the version of React we're using is six months old now" without
  waiting for individual features to surface them.
  Kind: chore.
  Lanes: deps, build, ci.
  Source: user-2026-05-08 ("ensure that we are on the latest version
  of all dependencies"); reinforces global rule § 5.

- 📋 [mame-curator-1076] **Review the `macos-latest` CI runner pin ahead of the macOS 26 migration.**
  CI annotation on run 28463638134 (2026-06-30): "The macos-latest label will migrate to macOS 26 beginning June 15, 2026" (actions/runner-images#14167). The `macos-latest` matrix leg in `.github/workflows/*` will roll to macOS 26 automatically on that date. Before 2026-06-15, confirm the Python/uv toolchain + test suite still green on macOS 26 (or pin to `macos-15` deliberately with a reason per global rule 5a). Low priority — auto-migration, not a break.
  **Layman:** GitHub is changing what "latest macOS" means for our test runner on 15 June 2026 — check our setup still works before then.
  Kind: chore.
  Lanes: ci.
  Source: ci-annotation-2026-06-30.

- ✅ [mame-curator-1077] **Split `LibraryPage.tsx` (579 lines) under the frontend file-size hard cap.**
  `frontend/src/pages/LibraryPage.tsx` is 579 lines, over the frontend file-size hard cap (`coding-standards.md` §2). It is NOT in the DS02 acknowledged-exceptions list (those are `copy/runner.py` 540, `strings_internal.ts` 646, `api/schemas.ts` 591). The breach predates P14 — `docs/specs/P14.md` § "Module layout" called it out as a follow-up concern ("extract a small `LibraryHeader.tsx` if convenient") and not a P14 blocker. Likely split lines: the header/progress-chip + walkthrough-toggle block into `LibraryHeader.tsx`, and/or the review-state + cart wiring into a hook. Note: `coding-standards.md` §2 and `docs/specs/P14.md` disagree on the exact frontend cap (350 vs the 500 DS02 treats as hard) — confirm the canonical number when picking this up.
  **Layman:** One of the library screen's source files has grown too big and should be broken into smaller pieces for readability.
  Kind: refactor.
  Lanes: frontend.
  Source: in-session-2026-06-30 (surfaced during 1060/1061 P14 docs work).
  Resolved (2026-06-30): split LibraryPage.tsx 579→314 lines, under the coding-standards §2 frontend component hard cap (350). The §15-precedence-authoritative cap is 350 (the bullet's 350-vs-500 doubt resolved in favour of coding-standards.md). Non-render logic extracted to new pages/useLibraryController.ts (318 lines) + pure pages/libraryPageHelpers.ts (61 lines); all JSX kept in the page so the source-text structural tests (LibraryPage_error_boundary, landmark_labels) keep asserting the rendered shape. Behaviour-preserving — 323 frontend tests green, tsc -b + eslint clean.

- ✅ [mame-curator-1078] **Surface the "review state isn't snapshotted" caveat in the Snapshots UI.**
  `docs/specs/P14.md` § "Snapshot policy" specified a one-line caption (`settings.snapshots.stateExclusionNote`) noting that `data/state.yaml` is not snapshotted, so review-state changes cannot be rolled back via Settings → Snapshots (recovery is `activity.jsonl` replay only). That caption was never shipped — `frontend/src/strings_internal.ts` has no such string and `SnapshotsTab.tsx` shows no review-state caveat. Add the caption so the exclusion is visible to the user. Low priority (behavioural gap is documented, just not surfaced in-app).
  **Layman:** The app saves restore-points for your settings but not for your per-game review marks. The screen never tells you that, so add a one-line note.
  Kind: fix.
  Lanes: frontend.
  Source: in-session-2026-06-30 (surfaced by cold-eyes on review_state_spec.md).
  Resolved (2026-06-30): added settings.snapshotsStateExclusionNote string + rendered it as a caption in SnapshotsTab.tsx (both empty + populated states). Text per P14 spec §875. Flat key name (snapshotsStateExclusionNote) to match the existing flat snapshotsXxx convention, not the spec's dotted settings.snapshots.stateExclusionNote. +2 vitest cases.

### 🧪 Test Audit 2026-05-20

Framework: pytest (backend) + vitest (frontend) · Files scanned: 167
(113 backend + 54 frontend = 50 vitest + 4 Playwright) · Dimensions: all 18
· Raw findings: ~33 · Fixed inline: 14 (all count-neutral
correctness / assertion-quality / slow-marker fixes + 1 pre-existing red
test) · Deferred below: 1065–1070 (grouped) · Suite green at fold-in:
761 backend + 320 frontend tests at 87.51 % coverage. Several lower-severity
nits re-confirmed already-open FP31 items and were **not** re-filed:
`_seed_existing_playlist` dedup ([mame-curator-1054] c), world-lock
parametrize ([mame-curator-1055] a), `test_routes_copy.py:79` vacuous
pass ([mame-curator-1052]), `fireEvent`→`userEvent`
([mame-curator-1048]), `@pytest.mark.asyncio` cleanup
([mame-curator-1050]), `_url_cache` white-box ([mame-curator-1055] i),
retroarch-not-executable coverage ([mame-curator-1055] b).

**Pre-existing failure fixed inline (no roadmap entry):** `main` was red at
HEAD — `tests/docs/test_arch_diagrams.py::test_claude_md_architecture_diagram_matches_source_tree`
failed because CLAUDE.md's architecture diagram gained a `frontend/` row
(cold-eyes docs sweep, commit `7ff03ec`) but the CLAUDE.md arch test lacked
the `frontend/` exception its `README.md` sibling already carried. Root-caused
by mirroring the README exception — a test-asymmetry defect (dimensions 1 +
10), itself a legitimate test-audit catch.

**Deferred to roadmap (this sub-section):**

- ✅ [mame-curator-1065] **Test-audit 2026-05-20 — dedup nits beyond
  [mame-curator-1054].** (a) `tests/api/test_fp21_fixes.py` — extract a
  `_make_job(tmp_path, history=0)` helper for the byte-identical
  CopyPlan+Job construction (chunk c-001). (b)
  `frontend/.../CartBar.test.tsx` — extract `renderCartBar(overrides)`;
  5 tests inline the full 8-prop render block (chunk fc-002). (c)
  `frontend/.../CopyModal.test.tsx` — extract `openAbortPrompt()`; 3
  abort-path tests repeat render+cancel-click (chunk fc-002). (d)
  `frontend/.../StatsPage.test.tsx` — hoist the 3 identical renders into
  `beforeEach` (chunk fc-005). (e) `frontend/.../ActivityPage.test.tsx:50`
  — use the file's own `renderAt` helper instead of an inline render
  (chunk fc-005). (f) `frontend/.../LibraryPage_error_boundary.test.ts:39`
  — extract `findLastJsxOpenTag()`; the regex+while-loop is copy-pasted
  across both `it` blocks (chunk fc-001). (g)
  `tests/updates/test_snaps.py:154,175` — extract the shared
  overwrite/force setup. Kind: refactor. Lanes: backend tests, frontend
  tests. Source: test-audit-2026-05-20.
  Resolved (2026-06-10): helpers extracted — `_make_job()` (a);
  `renderCartBar()`/`cartBarProps()` (b); `openAbortPrompt()` (c);
  `beforeEach` render (d); `renderAt()` reuse (e); `findLastJsxOpenTag()`
  (f); (g) folded into 1066(b)'s parametrized snaps test. 764 backend +
  320 frontend tests green; ruff/format/mypy/bandit/eslint/tsc clean.

- ✅ [mame-curator-1066] **Test-audit 2026-05-20 — verbosity / parametrize
  polish beyond [mame-curator-1055] (a).** (a)
  `tests/api/test_routes_copy.py:36` — parametrize the r22/r23/r24 shape
  tests (chunk c-002). (b) `tests/updates/test_snaps.py` — parametrize the
  `force=False/True` overwrite pair (chunk c-010). (c)
  `frontend/.../useValidateCart.test.tsx:41-56` — `it.each` for the
  all-existing / all-missing pair (chunk fc-004). (d)
  `tests/filter/test_drops.py:150` — split the 4-predicate
  `…_mechanical_false_keeps_them` test so a failure names the offending
  predicate (chunk c-006). Kind: refactor. Lanes: backend tests, frontend
  tests. Source: test-audit-2026-05-20.
  Resolved (2026-06-10): parametrized — r22/r23/r24 →
  `test_route_r22_r24_action_job_not_found` (a); snaps force pair →
  `test_refresh_snaps_overwrite_honours_force`, also closing 1065(g) (b);
  useValidateCart all-existing/all-missing → `it.each` (c); test_drops
  4-predicate split into per-rule parametrize ids (d). DS05 count pins
  bumped 611→608 / 305→303 with cited reasons.

- ✅ [mame-curator-1067] **Test-audit 2026-05-20 — coverage gaps beyond
  [mame-curator-1053].** (a) `tests/filter/test_drops.py` — only
  `drop_bios_devices_mechanical` has a flag-disabled (`=False`) "keeps
  them" test; add the equivalents for `drop_mature`,
  `drop_preliminary_emulation`, `drop_chd_required`,
  `drop_japanese_only_text` (chunk c-006). (b)
  `tests/updates/test_snaps.py:214` — add an explicit ZIP path-traversal
  test (`"../evil.png"` rejected, nothing escapes dest); the SUT guard
  exists but is never directly asserted (chunk c-010). Kind: test. Lanes:
  backend tests. Source: test-audit-2026-05-20.
  Resolved (2026-06-10): (a) added `test_togglable_drop_flags_false_keeps_them` in test_drops.py — flag-disabled `=False` keeps-them locks for drop_mature / drop_preliminary_emulation / drop_chd_required / drop_japanese_only_text (every togglable predicate now has one). (b) added `test_refresh_snaps_rejects_zip_path_traversal` in test_snaps.py — `../evil.png` skipped, files_extracted==1, nothing escapes dest; mutation-checked (guard off → 2 extracted → test fails). DS05 pin 608→610.

- ✅ [mame-curator-1068] **Test-audit 2026-05-20 — reliability /
  assertion hardening.** (a) `tests/api/test_fp09_fixes.py:247`
  (`test_b7_fs_list_parent_filtered_against_allowlist`) — the assertion is
  vacuous when `body["parent"] is None`; a regression that always returns
  `parent=null` passes silently. Needs a deterministic allowlist setup so
  the "parent outside allowlist → None" path is asserted exactly (the
  naive `assert is None` is environment-dependent on `$HOME`'s parent;
  chunk c-001). (b) `tests/media/test_sources.py:68` + `:242`
  (`*_prepare_is_noop`) — prove "no HTTP attempted" via `respx.mock` with
  no registered routes (`assert_all_called`) instead of relying on a real
  `ConnectError` propagating; a silently-swallowed network error currently
  still passes (chunk c-008). Kind: fix. Lanes: backend tests. Source:
  test-audit-2026-05-20.
  Resolved (2026-06-10): (a) `test_b7_fs_list_parent_filtered_against_allowlist` rewritten deterministically via the `fake_home` allowlist root — lists a subdir (parent exposed) then the root (parent=None, up escapes sandbox); no longer vacuous on the parent-is-None case. (b) both `*_prepare_is_noop` tests now mount a catch-all respx route returning 500 and assert `not catch_all.called` — a swallowed network call flips that flag (verified respx trips on a real GET). Count-neutral.

- ✅ [mame-curator-1069] **Test-audit 2026-05-20 — fixture-scope perf in
  `tests/api/conftest.py:27-66`.** Seven read-only static-file `Path`
  fixtures (`mini_dat`, `listxml`, `catver_ini`, `languages_ini`,
  `bestgames_ini`, `mature_ini`, `series_ini`) are function-scoped and
  rebuilt for every api test; promote to `scope="session"` (they are
  never mutated). Kind: perf. Lanes: backend tests. Source:
  test-audit-2026-05-20 chunk c-001.
  Resolved (2026-06-10): the 7 read-only static-file Path fixtures (mini_dat, listxml, catver_ini, languages_ini, bestgames_ini, mature_ini, series_ini) in tests/api/conftest.py promoted to scope="session" — never mutated, so built once for the api suite. Count-neutral; full suite 769 green @ 87.51%.

- ✅ [mame-curator-1070] **Test-audit 2026-05-20 — ruff `# noqa`
  false-directive noise in `tests/media/test_cache.py:20`.** The FP31
  hoist comment contains the literal token `# noqa: E402` in prose
  (describing the old import); ruff parses it as a malformed `# noqa`
  directive and emits a warning on every `ruff check` run (does not fail
  the gate). Rephrase so the token is not directive-shaped (e.g. drop the
  leading `#`). Kind: doc-fix. Lanes: backend tests. Source:
  test-audit-2026-05-20 (discovered during the closing gate run).
  Note (2026-06-10): a sibling instance in `tests/api/test_fp21_fixes.py`
  (a prose `# noqa: S108`) was surfaced by the 1065/1066 closing gate and
  fixed in passing — reworded to name "a bandit S108 waiver" with no
  directive-shaped token. This item (`test_cache.py:20`, `# noqa: E402`)
  remains open.
  Resolved (2026-06-10): reworded the prose `# noqa: E402` in test_cache.py:20 to "an E402 import-not-at-top waiver" (no directive-shaped token). `ruff check --no-cache` now emits no "Invalid `# noqa` directive" warning (the prior runs were cache-masked; --no-cache surfaced it).

- ✅ [mame-curator-1071] **CI — GitHub Actions Node 20 deprecation +
  runner redirect.** The closing CI run (`26187276453`) annotated:
  `actions/upload-artifact@v4` runs on Node.js 20 — GitHub forces Node 24
  from 2026-06-02 and removes Node 20 on 2026-09-16; bump to a
  Node-24-compatible release (`@v5`) or set
  `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true`. Also `windows-latest`
  redirects to `windows-2025-vs2026` by 2026-06-15 (informational —
  pin the image if reproducibility matters). Not a test-quality finding;
  surfaced while watching this sweep's CI. Kind: chore. Lanes: ci.
  Source: test-audit-2026-05-20 closing CI run.
  Resolved (2026-06-10, dep-freshness sweep): `actions/upload-artifact`
  @v4 → @v7 (Node 24) in both ci.yml + release.yml; `download-artifact`
  @v4 → @v8; `softprops/action-gh-release` @v2 → @v3; `astral-sh/setup-uv`
  @v8.1.0 → @v8.2.0. All v3+/v7+/v8 majors are Node-20→24 runtime bumps
  only (no input changes; ubuntu-latest already supports Node 24 + runner
  ≥2.327.1). `windows-latest` left floating by design — pinning to
  `windows-2025-vs2026` is a maintenance burden the informational redirect
  doesn't warrant for this project.

- ✅ [mame-curator-1072] **Frontend `npm run build` (`tsc -b`) is broken —
  3 pre-existing type errors in `src/test/` not caught by CI.** Discovered
  during the 2026-06-10 dep-freshness sweep; **proven pre-existing** (the
  identical 3 errors reproduce on the pre-bump lockfile — NOT caused by the
  dep bump). CI's frontend type gate is `npx tsc --noEmit`, but
  `frontend/tsconfig.json` is a solution file (`files: []` + project
  references), so `tsc --noEmit` type-checks **zero** files — the real
  build (`tsc -b`, via `npm run build`) is the only thing that follows the
  references into `src/test/**`, and CI never runs it. Errors: (a)
  `src/test/renderWithClient.tsx:15,45` — bare global `JSX.Element` doesn't
  resolve under the build tsconfig (use `ReactElement` / `React.JSX.Element`
  / `import type { JSX } from 'react'`); (b) `src/test/handlers.ts:31` —
  MSW `JsonBodyType` rejects an `unknown` arg (needs a cast/narrowing).
  Consequence: `frontend/dist/` (the committed, API-served bundle) **cannot
  be regenerated** until this is fixed, so the 2026-06-10 frontend dep bumps
  (React 19.2.7, Vite 8.0.16, etc.) won't reach the served bundle yet. Fix
  also wants a real CI build gate (`npm run build` or `tsc -b`) so this
  class can't recur silently. Kind: fix. Lanes: frontend, ci. Source:
  dep-freshness sweep 2026-06-10.
  Resolved (2026-06-10): (a) `renderWithClient.tsx` — global `JSX.Element`
  → `ReactElement` (imported from react); (b) `handlers.ts` — helper param
  `unknown` → MSW `JsonBodyType` so `HttpResponse.json()` accepts it.
  CI gate added: the frontend job's vacuous `npx tsc --noEmit` step (root
  tsconfig is a `files: []` solution file → checks zero files) replaced
  with `npm run build` (`tsc -b` + vite) in BOTH ci.yml + release.yml, so
  a build-only type error now fails CI. `frontend/dist/` regenerated
  against the 2026-06-10 bumped deps (React 19.2.7 / Vite 8.0.16). Build,
  eslint, vitest (320) all green.

### 🧪 Test Audit 2026-05-18 (FP31 — second sweep)

Framework: pytest (backend) + vitest (frontend) · Files scanned: 163
(113 backend + 50 frontend) · Dimensions: all 18 · Raw findings: 106 ·
Actionable after triage: ~40 (6 HIGH fixed inline, 18 MEDIUM fixed
inline, 1 reverted SUT-design item below, ~14 LOW + 3 INFO deferred as
follow-ups below) · Suite green at fold-in: 758 backend + 320 frontend
tests at 87.51 % coverage. Allowlist gained 1 new entry (014) for the
test_runner_lifecycle.py negative-wait pattern (same shape as 008).

**Fixed inline (no roadmap entry needed) — HIGH:**

- ✅ `tests/api/test_fp09_fixes.py:362` — wrapped the SSE history-replay
  `asyncio.run(_drive())` in `asyncio.wait_for(timeout=15)`. Without this
  bound, a regression that breaks `history_replay` or the terminal-state
  sentinel would hang the suite forever waiting for a `job_finished`
  event that never lands.
- ✅ `tests/api/test_fp09_fixes.py:64` — tightened the corrupt-report
  assertion from `status_code in (404, 502)` to `== 502` with a typed
  code check. The 404 fallback masked the actual contract (corrupt
  content must surface as `CopyReportCorruptError`, not "missing file").
- ✅ `tests/copy/test_fp28_recyclebin_lock.py:116-117` — added 10-second
  timeouts + `is_alive()` checks to the dual-worker thread joins. A
  regression that leaves the O_EXCL lockfile held would otherwise hang
  the test runner indefinitely (threads were not daemons; joins were
  unbounded).
- ✅ `tests/media/test_cache.py:275` — hoisted the late `from
  mame_curator.media.cache import …` (behind `# noqa: E402`) to the
  top, alongside the public `from mame_curator.media import …` imports
  used by the rest of the file. Added an `is`-identity assert so a
  regression where the public re-export silently diverges from the
  internal module fails loudly. Previously: a public re-export break
  would have left half the file's tests silently passing.
- ✅ `frontend/src/hooks/__tests__/useValidateCart.test.tsx` — hoisted
  the byte-for-byte MSW handler (3 verbatim copies) into a single
  `beforeEach`. Also added a 4th test that exercises the
  500-error path (`isError flips true when the server returns 500`),
  closing the chunk fc-002 coverage gap.
- ✅ `frontend/src/hooks/__tests__/useCart.test.tsx` — migrated the
  two `Storage.prototype.setItem` failure tests from direct prototype
  reassignment in `try/finally` to `vi.spyOn(...).mockImplementation(...)`
  + a file-level `afterEach(() => vi.restoreAllMocks())`. Storage
  prototype no longer poisonable across tests.

**Fixed inline (no roadmap entry needed) — MEDIUM:**

- ✅ `test_fp21_fixes.py:60-67` — staggered the 500 progress-event
  timestamps by `timedelta(microseconds=i)` so `heapq.merge` has
  unambiguous ordering (chunk c-001 MED).
- ✅ `test_fp28_media_proxy_headers.py:38` — flipped `respx.mock(
  assert_all_called=True)` so a regression that bypasses the upstream
  surfaces as "registered mock not called" (chunk c-001 MED).
- ✅ `test_fp25_world_lock.py` — added `releases == acquires` assertions
  to the four route tests that previously only checked `acquires >= 1`
  (chunk c-001 MED). A route that acquires but never releases
  (production deadlock) now fails the test.
- ✅ `test_review_state_parity.py:23-24` — guarded the `/api/state`
  setup POSTs with 200-checks so a regression returning 404/422 from
  state-set doesn't collapse both predicates to "all pending" and
  trivially pass (chunk c-001 MED).
- ✅ `test_routes_config.py:38` — dropped the `or snaps.get("snapshots")`
  fallback (silently masking schema drift), tightened to `len(items) >= 1`
  (chunk c-002 MED).
- ✅ `test_sse.py:23` — added `@pytest.mark.slow` to the 18 MiB-I/O SSE
  end-to-end test (chunk c-002 MED).
- ✅ `test_routes_fs.py:96-104` — added an actual HTTP assertion to the
  symlink-traversal sandbox case (chunk c-002 MED — the case had been
  set up but never executed).
- ✅ `test_routes_fs.py:107` — removed unused `monkeypatch:
  pytest.MonkeyPatch` parameter from `test_fs_roots_per_platform`
  (chunk c-002 LOW).
- ✅ `test_world_state_bytes_cache.py:51-53` — replaced
  `hasattr(__getitem__) + hasattr(__iter__)` with `isinstance(bbm,
  Mapping)` (chunk c-003 MED — a `list` satisfied the old shape check).
- ✅ `test_filter_snapshot.py:54` — added an early `return` after the
  `UPDATE_SNAPSHOTS=1` write so update mode doesn't trivially assert
  the just-written snapshot equals itself (chunk c-007 MED).
- ✅ `test_filter/conftest.py`-anchored `OVER_CAP` — hoisted the
  in-body `from tests.filter.conftest import OVER_CAP` to module level
  in `test_overrides.py:8` + `test_sessions.py:8`; dropped the
  underscore alias in `test_io.py:15` (chunk c-007 LOW/MED).
- ✅ `test_listxml.py` + `test_listxml_cloneof.py` — folded the duplicated
  `test_missing_file_raises` + `test_malformed_xml_raises` standalones
  into a single parametrized pair in `test_listxml.py` covering all
  three `parse_listxml_*` functions; removed both standalones from
  `test_listxml_cloneof.py`; added a `match="parse"` guard on the
  malformed-XML case (chunk c-009 MED + LOW).
- ✅ `test_smoke.py:8` — removed the tautological `assert mame_curator
  is not None`; collapsed into the `test_version_is_set` test whose
  attribute lookup already proves importability (chunk c-009 LOW).
- ✅ `test_parser/test_cli_parse.py:28-37` — removed
  `test_parse_command_unknown_path_returns_nonzero` (byte-for-byte
  duplicate of `test_runtime_error_returns_exit_code_1_not_2`; chunk
  c-008 MED).
- ✅ `test_parser/test_fp28_license_re.py` — stripped the three
  parametrize cases already covered verbatim in `test_manufacturer.py`;
  kept only the FP28 nested-parens regression-lock and the closest-shape
  negative control (chunk c-009 MED).
- ✅ `test_filter/test_drops.py` — added
  `test_year_none_survives_year_range_filter` to close the year-None
  guard coverage gap (chunk c-006 LOW).
- ✅ `test_docs/test_no_pre_release_pins.py:67-73` — `FileNotFoundError`
  caught per-file inside `_gitleaks_env_pins` so a stripped CI image
  missing one workflow still reports the other file's pin (chunk c-006
  LOW).
- ✅ `test_docs/test_version_lockstep.py:34,41` — added message args to
  the `isinstance(version, str)` assertions naming the file + observed
  type (chunk c-006 LOW).
- ✅ `tests/copy/_runner_helpers._machine` — moved as the canonical
  `_machine` for `test_fp01_fixes.py` / `test_fp02_fixes.py` /
  `test_preflight.py`; deleted the three byte-for-byte duplicates
  (chunks c-004 / c-005 MED).
- ✅ `tests/filter/test_fp28_runner_logger.py` — replaced 19-line
  `_make_machine` builder with conftest `m(**kwargs)` helper (chunk
  c-006 LOW).
- ✅ `tests/filter/test_fp28_apply_session_error.py:48` — hoisted
  in-body `make_empty_ctx` import to module top (chunk c-006 LOW).
- ✅ `tests/copy/test_fp28_recyclebin_lock.py:65` — `monkeypatch: object`
  → `monkeypatch: pytest.MonkeyPatch`; removed accompanying
  `type: ignore[attr-defined]` (chunk c-004 MED).
- ✅ `tests/updates/test_snaps.py:109` — replaced set-membership
  assertion with per-file equality so a loop-variable-capture
  regression that wrote the same bytes to every output path is caught
  (chunk c-010 MED).
- ✅ `frontend/src/pages/__tests__/SessionsPage.test.tsx:38` —
  `toBeGreaterThan(0)` → `toHaveLength(1)` for the Active badge
  (chunk fc-003 MED).
- ✅ `frontend/src/components/library/__tests__/LibraryGrid.test.tsx:103-106`
  — `expect(spacer).toBeTruthy()` → typed `querySelector<HTMLElement>` +
  `.toBeInTheDocument()`; removed two `as HTMLElement` casts (chunk
  fc-004 MED).
- ✅ `frontend/src/hooks/__tests__/useCopySession.test.tsx:99` — removed
  redundant `cleanup()` in `afterEach`; vitest `globals: true` auto-cleans
  via RTL (chunk fc-002 MED).
- ✅ `frontend/src/hooks/__tests__/useCopySession.test.tsx:300-310` —
  emit `job_started` before sending the malformed payload so the
  "state is running; bad message must not crash it back to null"
  precondition is explicit (chunk fc-002 MED).

**Reverted MEDIUM (deferred to roadmap as separate item):**

- ⚠ `FsBrowser.test.tsx open=false` request-spy: surfaced that the
  component fires its `useQuery` handlers on mount regardless of `open`.
  That's a SUT design question (prefetch on close vs `enabled: open`
  gating), not a test-only fix — see [mame-curator-1047] below.

**Deferred to roadmap (this sub-section):**

- ✅ [mame-curator-1046] **FP31 follow-up — file-size cap splits in
  `tests/media/test_sources.py` + `tests/copy/test_fp01_fixes.py`.**
  `tests/media/test_sources.py` is 546 lines (over the 500-line hard
  cap) — covers four independent source implementations (Libretro,
  ProgettoSnaps, ArcadeDB, Wikipedia) separated by section comments.
  `tests/copy/test_fp01_fixes.py` is 424 lines (over the 300 soft cap)
  — 7 logical groups. Both need DS05-style seam splits; tests/sources
  extract `_machine()` + `_make_unbounded_limiter()` to a new
  `tests/media/conftest.py` during the split.
  Kind: refactor. Lanes: backend tests. Source: test-audit-2026-05-18
  FP31 chunks c-004 + c-008 (HIGH for c-008's hard-cap violation).
  Resolved (2026-06-10): split `test_sources.py` (554 lines → 4 per-source
  files `test_sources_{libretro,progettosnaps,arcadedb,wikipedia}.py`, each
  <190) + new `tests/media/conftest.py` holding `_machine` /
  `_make_unbounded_limiter`; split `test_fp01_fixes.py` (423 → 272) into it
  + new `test_fp01_error_branches.py` (164, the Tier-3 playlist + FP08
  control-byte tests). Count-neutral; 216 copy+media tests green.

- ✅ [mame-curator-1047] **FP31 follow-up — FsBrowser prefetch policy
  when dialog is closed.** Surfaced when adding a request-spy assertion
  to `FsBrowser.test.tsx`'s "does not render when open=false" test:
  the spy caught 3 requests (home / roots / allowed-roots) even though
  the component renders nothing. Either gate the queries with
  `enabled: open` or document the prefetch-on-mount choice. Test was
  reverted to the original "no dialog" assertion; the SUT decision
  needs to happen first.
  Kind: fix. Lanes: frontend, frontend tests. Source:
  test-audit-2026-05-18 FP31 chunk fc-003 MED.
  Resolved 2026-06-30: gated useFsHome/useFsDriveRoots/useFsAllowedRoots/useFsListing on `enabled: open` (default-true params; FsBrowser passes `open`). A closed-but-mounted FsBrowser now issues zero fs requests. Regression-locked by the rewritten 'does not render OR fetch when open=false' request:start spy test.

- ✅ [mame-curator-1048] **FP31 follow-up — frontend
  `fireEvent.click` → `userEvent.click` migration sweep.** Across at
  least 8 files (`CartPanel`, `CartBar`, `GameCard`, `FeaturedTilesRow`,
  `AppShell`, `OnboardingBanner`, `DryRunModal`, `CopyModal`,
  `YearRangeEditor`) — `fireEvent` skips the pointer/hover synthetic
  events `userEvent` fires. Highest-risk case is
  `GameCard.test.tsx:154` which tests Add-button `stopPropagation`
  vs the row's `onOpen` (the mechanism is exactly the pointer-event
  chain that `fireEvent` skips). One-shot sweep; mechanical.
  Kind: refactor. Lanes: frontend tests. Source:
  test-audit-2026-05-18 FP31 chunks fc-001/fc-002/fc-003/fc-004/fc-005
  (LOW/MED across the suite).
  Resolved (2026-06-11): migrated every fireEvent.click site (AppShell, CartPanel, CartBar, OnboardingBanner, FeaturedTilesRow, GameCard) to `await user.click` via `userEvent.setup()`. fireEvent.error (GameCard image-error) and fireEvent.change (YearRangeEditor direct value-set) kept — no userEvent equivalent / out of .click scope. 320 vitest green; tsc/eslint clean.

- ✅ [mame-curator-1049] **FP31 follow-up — `userEvent` static API →
  `userEvent.setup()` migration in 3 components**
  (`CmdKPalette.test.tsx`, `ConfirmationDialog.test.tsx`,
  `no-checkbox-for-prefs.test.tsx`). The static API is deprecated in
  `@testing-library/user-event` v14; the setup-instance form shares
  pointer/keyboard state and delay config across calls in a test.
  Kind: refactor. Lanes: frontend tests. Source:
  test-audit-2026-05-18 FP31 chunk fc-001 MED.
  Resolved (2026-06-11): scope expanded to a full-suite sweep (user-approved) — all 30 userEvent test files migrated to the `userEvent.setup()` instance form; zero static `userEvent.<method>` calls remain (was 3-file scope, but 3-of-25 would have worsened consistency). FiltersSidebar fake-timer test uses `setup({ advanceTimers })`. 320 vitest green; tsc/eslint clean.

- ✅ [mame-curator-1050] **FP31 follow-up — `@pytest.mark.asyncio`
  decorator cleanup under `asyncio_mode = "auto"`.** Redundant
  decorators identified in `test_fp28_jobs_loop_thread.py` (1),
  `test_downloads.py` (11), and `test_ini.py` (3). Auto mode collects
  every `async def test_*` as a coroutine without the decorator — the
  decorator is cargo-cult noise. Mechanical sweep across the suite.
  Kind: refactor. Lanes: backend tests. Source: test-audit-2026-05-18
  FP31 chunks c-001 / c-009 / c-010 LOW.
  Resolved (2026-06-10): stripped all 15 redundant `@pytest.mark.asyncio`
  decorators (1 in test_fp28_jobs_loop_thread + 11 in test_downloads + 3 in
  test_ini); `asyncio_mode = "auto"` still collects them. Dropped the
  now-unused `import pytest` in test_ini.py. Count-neutral.

- ✅ [mame-curator-1051] **FP31 follow-up — broaden
  `pytest.raises((SessionsError, ValueError))` unions in
  `test_filter/test_sessions.py` (4 sites) + `test_filter/test_types.py`
  (1 site).** Now that the FP06 B2 migration is shipped, the precise
  post-fix exception is known: `ValidationError` (Pydantic) for direct
  construction paths, `SessionsError` for loader paths. Pin each to the
  specific type and add `match=` patterns (chunk c-007 LOW).
  Kind: refactor. Lanes: backend tests. Source: test-audit-2026-05-18
  FP31 chunk c-007 LOW.
  Resolved (2026-06-10): all 5 sites pinned to `pytest.raises(ValidationError,
  match=...)`. Verified empirically that the 4 direct-construction paths
  (`Sessions(...)` / `Session(...)`) and the frozen-field rebind in
  test_types.py all raise Pydantic's `ValidationError` (a `ValueError`
  subclass — which is why the old union passed); each now carries a specific
  `match=` for its validator message.

- ✅ [mame-curator-1052] **FP31 follow-up — `test_routes_copy.py:79`
  pause/resume/abort test passes vacuously on fast runners.** Both
  `pause` and `abort` accept `status_code in (200, 404)`; on fast CI
  the tiny fixture files complete in microseconds and both return 404,
  so the test passes having exercised nothing. Decision needed:
  guard with skip-if-both-404, slow the fixture, or delete in favour
  of the `test_sse.py` coverage. Kind: fix. Lanes: backend tests.
  Source: test-audit-2026-05-18 FP31 chunk c-002 MED.
  Resolved 2026-06-30: rewrote the vacuous test_pause_resume_abort_copy to assert the transitional state on the 200 branch and job_not_found on the 404 branch (non-vacuous on both race outcomes), added the missing resume call, and corrected the false docstring (real deterministic pause/resume/cancel coverage is test_controller.py + test_runner_lifecycle.py, NOT test_sse.py).

- ✅ [mame-curator-1053] **FP31 follow-up — coverage gaps in `test_routes_media.py`
  (no `httpx.TransportError` mock), `test_activity.py` (7 of 10
  `ActivityEventType` variants have no round-trip test), and
  `test_useFs.test.tsx` (success-path of `useFsGrantRoot` untested).**
  Three small additive coverage items grouped by theme: "happy path
  tested, error/alternate branch in same file untested."
  Kind: fix. Lanes: backend tests, frontend tests. Source:
  test-audit-2026-05-18 FP31 chunks c-002 / c-003 / fc-002 LOW.
  Resolved 2026-06-30: added httpx.TransportError test in test_routes_media.py (->502 media_upstream_error, exercises the previously-uncovered except httpx.HTTPError branch), a parametrized round-trip over all 10 ActivityEventType variants + a coverage guard in test_activity.py, and the useFsGrantRoot onSuccess->cache test in useFs.test.tsx.

- ✅ [mame-curator-1054] **FP31 follow-up — refactoring & dedup nits:**
  (a) `tests/api/test_static_mount.py` extract `_rebuilt_client(stub,
      monkeypatch, config_file)` helper (4 duplicated app-rebuild
      blocks). chunk c-003 MED.
  (b) `tests/cli/test_fp28_serve_signal.py:45-67` —
      `_build_minimal_config` duplicates `tests/api/conftest.py`'s
      `config_file` fixture; move the fixture to the top-level
      `tests/conftest.py` so both trees share it. chunk c-003 LOW.
  (c) `tests/copy/test_fp01_fixes.py` + `test_fp02_fixes.py` — extract
      `_seed_existing_playlist` 12-line helper to
      `tests/copy/conftest.py`. chunk c-004 MED.
  (d) `tests/filter/test_runner.py:98,112,156` — add an
      `o(**entries)` factory in `tests/filter/conftest.py` to absorb
      the 3 repeated `Overrides(entries={...})` constructions and
      drop the matching `# type: ignore[call-arg, unused-ignore]`
      suppressions. chunk c-007 MED.
  (e) `tests/copy/test_fp01_fixes.py:34,49` — `_machine` lifted in
      the inline pass; `_seed_existing_playlist` deferred to (c).
  (f) `tests/updates/conftest.py` — replace per-file `_no_sleep`
      passthroughs in `test_ini.py` + `test_snaps.py` with a
      subdirectory autouse fixture. chunk c-010 LOW.
  Kind: refactor. Lanes: backend tests. Source: test-audit-2026-05-18
  FP31 chunks c-003/c-004/c-007/c-010 MEDIUM/LOW.
  Resolved (2026-06-10): (a) `_rebuilt_client(dist, monkeypatch, config_file)`
  helper folds the 4 app-rebuild blocks (rebuilt app reachable via
  `client.app`); (c) `_seed_existing_playlist` lifted to
  `tests/copy/conftest.py` (now shared by fp01 / fp01_error_branches / fp02);
  (d) `o(**entries)` factory in `tests/filter/conftest.py` absorbs 4
  `Overrides(entries=…)` constructions + drops their `type: ignore`; (e)
  `_machine` was already lifted to `_runner_helpers` in the inline FP31 pass;
  (f) new `tests/updates/conftest.py` with one autouse `_no_sleep`.
  (b) **deliberately not done** — moving `config_file` to the top-level
  `tests/conftest.py` would drag api-only fixtures into the shared root,
  including `source_dir` / `dest_dir` that collide *by name* with
  `tests/copy/conftest.py`'s same-named fixtures; over-engineering for a LOW
  dedup nit, and the cli `_build_minimal_config` is a documented minimal
  subset (4 paths), not a true duplicate of the 11-fixture `config_file`.

- ✅ [mame-curator-1055] **FP31 follow-up — assorted LOW/INFO test polish:**
  (a) `tests/api/test_fp25_world_lock.py:47-73` — parametrize 7
      structurally-identical per-route world-lock tests. chunk c-001
      LOW.
  (b) `tests/api/test_fp28_validate_paths_retroarch.py` — add
      "exists but not executable" (`chmod 0o644`) test for the
      `os.X_OK` branch. chunk c-001 LOW.
  (c) `tests/cli/test_cli_setup.py` + `tests/copy/test_activity.py` —
      add docstrings to 4 named tests (`test_setup_overwrites_with_force`,
      `test_setup_errors_on_missing_source_dat`,
      `test_activity_log_append_writes_one_line`,
      `test_read_activity_yields_newest_first`). chunk c-003 LOW.
  (d) `tests/api/test_fp21_fixes.py:254` — rename
      `test_under_pressure` to
      `test_fp21_l_progress_history_deque_has_finite_maxlen` (no
      pressure is applied). chunk c-001 LOW.
  (e) `tests/test_downloads.py:241-286` — calibrate the tracemalloc
      threshold comment against the active respx/httpx version pin.
      chunk c-009 LOW.
  (f) `tests/parser/test_exports.py:65,75` — add a `pyproject.toml`
      sentinel check before resolving `parents[2]` for `spec.md`
      lookup. chunk c-009 LOW.
  (g) `tests/copy/test_preflight.py:159` — tighten
      `free_space_gap_bytes >= -sf2_size` to a two-run gap-difference
      check (chunk c-005 LOW).
  (h) `tests/media/test_escape.py:47` — fix misleading inline
      parametrize comment. chunk c-008 LOW.
  (i) `tests/media/test_sources.py:448` — fold the private
      `_url_cache` write into the `prepare()`-mocked test (deferred
      until the file-split lands per [mame-curator-1046]). chunk
      c-008 MED.
  (j) `tests/media/test_sources.py:509` — replace dead
      `url.endswith("Pac_flyer.png")` branch with `"Pac_flyer.png" in
      url`. chunk c-008 LOW.
  (k) `frontend/src/components/library/__tests__/{DryRunModal,CopyModal,
      CartBar}.test.tsx` — `toHaveBeenCalled()` →
      `toHaveBeenCalledOnce()` on `onConfirm` / `onPause` / `onResume`
      / `onBulkAdd` (chunk fc-004 LOW).
  (l) `frontend/src/lib/__tests__/queryClient.test.tsx` — add
      `{ timeout: 3000 }` to `waitFor` calls (chunk fc-001 LOW).
  (m) `frontend/src/components/__tests__/{ErrorBoundary,Confirmation
      Dialog}.test.tsx` — add file-level `afterEach(() =>
      vi.restoreAllMocks())` so `console.error` spies survive
      assertion failures (chunk fc-001 LOW).
  (n) `frontend/src/components/alternatives/__tests__/AlternativesDrawer.test.tsx`
      — add missing `manufacturer_raw`/`bytes`/`parent` to fixture
      objects or extract a `makeGameCard()` factory (chunk fc-002
      MED).
  (o) `frontend/src/components/library/__tests__/OnboardingBanner.test.tsx`
      — switch hardcoded regex fragments to `strings.library.onboarding.body`
      references (chunk fc-005 LOW).
  Kind: refactor. Lanes: backend tests, frontend tests. Source:
  test-audit-2026-05-18 FP31 chunks c-001/c-003/c-005/c-008/c-009 +
  fc-001/fc-002/fc-004/fc-005 LOW.
  Resolved (2026-06-10): all 15 sub-items (a–o). (a) merged the two
  async-introspection tests into one parametrized-over-7 test; (b) added the
  exists-but-non-executable (0o644) X_OK test (+1 test); (c) 4 docstrings;
  (d) renamed to `test_fp21_l_progress_history_deque_has_finite_maxlen`;
  (e) tracemalloc comment now cites the respx 0.23 / httpx 0.28 pins;
  (f) `_parser_spec_path()` adds a `pyproject.toml` sentinel; (g) preflight
  rewritten to a mocked-`disk_usage` two-run delta == kof94_size check;
  (h) escape parametrize comment fixed; (i) `_url_cache` white-box write →
  `prepare()`-mocked; (j) dead `endswith` branch dropped; (k)
  `toHaveBeenCalledOnce`; (l) `waitFor` timeouts; (m) file-level
  `afterEach(restoreAllMocks)` in ErrorBoundary + ConfirmationDialog;
  (n) `makeGameCard()` factory (note: `manufacturer_raw`/`bytes`/`parent`
  are no longer on the `GameCard` type — that half of the finding was
  stale; adding them would break `tsc`); (o) OnboardingBanner asserts via
  `strings.library.onboarding.body`. +1 backend test (b); frontend
  count-neutral.

- ✅ [mame-curator-1056] **FP31 follow-up — `tests/api/test_fp09_fixes.py:159-177`
  convert `asyncio.run()` sync wrapper to `@pytest.mark.asyncio async def`.**
  Today the test manages the lifespan context manually inside a sync
  function. Benign under `asyncio_mode = "auto"` but
  incompatible with the strict-mode opt-in some teams adopt later.
  Kind: refactor. Lanes: backend tests. Source: test-audit-2026-05-18
  FP31 chunk c-001 MEDIUM.
  Resolved (2026-06-10): converted `test_b4_app_state_has_shared_media_client`
  to a native `async def` (auto-mode collects it) — dropped the
  `asyncio.run(_check())` wrapper + the nested `_check` coroutine; the
  lifespan context is now entered directly with `async with`.


- ✅ [mame-curator-1074] **FP31 follow-up — decide keep-vs-migrate for the 3 remaining non-click `fireEvent` calls in the frontend tests.**
  After the 1048/1049 sweep the only `fireEvent` calls left are 3 non-click ones, left alone deliberately: `fireEvent.error(img)` in GameCard.test.tsx (simulates an image load failure) and `fireEvent.change(input, ...)` x2 in YearRangeEditor.test.tsx (directly sets a number input's value). `fireEvent.error` has NO userEvent equivalent and MUST stay (an image error is not a user action). `fireEvent.change` is a legitimate RTL idiom for controlled inputs but could migrate to `user.clear()` + `user.type()` for full consistency. Low priority. NOTE: migrating the change calls is not free -- `user.type('2000')` fires an onChange per keystroke, so the `toHaveBeenLastCalledWith(2000)` / `(null)` assertions must be re-checked. Do NOT blindly sweep `fireEvent.error`.
  Kind: refactor.
  Lanes: frontend tests.
  Source: in-session-2026-06-11 (1048/1049 userEvent sweep leftovers).
  Resolved 2026-06-30: decision is KEEP all 3 non-click fireEvent calls. fireEvent.error has no userEvent equivalent (image error is not a user action); fireEvent.change is the idiomatic atomic set for controlled inputs and migrating to user.type would break the toHaveBeenLastCalledWith assertions per-keystroke. Documented the rationale at each call site.

- 📋 [mame-curator-1075] **Repo-wide Prettier formatting debt in the frontend tree (not CI-gated).**
  `npx prettier --check` flags ~45 frontend files, including many untouched by recent work -- pre-existing, repo-wide debt. `npm run format` (prettier --check) is NOT part of the CI gate (CI runs eslint + tsc -b + vitest only), which is why it has never blocked. Every file touched in the 1048/1049 userEvent sweep was already prettier-dirty at HEAD, so the sweep neither introduced nor fixed it. Fix: one standalone `prettier --write` debt-sweep commit across the frontend tree (kept separate so the pure-formatting churn doesn't muddy feature diffs), and optionally add `npm run format` to the CI workflow to stop re-drift.
  Kind: chore.
  Lanes: frontend.
  Source: in-session-2026-06-11.

### 🧪 Test Audit 2026-05-18

Framework: pytest (backend) + vitest (frontend) · Files scanned: 152
(102 backend + 50 frontend) · Dimensions: all 18 · Raw findings: 102 ·
Actionable after triage: ~20 (top 4 fixed inline, 16 retained as
follow-ups below) · Suite green at fold-in: 726 backend + 319 frontend
tests at 87.78 % coverage. Allowlist gained 3 new entries (008–010)
documenting test-audit-specific false positives.

**Fixed inline (no roadmap entry needed):**

- ✅ Orphaned `it()` blocks in `GameCard.test.tsx:174,188` (outside
  `describe()`, reported as anonymous top-level tests). Hoisted into the
  closing `})` of the parent describe.
- ✅ `vi.useFakeTimers()` without try/finally in `FiltersSidebar.test.tsx`
  (a failing assertion would leak fake timers into the next test).
  Wrapped in try/finally so cleanup always runs.
- ✅ Tautological / disjunction assertions in `test_routes_copy.py:21,65`,
  `test_routes_curate.py:108`, `test_routes_activity.py:54,58`,
  `test_error_quoting.py:47`, `test_routes_games.py:125` — replaced with
  schema-anchored `and` conjunctions or `assert response.status_code in
  (...); if 404: pytest.skip(...)`.
- ✅ Byte-for-byte duplicate test (`test_b6_no_op_patch_preserves_filter
  _result` in `test_fp09_fixes.py:221` duplicated
  `test_filter_recompute_idempotent_under_no_op_patch` in
  `test_routes_config.py:123`). Deleted the duplicate; pin bumped in
  `test_ds05_test_count_stable.py` (and the regex now matches `async
  def test_…` too — previously 37 async tests escaped the count guard).
- ✅ Builder-/fixture-duplication: `m(**kw)` Machine builder (3 filter
  test files), `_empty_ctx()` (3 files), `_raise_oserror` (2 parser
  files), `_no_sleep` autouse fixture (2 root/updates files),
  `renderWithClient()` (5 hook test files), `_OVER_CAP` byte constant
  (3 filter files). All hoisted to the relevant `conftest.py` /
  `frontend/src/test/renderWithClient.tsx`.
- ✅ Loop-over-cases anti-patterns: `test_static_mount.py:180` (10
  cases), `test_sessions.py:117` (3 cases). Both now use
  `@pytest.mark.parametrize` so the first failure doesn't hide the rest.
- ✅ Hypothesis `@settings(deadline=None)` in `test_property.py` lacked
  `suppress_health_check=[HealthCheck.too_slow]` — added; prevents the
  cold-CI flake mode.
- ✅ `pytest.raises(RuntimeError)` without `match=` in
  `test_fp28_jobs_loop_thread.py:58` — added match pattern so the test
  fires for the right RuntimeError source.
- ✅ Stale RED-phase docstring drift in `test_world_state_bytes_cache.py:25`
  (claimed `@pytest.mark.xfail(strict=True)` markers exist; they
  don't). Docstring updated to reflect GREEN status.
- ✅ `tracemalloc` baseline pollution in `test_routes_activity.py:148` —
  added `tracemalloc.clear_traces()` immediately before the request so
  fixture-setup allocations don't inflate the baseline.
- ✅ Microtask hack in `NotesEditor.test.tsx:23` (`await Promise.resolve()`
  after `blur()`) — replaced with `await waitFor(...)`.
- ✅ Redundant `cleanup()` calls in `no-checkbox-for-prefs.test.tsx`
  (4 sites) — vitest `globals: true` already auto-cleans (DS04 T3.1
  pattern); removed.
- ✅ Dead conftest fixtures in `tests/copy/conftest.py`
  (`machine_kof94`, `machine_sf2ce`, `make_zip` — declared, never
  consumed). Removed; bumped `bios_chain` to module scope.
- ✅ Parser CLI assertion strength: `test_cli_parse.py:20-22` was
  label-only (`"bios:" in output`); fixture has known counts so changed
  to `"bios: 1" in output`. Same file's `exit_code != 0` tightened to
  `== 1` so argparse-2 collision can't slip past.

**Retained as roadmap follow-ups:**

- 📋 [mame-curator-1040] **Test-audit FP01 — fixture-scope optimisation for
  `api/conftest.py::client`.** Verified 2026-05-18: actually **117 api
  tests** (not 37 as the chunk reported) consume `client`/`app` across
  19 files, totalling 169 api tests in 15.43 s locally. Microbench shows
  `create_app + TestClient lifespan` costs **~48 ms warm (~82 ms cold)**
  per call — `~8 s` aggregate over the suite, not the 30–60 s the chunk
  estimated. The proposed split into `app_readonly` (session-scoped) +
  `app` (function-scoped) is still real engineering work, but it
  requires:
  (1) classifying every api test as read-only vs mutation (almost every
      non-GET route mutates `app.state.world` via `replace_world` — the
      read-only set is narrower than the chunk implied);
  (2) hoisting `tmp_path` → `tmp_path_factory` for the session-scoped
      branch, plus `monkeypatch.MonkeyPatch` context for `fake_home`;
  (3) deciding whether to snapshot+restore `app.state.world` between
      tests (alternative to a strict read-only-only split).
  Deferred to a dedicated phase with that classification pass up front —
  fixing it as a one-shot fold-in risks subtle cross-test pollution. See
  `tests/api/conftest.py` and the `app_started` fixture (added by FP06,
  2026-05-18) as the foundation.
  Kind: refactor. Lanes: backend tests. Source: test-audit-2026-05-18
  chunk-3 (HIGH); verification 2026-05-18 fold-in.

- ✅ [mame-curator-1041] **Test-audit FP02 — eliminate file-size timing
  trick in SSE C1 test.** Closed 2026-05-18 in the FP-fold-in commit:
  `test_c1_subscriber_after_start_sees_job_started_via_history_replay`
  no longer writes 3-MiB fake zips. Verified that `_events_iterator`'s
  register-then-snapshot ordering (FP21-K) plus the post-replay sentinel
  for terminal-state jobs covers every interleaving, including "worker
  already finished before subscriber connected." Test now runs in 0.61 s
  (down from a `@pytest.mark.slow`-marked outlier) and the file-size
  crutch is gone.
  Kind: refactor. Lanes: backend tests. Source: test-audit-2026-05-18
  chunk-4 (HIGH).

- ✅ [mame-curator-1042] **Test-audit FP03 — SettingsPage invariant
  coverage gap.** Closed 2026-05-18 in the FP-fold-in commit. Test no
  longer iterates a hardcoded subset of 5 tab labels; instead it queries
  `screen.getAllByRole('tab')` and visits every tab the page renders,
  so a future preference landing on Paths/Snapshots/Backup/About is
  guarded by the same invariant. Lifts the dependency on the tab-label
  string list staying in sync with `SECTION_KEYS` in SettingsPage.tsx.
  Kind: refactor. Lanes: frontend tests. Source: test-audit-2026-05-18
  chunk-8 (MEDIUM).

- ✅ [mame-curator-1043] **Test-audit FP04 — collection-time file reads
  in parametrized docs tests.** Closed 2026-05-18 in the FP-fold-in
  commit. Verified: `test_dep_pin_coupling.py:54` parametrizes over the
  static `_COUPLED_TOOLS` tuple (no I/O) and was a false positive (now
  in `docs/audit-allowlist.md` allowlist-011). The real finding —
  `test_no_pre_release_pins.py::_all_pins()` reading 5 manifest files
  at parametrize-collection time — is fixed: each reader is wrapped in
  `try/except FileNotFoundError` and missing-file cases emit a named
  `pytest.skip` sentinel instead of an unhandled collection-time
  exception.
  Kind: refactor. Lanes: backend tests, ci. Source:
  test-audit-2026-05-18 chunk-6 (HIGH).

- ✅ [mame-curator-1044] **Test-audit FP05 — fixture / handler dedup
  follow-ups.** Closed 2026-05-18 in the FP-fold-in commit. Verified
  the five sub-claims and extracted the two clear Rule-of-Three wins:
  (1) `FsBrowser` sandbox-error MSW handler (5 inlined copies) →
  `makeSandboxedListHandler(home, homeListing)` in
  `frontend/src/test/handlers.ts`; (2) `FilterSidebarState` 11-field
  neutral value object (4 copies across 2 files) → `baseFiltersValue`
  in new `frontend/src/test/fixtures.ts`. Three sub-claims false-
  positive: `test_fp01_fixes.py` / `test_fp02_fixes.py` don't exist
  (allowlist-012); pacman GameCard fixture appears in only one file
  (allowlist-013); `CopyPlan+JobManager+Job` setup is 2-place in a
  single file (below Rule-of-Three).
  Kind: refactor. Lanes: backend tests, frontend tests. Source:
  test-audit-2026-05-18 chunks 2/4/7/8 (MEDIUM).

- ✅ [mame-curator-1045] **Test-audit FP06 — `del client` antipattern
  in api tests.** Closed 2026-05-18 in the FP-fold-in commit. New
  `app_started` fixture in `tests/api/conftest.py` yields `app` after
  the FastAPI lifespan has fired, without exposing an unused
  `TestClient`. Migrated the 4 cited call-sites in `test_state.py` and
  `test_world_state_bytes_cache.py`. The fixture is also the foundation
  for the larger 1040 (FP01) split when that phase lands.
  Kind: refactor. Lanes: backend tests. Source:
  test-audit-2026-05-18 chunk-3 (MEDIUM).


### 🔍 Indie-review fold-in (2026-05-14)

- ✅ [mame-curator-1031] **FP27 — Tier 1 review fold-in: zombie
  features + data integrity.** Closed 2026-05-14
  (`cfe612c..976b119`). 16 sub-bullets across 5 commits + cluster
  R1 fold-in; spec converged on cold-eyes loop 5 (0 residual
  findings); 551 backend + 279 frontend tests green at close. See
  [`CHANGELOG.md`](CHANGELOG.md) for the per-bullet breakdown.
  Bundles ~14 findings from the 2026-05-14 11-lane `/indie-review`.
  Dominant pattern: declared + exported + documented features with
  zero non-test callers — `filter.ConfigError`
  (`src/mame_curator/filter/errors.py:10`), `copy.PreflightError`
  (`src/mame_curator/copy/errors.py:34`), `recycle_file` /
  `purge_recycle` activity-log writes
  (`src/mame_curator/copy/recyclebin.py:23,142` — audit trail
  half-shipped per `copy/spec.md:266`), `useCopySession.resolveConflict`
  (`frontend/src/hooks/useCopySession.ts:175` — three live buttons
  silently dropping the user's conflict choice), CmdK palette `games`
  + `settings` sections
  (`frontend/src/components/CmdKPalette.tsx:30` — declared types,
  zero producers), most advertised keyboard shortcuts (design spec
  § "Keyboard shortcuts" promises `/` `?` `g …` `a` `n`, no
  handlers), `useKeyboard` chord engine
  (`frontend/src/hooks/useKeyboard.ts:80`), `--version` flag
  (`src/mame_curator/cli/spec.md:38`), four dead `strings.ts`
  entries, and `parse_listxml_bios_chain` + `BIOSChainEntry` not in
  `parser/__init__.py.__all__` or `parser/spec.md` despite three
  modules consuming them. Plus data-integrity gaps:
  `executor.copy_one` chunked path never `fsync`s the `tmp` before
  `os.replace` (`src/mame_curator/copy/executor.py:26` — power-cut
  hazard on big ROM transfers); `persist.restore_snapshot` unlinks
  live files before atomic-writes of restored ones
  (`src/mame_curator/api/persist.py:103`); `downloads.download`
  docstring promises streaming but body fully buffered
  (`src/mame_curator/downloads.py:135` — ~3× RAM amplification);
  `media/cache.py:fetch_with_cache` has no size cap, no scheme
  check, no streaming; `GET /api/activity` reads + parses the
  entire JSONL on every request
  (`src/mame_curator/api/routes/activity.py:32`). Plus load-bearing
  doc drift: `CLAUDE.md:51` says `api/ (P04 — next)` though P04
  shipped 2026-05-01; the README + CLAUDE architecture diagrams
  list `help/` + `setup/` modules that don't exist as packages.
  Layman: A fresh-eyes code review found ~14 places where the docs
  claim a feature exists but the code doesn't actually deliver —
  buttons that do nothing, shortcuts that aren't wired, error types
  that are never raised — plus a handful of "could lose data on a
  crash" spots in the copy + snapshot paths. None are user-blocking
  today but they're the kind of "looks like it works" bugs that
  surprise people later. A fix-pass to burn them off before any new
  feature lands.
  Kind: review-fix.
  Lanes: backend, frontend, docs.
  Source: indie-review-2026-05-14 Tier 1.

- ✅ [mame-curator-1032] **FP28 — Tier 2 review fold-in: hardening
  + correctness.**
  Bundles ~12 second-tier findings from the same sweep. Concurrency:
  `JobManager._emit` mutates `lifecycle_history` + `subscribers`
  without the lock (`src/mame_curator/api/jobs.py:282`); recyclebin
  counter race on parallel sessions (`recyclebin.py:51`);
  `target_dir_existed` rollback can `rmdir` a sibling's
  just-created dir. Correctness: `_LICENSE_RE` breaks on
  `"Atari (JSA III) (Williams license)"` (nested parens at
  `src/mame_curator/parser/manufacturer.py:11`); `REGION_RE`
  false-positives `World Heroes`-class titles
  (`filter/heuristics.py:12`); `Machine.description` uses `.text`
  only and loses mixed-content (`parser/dat.py:170`);
  `filter.runner` declared `logger` is never called despite Phase C
  spec line 71 requiring it; `_apply_session` raises raw `KeyError`
  on stale post-`model_copy` `sessions.active`. Boundary hardening:
  `_validate_paths` doesn't check `retroarch` / `retroarch_core`
  paths (local-exec via `POST /api/config/import`); `media_proxy`
  returns hardcoded `image/png` + no `Cache-Control` headers. CLI
  exit-code drift: `serve` swallows `KeyboardInterrupt` and returns
  0 instead of 130 (`src/mame_curator/cli/__init__.py:485`); bare
  `except Exception` loses tracebacks; `refresh-inis` surfaces a
  raw `ImportError` traceback when httpx is missing. Plus the
  design § 6.6 deferral: mirrors + sha256 promised on every INI
  refresh, current `updates/ini.py:42` delivers neither (decide vs
  P12 deferral).
  Layman: Same review found ~12 more places where the code
  technically works but has hardening gaps — race conditions only
  visible under heavy concurrent use, regex bugs that mis-tag a
  small minority of games, wrong exit codes that break shell
  scripts. Lower-urgency than FP27 but still bound for v1.3.
  Kind: review-fix.
  Lanes: backend, frontend, cli.
  Source: indie-review-2026-05-14 Tier 2.

### 📝 Cold-eyes 2026-05-18

**Theme:** Docs reviewed: 12 lanes (contracts, standards, decisions,
spec/P10, spec/P14, spec/FP27, spec/FP28, spec/DS02..DS05,
per-feature-specs). Single-pass with all severities folded inline;
items below are the verified deferrals that couldn't be auto-fixed
under a docs-review skill.

- ✅ [mame-curator-1057] **Author `src/mame_curator/api/spec.md`.**
  Shipped P04 API module ships without a co-located `spec.md`,
  violating the project rule in `coding-standards.md § 7` + `CLAUDE.md`
  ("No feature merges without a `spec.md` next to its code"). Three
  cold-eyes lanes flagged the gap.
  Layman: We have a contract document for some shipped modules but
  not all — fill in the missing ones so reviewers can audit the
  whole codebase by reading the contracts.
  Kind: doc.
  Lanes: api, docs.
  Source: cold-eyes-2026-05-18 lanes standards + per-feature-specs + decisions.
  Resolved 2026-06-30: authored src/mame_curator/api/spec.md — the co-located P04 API contract (app factory + lifespan app.state model, frozen WorldState + the 14-route world_lock concurrency invariant, the ApiErrorBody envelope + 24-entry code/status table, the 46-route inventory, copy-job lifecycle + SSE, the home+4-paths FS sandbox, config snapshots/persistence, media proxy, SPA fallback). Ran /cold-eyes to a clean pass (4 loops; every verified HIGH/MEDIUM/LOW fixed — home-root allowlist omission, TokenBucket name + config key, 12→14 lock count, video temporal claim, limiter construction shape, root-id hash shape, MediaRateLimited wire-reachability note).

- 📋 [mame-curator-1058] **Author `src/mame_curator/media/spec.md`.**
  Shipped P05 module (with P10 still in flight) ships without a
  co-located `spec.md`. Same rule violation as 1057. Wait for P10 to
  close before drafting so the spec captures the full source surface
  (libretro + progettoSnaps + ArcadeDB + Wikipedia + MobyGames).
  Layman: Same fill-in-the-gap as 1057 but for the media-cover module.
  Kind: doc.
  Lanes: media, docs.
  Source: cold-eyes-2026-05-18 lanes standards + per-feature-specs.
  Re-checked 2026-06-30 (1060/1061 session): still blocked. P10 remains in flight per .claude/workflow.md §1 — Step 3, chunk 6 (MobyGames) plus chunks 7–11 (registry/orchestrator) unshipped. Gate holds: drafting media/spec.md now would document a partial source surface (MobyGames absent). Stays parked until P10 closes.

- ✅ [mame-curator-1059] **Author `src/mame_curator/updates/spec.md`.**
  Shipped P07 module ships without a co-located `spec.md`. Same rule
  violation as 1057. ADR-0004 § "Post-v1 hardening path" already
  identifies this as the first step; lift it from a buried footnote to
  a tracked bullet.
  Layman: Same fill-in-the-gap as 1057 but for the auto-update module.
  Kind: doc.
  Lanes: updates, docs.
  Source: cold-eyes-2026-05-18 lanes standards + per-feature-specs + decisions.
  Resolved 2026-06-30: authored src/mame_curator/updates/spec.md — the co-located P07 reference-data-refresh contract (refresh_inis / refresh_snaps / discover_snap_pack_url, the two report dataclasses, the 2x disk-space gate + dest_dir/parent probe, the path-separator zip-slip defense, the complete failure-mode enumeration: report-vs-raise for disk-gate/download vs extract/discovery-HTTP). Ran /cold-eyes to a clean pass (6 loops; every verified HIGH/MEDIUM/LOW fixed — INI mandatory/fifth framing, dangling ROADMAP ref, MiB/MB units, pack retention, DEFAULT_DEST, extract-failure-raises correction, discovery raise_for_status path). 1058 (media spec) stays blocked per its body until P10 closes.

- ✅ [mame-curator-1060] **Author `docs/journal/P14.md`.**
  P14 closed 2026-05-17 with tag `P14-complete` but no journal entry.
  Every other closed phase has one (`DS02`, `DS03`, `DS04`, `DS05`,
  `FP27`, `FP28`). Standalone fix; scrape the close commit body +
  CHANGELOG `### P14` section for the journal body.
  Layman: Missing diary entry for the per-game-review-state phase.
  Kind: doc.
  Lanes: docs.
  Source: cold-eyes-2026-05-18 lane spec/P14.
  Resolved 2026-06-30: authored docs/journal/P14.md from the P14-complete tag body + CHANGELOG ### P14 — chunk→commit map, the passive-swap (INV-4) / per-request-filter architecture, the chunk 8+15 folding, and the 507→535 backend / 289→300 frontend test deltas.

- ✅ [mame-curator-1061] **Promote P14 review-state contract to a
  module-co-located spec.** P14 spec § Files-touched lists
  `src/mame_curator/filter/review_state_spec.md` as the close-time
  promotion target; it doesn't exist on disk and the contract lives
  inside `filter/spec.md` for now. Extract the review-state clauses
  into the co-located file (or merge them into the larger module spec
  if the project prefers one-spec-per-module).
  Layman: Optional restructure — split the review-state contract into
  its own document, mirroring how parser, copy, cli already have
  per-feature specs.
  Kind: doc.
  Lanes: filter, docs.
  Source: cold-eyes-2026-05-18 lane spec/P14.
  Resolved 2026-06-30: created src/mame_curator/filter/review_state_spec.md — the per-feature co-located contract (model/loader/enums, the three /api/state routes, the ?review_state= per-request filter, the passive-swap fact, 13 invariants) extracted from docs/specs/P14.md and verified clause-by-clause against shipped code. De-staled P14's two promotion notes and added a filter/spec.md back-pointer. User elected the separate-file option over merging into filter/spec.md. Ran /cold-eyes to a clean pass (3 loops): fixed a world-lock over-claim (GET is lock-free), an unshipped-snapshot-caption claim (→ roadmapped 1078), a GET-can't-404 nit, and a coupled copy/spec.md ReviewStateDetails type bug (str, not ReviewStateValue).

- 📋 [mame-curator-1062] **Re-introduce a Radix-Esc regression lock
  for FP27 A6a.** `frontend/src/components/__tests__/EscOverlayBehavior.test.tsx`
  was deleted by DS04 ("-2 from EscOverlayBehavior deletion") but
  FP27 § A6a / R1d depend on it as the lock that ambient Esc handling
  in Radix `Dialog` + `AlertDialog` is honored. If Radix ever drops
  the ambient handler, A6a silently regresses. Restore the assertion
  somewhere — either as a slim regression test or merged into an
  existing Dialog test.
  Layman: A safety-net test that ensures pressing Esc closes overlays
  was deleted; restore it so a future library upgrade can't quietly
  break this.
  Kind: test.
  Lanes: frontend, tests.
  Source: cold-eyes-2026-05-18 lane spec/FP27.

- 📋 [mame-curator-1063] **Resolve `docs/help/` build-tooling gap.**
  FP27 pre-spec verification noted that `docs/help/` doesn't exist
  at repo root; running help routes in dev returns 404 unless
  `MAME_CURATOR_HELP_DIR` is set. Either build tooling that populates
  `docs/help/` ships, or the help routes need a graceful in-tree
  fallback. Currently a load-bearing ghost feature.
  Layman: The in-app Help pages route silently 404s on a fresh
  checkout — wire up the missing piece that populates the help
  directory.
  Kind: fix.
  Lanes: api, docs.
  Source: cold-eyes-2026-05-18 lane spec/FP27.

- ✅ [mame-curator-1064] **Reconcile `CLAUDE.md` "fix-passes don't
  get specs" rule with the FP05/FP25/FP27/FP28 precedent.** CLAUDE.md
  states *"Fix-passes (`FP##` / `DS##`) don't get specs — they
  correct code against the existing module spec."* In practice every
  recent multi-tier fold-in (FP05, FP25, FP27, FP28, DS02–DS05) has
  shipped a full spec, and the journal entries explicitly credit the
  spec for catching highest-leverage drift before implementation. Pick
  one — either amend CLAUDE.md to allow long-form specs for multi-tier
  fold-ins, or trim those specs and move the body into journals.
  Layman: The project rules say fix-pass passes don't need a spec,
  but in practice every big one does — line up rules and reality.
  Kind: doc.
  Lanes: docs.
  Source: cold-eyes-2026-05-18 lane spec/FP27 (H1).
  Resolved 2026-06-30: amended the CLAUDE.md spec-discipline rule — fix-passes still don't *require* their own spec, but a multi-tier fold-in MAY carry a long-form docs/specs/<ID>.md when the upfront contract earns its keep, matching the FP05/FP27/FP28/DS01–DS05 reality the journals credit. User elected amend-the-rule over trimming the 11 existing specs.

### 🤝 Community & funding

- 📋 [mame-curator-1073] **Add a GitHub Sponsors donation link.**
  User-requested. Minimal deliverable: `.github/FUNDING.yml` with `github: [<handle>]` so the GitHub repo shows a "Sponsor" button. Optional surfaces: a README sponsor badge/link and an in-app Support/Donate link (e.g. on the About / help surface — pulls in the frontend lane if added). Prerequisite: the maintainer must have GitHub Sponsors enabled on their account, and the Sponsors handle confirmed (repo owner is `milnet01`) before `.github/FUNDING.yml` is written — an unconfigured handle renders a dead button. Source: user-request 2026-06-10.
  **Layman:** Add a "Sponsor" button to the project so people can donate to the maintainer.
  Kind: chore.
  Lanes: packaging, docs.
  Source: user-request-2026-06-10.

---

## 1.4.0 — Library polish (target: 2026-Q3)

**Theme:** UX touch-ups and review-state tracking deferred when
v1.0.0 shipped on a tight budget. The single largest feature is
P14 (per-game review state).

### 🎨 Features

- ✅ [mame-curator-1014] **P14 — Per-game review state (closed 2026-05-17).**
  Shipped: per-game enum (`pending` / `reviewed` / `skipped` /
  `needs-decision`) persisted under `data/state.yaml` (single file
  rather than `data/state/` per Step-1 design call — see spec
  §"Open design calls"). Frontend-only badge on GameCard when state
  is non-default; segmented review-state filter (`RadioGroup`)
  above the existing sidebar switches; keyboard shortcuts (R / S /
  ?) wired both inside the library grid and inside the alternatives
  drawer; progress chip + walkthrough toggle in the /library
  header; walkthrough auto-advance on by default, persisted in
  localStorage. Activity log gains a `review_state` event for every
  mutation (state/previous as plain strings so the log records the
  sparse-store sentinel `"pending"`). 13 INVs codified in
  `docs/specs/P14.md`. Lanes: api, frontend, persist, tests.

- 📋 [mame-curator-1038] **FP30 — Auto-save indicator on Settings page.**
  Settings page already auto-saves on every change via
  `useConfigPatch` (`frontend/src/hooks/useConfig.ts:21`), but
  `onSuccess` emits no UI feedback — only `onError` toasts. Users
  edit RetroArch paths (or any other field), the PATCH succeeds
  silently, and there's no signal the save happened. Fix: wire a
  brief success toast or a subtle inline "Saved ✓" pill on every
  successful PATCH, mirroring the `useReviewState` hook's pattern.
  Layman: When you change a setting it saves automatically right
  now, but the page doesn't say anything — so it feels like nothing
  happened. Add a small "Saved" indicator that flashes briefly each
  time.
  Kind: fix.
  Lanes: frontend, tests.
  Source: user-2026-05-17 ("the settings page seems to save in
  'real time' (as you make changes, they are saved automatically.
  This is awesome but there is no indication that this is
  happening").
  Dependencies: none.

- 📋 [mame-curator-1039] **P16 — UI polish + theme expansion.**
  Visual-polish pass across the app for end-user perception of
  professionalism. Tactical surface: typography (font choice,
  weights, sizing rhythm), spacing rhythm (padding / margins /
  vertical-rhythm consistency), color depth (hover / focus / active
  state polish across themes), iconography (button hierarchy, icon
  density), loading / empty states (skeleton screens, empty-list
  illustrations), information density. Existing four arcade themes
  (`double_dragon`, `pacman`, `sf2`, `neogeo`) get a quality pass
  + possibly two more (Galaga, Donkey Kong, CPS-2 — user to
  confirm at Step 1). Scope-firewall: visual polish only; no new
  features.
  Layman: Pass over every screen for visual quality —
  fonts, spacing, colors, loading screens. Also improve the existing
  arcade-themed colour schemes (Pac-Man, Street Fighter II, Neo Geo,
  Double Dragon) and maybe add a couple more.
  Kind: implement.
  Lanes: frontend, tests.
  Source: user-2026-05-17 ("I would also like the whole site to be
  made more professional looking too please. Also, add in themes
  too please. Maybe base the themes on some popular arcade / MAME
  games").
  Dependencies: none.

### 📚 Documentation

- ✅ [mame-curator-1029] **README hero shot + 4 screenshots (closed 2026-05-16).**
  Shipped: library hero image at the top of the README; new
  `## Screenshots` section with a 2×2 grid (alternatives drawer,
  filters tab, sessions panel, plus a pointer to the regen recipe).
  Captures generated by a new dedicated Playwright spec at
  `frontend/screenshots/capture.spec.ts` pointing at the real
  `config.yaml`. The settings-paths capture was deliberately
  omitted (it shows personal `/mnt/...` mount paths).
  Kind: doc.
  Lanes: docs.
  Source: planned (deferred from P09 slim, 2026-05-04).

- ✅ [mame-curator-1030] **CONTRIBUTING.md (closed 2026-05-16).**
  Shipped: top-level `CONTRIBUTING.md` covering local-dev quickstart,
  bug-report template, the local CI gate (backend five + frontend
  three), TDD-first policy with per-module coverage floors, the
  per-feature `spec.md` requirement, Conventional Commits, a
  summary of the App-Build 9-step phase loop, and a "what this
  project deliberately does not do" section. README's short
  Contributing stub now points at `CONTRIBUTING.md`.
  Kind: doc.
  Lanes: docs.
  Source: planned (deferred from P09 slim, 2026-05-04).

---

## Considered / under research (no target date)

**Theme:** post-v1 features captured during user feedback. Each is
desirable but not urgent — they graduate to a release-target
section above once they reach the top of the queue. The status
emoji is 💭 because scope or feasibility is still being thought
through.

### 🎨 Features

- 🚧 [mame-curator-1005] **P10 — Media coverage expansion.**
  Add fallback art sources beyond libretro-thumbnails:
  progettoSnaps (~60–70% gap-closer, no auth, ~1 day),
  ArcadeDB JSON API (highest-quality images, rate-limited, ~2
  days), Wikipedia / MediaWiki (one or two sentences of flavor
  text on the alternatives drawer, ~1 day), and Mobygames
  (port-cover fallback, requires an API key, ~2 days). New
  `media.sources` array in `AppConfig` so users can opt out of
  slow or rate-limited sources. EmuMovies stays out of scope (paid
  account required).
  Layman: Many games show blank tiles because the upstream art
  source doesn't have them. Pull artwork from additional sites
  (progettoSnaps, ArcadeDB, Wikipedia, MobyGames) so more games
  show a face.
  Kind: implement.
  Lanes: media, frontend, tests.
  Source: user-2026-05-04 ("Are there additional sites that game
  metadata can be scraped from?").
  Dependencies: P05 ✅, FP10 ✅.

- 💭 [mame-curator-1010] **P12 — In-app self-update + INI
  diff-preview UI.**
  App self-update via `updates/app.py` (version compare; snapshot
  config / overrides / sessions before update; git-pull on dev
  mode or release-download on frozen install; one-click rollback).
  `updates.channel` wiring (`stable` checks tagged releases; `dev`
  checks `main`). UpdatesPanel in Settings ("Check now", "What's
  new" modal rendering the upstream CHANGELOG, "Apply update" with
  progress + rollback). INI refresh diff-preview modal: run new
  INI files against the parsed DAT and show "new winners / dropped
  winners / changed winners" before confirming.
  Layman: Let users update the app from inside it (no
  command-line). When the reference INI files update — the lists
  of "which games are mature", "which are best in show", etc. —
  show a preview of what'll change BEFORE applying ("12 games
  newly flagged mature; 3 unflagged").
  Kind: implement.
  Lanes: updates, frontend, api, tests.
  Source: planned (deferred from P07, 2026-05-04, with user
  acceptance: "I do still want self update but that can be added
  later").
  Dependencies: P07 ✅ (downloads + INI refresh CLI).

- 📋 [mame-curator-1079] **MobyGames cover-URL parse + JSON-body caching (P10 chunk 6 deferred half).**
  P10 chunk 6 shipped the key-handling half of `MobyGamesSource`
  (env/0600-dotfile resolution, missing-key + 401/403 disable,
  key-redacted errors, rate-limit). The success-path cover-URL
  extraction + JSON-body caching are DEFERRED: the spec's guessed
  `cover_url` field is unverified and the real MobyGames `/v1/games`
  response nests the cover differently, so the parse can't be written
  correctly without a real API key (none on this machine; no anonymous
  API access). To close: register a free key at mobygames.com, capture
  `tests/fixtures/mobygames_pacman.json`, pin the cover field path in
  docs/specs/P10.md § "4. MobyGames", implement the 200-path parse in
  `src/mame_curator/media/mobygames.py` (replacing the deferred no-op),
  add a happy-path `prepare`-populates-cover test, and delete
  `test_mobygames_source_200_does_not_populate_cover_yet`. Until then
  MobyGames is in the chain (when keyed) but yields no covers — it's
  last in the default fallback order, so zero user-visible regression.
  Dependencies: P10 chunk 7 (registry/orchestrator) does NOT block this;
  this can land as a post-P10 fix-pass.
  **Layman:** MobyGames knows your key but can't pull a cover image yet — that last step needs a real key to confirm the data format. Finish it once a key is available.
  Kind: implement.
  Source: in-session-2026-07-01 (P10 chunk 6 — user elected "key-handling now, fetch later").

- 💭 [mame-curator-1080] **UI localization — translate the interface into additional languages.**
  Frontend-only localization (i18n) of every visible label / message.
  Decision (2026-07-01, user): go route (a) — adopt a real i18n library
  (not the hand-rolled per-locale catalogue). All the strong React i18n
  libraries are free / open-source (MIT), so cost is not a factor.
  Shortlist for the Step-1 spec to lock: react-i18next (frontrunner —
  largest community + docs, safest for a solo maintainer), LinguiJS
  (alternative — native ICU message format + auto-extraction + strong
  TypeScript), FormatJS/react-intl (ICU-heavyweight fallback). Spec picks
  one after weighing how the 45 interpolation functions migrate + bundle
  size.

  New sub-decision the spec must also settle: source of the actual
  translated *text* (the library only organises/displays it). Human
  translation (most accurate) vs a machine-translation seed — free options
  noted for the latter: LibreTranslate (self-hostable OSS), Argos Translate
  (offline), DeepL free API tier. Likely: MT-seed 1-2 pilot locales, then
  refine.

  **Enabler (mostly done):** all user-facing copy already funnels through
  one catalogue — `frontend/src/strings_internal.ts` (682 lines, section-
  keyed) behind the stable `strings.ts` facade (DS02 A3). There are no
  scattered hardcoded strings to hunt down; that groundwork is the hard 80%.

  **The design fork to settle at spec time (Step 1):** 45 of the catalogue
  entries are interpolation *functions*, not plain strings — plurals,
  multi-arg, `n.toLocaleString()` (e.g. `progressChip(handled, total, pct)`,
  `bulkAdd(n)`). A naive `strings.<lang>.ts` object-swap can't localise
  those cleanly. Two credible approaches:
    (a) Adopt a real i18n library (react-i18next or FormatJS/react-intl)
        with ICU message format — proper plural/gender rules, locale
        detection + switching, an extraction pipeline for translators. Cost
        is migrating the 682-line catalogue + 45 functions to message keys.
    (b) Keep the typed hand-rolled catalogue: one `strings.<lang>.ts` per
        locale implementing the same shape (functions included) + a light
        locale-switch context. No new dependency, keeps the typed call
        sites, cheaper to start — but each translator writes plural logic
        in code and there's no ICU tooling.

  **Sub-pieces (regardless of fork):** browser-locale detection
  (`navigator.language`); a persisted UI-language config field (distinct
  from the game-metadata `languages.ini` / `region_priority` filtering —
  that's the games' own languages, not the app's); a Settings LanguageSwitcher
  (parallels ThemeSwitcher / LayoutSwitcher); number/date via `Intl`; a
  translation-file workflow; pick 1–2 pilot locales to prove the pipeline.

  **Out of scope:** backend stays English — it emits error *codes*, and the
  frontend `errorByCode` map already turns them into friendly copy, so
  localisation is entirely frontend-side. CLI (`rich.Console`) output stays
  English (operator-facing). RTL layout (Arabic/Hebrew) is a likely
  follow-up, not v1 of this feature.

  Kind: feature. Post-v1; needs a Step-1 spec + cold-eyes to resolve the
  fork before sizing. Dependencies: none hard.
  **Layman:** Today every menu, button, and message is English only. Add the ability to display the interface in other languages (Spanish, French, German, …) with a language picker in Settings, next to the existing theme and layout pickers.
  Kind: feature.
  Source: user-request-2026-07-01 ("Please roadmap adding support for additional languages" → clarified: translate the UI)..

### 🔌 Plugins / extensions

- 💭 [mame-curator-1007] **P11 — Contribute missing thumbnails
  back to libretro-thumbnails.**
  When the user has a CC-compatible image for a game the upstream
  repo doesn't have, generate a staged-files-plus-PR flow so the
  artwork can be contributed back. Default manual-PR path (`git
  format-patch` instructions, no GitHub auth needed); optional
  auto-PR path with a `keyring`-stored PAT scoped to `public_repo`.
  License gate confirms CC-BY compatibility before any upload.
  "Missing-upstream" library filter surfaces eligible candidates
  for batch contribution.
  Layman: When the app identifies a game the upstream art
  collection doesn't have, package the artwork and contribute it
  back (with the user's permission) so other people benefit too.
  Manual flow by default; optional one-click flow with a GitHub
  token.
  Kind: implement.
  Lanes: api, frontend, media.
  Source: user-2026-05-04 ("Can we upload ones they don't have on
  this github project?").
  Dependencies: P05 ✅; P10 (more useful alongside expanded local
  sources).

---

## Future enhancements

Captured in
[`docs/superpowers/specs/2026-04-27-roadmap.md` § "Future enhancements"](docs/superpowers/specs/2026-04-27-roadmap.md):
software-list routing, EmulationStation `gamelist.xml` exporter,
LaunchBox interop, DAT-version-upgrade workflow, cloud sync of
`overrides.yaml` / `sessions.yaml`, multi-user mode, i18n, themes
from more arcade classics. **Deliberately deferred** to keep
v1.0.0 shippable; not part of the v1 plan. Items graduate to
"Considered / under research" above when they near the front of
the queue.

---

## How to propose a roadmap item

1. **What** — one sentence describing the change.
2. **Why** — the problem it solves or the user need it serves.
3. **Prior art** — links to similar implementations elsewhere, if
   any.
4. **Scope** — what's in / what's out; rough size (one PR / one
   phase / multi-phase).
5. **Category** — which release target + theme section it belongs
   under.

Open a PR adding a bullet to the right section. Set the status
emoji to 📋 (planned) or 💭 (still researching). New bullets get
the next free `[mame-curator-NNNN]` from `.roadmap-counter` at the
repo root; bump the counter in the same PR.

```bash
# Allocate the next ID:
echo $(($(cat .roadmap-counter) + 1)) > .roadmap-counter
printf "mame-curator-%04d\n" $(cat .roadmap-counter)
```

See [`docs/standards/roadmap-format.md`](docs/standards/roadmap-format.md)
for the full format spec (`mame-roadmap-format: 1`).

---

## How findings get folded

After every `/audit`, `/indie-review`, or `/debt-sweep`, actionable
findings land in this file as a new `🔍 …-fold-in (YYYY-MM-DD)`
section under the active release target. False positives go to
[`docs/audit-allowlist.md`](docs/audit-allowlist.md); items
deferred on an unbuilt dependency go to
[`docs/known-issues.md`](docs/known-issues.md).

Closed phases and fix-passes move out of this file and into
[`CHANGELOG.md`](CHANGELOG.md). The full per-phase history (P00 →
P15 + FP01 → FP28 + DS01 → DS05) plus shipped releases
(v1.0.0 → v1.2.0) live there.

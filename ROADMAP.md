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

- 📋 [mame-curator-1039] **P15 — UI polish + theme expansion.**
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
P15 + FP01 → FP26 + DS01) plus shipped releases (v1.0.0 →
v1.2.0) live there.

# DS04 — Test-suite quality sweep

- **Status:** ✅ closed 2026-05-15 (tag `DS04-complete`; see `../journal/DS04.md`)
- **Kind:** refactor (test-code only — no production code changes; one production-spec citation update where a test was locking dead behaviour)
- **Source:** 5-lane test-suite audit 2026-05-15 (parser+filter / copy / api+media+downloads / frontend components+hooks+lib / frontend pages+e2e+strings) on commit `06fe3b8` (FP27-complete).
- **Theme:** the 5-lane audit surfaced 51 test-suite quality findings clustered by six shared patterns: (1) **dead-spec coverage** — tests that pass against code paths the spec retired (1 site, the FP25-C rollback pair contradicting `copy/spec.md:260`'s FP21-D supersession); (2) **prototype / global-state pollution** in vitest that leaks across files (3 sites); (3) **unnecessary I/O** — 50k-line JSONL writes, 6 MiB string allocations, 2 MB YAML writes, and a 2.5 s Playwright sleep; (4) **FP##-named test-file debris** — `test_fp01_fixes.py`, `test_fp02_fixes.py`, `test_fp09_fixes.py`, `test_fp21_fixes.py` containing assertions subsumed by canonical module tests; (5) **fixture / helper sprawl** — same `_machine`, `renderWithClient`, 47-line `config` blocks duplicated across 4-30 sites; (6) **over-cap test files** — `SettingsPage.test.tsx` (686), `tests/copy/test_runner.py` (528), `tests/copy/test_fp01_fixes.py` (478), `tests/parser/test_dat.py` (453), `tests/copy/test_recyclebin.py` (327) all over the project's 300-soft / 500-hard cap. Also covered: a tautological assertion, two unbounded sleeps, an empty Hypothesis strategy, and ~12 redundant `afterEach(() => cleanup())` calls under auto-cleanup-on.
- **Dependencies:** FP27 ✅ (closed 2026-05-14). No live FP## in flight.
- **Queue impact:** **none** — DS04 opens as a new entry `[mame-curator-1033]`. Existing planned `[mame-curator-1021] DS02 — Tier 3 structural debt sweep` is untouched. The user picked DS04 as next-up; the queue becomes: **DS04 (this) → FP28 → DS02 (existing source-code structural) → DS03 → P09 polish → post-v1**.
- **Out of scope (deferred — captured as roadmap entries):**
  - **Architecture / source-code Tier 3 cleanup** — already tracked as `[mame-curator-1021]` DS02 (untouched).
  - **CI sharding for `@pytest.mark.slow` tracemalloc tests** — DS04 adds the marker, but separate-job sharding in CI is a `.github/workflows/ci.yml` change scoped to DS03 (dependency + CI sweep).
- **Out of scope (sub-fixes reclassified to conditional follow-ups):**
  - **`SettingsPage.test.tsx` 686-line file split** — DS04 collapses ~110 lines (T2.6 fixture extract + T2.12 retroarch parametrize + T3.10 triple-test collapse). If the file is still over the hard cap after T2/T3 land, `[mame-curator-1034]` opens for the seam-split work. Otherwise the placeholder closes immediately at DS04 close-phase.
  - **`tests/copy/test_runner.py` 528-line file split** — DS04 removes ~60 lines (T1.7 dead monkeypatch + T2 helper hoisting). Hard-cap split deferred to `[mame-curator-1035]` if still needed; closed at DS04 close-phase if not.
  - **`tests/parser/test_dat.py` 453-line file split into basic/security/validation** — pure-structural; deferred to `[mame-curator-1036]` (Tier 3 follow-up; the file's findings are mostly polish per the audit).

## Why a single fix-pass

All 51 sub-fixes come from one 5-lane audit on one HEAD. They share a single risk pattern: **the test surface has accumulated debt at a faster rate than the production code it locks**. Closing the findings piecemeal would mean three separate `/audit` + `/indie-review` cycles for what is structurally one tidy-up. Per FP05 / FP25 / FP27 precedent: large-cohort review fold-ins ship as one fix-pass with thematic tiers inside.

## Pre-spec verification (global rule 13)

Every cited `file:line` below was grep-confirmed against current source at HEAD `06fe3b8` before the spec was finalised. Two citations from the audit agents were **dropped / corrected during pre-spec verification**:

- **Original audit T1.4 citation `tests/api/test_fp25_world_lock.py:233`** for the `Path("/tmp/unused") # noqa: S108` smell was filename-mistyped. `grep -n "noqa: S108" tests/api/test_fp25_world_lock.py` returns empty. The correct location is `tests/api/test_fp21_fixes.py:233`. Citation corrected; T1.4 retained.
- The "`tests/api/test_routes_activity.py:180` stale comment" finding is real (the comment still says `f"/tmp/{i}"` but the planter writes `f"sample://{i}"`), but folds into T1.10's planter rewrite (the comment goes away when the helper goes away). Not a separate Tier-1 entry.

Spot-confirmed (sample):
- **T1.1 FP25-C dead-spec coverage** — `tests/copy/test_fp25_recyclebin.py:34-93` contains `test_fp25_c_recycle_error_raised_when_manifest_write_fails` and `test_fp25_c_recycle_rollback_returns_file_to_original_on_manifest_failure`. The second test's assertion `assert src.exists(), "rollback must restore the source file"` is contradicted by `src/mame_curator/copy/spec.md:260`: *"The pre-FP21-D move-then-write-then-rollback envelope (FP25-C) is superseded by this ordering — under any single-step failure, the source file is intact at its original location."* The test passes today only because the post-FP21-D code raises `RecycleError` from the manifest write *before* the source has moved, so `src.exists()` is trivially true — but the test's *premise* (a rollback) is dead. Drop both T1.1 sub-tests.
- **T1.7 dead `executor.copy_one` monkeypatch** — `src/mame_curator/copy/runner.py:17` is `from mame_curator.copy.executor import copy_one`. Python's import binds `copy_one` into the `runner` module namespace; patching `executor.copy_one` after that import has no effect on `runner`. **Executor patch = dead, runner patch = load-bearing.**
- **T1.10 _plant_50k_activity_log** — `tests/api/test_routes_activity.py:79` defines the planter; lines 94 (`for i in range(50_000):`), 135, and 166 confirm two usage sites writing the full 50k JSONL twice.
- **T1.11 Playwright waitForTimeout(2500)** — `frontend/e2e/fp25-ux-walkthrough.spec.ts:46` is the sole `waitForTimeout` site across all e2e specs.
- **T1.12 6 MiB string allocation** — `frontend/src/components/settings/__tests__/BackupTab.test.tsx:120` builds `'x'.repeat(6 * 1024 * 1024)` as a File body to trigger the 5 MB cap; the cap check happens on `File.size`, so the bytes are dead allocation.
- **T1.13 dual TestClient setup-check tests** — `tests/api/test_routes_stubs.py:124,131` and `tests/api/test_routes_stubs.py:148,161` each construct a fresh `TestClient(create_app(...))` inside the test body, paying full lifespan setup twice for two boolean-permutation cases.
- **FP21-D supersession** — `copy/spec.md:260` (single sentence cited above) is the authoritative retirement of the FP25-C envelope; the same paragraph documents the new write-manifest-first ordering.

## Scope

### Tier 1 — real waste / risk (14 sub-fixes)

- **T1.1 — Delete the FP25-C rollback tests.** `tests/copy/test_fp25_recyclebin.py:34-93` (two tests: `test_fp25_c_recycle_error_raised_when_manifest_write_fails`, `test_fp25_c_recycle_rollback_returns_file_to_original_on_manifest_failure`). The second test's "rollback returns file to original" premise is contradicted by `copy/spec.md:260`. **Fix:** delete both tests; keep the two `test_fp25_f_*` tests in the same file (they cover the still-valid atomic-write `.tmp` cleanup invariant).
- **T1.2 — Fix `LibraryGrid.test.tsx` prototype pollution.** `frontend/src/components/library/__tests__/LibraryGrid.test.tsx:10-36` overrides `HTMLElement.prototype.clientHeight/clientWidth/getBoundingClientRect` in `beforeAll` with no `afterAll` restore. **Fix:** capture the original descriptors in `beforeAll` (via `Object.getOwnPropertyDescriptor`), restore in `afterAll`. Move the override into `src/test/setup.ts` if a second file ever needs it (rule of three).
- **T1.3 — Fix `useCopySession.test.tsx` global-mutation leak.** `frontend/src/hooks/__tests__/useCopySession.test.tsx:336-353` has a nested `describe` whose `beforeEach` (line 339-340) sets `globalThis.EventSource = MockEventSource` *directly* — bypassing `vi.stubGlobal`. The file-level `afterEach` at line 101 calls `vi.unstubAllGlobals()`, but it can't restore something it never stubbed, so the mock leaks. The nested `afterEach` (line 343-345) only re-calls `cleanup()` — a harmless duplicate, not the load-bearing issue. **Fix:** rewrite the nested `beforeEach` as `vi.stubGlobal('EventSource', MockEventSource)`; drop the redundant nested `afterEach`.
- **T1.4 — Replace hardcoded `/tmp/` path.** `tests/api/test_fp21_fixes.py:233` is `JobManager(history_dir=Path("/tmp/unused")) # noqa: S108`. The lint-suppression-without-rationale matches the exact smell global rule 1 warns against. **Fix:** request `tmp_path` in the test signature; pass it. Drop `# noqa: S108`.
- **T1.5 — Parametrize 3 iterparse-OSError tests.** `tests/parser/test_listxml.py:40-74` has three near-identical tests differing only in which `parse_listxml_*` callable is invoked. **Fix:** collapse to one `@pytest.mark.parametrize("callable_, exc_match", [...])` over `(parse_listxml_disks, parse_listxml_cloneof, parse_listxml_bios_chain)`.
- **T1.6 — Relocate `test_listxml_cloneof.py`.** Currently `tests/filter/test_listxml_cloneof.py` but it tests the `parser/` module. The companion fixture `tests/filter/fixtures/listxml_cloneof.xml` moves with it. **Fix:** `git mv` both into `tests/parser/`; update fixture path resolution in the test if needed.
- **T1.7 — Remove dead `executor.copy_one` monkeypatch.** `tests/copy/test_runner.py:381-438` does `monkeypatch.setattr(executor, "copy_one", ...)` AND `monkeypatch.setattr(runner_module, "copy_one", ...)`. The executor patch is dead (runner imports `copy_one` into its own namespace at module load); the runner patch is load-bearing. **Fix:** delete the executor patch line; keep the runner-module patch.
- **T1.8 — Collapse 3 `data-columns` formula tests to `it.each`.** `LibraryGrid.test.tsx:69-152` has three tests asserting `data-columns === '5' | '6' | '1'` against the formula. **Fix:** `it.each([[1200, 'masonry', undefined, '5'], [1200, 'masonry', 6, '6'], [1200, 'list', 8, '1']])('renders N columns', ...)`.
- **T1.9 — Drop bare `time.sleep(0.1)`.** `tests/api/test_routes_copy.py:111` adds 100 ms per run with no assertion gating it. Comment claims "event-driven check is in test_sse.py; here a single sleep is sufficient" — but the test ends before the sleep matters. **Fix:** delete the sleep.
- **T1.10 — Lift `_plant_50k_activity_log` to a fixture.** `tests/api/test_routes_activity.py:79-156` plants the 50k JSONL twice (~5–10 MB I/O × 2). **Fix:** `@pytest.fixture(scope="function")` returning the path; both consuming tests reuse it. Drop the stale `# report_path is f"/tmp/{i}"` comment at line 180 (planter writes `f"sample://{i}"`).
- **T1.11 — Replace Playwright `waitForTimeout(2500)`.** `frontend/e2e/fp25-ux-walkthrough.spec.ts:46`. **Fix:** `await expect(toasts).toHaveCount(1)` using Playwright's default polling timeout; assert dedup by checking count stays at 1 after the natural wait.
- **T1.12 — Stub `File.size` instead of allocating 6 MiB.** `frontend/.../BackupTab.test.tsx:120-124`. **Fix:** `const huge = new File(['x'], 'huge.json', {type:'application/json'}); Object.defineProperty(huge, 'size', { value: 6 * 1024 * 1024 })`. Zero bytes allocated; same cap-check semantics.
- **T1.13 — Parametrize setup-check `retroarch_configured` tests + share TestClient.** `tests/api/test_routes_stubs.py:115-161` (two tests, fresh `TestClient(create_app())` each) + `tests/api/test_fp09_fixes.py:191-218` (second `TestClient(app)` inside a test that already has a fixture client). **Fix:** stubs.py — collapse to one `@pytest.mark.parametrize("retroarch, core, expected", [(True, False, False), (False, True, False), (True, True, True)])`. fp09.py — request the fixture's `client`; don't create a second.
- **T1.14 — Tighten tautological `querySelectorAll` count.** `LibraryGrid.test.tsx:69-70` asserts `expect(rendered).toBeLessThan(cards.length)` where `cards.length === 3000` — passes even at zero virtualised cards. **Fix:** `screen.queryAllByRole('button', { name: /^Game \d+/ })` so the assertion measures rendered cards specifically, not any nested button.

(Original audit T1.15 — `test_recyclebin.py:62-63` legacy-mtime fallback — reframed to Tier-3 docstring clarification, see T3.13 below. The legacy-fallback code path is still live and correctly exercised.)

### Tier 2 — polish, helper extraction, FP-debris fold-in (19 sub-fixes)

- **T2.1 — Promote `_machine(short, desc)` to `tests/copy/conftest.py`.** Currently duplicated at `test_fp01_fixes.py:36`, `test_fp02_fixes.py:33`, `test_runner.py:26`, `test_preflight.py:15`. **Fix:** define once in `tests/copy/conftest.py` as a fixture or module-level helper; import sites.
- **T2.2 — Promote `_plan(...)` builder to `tests/copy/conftest.py`.** Currently inlined in `test_runner.py:30-52`, `test_preflight.py:19-33`, `test_fp01_fixes.py:111-120`. **Fix:** same as T2.1.
- **T2.3 — Promote `_seed_existing_playlist` + `_entry` helpers to `tests/copy/conftest.py`.** Duplicated verbatim between `test_fp01_fixes.py:75-86` and `test_fp02_fixes.py:37-59`.
- **T2.4 — Promote `_make_job(manager, plan, history=...)` to `tests/api/conftest.py`.** `tests/api/test_fp21_fixes.py:60-67, 141-180` copy-paste 12 lines of `Job(...)` construction with the same plan / dummy controller / `Thread()`.
- **T2.5 — Extract `renderWithClient` to `frontend/src/test/queryWrapper.tsx`.** Currently duplicated in `useConfig.test.tsx`, `useFs.test.tsx`, `useValidateCart.test.tsx`, `useCopySession.test.tsx`, `FsBrowser.test.tsx`, `queryClient.test.tsx`. **Fix:** one helper exporting `renderWithClient(ui, { retry: false } = {})`.
- **T2.6 — Extract `SettingsPage.test.tsx` `config` fixture.** 47-line fixture inlined ~30 times across the 686-line file. **Fix:** move to `frontend/src/test/fixtures/configResponse.ts` exporting a `baseConfig()` factory.
- **T2.7 — Extract `tests/api/conftest.py` 50-line YAML literal.** `tests/api/conftest.py:101-173`. **Fix:** lift to `tests/api/fixtures/config_template.yaml`; `read_text().format(...)` at the fixture call site.
- **T2.8 — Extract `no-checkbox-for-prefs.test.tsx` 47-line fixture.** Lines 22-69. **Fix:** import the `baseConfig()` factory from T2.6 (the shape is the same).
- **T2.9 — Delete duplicate KeyboardInterrupt-cleanup test.** `tests/copy/test_fp01_fixes.py:43-69` and `tests/copy/test_fp02_fixes.py:317-339` both assert `copy_one` cleans `.tmp` on `KeyboardInterrupt`. Post-FP27-B1 both branches funnel through `_chunked_copy`, so they exercise the same code path. **Fix:** keep FP02's variant (uses `progress=` callback — exercises the more common code path); delete FP01's.
- **T2.10 — Delete duplicate same-second-recycle tests.** `tests/copy/test_fp01_fixes.py:247-269` ≈ `test_fp02_fixes.py:158-194` ≈ `test_recyclebin.py:95-107`. **Fix:** keep FP02's (strongest, exercises `session_id`-distinguishing assertion) and `test_recyclebin.py`'s (canonical); delete FP01's copy.
- **T2.11 — Delete duplicate `CopyError.__str__` repr tests.** `tests/copy/test_fp01_fixes.py:332-342` is subsumed by `tests/copy/test_errors.py:15-46` (which already iterates over all subclasses). **Fix:** delete FP01's pair.
- **T2.12 — Parametrize `SettingsPage.test.tsx` retroarch_configured tests.** Lines 77-145 (two near-identical 70-line tests differing only in one boolean and one expected-text regex). **Fix:** `it.each([[true, /configured/i], [false, /not configured/i]])`.
- **T2.13 — Drop cart-flow e2e unit-duplicate tests.** `frontend/e2e/cart-flow.spec.ts` re-asserts "Copy disabled when empty" (lines 83-90), expand chevron toggle (line 67), remove row (lines 74-80), empty-bar after remove — all already covered at `CartBar.test.tsx` + `CartPanel.test.tsx`. **Fix:** keep only the **"cart flow: add → footer-updates → ✓Added → onboarding-banner-dismiss"** integration scenario (the top-of-file `test('cart flow', ...)` block) — that is the only e2e-only coverage. Drop the three Unit-duplicate `test('cart: ...')` blocks below it.
- **T2.14 — Fix Hypothesis empty-strategy test.** `tests/api/test_routes_config.py:126-141` uses `@given(st.fixed_dictionaries({}))` which generates only `{}`. **Fix:** either delete `@given` (it's pure scaffolding) or expand the strategy to actual no-op shapes. Prefer delete.
- **T2.15 — Extract `withSandboxedFsHandlers()` helper.** `frontend/.../FsBrowser.test.tsx:50-73, 153-167, 228-241, 263-277, 313-336` — 5 near-identical `server.use(...)` blocks for the `fs_sandboxed` listing.
- **T2.16 — Reuse `_OVER_CAP` for 1-MiB cap tests.** `tests/filter/test_overrides.py:64` and `tests/filter/test_sessions.py:107` each write a 2 MB string via `tmp_path` for a 1-MiB pre-parse cap check. The cap fires on byte length — same `_OVER_CAP = b"0" * (1024*1024 + 1)` pattern from `test_io.py:16` works. **Fix:** parametrize / share the byte payload; drop the 2 MB writes.
- **T2.17 — Drop or `@pytest.mark.slow` the `perf_counter` flake-prone assert.** `tests/parser/test_dat.py:173-193` has a secondary `elapsed < 5.0` assertion alongside the load-bearing 100 KB length assert. **Fix:** drop the elapsed assertion; the length one stands alone.
- **T2.18 — Remove Linux-only `OSError-skip` clauses.** Six sites in `test_overrides.py:88-91`, `test_sessions.py:244-245, 297-298`, `test_io.py:31-32, 49-51, 70-71`. Project's CI is Linux-only. **Fix:** delete the `try/except OSError: pytest.skip(...)` blocks; tests run on Linux unconditionally.
- **T2.19 — Fix module-scoped fixture mutation.** `tests/copy/conftest.py source_dir` is `scope="module"` but `tests/copy/test_executor.py:99` writes `big.zip` into it, leaking state across tests in the module. **Fix:** create `big.zip` inside the consuming test via `tmp_path / "big.zip"`, not into the shared fixture.

### Tier 3 — informational + light polish (13 sub-fixes)

- **T3.1 — Remove 12 redundant `afterEach(() => cleanup())` calls.** Vitest auto-cleanup is on globally (`globals: true` + RTL `cleanup` auto-registered). **Fix:** delete the explicit `afterEach(() => cleanup())` from `FiltersSidebar.test.tsx`, `ChipListEditor.test.tsx`, `DragReorderList.test.tsx`, `BackupTab.test.tsx`, `FsBrowser.test.tsx`, `SnapshotsTab.test.tsx`, `YearRangeEditor.test.tsx`, `EscOverlayBehavior.test.tsx`, `useConfig.test.tsx`, `useFs.test.tsx`, `useCopySession.test.tsx`, `useValidateCart.test.tsx`.
- **T3.2 — Fix `getByText().closest('button')` a11y-anti-pattern.** `frontend/.../FeaturedTilesRow.test.tsx:32-34`. **Fix:** `getByRole('button', { name: 'Capcom Classics' })`.
- **T3.3 — Delete pure `pytest.skip` placeholder.** `tests/api/test_routes_games.py:217-233` is a `pytest.skip` whose only purpose is to point at `tests/filter/test_runner.py:156` for the real coverage. **Fix:** delete the test; record the cross-reference in `api/routes/spec.md` or wherever the API contract for the no-listxml self-parents behavior lives.
- **T3.4 — Tag `tracemalloc` tests with `@pytest.mark.slow`.** Three sites: `tests/api/test_routes_activity.py` (B5 50k log), `tests/media/test_cache.py` (B4 streaming), `tests/test_downloads.py` (B3 streaming). Threshold-brittle. **Fix:** add the marker; register `slow` in `pyproject.toml [tool.pytest.ini_options]`.
- **T3.5 — Delete or implement `src/test/fixtures.ts`.** Currently a 7-line doc-only file promising a "3,000-card grid fixture built lazily" that doesn't exist; `LibraryGrid.test.tsx` reimplements `fakeCards()` locally. **Fix:** delete the file (post-T1.8, the data-columns tests collapse and the imagined fixture is over-engineered).
- **T3.6 — Update `CmdK SECTION_ORDER` test pattern.** `frontend/.../CmdKPalette.test.tsx:89-105` uses `throw new Error(...)` for the static-export assertion. **Fix:** `expect(SECTION_ORDER).toEqual(['actions', 'help'])`. Better diagnostic; idiomatic vitest.
- **T3.7 — Drop tautological `cart.getAttribute('href')` assertion.** `frontend/.../AppShell.test.tsx:32` — the prior line already asserts `tagName === 'BUTTON'`, so `href === null` is implied. **Fix:** delete the redundant assert.
- **T3.8 — Don't assert Tailwind class strings.** `frontend/.../AppShell.test.tsx:42-49` asserts `font-medium` class — implementation detail. **Fix:** assert `aria-current="page"` (the semantically correct active-link signal).
- **T3.9 — Delete `EscOverlayBehavior.test.tsx`.** The suite tests Radix's built-in `<Dialog>`/`<AlertDialog>` Escape-key behaviour, not project code. FP27 A6a's contract was "doc-truth the design spec to credit Radix"; the regression-lock test is library-coverage. **Fix:** delete the file. Radix upgrades surface via dependency-bump regression in DS03.
- **T3.10 — Collapse `SettingsPage.test.tsx:593-608` triple-test cluster.** Three tests in a row hammer the DAT-confirm flow with overlapping assertions. **Fix:** keep `open-confirm` and `cancel-resets-and-no-patch`; delete the third.
- **T3.11 — Switch Playwright trace setting.** `frontend/playwright.config.ts` currently `trace: 'retain-on-failure'` with `retries: process.env.CI ? 2 : 0`. **Fix:** `trace: 'on-first-retry'`.
- **T3.12 — Pin one outcome in `HelpPage.test.tsx:160-191`.** The `FP25-J` test accepts two outcomes (img absent OR img with no src) and `return`s early on outcome (a), making the assertion vacuous on that branch. **Fix:** pin to one outcome (whichever the current renderer produces); the test becomes non-vacuous.
- **T3.13 — Document legacy-mtime fallback in `test_recyclebin.py:62-63` docstring.** The test correctly exercises a still-live legacy code path (purge eligibility falls back to dir mtime when no manifest is readable), but the audit's confusion is symptomatic of an under-commented fallback. **Fix:** add a one-line docstring naming the legacy-fallback path.

## Acceptance criteria (closed 2026-05-15; see `../journal/DS04.md` for outcomes)

> **Post-close path drift:** several citations below predate the
> DS05 test-file seam-split sweep (closed 2026-05-16). In particular,
> `tests/parser/test_dat.py` was split into `test_dat_basic.py` +
> `test_dat_security.py` + `test_dat_validation.py` per
> `[mame-curator-1036]`. Pre-DS05 paths are preserved here as the
> historical record; current paths are in the journal.

- All five gates green after every batch: `pytest`, `ruff check`, `ruff format --check`, `mypy`, `bandit -ll`.
- Frontend gates green: `npm run lint`, `npm run typecheck`, `vitest --run`, `playwright test` (9 e2e → ≤ 9).
- Coverage gates per `CLAUDE.md`: `parser/` ≥90, `filter/` ≥95, `copy/` ≥85, `api/` ≥80, frontend ≥70, overall backend ≥85.
- **Baseline captured at Step 2** of the loop; per-batch test counts may only drop where a deletion is itemised in this spec. No silent regressions.
- Zero `# noqa: S108` in `tests/` after T1.4.
- Zero `time.sleep(...)` in `tests/` without an inline rationale comment after T1.9.
- Zero `page.waitForTimeout(...)` in `frontend/e2e/` after T1.11.
- No test file over the **hard cap** of 500 lines after the sweep — **or** an explicit conditional follow-up opened against it. `test_runner.py` (528) and `test_fp01_fixes.py` (478, edge) were the at-risk files; T1.7 + T2 helper hoisting brought `test_runner.py` down slightly but it stayed over cap, so the residual splits were tracked as `[mame-curator-1034]` / `[mame-curator-1035]` / `[mame-curator-1036]` and resolved in DS05.
- Every FP## test file's remaining content has been justified (kept = structural/introspection coverage canonical files don't have; deleted = subsumed).

## Test strategy

This is a **test-of-tests** sweep — the production behaviour the tests lock does not change. The Step 3 "RED" phase is unusual:

- **For deletions (T1.1, T1.9, T2.9–T2.11, T2.13, T2.14, T3.1, T3.3, T3.5, T3.9)** — RED is "the test exists and passes today; the deletion is justified by the spec/audit citation, not by a new failing test". Each deletion gets a rationale comment in the batch commit message.
- **For refactors (T1.2, T1.3, T1.5, T1.6, T1.7, T1.8, T1.10, T1.13, T2.1–T2.8, T2.12, T2.15, T2.16, T2.18, T2.19, T3.2, T3.6–T3.8, T3.10, T3.11, T3.12, T3.13)** — same green-after-refactor expectation: the test passes before and after, just with less debt around it.
- **For corrections (T1.4, T1.11, T1.12, T1.14, T2.17)** — same: the test still passes after the fix, just exercises the contract cleanly.

The integrity check is: **before each batch**, capture `pytest -q | tail -1` count + per-module coverage percentages; **after each batch**, the count may drop (deletions) but coverage must not regress below the gate.

## Batching

- **Batch T1a — Tier 1 backend mechanical** (T1.1 delete FP25-C tests, T1.5 parametrize iterparse, T1.6 relocate test_listxml_cloneof, T1.7 dead monkeypatch, T1.9 drop sleep, T1.10 fixture-ify planter, T1.13 parametrize setup-check). ~150 LoC delta.
- **Batch T1b — Tier 1 hardening** (T1.4 noqa:S108 → tmp_path). ~5 LoC delta.
- **Batch T1c — Tier 1 frontend** (T1.2 prototype-pollution restore, T1.3 useCopySession hook conflict, T1.8 it.each, T1.11 Playwright sleep replace, T1.12 File.size stub, T1.14 tighten querySelectorAll). ~80 LoC delta.
- **Batch T2a — Tier 2 backend helpers + deletions** (T2.1–T2.4 conftest helpers, T2.7 YAML extract, T2.9–T2.11 dup deletions, T2.14 Hypothesis fix, T2.16 _OVER_CAP reuse, T2.17 perf_counter assert, T2.18 OSError-skip removals, T2.19 fixture mutation). ~250 LoC delta.
- **Batch T2b — Tier 2 frontend** (T2.5 renderWithClient, T2.6 + T2.8 configResponse fixture, T2.12 retroarch parametrize, T2.13 cart-flow e2e duplicates, T2.15 withSandboxedFsHandlers). ~200 LoC delta.
- **Batch T3 — Tier 3** (T3.1–T3.13 — all light polish, can land as one). ~70 LoC delta.

Six batches; commit count target ~6 + 1 closing-review cluster commit + 1 close commit. Cluster R1 fold-in only if the closing review surfaces new findings on the sweep itself.

## Conditional roadmap follow-ups

Each item below opens a ROADMAP placeholder at DS04 open-phase; closing checklist verifies file size post-T2/T3 and **closes the placeholder immediately** (drops the bullet) if the work landed inline, or leaves it `📋` if still needed:

- **`[mame-curator-1034]`** `SettingsPage.test.tsx` seam-split — opens only if T2.6/T2.12/T3.10 don't bring it under the 500-line hard cap.
- **`[mame-curator-1035]`** `tests/copy/test_runner.py` seam-split — same gating condition.
- **`[mame-curator-1036]`** `tests/parser/test_dat.py` split into basic/security/validation — pure-structural; cosmetic file-cap polish.

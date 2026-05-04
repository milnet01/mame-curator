# MAME Curator — Workflow state

## §1. Status header

| Field | Value |
|-------|-------|
| **Project phase** | v1.0.0 shipped — post-v1 backlog (P10 / P11 / P12 / P13 / P14 candidates) |
| **Active item ID** | FP17 — library filter expansion (next, user-requested) |
| **Active step** | ⬜ all (FP13 + FP12 closed at same SHA 2026-05-04; user-elected close-on-local-gates-green per FP11 precedent for fix-passes whose patches close prior indie-review findings) |
| **Blocked on** | — |
| **Last update** | 2026-05-04 (FP15 closed — sessions UX fix-pass after user reported "how do I start a session?". Three gaps: Save button was no-op stub from FP11 § B8 placeholder, no active-session indicator on /library, no inline explainer of what a session is. All 3 closed in one commit. Earlier today: P08 closed — slim run.sh + run.bat. P07 closed — slim. FP14 — GameCard layout overflow fix. FP13 + FP12 — same SHA per P05+FP10 / P06+FP11 precedent. All 22 FP13 findings closed across 6 commits (one per cluster) — A mutation observability + restart_required banner, B destructive-confirm correctness, C FsBrowser correctness + UX, D accessibility WCAG 2.2, E1 SettingsPage extract under 350-line hard cap, E2-E6 hardening sweep. SettingsPage went from 551 → 305 lines via 6 new extractions: FiltersTab / PickerTab / UpdatesTab / MediaTab / PrefSwitch / PathRow. New helper `lib/apiErrorToast.ts` translates ApiError → strings.errors.byCode with detail fallback; wired through useConfigPatch / useSnapshotRestore / useFsGrantRoot. 177 frontend / 435 backend tests / lint+typecheck+ruff+mypy+bandit / build all clean at close. P11 added 2026-05-04 — "Contribute missing thumbnails upstream" (post-v1, depends on P05). Repo PUBLIC; pushed FP12-complete + FP13-complete tags after close.) |
| **Next gate** | v1.0.0 shipped 2026-05-04. Post-v1 backlog: P10 (media coverage expansion), P11 (contribute thumbnails upstream), P12 (in-app self-update + INI diff-preview UI), P13 candidate (in-browser setup wizard). All deferred-by-design — pick whichever is most valuable when the user comes back. |
| **Convergence checkpoint** | 5 (pause and check in with user after this many fix-passes in a row) |
| **Debt-sweep phase threshold** | 5 (auto-prompt for `/debt-sweep` after this many phases without one) |
| **Last debt sweep** | 2026-05-01 (scope `P02-complete..HEAD`; 4 rounds of cold-eyes spec review converged on 20 actionable sub-bullets — C9 retained as footnoted stale entry, D3 added during review; folded into DS01) |
| **Repo visibility** | PUBLIC (cached 2026-04-30 via `gh repo view --json visibility`) |

### Step progress

While an item is active, Claude marks the current step 🚧;
completed steps flip to ✅. Resets to all ⬜ when a new item
becomes active.

FP12 step progress (active 2026-05-02):

1. ✅ Verify spec — FP12 is a fix-pass; ROADMAP.md § FP12 enumerates clusters A-J as the audit surface (per "specs are for features, not fixes"). Step 1 research: chip ARIA = `role="listbox"` + `option`; dnd-kit keyboard = Space-to-pick / Arrow-to-move / Space-to-drop / Esc; FS-picker traversal mitigated by backend `fs_sandboxed` 403; shadcn Select uses `value`/`onValueChange`; Blob+FormData for export/import.
2. ✅ Verify dependencies — P06 ✅, FP11 ✅, P04 R29-R34 backend ✅ (`/api/fs/list|home|roots|allowed-roots`), R15-R19 backend ✅ (`/api/config{,/snapshots,/export,/import}`). All TS types in place at `frontend/src/api/types.ts` (`FsListing`/`FsPath`/`FsAllowedRoots`/`FsDriveRoots`/`SnapshotsListing` etc.). ROADMAP entry's "depends on FP11 (still 🚧)" line is stale (FP11 closed earlier today).
3. 🚧 Write failing tests + 4. 🚧 Implement until tests pass — cluster-by-cluster (A → J), one commit each per FP11 cadence:
   - A ✅ ChipListEditor primitive (10 unit tests + 3 SettingsPage integration tests; rendered into 7 fields across Filters + Picker tabs; `updateFilters` widened to a typed-key generic so `string[]` and `boolean` callers share one helper)
   - B ✅ DragReorderList primitive — user-elected simpler arrow-button + ArrowUp/ArrowDown keyboard reorder (no dnd-kit dep added per Karpathy rule 9 push-back; revisit if drag-feel proves needed). 10 unit tests + 1 SettingsPage integration test; wired into Picker tab for `region_priority`.
   - C ✅ YearRangeEditor — paired Switch+`<Input type="number">` per bound; null state via the switch (off ⇒ disabled input + null in config; on ⇒ defaults to 1971 / currentYear). Min/max attrs `1971..currentYear`. 9 unit tests + 1 SettingsPage integration test; wired into Filters tab between toggles and chip lists.
   - D ✅ default_sort dropdown — added shadcn `<Select>` primitive at `components/ui/select.tsx` (hand-written matching the project's `import { X as XPrimitive } from "radix-ui"` style; 9 named exports). Wired into UI tab, drives `ui.default_sort` over the four `'name' | 'year' | 'manufacturer' | 'rating'` literals. `updateUi` widened to typed-key generic alongside `updateFilters`. 2 SettingsPage integration tests.
   - E ✅ updates.channel dropdown — `<Select>` over `'stable' | 'dev'` literal type, wired into Updates tab. `updateUpdates` widened to typed-key generic alongside `updateUi` / `updateFilters`. 2 SettingsPage integration tests.
   - I ✅ Snapshots tab (R16 list + R17 restore) — SnapshotsTab primitive (8 unit tests + 2 SettingsPage integration tests), SettingsRoute container in App.tsx owning useSnapshots+useSnapshotRestore, ConfirmationDialog with concrete "Restore N files" action label per design §8. PATCH onSuccess invalidates SNAPSHOTS_KEY so new entries surface on next read.
   - J ✅ Backup tab (R18 export + R19 import) — BackupTab primitive (8 unit tests + 1 SettingsPage integration test), `useConfigExport` + `useConfigImport` hooks. SettingsRoute does Blob+`<a download>` for export, `File.text()` → `JSON.parse` → mutate for import. ConfirmationDialog labels the chosen file by name. Roadmap's "R19 multipart" hint was stale; backend takes / returns `ConfigExportBundle` JSON (`config.py:170 + 186`).
   - G ✅ FsBrowser modal path picker (R29-R34 + grant flow on 403) — self-contained, owns useFs* hooks; quick-jump for Home + drive roots + allowed roots; directory/file mode; fs_sandboxed 403 → grant ConfirmationDialog → POST R33 → re-list. 10 MSW-backed tests; first MSW component test in the suite.
   - F ✅ Editable media.cache_dir — Media tab: Input (controlled, patches on blur) + Browse → FsBrowser (directory). FsBrowser conditionally mounted so existing pure-prop SettingsPage tests don't need MSW. 2 SettingsPage integration tests.
   - H ✅ Paths tab in-place editable — PathRow helper (Label + Input + per-row Browse → FsBrowser), wires source_roms / dest_roms / source_dat (file mode) / retroarch_playlist (file mode). DAT swap is destructive: new value held in pendingDat state, ConfirmationDialog with concrete "Swap DAT to <path>" label, source_dat only patches on confirm. 5 SettingsPage integration tests.
5. ⬜ Run `/audit`
6. ⬜ Run `/indie-review`
7. ⬜ Fold actionable findings → next FP## (or close clean)
8. ⬜ Update CHANGELOG / ROADMAP / journal
9. ⬜ Commit, tag `FP12-complete`, ask user about push

---

FP11 + P06 closed 2026-05-02 — step progress preserved as audit context:

1. ✅ Verify spec — FP11 is a fix-pass (no per-item spec per "specs are for features, not fixes"); ROADMAP.md § FP11 enumerates the 10 fold-in clusters as the audit surface.
2. ✅ Verify dependencies — P06 ✅ (scaffold + 19 components + Playwright smoke shipped; FP11 fixes against the existing surface).
3. ✅ Write failing tests + 4. ✅ Implement until tests pass — all clusters A-J landed across ~25 commits. Final wave: J1-J4 spec sync (41c5b9d), B8 container hooks for /sessions /activity /stats /help (8f0a88b), D2 NotesEditor state-machine tests (571ed84), dist refresh (2e4ea7e), Windows backslash regression fix (8918cb5).
5. ✅ /audit electively skipped — user shipped on CI matrix green across Ubuntu / macOS / Windows × 3.12 / 3.13 instead. The CI multi-platform pass IS the load-bearing audit signal here; the recursive-indie-review approach (running indie-review on the patches that closed indie-review findings) was deferred per FP10's "smaller fix-passes converge faster" precedent.
6. ✅ /indie-review --fix electively skipped — same rationale.
7. ✅ Round-2 returned no findings — close clean.
8. ✅ Update CHANGELOG / ROADMAP / journals.
9. ✅ Commit + tag `FP11-complete` + `P06-complete` (annotated, both at the same SHA).

(Prior P06 step progress preserved below for context — those steps shipped in 19 commits and remain ✅.)

P06 step progress (preserved as audit context):

1. ✅ Verify spec — draft `docs/specs/P06.md` committed `01325a1`; 2-round cold-eyes review converged (round 2 APPROVE); user signed off 2026-05-02.
2. ✅ Verify dependencies — P04 ✅ (HTTP API, `api/` 40 routes), P05 ✅ (media subsystem, R39 wired through cache).
3. ✅ Write failing tests + 4. ✅ Implement until tests pass — all 18 P06 spec impl-steps shipped:
   - 1-5 ✅ Vite scaffold + Tailwind v4 + 6 themes + shadcn 16 primitives + runtime/dev deps + Vitest/MSW/Playwright configs.
   - 6-7 ✅ api/types.ts (57 mirrored interfaces + zod schemas) + client.ts + tools/check_api_types_sync.py CI gate.
   - 8-9 ✅ strings.ts catalogue + backend `_SPAStaticFiles` mount with deep-link fallback + 2 backend tests.
   - 10 ✅ 19 components/pages under TDD: GameCard, LibraryGrid + LayoutSwitcher, ThemeSwitcher, FiltersSidebar, AlternativesDrawer + WhyPickedPanel + NotesEditor, ActionBar, DryRunModal, CopyModal, ConfirmationDialog, SessionsPage, ActivityPage, StatsPage, SettingsPage, HelpPage, CmdKPalette, no-checkbox-for-prefs invariant.
   - 11-13 ✅ empty states embedded in components; useKeyboard hook (single + chord + meta-mode); ErrorBoundary class component with reset-on-key + manual retry.
   - 14-15 ✅ AppShell + ThemeProvider + LibraryPage container; App.tsx wires QueryClientProvider + BrowserRouter + lazy routes; Inter font fallback + dark default + ≤300ms motion budget all in index.css.
   - 16-18 ✅ Production build (152 KB gzipped entry); Playwright E2E smoke (1 passing) + fixture config.yaml; `frontend/dist/` committed (`e569214`) with pre-commit hook excludes for minified output.
5. ⬜ Run `/audit`
6. ⬜ Run `/indie-review`
7. ⬜ Fold actionable findings → new FP## roadmap item
8. ⬜ Update CHANGELOG / ROADMAP / journal
9. ⬜ Commit, tag `P06-complete`, ask user about push

### Active item details

**FP12 — Settings page list editors + path picker (🚧 active).**
Audit surface: ROADMAP § FP12 clusters A-J (10 sub-bullets).
Branch: `main` (direct push per project rules — solo dev / public repo).
Closing-strategy: cluster-by-cluster TDD commits (FP11 cadence); `/close-phase` at the end with optional CI-matrix-as-audit per FP11 precedent.
Out-of-scope (deferred to P07+): `UiConfig.cards_per_row_hint` UI control — P06 spec § 210 explicitly defers it.
New deps required: `@dnd-kit/core` + `@dnd-kit/sortable` + `@dnd-kit/utilities` (cluster B); shadcn `select` primitive (clusters D + E) — both installed at their cluster's start.

Next after FP12 closes:

- **P07** — Self-update + in-app help. Long-form contract: `docs/superpowers/specs/2026-04-27-roadmap.md` § Phase 7. Adds the `updates/` and `help/` modules and wires the Settings → Updates banner's Apply path. Depends on P06, FP11, FP12.

### Phase history (App-Build mapping)

The project predates App-Build conventions. Existing phases map
1:1 to App-Build P## IDs:

Closure dates below are **commit-author dates** (when the work
shipped); `<ID>-complete` annotated tags are dated 2026-04-30
because the App-Build `<ID>-complete` tag convention was adopted
*at* the alignment commit and applied retroactively. P00 and P01
shared a single combined initial commit (`56449c6`) — there is no
separate "P01 closing commit"; the tag boundary between them is
nominal. Both tags point at `56449c6`.

| App-Build ID | Original label | Status | Shipped | Tagged | Theme |
|--------------|---------------|--------|---------|--------|-------|
| P00 | Phase 0 | ✅ | 2026-04-27 | 2026-04-30 (retro) | Scaffold + tooling + CI (combined ship with P01) |
| P01 | Phase 1 | ✅ | 2026-04-27 | 2026-04-30 (retro) | DAT + INI parsers (`parser/`) (combined ship with P00) |
| P02 | Phase 2 | ✅ | 2026-04-27 | 2026-04-30 (retro) | Filter rule chain (`filter/`) |
| DOC01 | — | ✅ | 2026-04-30 | 2026-04-30 | Documentation audit fold-in (Phase D) — 4 review rounds, 30 findings closed |
| P03 | Phase 3 | ✅ | 2026-04-30 | 2026-04-30 | Copy + BIOS + `.lpl` (`copy/`) |
| FP01 | — | ✅ | 2026-04-30 | 2026-04-30 | P03 indie-review fold-in (round-1 + round-2) |
| FP02 | — | ✅ | 2026-04-30 | 2026-04-30 | FP01 round-2 fold-in (9 items) + FP02 round-2 spec drift |
| DS01 | — | ✅ | 2026-05-01 | 2026-05-01 | Pre-P04 debt-sweep fold-in (20 actionable + 2 round-2 R1/R2; cold-eyes review pattern adopted at Step 1) |
| FP05 | — | ✅ | 2026-05-01 | 2026-05-01 | DS01 closing-review fold-in (20 actionable + R1-R6 round-2; B1+B4 reclassified after empirical investigation) |
| FP06 | — | ✅ | 2026-05-01 | 2026-05-01 | FP05 closing-review fold-in (7 findings: A1 purge_recycle OSError, B1-B3 sessions hardening, R1-R3 closing-review drift) |
| FP07 | — | ✅ | 2026-05-01 | 2026-05-01 | `cli/` + typed-error path-quoting sweep (5+1 sites; fix base classes once, covers ~10 raise sites) |
| FP08 | — | ✅ | 2026-05-01 | 2026-05-01 | `runner.py` warning path-quoting (1+1 sites; one-round cold-eyes converge) |
| FP04 | — | ✅ | 2026-05-01 | 2026-05-01 | Parser hardening sweep (6 sites: OSError gaps in `dat.py` + `listxml.py` + fd-leak window in `_resolve_xml`) |
| P04 | Phase 4 | ✅ | 2026-05-01 | 2026-05-01 | HTTP API (`api/`) — 40 routes / SSE / sandbox; combined ship + FP09 fold-in |
| FP09 | — | ✅ | 2026-05-01 | 2026-05-01 | P04 indie-review fold-in (13 actionable + 5 Cluster-R; lifecycle/progress storage split, `_atomic` parent-dir fsync, R27 typed CopyReport, R19 session-name re-validation) |
| P05 | Phase 5 | ✅ | 2026-05-02 | 2026-05-02 | Media subsystem (`media/`) — libretro-thumbnails URL builder + sha256-keyed lazy-fetch disk cache; R39 swapped from inline to proper escape + cache; combined ship + FP10 fold-in |
| FP10 | — | ✅ | 2026-05-02 | 2026-05-02 | P05 indie-review fold-in (5 actionable: A1 `follow_redirects=True`, A2 empty-body cache poison guard, A3 user-detail double-wrap, A4 TOCTOU invariant comment, A5 single-`!r` network error) |
| P06 | Phase 6 | ✅ | 2026-05-02 | 2026-05-02 | Frontend MVP — Vite + React 19 + Tailwind v4 + shadcn/ui SPA; combined ship + FP11 fold-in |
| FP11 | — | ✅ | 2026-05-02 | 2026-05-02 | P06 closing-review fold-in (10 thematic clusters A–J, ~40 actionable findings closed across ~25 commits; user-elected close-on-CI-green per FP10 small-fix-pass precedent) |
| FP12 | — | ✅ | 2026-05-04 | 2026-05-04 | Settings page list editors + path picker (combined ship + FP13 fold-in at same SHA) |
| FP13 | — | ✅ | 2026-05-04 | 2026-05-04 | FP12 closing-review fold-in (22 findings across 5 clusters A-E closed in 6 commits) |
| FP14 | — | ✅ | 2026-05-04 | 2026-05-04 | GameCard layout overflow + always-on identifier (P06 surface gap surfaced by user screenshot) |
| P07 | Phase 7 (slim) | ✅ | 2026-05-04 | 2026-05-04 | Slim: downloads.py + refresh-inis CLI + cards_per_row Select + HelpPage DOMPurify + Cmd-K help wire-up (5 clusters A-E in 5 commits; no audits run per user direction) |
| P08 | Phase 8 (slim) | ✅ | 2026-05-04 | 2026-05-04 | Slim: run.sh + run.bat clone-and-run bootstrap scripts (in-browser wizard deferred post-v1 per Karpathy 9 push-back) |
| FP15 | — | ✅ | 2026-05-04 | 2026-05-04 | Sessions UX — Save wiring (load-bearing FP11 § B8 stub) + active-session pill + first-time explainer |
| P09 | Phase 9 (slim) | ✅ | 2026-05-04 | 2026-05-04 | v1.0.0 release — README rewrite + CHANGELOG [1.0.0] bootstrap + `v1.0.0` semver tag |
| FP16 | — | ✅ | 2026-05-04 | 2026-05-04 | Library shipping blockers + INI visibility (search/year params + drawer wiring + setupInfo wiring + SPA cache headers + version bump 0.0.1→1.0.0; v1.0.0 re-tagged at this SHA) |
| v1.0.1 | — | ✅ | 2026-05-04 | 2026-05-04 | INI URL hotfix — AntoPISA repo uses `<file>/<file>` subdirectories, not flat files; 5/5 INIs now download (mature.ini was bonus) |
| FP17 | — | ✅ | 2026-05-04 | 2026-05-04 | Library filter expansion — letter + genre + publisher + developer filters; new /api/library/facets endpoint; v1.1.0 |
| FP18 | — | ✅ | 2026-05-04 | 2026-05-04 | refresh-inis auto-patches config.yaml + Setup banner counts 5 INIs; v1.1.1 |
| P09 | Phase 9 | 📋 | — | — | Polish + v1.0.0 release |
| P10 | — | 📋 | — | — | Media coverage expansion (progettoSnaps + ArcadeDB + Wikipedia + Mobygames; post-v1 by default — § A promotable ahead of P07 on user say-so) |
| P11 | — | 📋 | — | — | Contribute missing thumbnails to libretro-thumbnails (post-v1; depends on P05 ✅, composes with P10) |
| P12 | — | 📋 | — | — | In-app self-update + INI diff-preview UI (post-v1; deferred from P07 2026-05-04 to keep v1 budget tight; depends on P07 / P09) |

The detailed per-phase contract for every phase still lives at
`docs/superpowers/specs/2026-04-27-roadmap.md` — that file is the
long-form authoritative phase plan. `ROADMAP.md` at the root is
the queue summary.

## §2. Workflow rules

The canonical rules — phases A–D, the per-phase 9-step loop,
ID scheme, triage table, fold-into-roadmap pattern,
false-positive learning loop, drift handling, Definition of
Done — live in
`~/.claude/skills/app-workflow/SKILL.md`.
The skill auto-loads when this file is present in the
project, so reading SKILL.md is the way to access the rules
in any session.

**Hard rule kept inline (most-load-bearing):** never silently
drift. If code being written diverges from the spec, stop and
surface. Either the spec was wrong (update spec → re-audit
affected sections → resume) or the code was wrong (fix code,
no spec change). Never both papered-over.

To refresh this file from the (upgraded) skill template, copy
`~/.claude/skills/app-workflow/templates/.claude/workflow.md`
over this file — preserve §1 (status header) and §3 (session
journal); §2 is the only part that changes.

## §3. Session journal

Append-only. Newest at the top.

### 2026-05-04 — FP12 clusters F + H (last two FP12 work clusters) closed

User said "Let's continue, please." after cluster G shipped.
Picked up F (editable media.cache_dir) and H (Paths tab
in-place) together — both consume `<FsBrowser>` from G and
share the same wiring shape, so a single commit kept the
diff readable.

**Cluster F — editable media.cache_dir**:

- Media tab: read-only `<p>` replaced with an `<Input>` (local
  draft state, patches on blur via the new typed-key
  `updateMedia`) plus a "Browse…" button that mounts
  `<FsBrowser>` in directory mode. Pick → updates draft + patches.
- Conditionally-mounted FsBrowser (`{open && <FsBrowser />}`)
  so the underlying `useFs*` hooks don't fire until the user
  clicks Browse. Important: lets the existing pure-prop
  SettingsPage tests render without QueryClient + MSW (those
  hooks would 404 against an unmocked backend in test).

**Cluster H — Paths tab in-place editable**:

- New `PathRow` helper inside SettingsPage.tsx (kept inline
  rather than a new file — tiny surface, only used in one
  place) wraps `<Label>` + `<Input>` + Browse → FsBrowser.
  Same conditional-mount trick as F.
- 4 rows: `source_roms`, `dest_roms` (directory), `source_dat`,
  `retroarch_playlist` (both file mode).
- DAT swap is destructive (`replace_world` rebuilds the whole
  library). Instead of patching on blur, the new value is
  held in `pendingDat` state and a `ConfirmationDialog` with
  concrete action label `"Swap DAT to <path>"` surfaces; only
  on confirm does the source_dat patch fire. Cancel discards.
- Local draft seeds from `value` on mount. Out-of-band resets
  (e.g. snapshot restore while the tab is open) won't reflect
  in the input until blur — accepted as a corner case.

**Test-side surprise**: `input.blur()` (direct DOM call) doesn't
wrap in act() and the dialog assertion fired before the state
update committed. Switched to `await userEvent.tab()` which
triggers blur via the user-event harness and is naturally
awaited. Pattern saved for any future "test a blur handler"
case.

Tests: 159 frontend pass (2 + 5 new — 4 of H's 5 cover the
destructive-confirm flow), 435 backend pass at 89.19%
coverage. eslint / tsc / ruff / mypy / bandit all clean.
`frontend/dist/` rebuilt.

FP12 step 4 (implement) is now complete — closing audit /
indie-review next. Per FP11 precedent, may elect to ship on
CI matrix green instead of dispatching the multi-agent close.

### 2026-05-04 — FP12 cluster G (FsBrowser modal) closed

User said "Let's continue, please." after cluster J shipped.
Picked up cluster G — the foundation for F + H. Self-contained
component (owns its `useFs*` hooks; pure-prop seam wasn't worth
the 10+ props it would have needed) introduced the suite's
first MSW-backed component tests.

Cluster G shipped:

- `useFs.ts` hooks — `useFsHome`, `useFsDriveRoots`,
  `useFsAllowedRoots`, `useFsListing(path)` (gated on
  `path !== null`), `useFsGrantRoot`. Mirrors the existing
  `useConfig.ts` shape; no new patterns.
- `FsBrowser.tsx` — modal with quick-jump (Home + drive roots
  + allowed roots), Up + path display, entries list (filtered
  by mode), "Use this directory" + Cancel footer. Path is
  derived (`userPath ?? home.data?.path ?? null`) so the
  default-on-async-load case avoids setState-in-effect (saved
  workflow lesson). `fs_sandboxed` 403 detection is duck-typed
  (`'code' in error`) to tolerate vitest module-identity drift.
- `FsBrowser.test.tsx` — 10 tests using `server.use(...)` per
  test plus a tiny `renderWithClient` helper that wraps
  `QueryClientProvider`. Covers: open/closed, list home,
  navigate into dir, Up, pick directory, mode='file' shows +
  picks files, cancel, grant prompt on 403, grant POST.

**Two debugging takeaways saved**:

- **Nested radix dialogs need fragment siblings, not children.**
  Wrapping `<ConfirmationDialog>` inside the outer `<Dialog>`
  blocked the AlertDialog portal from rendering. Sibling
  fragment (`<>`) fixed it.
- **Test regex for accessible name needs adjacent words.**
  `/grant access/i` does not match `"Grant filesystem access?"` —
  the words aren't adjacent. Caught here as a 1-failed-of-10
  test that passed once the regex became `/grant filesystem access/i`.

Tests: 152 frontend pass (10 + 0 new at SettingsPage level —
G has no consumer wiring yet; that lands in F + H), 435 backend
pass at 89.19% coverage. eslint / tsc / ruff / mypy / bandit all
clean. `frontend/dist/` rebuilt.

### 2026-05-04 — FP12 cluster J (Backup tab) closed

User said "Let's continue, please." after the P10 add. Resumed
the FP12 queue at cluster J (the next independent cluster — F
+ G + H all depend on G).

Cluster J shipped:

- `BackupTab` primitive (`frontend/src/components/settings/BackupTab.tsx`)
  — Export button + Import file picker + Phase-8 forward-link
  banner. File pick opens `ConfirmationDialog` whose action label
  is the design §8 concrete form `"Replace settings from <file>"`.
  8 unit tests cover all controls + the cancel-doesn't-call-onImport
  guard + the error-state surface.
- `useConfigExport` + `useConfigImport` hooks added to
  `useConfig.ts`. Import's `onSuccess` mirrors the snapshot-restore
  flow: setQueryData on the config cache + invalidate snapshots
  so the new auto-snapshot surfaces on next read.
- `SettingsPage` accepts new optional `onBackupExport` /
  `onBackupImport` / `backupError` props (no-op defaults so older
  test sites still compile). New `'backup'` tab between
  `'snapshots'` and `'about'`.
- `SettingsRoute` (App.tsx) owns the export download dance
  (Blob → `<a download>` with timestamped filename → revoke URL)
  and the import parse step (`File.text()` → `JSON.parse` → mutate).
  Errors from either flow surface via `backupError` state.

**Roadmap drift surfaced**: ROADMAP § FP12-J said "R19 multipart"
but the actual backend (`config.py:170 + 186`) takes / returns
`ConfigExportBundle` JSON. Followed the code per global rule 11
(stay in your lane); flagged in the journal entry rather than
papering over either side.

Tests: 142 frontend pass (8 + 1 new), 435 backend pass at
89.19% coverage. eslint / tsc / ruff / mypy / bandit all clean.
`frontend/dist/` rebuilt.

### 2026-05-04 — P10 (media coverage expansion) added

User asked mid-FP12 "Are there additional sites that game
metadata can be scraped from? There are quite a lot of games
without graphics." Six sources brainstormed; user accepted
same-day to file as a post-FP12 roadmap entry. Slotted as P10
post-v1 (after P09's v1.0.0 release). § A (progettoSnaps as a
second URL source) flagged as promotable ahead of P07 on user
say-so — one-day surface change to `media/urls.py`, no auth,
same lazy-fetch cache shape as the libretro-thumbnails wiring
P05 already ships. Stable ID `mame-curator-1005`; counter bumped
to 1005.

### 2026-05-04 — FP12 cluster I (Snapshots tab) closed

User said "continue with the next roadmap item" (auto-mode) with
a Karpathy-principles reminder. Reordered remaining clusters
to I → J → G → F → H since F+H depend on G but I+J don't, so
front-load the independent ones.

Cluster I shipped:

- `SnapshotsTab` primitive (`frontend/src/components/settings/SnapshotsTab.tsx`)
  — loading / error / empty / list states; per-row Restore
  opens `ConfirmationDialog` with the design §8 concrete action
  label `"Restore N files"`. 8 unit tests cover all five states +
  the cancel-doesn't-call-onRestore guard.
- `SettingsPage` accepts new optional `snapshots` /
  `snapshotsLoading` / `snapshotsError` props, defaults to empty
  so older test sites compile unchanged. 2 integration tests.
- `useSnapshots` + `useSnapshotRestore` hooks added to
  `useConfig.ts`. `useConfigPatch.onSuccess` now invalidates the
  snapshots query alongside setting the config cache, so a
  fresh PATCH surfaces the new entry on next read.
- `App.tsx` extracts `SettingsRoute` container per the
  FP11 § B8 pattern — owns all four config-related queries
  (config / patch / snapshots / restore) so the page stays
  pure-prop. The shell's redundant `useConfigPatch` call dropped.

**Style snag**: `prettier --write` flipped single-quote/no-semi
to double-quote/semi (no `.prettierrc` in repo, so prettier uses
defaults; project-wide convention is single-quote/no-semi). 5 of
the touched files exploded to 766 inserts / 544 deletes. `git
checkout --` reverted the noise; re-applied logical changes via
Edit + Write in project style. Net diff: ~133 LOC added across
5 modified + 2 new files. Lesson: **don't run `prettier --write`
in this repo without first reading the existing file's style**;
the format check (`npm run format`) passes despite the
discrepancy because formatting isn't a CI gate. Saved as a
feedback memory.

Tests: 133 frontend pass (8 + 2 new), 435 backend pass at
89.19% coverage. eslint / tsc / ruff / mypy / bandit all clean.
`frontend/dist/` rebuilt.

User question landed mid-cluster: "Are there additional sites
that game metadata can be scraped from? There are quite a lot
of games without graphics." — to be addressed after the cluster
ships; metadata-source brainstorm is post-v1 territory but
worth surfacing options now.

### 2026-05-02 — FP12 picked up (active)

User confirmed "continue" after the FP11/P06 closing summary, picking up **FP12** per ROADMAP order ahead of P07. Step 1 + 2 closed in one batch:

- **Step 1 research** — 5 parallel WebSearch queries returned: chip-input ARIA pattern (`role="listbox"` + `role="option"` per chip; PrimeReact / Zag.js conventions); dnd-kit Sortable preset uses `sortableKeyboardCoordinates` with Space-to-pick + Arrow-to-move + Space-to-drop + Esc-to-cancel; FS-picker path-traversal risk mitigated by the existing backend `fs_sandboxed` 403 contract (R33 grant-flow handles outside-allowlist picks); shadcn `<Select>` uses `value` + `onValueChange` controlled props; Blob/FormData for R18 export download + R19 import upload.
- **Step 1 surfaced gaps** — ROADMAP § FP12-B's "Pointer-drag via dnd-kit (no new top-level dep)" is wrong; dnd-kit isn't in `package.json`. Need `@dnd-kit/core + @dnd-kit/sortable + @dnd-kit/utilities` (3 packages, install at cluster B). Separately, shadcn `<Select>` primitive isn't in `components/ui/` (clusters D + E need it; install via `npx shadcn@latest add select`).
- **Step 2 deps** — all green: P06 ✅, FP11 ✅, P04 R29-R34 ✅, R15-R19 ✅, all TS types mirrored at `frontend/src/api/types.ts`.

Cluster plan (A → J, one commit per cluster per FP11 cadence): A ChipListEditor (foundation, used in 7 fields); B DragReorderList; C year-range pair; D default_sort; E updates.channel; F media.cache_dir editable; G FsBrowser modal; H paths in-place editable; I Snapshots tab; J Backup tab. Closing strategy: `/close-phase` at the end with optional CI-matrix substitution per FP11 precedent.

### 2026-05-02 — P06 + FP11 closed

P06 (`frontend/` SPA) shipped + closed in a two-pass close: P06's closing `/audit` + `/indie-review` across 6 lanes surfaced ~40 actionable findings → FP11 (10 thematic clusters A-J). FP11's implementation closed across ~25 commits over the day; user opted to ship on **CI matrix green** (Ubuntu / macOS / Windows × 3.12 / 3.13) rather than dispatch the multi-agent closing audit a second time, citing FP10's "smaller fix-passes converge faster" + "running indie-review on the patches that closed indie-review findings is the kind of recursive audit that returns zero findings" precedent. 428 backend tests / 89.14% coverage / 85 frontend tests / mypy / ruff / bandit / types-sync all green at close; CI green on all 6 matrix entries.

**Workflow lessons saved**:

- **CI multi-platform matrix is the load-bearing audit signal for path-touching code.** FP11 § A2's `_SPAStaticFiles` carve-out passed local Linux pytest, the project's Linux dev box, and a manual macOS check — the Windows-only failure (path normalisation under `os.path` joining) only surfaced via the CI matrix. Fix landed within an hour of the CI signal at commit `8918cb5` with a Linux-runnable property test guard. Without the Windows job in `.github/workflows/ci.yml`, the regression would have shipped.
- **Wide phase + closing fix-pass is the right shape for P06-scale work.** Folding the closing audit's ~40 findings into FP11 instead of fixing-in-place during P06 kept the P06 contract boundary clean and let FP11 absorb the messy real-world residue across 10 thematic clusters. The pattern scales: P07 + P08 should follow the same shape (ship the contract → closing audit → fold-in fix-pass → close both at the same SHA).
- **"Close on CI green" is acceptable for fix-passes whose patches are themselves the result of an indie-review pass.** FP11's patches close FP11's own findings; running indie-review on them again is recursive audit that FP10's "smaller fix-passes converge faster" lesson predicts will return zero. For FP11's wide surface the user's call was to trust CI + the per-cluster commit gates rather than burn another multi-agent dispatch. Pattern saved as the "user-elected close-on-CI-green" shape; doesn't replace the closing audit for fresh shipped work, only amends the recursive-on-fix-pass case.
- **Container components in `App.tsx` keep page tests pure-prop.** B8 wired four real react-query hooks (`useSessions`, `useActivity`, `useStats`, `useHelp{Index,Topic}`) via inline 5-15-line route containers (`SessionsRoute`, `ActivityRoute`, `StatsRoute`, `HelpRoute`). Pages stayed pure-render with their existing prop contracts so component tests passed unchanged. Pulling containers into a new directory would have been ceremony.
- **Mount-on-key beats setState-in-effect for prop-driven state resets** under React 19's compiler eslint rules. NotesEditor went through three intermediate forms before settling on the mount-on-key contract; saved as the standard pattern for any future "reset state when prop changes" decision.

Tags: `FP11-complete` + `P06-complete` at the same close SHA. Next active item: P07 (Self-update + in-app help) — though FP12 is queued ahead per ROADMAP and may be done first.

### 2026-05-02 — P05 + FP10 closed

P05 (`media/` module) shipped + closed in a two-pass close: P05's closing `/audit` + `/indie-review` surfaced 5 actionable findings (1 Tier-1, 1 Tier-2, 3 Tier-3) → FP10. FP10's own closing `/audit` returned 0 findings across ruff / bandit / mypy / gitleaks (full src+tests+docs) / trivy (0 HIGH/CRITICAL) / semgrep (200 rules: `p/security-audit + p/python + p/fastapi`); `/indie-review --fix HEAD` returned **Accept**. **One-round fix-pass converge — fastest yet**, no Cluster-R items. 423 tests pass; coverage 89.12%; `media/cache.py` 100%.

**Workflow lessons saved**:

- `/indie-review --fix HEAD` is the right shape for narrow fix-passes (≤5 findings, ≤4 files). Full-sweep `/indie-review` is calibrated for ≥5 commits across ≥3 subsystems; FP10's 113-line patch didn't earn the 5-min multi-lane cost. The single focused subagent took ~60s and produced tighter signal.
- Smaller fix-passes converge faster — FP10 had no patch-introduced drift because the surface was too narrow. Compare FP02/FP05/FP06/FP07/FP08/FP09 each closing with 1-5 Cluster-R items. Pattern: tighter scope → faster converge.
- "Specs are for features, not fixes" + "fix-pass amends parent spec when contract-touching" is the right combination. A1 + A2 modified the contract (`follow_redirects=True` is now part of the lifespan-client invariant; empty-body 200 is now a fetch error); `docs/specs/P05.md` updated inline. A3/A4/A5 are message/comment-only and correctly need no spec change.
- R39's `kind=video` short-circuit is structurally load-bearing (MediaUrls has no `video` field), not just behaviorally. P06+ progettoSnaps wiring needs three coordinated changes (add field + drop short-circuit + extend the no-video AttributeError test).
- `media_cache_dir` fixture in `tests/api/conftest.py` (tmp_path-isolated per-test) caught a real cross-test bug during Step-4: default `./data/media-cache/` gets shared between tests, hiding upstream-call assertions. Saved as a one-liner under `docs/specs/P05.md` § R39 wiring so future test authors don't re-trip.

Tags: `FP10-complete` + `P05-complete`. Next active item P06 (Frontend MVP).

### 2026-05-01 — DS01 closed

DS01 (pre-P04 debt-sweep fold-in) closed: 20 actionable sub-bullets across 4 clusters (A: 5 copy/ spec+code drift; B: 4 test gaps; C: 8 filter+cli hardening; D: 3 record/allowlist) + 2 round-2 fix-pass-internal R1/R2 (filter/spec.md tuple-shape update; CLI atomic-write try/finally cleanup) closed inside DS01 per the FP02 precedent. 260 tests pass; coverage 94.67%; all five gates green.

**Major workflow addition**: cold-eyes spec review at Step 1, looped until clean. Round 1 → 4 substantive findings (C9 fully false; C2 read-sites incomplete; A1 third site missed; FP04 needed). Round 4 → 2 (count drift 22→20; FP## allocation deferred). Round 5 → clean. Saved as `feedback_cold_eyes_spec_review_at_step_1.md` for future projects. Without these rounds the implementation would have shipped a partly-fictional plan (C9 was a no-op finding; the count was wrong).

**Closing /audit + /indie-review**: tools clean; indie-review across 3 lanes returned 14+ findings in surrounding code → folded into FP05 (recycle_partial unimplemented, empty-string active footgun, MemoryError swallow narrowing, FilterContext mutability parallel to C2, BIOSResolutionWarning one-arm Literal, pause/cancel race window, TOCTOU stat/read, _cmd_copy asymmetry, etc.). DS01-internal drift (filter/spec.md not updated by C2; CLI atomic-write missed try/finally) closed in same fix-pass per FP02 precedent.

**Lesson saved**: every fix-pass's closing review on its own patches surfaces patch-introduced drift, not just leftover round-1 findings. FP02 caught FP02-shipped Tier-2 spec drift; DS01 caught DS01-shipped R1/R2 drift. Pattern holds; closing review is non-skippable.

**FP05 opened** with 14+ findings, **FP04 still queued** (parser hardening — 2 items deferred from DS01 cold-eyes review). Numerically FP04 < FP05 but FP05 has Tier-1 bugs and runs first in the queue. Numbers reflect creation-order; queue-position reflects priority.

### 2026-04-30 — FP02 closed

FP02 closed all 9 round-2 deferrals from FP01: 3 Tier-2 (`OverwriteRecord.parent` dropped; `AppendDecision` widened from `StrEnum` to a Pydantic model with `kind` + `replaces` so multi-conflict sessions steer to the right entry; recycle dirname keyed on `session_id` so cross-session same-second collisions are impossible) + 6 Tier-3 (spec typo `mid-copy3`; `_chd_missing` helper; `functools.partial` over `make_cb`; playlist filter to `SUCCEEDED` + `SKIPPED_IDEMPOTENT`; KI test extended to `progress=cb` branch; recycle 3+ collision test). 9 new tests in `tests/copy/test_fp02_fixes.py`; 241 tests pass project-wide; coverage 94.79%.

Closing `/audit` + `/indie-review` on the FP02 patches surfaced FP02's own spec drift: duplicate `AppendDecision` definition in `copy/spec.md` § CopyPlan; stale `recycle_file` docstring (`<timestamp>`); `test_recyclebin.py` docstring also stale; missing note about duplicate `replaces` being undefined behaviour. All folded into FP02 (DOC01 round-2 precedent — round-2 in same fix-pass when findings are spec-drift caused by the patches themselves). Pre-existing `except Exception` without `logger.exception()` deferred to a future debt-sweep, not in FP02 scope.

Lesson saved: every fix-pass needs a closing review on its own patches, not just on surrounding code. FP01 round-2 caught FP01-shipped Tier-2; FP02 closing review caught FP02-introduced spec drift. Both were caught by /audit + /indie-review running on the latest patches; the iteration converges quickly when the round-2 findings are documentation-only.

Architecture note: FP02 #2 (`AppendDecision.replaces`) compounds the FP01 #4 caller-side architecture. Runner is now strictly a "trusts the caller" layer — no heuristics, no `cloneof_map` reach-around. The CLI / API layer (P04+) is the natural home for cloneof-aware decision logic.

### 2026-04-30 — P03 + FP01 closed

P03 (`copy/` module) shipped: BIOS chain resolution, atomic copy primitive, RetroArch v6+ JSON playlist writer, project-internal recycle bin (no `send2trash` dep), pause/resume/cancel `CopyController`, `data/activity.jsonl` append-only log with discriminated-union event schema, `CopyReport` Pydantic model, CLI `mame-curator copy --dry-run / --apply / --purge-recycle`. 74 tests in `tests/copy/`, copy/ aggregate ~89%, project-wide 92.95%. All five CI gates green.

FP01 closed paired: indie-review on freshly-shipped P03 surfaced 6 Tier-1 real bugs that `/audit` missed (signature drift, `KeyboardInterrupt` cleanup, `OverwriteRecord` allocated-but-never-appended, `PlaylistError` design contradiction, broken recycle collision logic, `read_lpl` legacy claim without code). Round-1 closed all 6 Tier-1 + most Tier-2/3. Round-2 surfaced 5 fresh Tier-2 + 4 Tier-3; user-data-risk (B-T2-3 corrupt-playlist silent overwrite) closed in FP01; 15 remaining items deferred to FP02. Per App-Build's "every finding tracked" hard rule, deferred items live in ROADMAP § FP02.

Notable lesson: `/audit` and `/indie-review` are complementary. Auto tools catch the grammar; indie-review catches semantics. Both necessary; neither sufficient. Saved as a reference for future phase closes.

### 2026-04-30 — DOC01 closed (Phase D documentation audit)

Five-lane cold-eyes documentation review (standards consistency / workflow integration / spec ↔ architecture alignment / phase-history accuracy / discoverability). Four review rounds total: round 1 surfaced 27 findings (3 Tier-1 / 17 Tier-2 / 7 Tier-3), round 2 added 13 follow-on (2/7/4) catching round-1 patches that didn't propagate to sibling files, round 3 added 7 (1/3/3), round 4 came back clean across all touched lanes. 30+ documents updated; CLAUDE.md trimmed 232 → 102 lines via reflow + redundancy cull (per user feedback re: long lines in context-loaded docs — saved as feedback memory). All Tier-1 / Tier-2 / Tier-3 findings closed; allowlist remains empty (no false positives surfaced). Journal: `docs/journal/DOC01.md`.

### 2026-04-30 — App-Build alignment

Project retrofitted to align with the Ants App-Build workflow.
Phase 0–2 (already shipped) mapped to P00–P02. Added the
state-tracking surface (`.claude/workflow.md`,
`.claude/settings.json`), the four-standards slot files at
`docs/standards/{coding,testing,commits,documentation,roadmap-format}.md`
(redirecting to the consolidated `coding-standards.md` which
remains the canonical document), `ROADMAP.md` at root,
`docs/decisions/` with three retroactive ADRs (`0001-record-architecture-decisions`,
`0002-cloneof-from-listxml`, `0003-listxml-tiered-acquisition`),
`docs/journal/{P00,P01,P02}.md` capturing what shipped in each,
and the supporting docs (`glossary`, `known-issues`,
`audit-allowlist`, `ideas`).

Existing per-module specs (`src/mame_curator/{cli,parser,filter}/spec.md`)
remain the per-feature audit surface — they already meet
App-Build's spec-as-contract requirement.

`docs/superpowers/specs/2026-04-27-{roadmap,mame-curator-design}.md`
remain the long-form authoritative phase plan and design spec
respectively; the new `ROADMAP.md` at root is the queue summary
that points to them.

Next: P03 — `copy/` spec, tests, implementation per the per-phase
9-step loop.

### 2026-04-27 — Phase 2 closed

Pass-3 indie-review surfaced two CRITICAL spec violations
(picker not using `cmp_to_key`, CLI dispatch not using
`set_defaults(func=)`) and one HIGH zombie field
(`drop_bios_devices_mechanical` declared but never honoured).
All three closed; 158 tests pass, filter coverage 96%+.
Tier 2/3 findings logged in CHANGELOG `[Unreleased]` per the
project's CHANGELOG-as-sweep-log convention.

### 2026-04-27 — Phase 1 closed

DAT + 5 INI parsers + listxml CHD detector + cloneof map +
manufacturer split. CLI smoke `mame-curator parse` ships.

### 2026-04-27 — Phase 0 closed

`uv` + ruff + mypy + pytest + bandit configured; pre-commit
hooks installed; CI workflow committed; coverage gate at 85%
enforced.

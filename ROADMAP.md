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

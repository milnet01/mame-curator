# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Versioning policy.** v1.0.0 shipped at P09 (2026-05-04).
> Subsequent minor releases (`v1.1.0`, `v1.2.0`, …) accumulate
> phase-closing `<ID>-complete` annotated tags between them —
> phase tags mark per-phase ship landmarks but are distinct
> from semver-versioned releases. The CHANGELOG remains the
> authoritative per-phase record; consult
> `git tag --list 'P*-complete' 'FP*-complete' 'DS*-complete'`
> to map phases to commits. Pre-v1 backwards-compatibility
> shims remain explicitly out of scope per coding-standards § 7.

## [Unreleased]

### FP34 — P10 third closing-review fold-in (2026-07-02)

The final review round confirmed FP33's fixes and found three small leftovers.

**Fixed**

- A corrupt or non-text MobyGames API-key file no longer takes the whole
  artwork feature down — it just disables that one source, like every other
  bad-key case. (mame-curator-1087)
- Housekeeping: corrected a "modifies data" marker on the API-key endpoint in
  the API spec (it only writes a key file, holds no lock), and added the
  friendly message for the "unknown media source" error. (mame-curator-1087)

### FP33 — P10 second closing-review fold-in (2026-07-02)

A deeper re-review after FP32 shipped found two real bugs FP32's first pass
missed — same class, one level deeper. Fixed TDD, a failing regression test
first.

**Fixed**

- **Security:** an artwork source could no longer be tricked into serving a
  private file off the server. The "serve a local file directly" fast-path is
  now restricted to the local snapshot pack; a network source (fetched over
  plain HTTP) handing back a `file://…` path is dropped instead of read off
  disk. (mame-curator-1086)
- FP32's "unexpected response shape" guard only checked the top level; a few
  deeper spots (a list element / URL field / thumbnail / link block that isn't
  the expected type) could still crash an image or "About" request. All are now
  type-guarded and fall through gracefully. (mame-curator-1086)
- A snapshot-pack folder the server can't read no longer takes the media
  feature down — it just disables that source. (mame-curator-1086)
- The "copy command" button no longer reads "Copied!" when you reopen the
  dialog without having copied again. (mame-curator-1086)
- Housekeeping: the API-key box trims pasted whitespace (and rejects a
  spaces-only key); three shipped media endpoints + one error code are now
  documented in the API spec; and several stale/dead doc references were
  corrected. (mame-curator-1086)

### FP32 — P10 closing-review fold-in (2026-07-02)

The closing indie-review of the media feature (run once all 11 P10 chunks had
shipped) found real defects the spec cold-eyes couldn't — they reviewed
contracts, not code paths. Fixed TDD, a failing regression test first.

**Fixed**

- An art source returning a valid-but-unexpected response (a JSON array or
  `null` instead of an object) could make an image request error out — and
  stay broken via a poisoned cache slot — instead of quietly trying the next
  source. Now it falls through the fallback chain as intended. (mame-curator-1085)
- The "copy `refresh-snaps` command" button no longer claims "Copied!" when the
  browser has no clipboard access (plain-HTTP LAN) or the copy is denied, and a
  stray file where the snapshot-pack folder is expected no longer takes the
  whole media feature down. (mame-curator-1085)
- The Wikipedia "Read more" link only renders for a genuine `https://` URL —
  defence against a poisoned/MITM link. (mame-curator-1085)
- Housekeeping: retired the dead 502 media-upstream error surface, made the
  rate-limiter safe under a non-monotonic clock, and the API-key dialog now
  shows the server's actual reason on failure instead of a generic message.
  (mame-curator-1085)

### P10 chunk 11 — Wikipedia "About" paragraph in the Alternatives drawer (2026-07-01)

**Added**

- The Alternatives drawer now shows a short Wikipedia "About" paragraph for the
  selected game, with a "Read more on Wikipedia" link and a CC-BY-SA
  attribution line. It appears only when a matching Wikipedia page exists —
  otherwise (or while loading) it's silently absent, since it's non-essential
  flavor text. Consumes the chunk-8 `GET /media/{name}/wiki` endpoint via the
  new `useWikipediaExtract` hook. (mame-curator-1005)

### P10 chunk 10 — Settings → Media source list (2026-07-01)

The Media tab in Settings gains a live list of your art sources.

**Added**

- A reorderable art-source list on Settings → Media: each source shows a
  status dot (green Active / grey Disabled), the image kinds it covers, and —
  when it's off — the reason why. Drag-free reorder (arrow buttons) sets the
  fallback priority, saved to your config. (mame-curator-1005)
- A "Configure…" button on MobyGames (when it has no key) opens a modal to
  paste your API key; on success the dot flips to green without a restart.
  (mame-curator-1005)
- A "Download pack…" button on progettoSnaps (when the pack isn't downloaded)
  opens a modal with the `mame-curator refresh-snaps` command and a copy
  button — run it in a terminal, reopen the tab, and it flips to green.
  (mame-curator-1005)

**Deferred**

- Turning a source fully off (a per-row enable/disable checkbox) is a
  follow-up (mame-curator-1084); chunk 10 ships reorder + status + the key /
  pack helpers. (mame-curator-1005)

### P10 chunk 9 — media source readiness + key-paste API (2026-07-01)

Backend for the upcoming Settings → Media tab: a way to see which art sources
are working and to paste a MobyGames API key.

**Added**

- `GET /api/media/sources` — per-source readiness: for each of the five art
  sources, whether it's active, whether it's in your fallback order, which
  image kinds it covers, and (if disabled) a human-readable reason (e.g.
  "no key configured" for MobyGames, "run refresh-snaps" for progettoSnaps).
  Surface-only — no network calls. (mame-curator-1005)
- `PUT /api/media/sources/{name}/secret` — paste a MobyGames API key; it's
  written to `data/secrets/mobygames.key` at mode 0600 (owner-only) via an
  atomic write, and the very next request picks it up (no restart). The key
  value is never logged and never appears in a config export. Unknown source
  name or empty key → 422. (mame-curator-1005)
- `SourceReadinessRow` / `SourceReadiness` / `SourceSecret` API schemas,
  mirrored in the frontend typed config. (mame-curator-1005)

**Security**

- The key-paste route uses loopback-trust (no auth gate) — the server binds
  `127.0.0.1` by default, consistent with every other write endpoint in the
  app. App-wide cross-site-request hardening is tracked as a future
  consideration (mame-curator-1083). (mame-curator-1005)

### P10 chunk 8 — Wikipedia "About" flavor-text endpoint (2026-07-01)

A new endpoint serves a one-paragraph Wikipedia summary for a game, for the
"About" section of the Alternatives drawer (the drawer UI itself lands later).

**Added**

- `GET /media/{name}/wiki` — returns a `WikipediaExtract` (`title` / `extract`
  / `url` / `license`) or JSON `null` when there's no matching Wikipedia page.
  It reuses the same Wikipedia REST summary the image source already fetches,
  so one lookup warms both caches. (mame-curator-1005)
- `src/mame_curator/media/wikipedia.py` — `WikipediaExtract` (frozen model)
  and `resolve_wikipedia_extract`, which shares the `wikipedia_limiter`
  rate-limit budget + the on-disk text cache with the chunk-5 image source,
  and applies the same parse-before-trust cache-poisoning guard.
- `WikipediaExtract` mirrored in the frontend typed config (`types.ts` + Zod
  `schemas.ts`) and added to the API type-sync gate. (mame-curator-1005)

**Behaviour note**

- The "About" paragraph is non-essential: if Wikipedia is rate-limited or
  unreachable, the endpoint returns `null` (the section just hides) rather
  than surfacing a 5xx error. (mame-curator-1005)

### P10 chunk 7 — media source registry + fallback orchestrator (2026-07-01)

The five P10 art sources become a real fallback chain. A media request now
walks the configured sources in order and returns the first hit, instead of
always going straight to libretro-thumbnails.

**Added**

- `src/mame_curator/media/resolve.py` — `resolve_image`, the fallback
  orchestrator: it walks the per-kind source chain, serving the first cached
  image and falling through past any source that rate-limits, errors, or has
  no candidate. A local snap-pack (`file://`) hit is served directly. Plus
  `build_registry`, the composition root that constructs the configured
  sources with the app-state rate limiters + MobyGames disabled-flag injected.
  (mame-curator-1005)
- `MediaSourceRegistry` (`media/sources.py`) — orders + filters the configured
  sources into a per-kind chain: unknown names dropped (one-time warning),
  `libretro` appended as the baseline, kind-mismatched and disabled sources
  skipped. (mame-curator-1005)
- `media.sources` config field (default order: libretro, progettoSnaps,
  arcadeDB, wikipediaImage, mobyGames) — the fallback priority; reorder to
  change which source is tried first. Mirrored in the frontend typed config.
  (mame-curator-1005)

**Changed**

- `GET /media/{name}/{kind}` now resolves through the fallback chain. **The
  502 `media_upstream_error` response is retired for media**: a single
  source's upstream 5xx / transport error no longer fails the request — the
  chain advances, and only a chain that misses everywhere returns 404
  `media_upstream_not_found`. This trades the 5xx-vs-404 distinction for
  resilience (one flaky mirror can't break a thumbnail). (mame-curator-1005)
- The keyless-MobyGames startup warning is now deduped process-wide, so
  per-request source reconstruction logs it once per process rather than on
  every thumbnail request. (mame-curator-1005)

### P10 chunk 6 — MobyGames key-handling (2026-07-01)

The fifth and final P10 fallback art source lands its key-handling half.
MobyGames needs a personal API key; the cover-image fetch that depends on
a real key to verify the response shape is deferred (mame-curator-1079).

**Added**

- `src/mame_curator/media/mobygames.py` — `MobyGamesSource` (boxart-only,
  `license_compatible=False`). Resolves an API key from `MOBYGAMES_API_KEY`
  or a mode-0600 `data/secrets/mobygames.key` dotfile (group/other-readable
  files are rejected with a warning), self-disables with a user-readable
  reason when no key resolves, and flips a process-wide `SourceDisabledFlag`
  on a 401/403 from a configured key. The lookup request carries the key in
  its query string, so every error/log message redacts it. Split into its
  own module so `sources.py` stays under the 500-line cap. (mame-curator-1005)
- `media.mobygames_rate_limit_per_min` config field (default 5 req/min) plus
  the `mobygames_limiter` token bucket and `mobygames_disabled` flag wired
  on `app.state` at lifespan startup. (mame-curator-1005)

**Deferred**

- MobyGames cover-URL parse + JSON-body caching — gated on a real API key
  to capture a fixture and verify the response field path. Until it lands,
  MobyGames participates in the chain (when keyed) but yields no covers;
  it is last in the default fallback order, so no user-visible regression.
  (mame-curator-1079)

### Cleanup / debt — frontend file-size + Snapshots caveat (2026-06-30)

Two `frontend` cleanup-debt items surfaced during the P14 docs work,
bundled by shared lane.

**Fixed**

- Settings → Snapshots now shows a one-line caveat that per-game review
  state is excluded from config snapshots, so review marks can't be
  rolled back there — recovery is via Activity replay. The caption
  (`settings.snapshotsStateExclusionNote`) was specified in the P14 spec
  but never shipped. (mame-curator-1078)

**Changed**

- `frontend/src/pages/LibraryPage.tsx` (579 lines) split under the §2
  frontend component hard cap of 350 lines — non-render logic extracted
  to a new `useLibraryController` hook plus pure helpers in
  `libraryPageHelpers.ts`; the JSX stays in the page so the source-text
  structural tests keep asserting the rendered shape. Behaviour-
  preserving (all 323 frontend tests green). (mame-curator-1077)

### P14 — Per-game review state (closed 2026-05-17)

Per-game `pending` / `reviewed` / `skipped` / `needs-decision` state
persists across sessions in `data/state.yaml` (sparse store —
absence = pending). Surfaces in the library grid via R / S / ?
keyboard shortcuts, a segmented filter in the sidebar, a frontend-
only badge on each card, and a header progress chip with a
walkthrough auto-advance toggle.

**Added**

- `src/mame_curator/filter/review_state.py` — frozen `ReviewState`
  Pydantic + two enums (`ReviewStateValue` storage 3-value,
  `ReviewStateFilter` query 5-value) + `load_review_state` loader
  mirroring `load_overrides`. `ReviewStateError` joins the typed-
  error hierarchy in `filter/errors.py`.
- Three routes on `api/routes/curate.py`: `GET /api/state`,
  `POST /api/state`, `DELETE /api/state/{short}`. Sparse-store
  enforced at the wire layer (`StatePostRequest.state: ReviewStateValue`
  rejects `pending` with 422 before the handler runs). No-op-write
  skip on both POST and DELETE.
- Per-request `?review_state=` filter on `GET /api/games`, applied
  in the route handler after the existing `keep()` slice (NOT in
  `run_filter()` — review state does not gate eligibility, so
  `world.filter_result` stays cached at world-build cost).
- `ActivityEvent` tagged union extended with a `REVIEW_STATE` arm +
  `ReviewStateDetails` payload. `state` and `previous` are plain
  `str` so the log records the sparse-store sentinel `"pending"`;
  `session_id` is the empty string per spec.
- `WorldState.review_state` field + `replace_world(review_state=)`
  kwarg as a **passive field swap** (INV-4 — review-state-only
  swaps leave `filter_result` `is`-identical to the base).
- Optimistic-UI `useReviewState` hook (React Query `onMutate` /
  `onError` rollback / `onSettled`; cache key `['reviewState']`).
- `useGameGridFocus` hook extracted from `LibraryGrid`'s existing
  FP21-T roving-tabindex, adds `focusNextPending(startIndex)` and
  `setActive(idx)`. The parameterised signature is load-bearing
  for the race the spec calls out (caller passes
  `activeIndex + 1` so the just-marked card is skipped regardless
  of when its state propagates).
- Frontend-only review-state badge on `GameCard` (parallel maps
  keyed by `ReviewBadgeKind`; lucide-react icons; tints
  `text-emerald-500` / `text-rose-500` / `text-amber-500`).
- Segmented review-state filter in `FiltersSidebar` (shadcn
  `RadioGroup`; `ToggleGroup` isn't in the project per spec).
- Grid R / S / ? handlers on `LibraryGrid` — toggle-on-same-key
  returns to pending; walkthrough auto-advance (default on) calls
  `focusNextPending(activeIndex + 1)` after a non-pending mutation;
  end-of-list surfaces a `walkthroughCaughtUp` toast.
- Drawer R / S / ? + ArrowUp / ArrowDown on `AlternativesDrawer`
  via `useKeyboard`. INV-7 — drawer mutations do NOT auto-advance
  regardless of walkthrough setting.
- LibraryPage header chip (`{handled}/{total} handled · {pct}%`)
  + walkthrough toggle persisted to
  `localStorage['mame-curator:walkthrough-mode']` (default `true`).
- 19 backend tests + 7 hook tests + 4 GameCard badge tests + 1
  cross-side parity contract test (INV-12) covering all 13
  invariants in `docs/specs/P14.md`.

**Notes**

- `data/state.yaml` does NOT snapshot (high-frequency keypress
  writes would churn the 200-entry shared snapshot pool); recovery
  is via `data/activity.jsonl` replay only.
- `frontend/src/pages/ActivityPage.tsx` already displays each
  event's human-readable `summary` — the chunk-4 emitter's
  `"marked sf2 as reviewed"` / `"cleared sf2"` summaries surface
  without a dedicated switch-case. The planned chunk-8 dedicated
  renderer folded into the generic path.
- US-keyboard-layout assumption for `?` (Shift+/ →
  `event.key === '?'`); R / S work on any layout. Follow-up could
  match `event.code === 'Slash' && event.shiftKey`.
- E2E Playwright spec deferred to a follow-up; per-test coverage
  in vitest + pytest pins behaviour against drift.

### Documentation bundle — README hero shot + CONTRIBUTING.md (closed 2026-05-16)

Two queued documentation items from 1.4.0 closed together as a single
docs bundle.

**Added**

- Hero shot at the top of `README.md` (`docs/screenshots/library.png`)
  and a new `## Screenshots` section showing the alternatives drawer
  (parent/clone picker), the filters tab in Settings, and the named-
  sessions panel.
- `CONTRIBUTING.md` covering local-dev quickstart, bug-report template,
  the local CI gate (backend five + frontend three), the TDD policy
  with per-module coverage floors, the per-feature `spec.md`
  requirement, Conventional Commits, a summary of the App-Build
  9-step phase loop, and a "what this project deliberately does not
  do" section.
- `frontend/screenshots/` directory holding a dedicated Playwright
  config (`playwright.config.ts`) + capture spec (`capture.spec.ts`)
  that regenerates `docs/screenshots/*.png` against the real
  `config.yaml`. Independent of `frontend/e2e/` so the regression
  suite continues to use the deterministic 6-machine fixture.

**Changed**

- `README.md`'s short "Contributing" section now points at the new
  `CONTRIBUTING.md` instead of restating commit conventions inline.

**Notes**

- The `settings — paths tab` capture was deliberately omitted from
  the spec — it renders the user's real `/mnt/...` mount paths, which
  isn't a good first-impression image for the README. Re-add behind a
  redaction step if it's wanted later.

### DS03 — Dependency freshness sweep (closed 2026-05-16)

8 clusters folding every direct dep + GitHub Actions pin + pre-commit
hook rev forward to its current latest stable, plus a new frontend CI
lane that gates `npm run lint` / `tsc --noEmit` / `npm test` on every
push. Spec at [`docs/specs/DS03.md`](docs/specs/DS03.md); closing
`/audit` returned clean (trivy/gitleaks/semgrep/ruff/bandit all zero
findings); closing `/indie-review` 4-lane sweep surfaced 7 actionable
findings folded as Cluster R1. Shipped across 10 commits
(`1916cd7..f9be074`).

Two new docs-tests at `tests/docs/` (`test_dep_pin_coupling.py`,
`test_no_pre_release_pins.py`) make the cross-pin invariants
(uv.lock ↔ pre-commit hook revs; ci.yml/release.yml ↔ pre-commit
gitleaks rev) CI-enforceable so the DS02-R2-shape "CI catches what
local missed" gap cannot recur for dep pins.

**Highlights (user-visible deliverables):**

- **Latest stable across the dependency tree.** Five Python runtime
  + dev floors bumped (`pydantic >=2.13`, `uvicorn[standard] >=0.47`,
  `sse-starlette >=3.4`, `hypothesis >=6.152`, `ruff >=0.15`).
  Eighteen frontend floors bumped (React 19.2.6, Vite 8.0.13,
  Vitest 4.1.6, Tailwind 4.3.0, TypeScript 6.0.3, ESLint 10.4.0,
  Playwright 1.60.0, etc.). Five pre-commit hook revs aligned.
- **Node 24 LTS.** `engines.node: "20.x"` → `"24.x"` (Node 20 reached
  End-of-Life April 2026; Node 24 is the current Active LTS).
- **New frontend CI lane.** `frontend-lint-types-test` job in
  `ci.yml` + `release.yml` (Linux-only matrix; reads
  `node-version-file: frontend/package.json` for the LTS floor;
  gates `npm ci` → `eslint` → `tsc --noEmit` → `vitest`). Closes the
  gap where every prior release shipped trusting local pre-commit
  for the frontend.
- **Opportunistic mypy 1 → 2.** The `>=1.13` constraint was unbounded
  so `uv lock --upgrade` pulled the major; `uv run mypy` returned
  clean on all 175 source files under `strict = true` unchanged, so
  the bump qualified under the spec's "non-breaking only" test. The
  mypy 2.0 strict-mode default-shifts (`--strict-bytes`,
  `--local-partial-types`) are documented inline in `pyproject.toml`
  so future contributors aren't surprised.
- **Cross-pin lockstep enforced.** New `tests/docs/test_dep_pin_
  coupling.py` asserts `uv.lock` ↔ `.pre-commit-config.yaml` parity
  for ruff/mypy/bandit and triple parity (`ci.yml` ↔ `release.yml` ↔
  `.pre-commit-config.yaml`) on `GITLEAKS_VERSION`. The HEAD-visible
  drift surfaced at Step 1 (pre-commit gitleaks `v8.21.0` vs CI
  `8.24.3`) is closed and the test prevents recurrence.
- **Spec-text drift caught.** Cluster H corrected `pnpm` →
  `npm` command samples in `docs/specs/{DS02,DS05}.md` that had
  diverged from `P06.md`'s source-of-truth ("npm not pnpm/yarn/bun").

**Deferred to follow-up phases (per the spec's non-breaking-only
rule):** pydantic v3, fastapi 1.0, react 20, vite 9, mypy 3.x,
`actions/upload-artifact` v5+, `actions/download-artifact` v5+,
`softprops/action-gh-release` v3, `pre-commit-hooks` v6,
`@types/node` v25.

### DS05 — Test-file seam-split sweep (closed 2026-05-16)

Three test files breaching their size caps split along stable seams;
one permanent fix for the DS02 R2 lesson wired into pre-commit.
Spec at [`docs/specs/DS05.md`](docs/specs/DS05.md); two cold-eyes
review loops converged on the implementation; closing `/audit`
returned clean (10/10 gates pass); closing `/indie-review` 5/5
lanes PASS with 2 LOW spec-history nits folded as Cluster R1.
Shipped across 7 commits (`738b418..d9c6817`).

Patterns addressed: three test files over their layer's hard cap
split into siblings + helper modules so the entire test suite
respects `coding-standards.md` § 2; one CI-only gate
(`tools/check_api_types_sync.py`) wired into `.pre-commit-config.yaml`
so the DS02 R2 "CI catches what local missed" gap is closed
permanently. No production-code changes; same tests run before
and after, just organised across more files.

**A — `SettingsPage.test.tsx` split (742 → 336 + 301 + 104)** `2e1f754`:

- New `_settingsPageFixtures.tsx` hoists the `render` wrapper +
  `config: AppConfigResponse` literal so all three test files
  import one source.
- `SettingsPage_render.test.tsx` (was L72-L349 of the original)
  carries the 9-tab headers + RetroArch Setup-banner `it.each`
  + Updates R36 banner + Filters/Picker chip-lists +
  Updates/Interface dropdown render-and-patch pairs.
- `SettingsPage_destructive_confirm.test.tsx` (was L520-L602)
  carries the FP12 § H + FP13 § B2 destructive-DAT-confirm
  cluster (4 `it` blocks).
- Main `SettingsPage.test.tsx` retains year-range, region-priority,
  snapshots, media-cache, paths, backup-export, restart-banner,
  cart_clear_on_copy + the DS02 D1 `?tab=` URL-state nested
  describe.

**B — `test_runner.py` split (526 → 240 + 277)** `1ed6d3f`:

- New `tests/copy/_runner_helpers.py` hoists `_machine` + `_plan`
  factory helpers so both test files import them.
- `test_runner_lifecycle.py` (was L274-L526) carries Pause /
  resume / cancel + DS01 + FP05 clusters.
- Main `test_runner.py` retains Dry-run + Apply + Playlist
  conflict tests.

**C — `test_dat.py` split (447 → 112 + 121 + 255)** `7b565f2`:

- `test_dat_basic.py` (was L13-L105): happy-path parsing.
- `test_dat_security.py` (was L107-L211): XXE entity
  exfiltration, billion-laughs DoS, zip-bomb member-size cap.
- `test_dat_validation.py` (was L212-L447): structural
  well-formedness, value-range checks, file-typing, driver-
  status rate-limiting, FP04 OSError surfacing.
- `mini_dat` fixture in `tests/parser/conftest.py` auto-inherited
  via pytest's conftest scoping; no fixture duplication.

**D — Permanent fix for the DS02 R2 lesson** `aa2ded0`:

- **D1:** `.pre-commit-config.yaml` gains a local
  `check-api-types-sync` hook (`pass_filenames: false`,
  `always_run: true`). The hook now fires on every commit so
  the Python ↔ TS drift gate runs locally, not just in CI.
- **D1-test:** `tests/tools/test_check_api_types_sync.py` pins
  two invariants: the script exits 0 at HEAD; `PYTHON_SOURCES`
  covers every `api/schemas*.py` sibling at HEAD (exact DS02 R2
  root-cause regression-lock — a future split that adds another
  sibling fires this test in the same commit).
- **D2:** `docs/standards/coding-standards.md` § 2 extended with
  an explicit test-file caps row (Python tests 500/300, frontend
  test files 500/300). Closes the test-cap ambiguity DS04 left
  unresolved.
- **D3:** `docs/journal/DS02.md` "What was learned" updated to
  cross-reference DS05 Cluster D as the closing fix for the
  R2 post-mortem follow-up.

**R1 — Closing-review fold-in (2 spec-history corrections)** `d9c6817`:

- **R1a:** `docs/specs/DS05.md` § "Tests to write first" said
  "three structural-assertion tests"; HEAD has 18 cases across
  two files. Spec updated.
- **R1b:** spec named `_settingsPageFixtures.ts`; HEAD is `.tsx`
  (JSX requirement). Spec note added.

Five backend gates green at close: 605 pytest pass / 87% coverage /
0 ruff / 0 ruff-format / 0 mypy / 0 bandit. Frontend gates green:
301 vitest pass / 0 eslint / 0 tsc. New pre-commit gate green:
`check_api_types_sync.py` exits 0 at HEAD (89 models scanned across
12 files; 61 TS interfaces match).

### DS02 — Tier 3 structural debt sweep (closed 2026-05-15)

18 sub-bullets across 7 clusters sourced from the 2026-05-04 +
2026-05-14 indie-review Tier 3 partitions and the 2026-05-14
debt-sweep mechanical-drift batch, scoped down by Step 1
verification (6 of 17 original sub-items dropped as verified stale).
Spec at [`docs/specs/DS02.md`](docs/specs/DS02.md); cold-eyes review
converged through 2 loops; closing `/audit` returned clean; closing
`/indie-review` surfaced 3 MED + 1 LOW on the DS02 surface itself,
folded as Cluster R1. Shipped across 4 commits (`c0a6ad6..eb000e4`).

Patterns addressed: five source files over the 500-line hard cap
split into smaller modules; six hardcoded "Loading…" JSX strings
moved into `strings.loading.*`; skip-to-main link + `<main>` label
+ `aria-live` polite regions on route-level loading fallbacks +
sibling-landmark labels on Help / Library / Cart asides; Settings-tab
URL state via `useSearchParams`; AlternativesDrawer + CopyModal
wrapped in `ErrorBoundary` with named-string fallbacks; CHANGELOG
versioning-policy paragraph refreshed to current truth +
`frontend/package.json` lockstep with `pyproject.toml` at v1.2.0 +
new `.claude/bump.json` recipe entry; `revision_key_of` memoization
via `@functools.lru_cache(8192)`; `WorldState.bytes_by_machine`
precomputed at construction so `GET /api/games` per-request bytes-sum
drops from O(M × R) to O(|filtered|).

**A — Oversized source file splits (A1–A5)** `8bf3844`:

- **A1:** `frontend/src/api/types.ts` 1032 → 493 lines; zod validators
  extracted to sibling `frontend/src/api/schemas.ts` (591 lines —
  acknowledged "Deliberately not in scope" exception, see R1c).
  Public import surface preserved via re-export.
- **A2:** `src/mame_curator/cli/__init__.py` 631 → 187 lines; one
  module per subcommand under `cli/commands/{parse,filter,copy,setup,
  serve,refresh_inis}.py`; dispatching `build_parser()` + `main()`
  stay in `cli/__init__.py`. `argparse.set_defaults(func=...)`
  dispatch shape unchanged.
- **A3:** `frontend/src/strings.ts` 622 → 14 lines (re-export barrel);
  body extracted to `frontend/src/strings_internal.ts` (646 lines —
  pre-approved as "Deliberately not in scope": per-domain folder
  split would force every call-site to update its import path).
- **A4:** `src/mame_curator/copy/runner.py` 518 → 540 lines (file
  still over cap); `_resolve_conflicts` (~80 lines) extracted as
  module-level helper. Full per-phase decomposition of `run_copy`
  remains deferred per spec § Deliberately not in scope (warrants
  its own focused spec).
- **A5:** `src/mame_curator/api/schemas.py` 515 → 329 lines (re-export
  facade); 40 Pydantic models split into 5 sibling modules
  (`schemas_copy.py`, `schemas_fs.py`, `schemas_games.py`,
  `schemas_overrides.py`, `schemas_setup.py`). Sibling-file layout
  preferred over the originally-named `schemas/` package directory
  (functionally equivalent, one fewer directory).

**B — Hardcoded UI strings (B1/B2)** `eeaff05`:

- **B1:** added six `strings.loading.*` entries (`sessions`, `activity`,
  `stats`, `help`, `settings`, `generic`) matching the existing
  `error.*` / `confirm.*` namespacing.
- **B2:** replaced six literal "Loading…" JSX strings in
  `frontend/src/App.tsx` with `strings.loading.*` references.

**C — Accessibility polish (C1–C4)** `eeaff05`:

- **C1:** "Skip to main content" link added at the top of
  `AppShell.tsx` (standard `sr-only focus:not-sr-only` pattern);
  `<main>` gains `id="main"` + `tabIndex={-1}`.
- **C2:** `<main>` landmark labelled via `strings.a11y.mainLandmark`
  so screen readers announce "Main content, region" not just
  "main, region".
- **C3:** five route-level loading fallbacks in `App.tsx` wrapped
  in `<div role="status" aria-live="polite">` so screen readers
  announce route transitions.
- **C4:** four sibling-landmark `aria-label`s on `<aside>` / `<article>`
  in `HelpPage.tsx` (topic list + rendered topic), `LibraryPage.tsx`
  (FiltersSidebar), and `CartPanel.tsx`.

**D — Settings-tab URL state (D1)** `eeaff05`:

- **D1:** `SettingsPage.tsx` now persists the active tab via
  `useSearchParams` (`?tab=…`). Deep-linking a tab works; back-button
  moves between tabs; default-tab behaviour preserved when the param
  is absent.

**E — ErrorBoundary nesting (E1/E2)** `eeaff05`:

- **E1:** `AlternativesDrawer` wrapped in `<ErrorBoundary>` so a
  render error stays scoped to the drawer subtree instead of
  crashing the library page.
- **E2:** `CopyModal` wrapped in `<ErrorBoundary>` for the same
  reason. Named fallback strings wired in R1b.

**F — Mechanical drift (F1/F2)** `eeaff05`:

- **F1:** `CHANGELOG.md` versioning-policy paragraph rewritten to
  current truth ("v1.0.0 shipped at P09 (2026-05-04). Subsequent
  minor releases accumulate phase-closing tags between them…").
- **F2:** `frontend/package.json` bumped 0.0.1 → 1.2.0 to match
  `pyproject.toml`; `.claude/bump.json` recipe entry added so future
  `/bump` runs roll both versions in lockstep.

**G — Perf micro-fixes (G1/G2)** `eeaff05`:

- **G1:** `revision_key_of` in `filter/heuristics.py` decorated with
  `@functools.lru_cache(maxsize=8192)`. Each call inside
  `_cmp_revision` (twice per pair × N log N comparisons per
  candidate-group sort) now hits the cache instead of redoing the
  regex-and-tuple work. Tests in
  `tests/filter/test_picker_revision_memoization.py` call
  `cache_clear()` before each stateful assertion so process-wide
  state doesn't leak between tests.
- **G2:** `bytes_by_machine: Mapping[str, int]` precomputed on
  `WorldState` at construction (`api/state.py`); call sites in
  `api/routes/games.py` now do `O(|filtered|)` instead of
  `O(M × R)` per request.

**R1 — Closing-review fold-in (3 corrections)** `eb000e4`:

- **R1a:** `frontend/src/api/types.ts:6` comment mis-cited the DS02
  cluster id for the zod extraction ("A3" — the strings split;
  the types/schemas split is A1). One-line correction.
- **R1b:** DS02 spec § E1/E2 promised named fallbacks on the two
  modal `ErrorBoundary` wraps; HEAD wrapped both modals
  structurally but passed no `fallback` prop. Added
  `strings.errors.alternativesFailed` + `strings.errors.copyModalFailed`
  and wired `fallback` props on both boundaries using the project's
  existing alert-panel pattern. Test extended with two source-text
  grep assertions (RED pre-fix, GREEN post-fix).
- **R1c:** DS02 spec amendments — § A5 acknowledges the sibling-file
  layout that actually shipped (vs originally-named `schemas/`
  package directory); § "Deliberately not in scope" adds
  `frontend/src/api/schemas.ts` (591 lines) entry with the per-domain
  split rationale.

Five backend gates green at close: 583 pytest pass / 87.27% coverage
/ 0 ruff / 0 ruff-format / 0 mypy / 0 bandit. Frontend gates green:
301 vitest pass / 0 eslint / 0 tsc.

### FP28 — Tier 2 review fold-in: hardening + correctness (closed 2026-05-15)

14 sub-fixes sourced from the 2026-05-14 11-lane `/indie-review` (Tier 2
partition). Spec at [`docs/specs/FP28.md`](docs/specs/FP28.md); cold-eyes
review converged through 3 loops (33 verified findings folded inline);
closing `/indie-review` surfaced 3 findings (1 HIGH + 2 MEDIUM) folded
as Cluster R1. Shipped across 6 commits (`cb35f26..72505d8`).

Patterns addressed: concurrency invariants under non-loop-thread or
parallel-session entry (`JobManager._emit`, `recycle_file`), regex
mis-capture on nested parens (`_LICENSE_RE`) and false-positive on
parenthetical-title region words (`REGION_RE`), mixed-content text
truncation in `Machine.description`, half-wired dual-channel
warnings in `filter.runner`, raw `KeyError` leaking past the typed-
error boundary in `_apply_session`, missing boundary validation for
`paths.retroarch` / `paths.retroarch_core` (PATCH → launch chain),
missing browser-cache headers in `/media/*` proxy, wrong POSIX exit
code from `serve` on Ctrl-C, bare `except Exception` around
`create_app`, raw `ImportError` traceback from `refresh-inis`, and
the wizard-vs-runtime trust-model split for INI refresh.

**A — Concurrency hardening (A1/A2/A3)** `cb35f26`:

- **A1:** hoisted `JobManager._loop` assignment from `start()` to
  `__init__` (with optional `loop` parameter + fallback for sync
  test fixtures), then enforced the loop-thread invariant at the top
  of `_emit` via `RuntimeError` (so `python -O` cannot strip the
  guard). Check sits after the existing `_current-is-None` early
  return so FP21-L's no-op-on-cleared-current contract is preserved.
- **A2:** wrapped the `recycle_file` critical section in a stdlib
  `os.O_EXCL` lockfile at `recycle_root / f"{session_id}.lock"` —
  serialises parallel sessions in the same `session_id` without
  pulling a `filelock` dep. Orphan recovery threshold 60 s (~1200x
  the same-fs p99); same-process contention falls through to a 10 ms
  retry-sleep.
- **A3:** under A2's lock, the `target_dir_existed` snapshot is
  race-free; neither rollback path (manifest-write OSError, post-
  move OSError) can rmdir a directory another session relies on.
  Inline comments at the snapshot site and the lock-acquire credit
  the invariant.

**B — Correctness regex + extraction + typed errors (B1–B5)** `a85307d`:

- **B1:** rewrote `_LICENSE_RE`'s developer capture from `.+?` to
  `[^()]+?` — nested-parens inputs like `"Atari (JSA III) (Williams license)"`
  now correctly bind publisher=`"Atari (JSA III)"`, developer=`"Williams"`
  instead of mis-binding to `"Atari"` / `"JSA III) (Williams"`.
- **B2:** tightened `REGION_RE` with a two-branch form — after the
  region token, allow either (whitespace + comma/close-paren/EOL —
  `(World)`, `(USA, Set 2)`) or (whitespace + non-uppercase char —
  `(World 910411)`, `(Europe v2.1)`). Rejects `(World Heroes 2)`
  because `Heroes` starts with an uppercase H. The lookahead branch
  was added during testing after the initial single-branch form
  broke real MAME `(Region YearOrVersion)` patterns.
- **B3:** switched `Machine.description`'s source from
  `description_elem.text` to `"".join(description_elem.itertext()).strip()`
  — mixed-content `<description>Foo <i>bar</i> baz</description>`
  now yields `"Foo bar baz"` rather than truncating at `"Foo "`.
  Defensive (MAME DATs don't currently ship mixed-content).
- **B4:** wired `logger.warning(msg)` alongside the existing
  `FilterResult.warnings.append(msg)` at the three override-
  rejection paths in `filter/runner.py`. Dual-channel contract per
  `filter/spec.md` § Phase C.
- **B5:** wrapped the `sessions.sessions[sessions.active]` subscript
  in `_apply_session` and re-raised bare `KeyError` as
  `SessionsError(FilterError)`. Reachable only via Pydantic v2
  `model_copy` (which skips validators); direct construction is
  blocked by the existing `model_validator`.

**C — Boundary hardening (C1/C2)** `0281695`:

- **C1:** extended `_validate_paths` to gate `paths.retroarch` (POSIX
  `os.access(p, os.X_OK)` / Windows `shutil.which`) and
  `paths.retroarch_core` (`.exists()` on both platforms — cores are
  `dlopen`/`LoadLibrary`'d, not directly executable). Closes the
  PATCH-config → launch chain — pre-fix a malicious PATCH could land
  `paths.retroarch=/usr/bin/evil-thing` which `api/routes/games.py:275`
  would then hand to `subprocess.run`.
- **C2:** replaced `media_proxy`'s hardcoded `media_type="image/png"`
  with `mimetypes.guess_type(str(path))[0] or "image/png"` (suffix-
  sniffed) and added `Cache-Control: public, max-age=2592000, immutable`
  per design § 6.3 ("Cache is permanent by default"). Pre-fix every
  page-load re-fetched libretro thumbnails despite the permanent
  on-disk cache.

**D — CLI exit-code + error-surface drift (D1/D2/D3)** `8fe7641`:

- **D1:** wrapped `uvicorn.run` in `try/except KeyboardInterrupt:
  return 130` (defence-in-depth — uvicorn currently catches Ctrl-C
  internally) and changed the trailing return from 0 to 130 so the
  function honours POSIX convention regardless of which side ends up
  catching the signal.
- **D2:** narrowed the bare `except Exception` around `create_app()`
  to `(ConfigError, ParserError, FilterError)`. Programmer errors
  (RuntimeError, AttributeError, ...) now propagate as tracebacks
  instead of being squashed into a one-line stderr message. Per
  coding-standards § 9 typed-error hierarchy: the traceback IS the
  actionable signal.
- **D3:** lifted the three inline imports (asyncio, httpx,
  mame_curator.updates) in `_cmd_refresh_inis` into a `try/except
  ImportError` mirroring `_cmd_serve`'s guard. Defence-in-depth
  pattern consistency — httpx is a top-level dep so the ImportError
  path only fires in exotic install states (pip install --no-deps,
  broken wheel, partial editable install).

**E — Design § 6.7 deferral (E1)** `8dcae9d`:

- **E1:** new ADR at
  [`docs/decisions/0004-ini-refresh-trust-model.md`](docs/decisions/0004-ini-refresh-trust-model.md)
  recording the wizard-vs-refresh split (§ 6.6 promised mirrors +
  sha256 for the wizard bootstrap; § 6.7 runtime refresh stays
  silent on integrity), current refresh trust posture (HTTPS-only,
  AntoPISA repo, no per-file sha256), and the post-v1 hardening
  path. One-line cross-link added to design.md § 6.7 so the next
  reviewer doesn't re-raise the conflated flag.

**R1 — Closing-review fold-in (3 corrections)** `72505d8`:

- **R1.1:** C2 tests were dead — `if status != 200: return` short-
  circuited the cache-control assertion without raising, and the
  sniff test was a bare `pytest.xfail` with no body (both would
  have passed against pre-fix code, failing acceptance criterion 9's
  red-pre-fix / green-post-fix demand). Rewrote both tests using
  the existing `tests/api/test_routes_media.py` respx mock pattern.
- **R1.2:** D2's narrowed-except is semantically dead at the
  immediate call site — `create_app` is currently a pure FastAPI
  factory and config validation happens inside the async lifespan.
  Amended the inline comment to name the dead-code constraint as
  defence-in-depth for a future refactor.
- **R1.3:** FP28.md § B2 spec text described a single-branch regex
  tightening; updated the spec body to document the two-branch
  lookahead form that shipped, naming the regression that drove
  the refinement.

### DS04 — Test-suite quality sweep (closed 2026-05-15)

37 sub-fixes sourced from the 2026-05-15 5-lane test-suite audit
(parser+filter / copy / api+media+downloads / frontend components /
frontend pages+e2e) on commit `06fe3b8` (post-FP27). Spec at
[`docs/specs/DS04.md`](docs/specs/DS04.md); cold-eyes loop converged
on a single pass (10 findings folded inline); closing review surfaced
3 comment-drift findings folded as Cluster R1. Shipped across
5 commits (`dca57b2..d5918a0`).

Patterns addressed: dead-spec coverage (FP25-C rollback tests
contradicting `copy/spec.md:260`'s FP21-D supersession), vitest
prototype / global-state pollution leaks, unnecessary I/O (50k JSONL
twice, 6 MiB string allocations, 2.5 s Playwright sleep, 2 MB YAML
writes), FP##-named duplicate tests subsumed by canonical files, an
empty Hypothesis strategy, 11 redundant `afterEach(() => cleanup())`
calls under vitest auto-cleanup, and a hardcoded `/tmp/` path with
`# noqa: S108`.

**T1a — Tier 1 backend mechanical batch** `dca57b2`:

- T1.1: deleted two FP25-C rollback tests in `tests/copy/test_fp25_recyclebin.py`. The "rollback returns file to original" premise was retired by FP21-D's manifest-first ordering (`copy/spec.md:260`); the tests passed today only because `src.exists()` was trivially true on the post-FP21-D path. Two FP25-F tests remain.
- T1.4: replaced `JobManager(history_dir=Path("/tmp/unused"))  # noqa: S108` in `tests/api/test_fp21_fixes.py:233` with `tmp_path`.
- T1.5: collapsed three iterparse-OSError tests in `tests/parser/test_listxml.py` (one per `parse_listxml_*` callable) to one `@pytest.mark.parametrize`.
- T1.6: relocated `test_listxml_cloneof.py` + `listxml_cloneof.xml` fixture from `tests/filter/` to `tests/parser/`; added a `listxml_cloneof` fixture to `tests/parser/conftest.py`.
- T1.7: removed the dead `monkeypatch.setattr(executor, "copy_one", ...)` in `tests/copy/test_runner.py`. `runner.py:17` imports `copy_one` at module level, so only the runner-module patch is load-bearing.
- T1.9: dropped a bare `time.sleep(0.1)` after copy abort in `tests/api/test_routes_copy.py`; no assertion was gating the wait. Removed the now-unused `import time`.
- T1.10: hoisted `_plant_50k_activity_log` from per-test helper to a `@pytest.fixture` in `tests/api/test_routes_activity.py`; dropped a stale comment that claimed the planter wrote `f"/tmp/{i}"` (actual format is `f"sample://{i}"`).
- T1.13: parametrized two `retroarch_configured` setup-check tests in `tests/api/test_routes_stubs.py` over `(has_retroarch, has_core, expected)`; added the missing `core_only` case for completeness.

**T1c — Tier 1 frontend batch** `908df0c`:

- T1.2: `LibraryGrid.test.tsx` `beforeAll` now captures original `clientHeight`/`clientWidth`/`getBoundingClientRect` descriptors and restores them in a new `afterAll`. The prior stub leaked the 1200×600 dimensions into every later-running test file.
- T1.3: dropped a nested `beforeEach`/`afterEach` in `useCopySession.test.tsx` that bypassed `vi.stubGlobal` (so `vi.unstubAllGlobals` couldn't restore) and added a redundant cleanup. The file-level setup at line 57 already covers nested describes.
- T1.8: collapsed three `LibraryGrid` `data-columns` formula tests to one `it.each` table over `(layout, hint, expected)`, adding the `'auto'` case the original rerender-based test exercised inline.
- T1.11: dropped `page.waitForTimeout(2500)` in `frontend/e2e/fp25-ux-walkthrough.spec.ts`. Playwright's `expect(toasts).toHaveCount(1)` auto-polls up to 5 s — comfortably covers the 1500 ms dedup window without a hardcoded sleep.
- T1.12: `BackupTab.test.tsx` size-cap test stubs `File.size` via `Object.defineProperty` instead of allocating a 6 MiB string.
- T1.14: replaced the tautological `querySelectorAll('[role="button"]').length < 3000` assertion in the `LibraryGrid` virtualization test with a non-vacuous spacer-height check (≥ 10,000 px for a 3,000-card grid at 280 px row pitch / 5 cols).

**T2a — Tier 2 backend batch** `9817c56`:

- T2.9: deleted `test_copy_one_cleans_tmp_on_keyboard_interrupt` from `tests/copy/test_fp01_fixes.py`. The equivalent at `test_fp02_fixes.py:317` uses a `progress=` callback and exercises the same `_chunked_copy` write path; post-FP27 B1 both branches funnel through it.
- T2.10: deleted `test_recycle_same_name_same_second_does_not_clobber` from `test_fp01_fixes.py`. The equivalent at `test_fp02_fixes.py:158` exercises a stronger `session_id`-distinguishing assertion; the canonical `test_recyclebin.py:95` pins the dir-uniqueness contract.
- T2.11: deleted `test_copy_error_str_renders_path_suffix` + `test_copy_error_str_without_path` from `test_fp01_fixes.py`. Subsumed by `tests/copy/test_errors.py:15-46` which iterates over every `CopyError` subclass and additionally locks the FP07 A4 control-byte repr contract.
- T2.14: dropped the `@given(st.fixed_dictionaries({}))` decorator in `tests/api/test_routes_config.py:126`. The strategy only ever generated `{}`, so the test wasn't actually Hypothesis-driven. Removed four unused Hypothesis imports.
- T2.16: `test_overrides_oversized_yaml_rejected` + `test_sessions_oversized_yaml_rejected` swap 2 MB valid-YAML payloads for `b"0" * (1024 * 1024 + 1)`. The 1 MiB pre-parse cap fires on byte count alone.
- T2.17: dropped the `elapsed < 5.0` defence-in-depth checks in `tests/parser/test_dat.py`'s billion-laughs test. The `len(desc) < 1000` length assertion is the strong signal; wall-time thresholds on CI flake.
- T2.19: `test_copy_progress_callback_emits_chunks` writes its 3 MiB source file into `tmp_path` instead of the module-scoped `source_dir`, so `big.zip` doesn't leak into other tests that iterate over the shared fixture.

**T2b + T3 — Tier 2 frontend dedup + Tier 3 polish** `0011eb8`:

- T2.12: collapsed two near-identical 70-line `retroarch_configured` tests in `SettingsPage.test.tsx` to one `it.each` table over `(configured, expectedText)`.
- T2.13: dropped three unit-duplicate tests from `frontend/e2e/cart-flow.spec.ts` (expand chevron, remove row, Copy-disabled). All covered deterministically at unit level by `CartBar.test.tsx` + `CartPanel.test.tsx`. Kept only the +Add → footer-updates → ✓Added → banner-dismiss integration scenario. Also removed the surviving test's `page.waitForSelector` (locator auto-wait covers it).
- T3.1: removed 11 redundant `afterEach(() => cleanup())` blocks across `FiltersSidebar.test.tsx`, `ChipListEditor.test.tsx`, `DragReorderList.test.tsx`, `BackupTab.test.tsx`, `FsBrowser.test.tsx`, `SnapshotsTab.test.tsx`, `YearRangeEditor.test.tsx`, `useConfig.test.tsx`, `useFs.test.tsx`, `useCopySession.test.tsx`, `useValidateCart.test.tsx`. Vitest `globals: true` enables RTL auto-cleanup. Where the `afterEach` was load-bearing for other work (mock-clear), kept the block and dropped only the redundant cleanup line.
- T3.2: `FeaturedTilesRow.test.tsx` swapped `getByText('Capcom Classics').closest('button')` for `getByRole('button', { name: 'Capcom Classics' })` — RTL idiom + a11y-regression detector.
- T3.3: deleted the `pytest.skip` placeholder `test_no_listxml_self_parents_every_machine` in `tests/api/test_routes_games.py`. A skip-only body inflates the test count without proving anything; the canonical coverage lives directly above at `test_cloneof_map_collapses_winners` (FP23 regression).
- T3.4: tagged four tracemalloc-based streaming tests (`test_routes_activity.py` × 2, `test_cache.py`, `test_downloads.py`) with `@pytest.mark.slow`; registered the marker in `pyproject.toml`.
- T3.5: deleted `frontend/src/test/fixtures.ts` — 7-line doc-only stub promising a fixture that didn't exist.
- T3.6: `CmdKPalette.test.tsx` SECTION_ORDER export check now uses `expect(...).toBeDefined()` instead of `throw new Error(...)`.
- T3.7: dropped the tautological `cart.getAttribute('href')` assertion in `AppShell.test.tsx`.
- T3.8: `AppShell.test.tsx` active-link assertion switched from a `font-medium` Tailwind class check to `aria-current="page"` (a11y contract).
- T3.9: deleted `frontend/src/components/__tests__/EscOverlayBehavior.test.tsx`. The suite regression-locked Radix's built-in `<Dialog>`/`<AlertDialog>` Escape-key behaviour — library-coverage, not project code.
- T3.11: `playwright.config.ts` switched `trace: 'retain-on-failure'` to `trace: 'on-first-retry'`.
- T3.12: pinned the surviving outcome in `HelpPage.test.tsx:160` FP25-J test (sanitizer keeps `<img>` with `src=null`); dropped the early-return branch that made the assertion vacuous on the alternate outcome.
- T3.13: clarified the legacy-mtime fallback docstring in `tests/copy/test_recyclebin.py`'s `test_recycle_retention_purges_old_entries`.

**Cluster R1 — closing-review fold-in** `d5918a0`: three comment-only corrections from the post-DS04 review on the changeset itself.

- R1a: rewrote T3.3's `audit-trail` comment to point at the actual canonical test (`test_cloneof_map_collapses_winners` in the same file) instead of a non-existent `api/routes/spec.md`.
- R1b: fixed the row-pitch number in `LibraryGrid.test.tsx`'s spacer-height comment (`280` px, not `~320` px).
- R1c: corrected the HTML rationale in `AppShell.test.tsx` (`href` is inert on `<button>`, not "doesn't exist").

**Out of scope / deferred:**

- **T1.15** (audit's `_os.utime` legacy-fallback rewording) reframed to T3.13 — the legacy-mtime code path is still live and correctly exercised.
- **T2.1–T2.4** (helper hoisting `_machine` / `_plan` / `_seed_existing_playlist` / `_entry` / `_make_job` to conftest) — the helpers are duplicated across 2–4 sites each, but file-cap acceptance criterion isn't met by helper hoisting alone (the two over-cap files need structural splits). Deferred to a future sweep.
- **T2.7** (extract 50-line YAML literal from `tests/api/conftest.py` to a fixture file) — same rationale.
- **T2.18** (remove 6 Linux-only OSError-skip clauses) — audit was incorrect; CI matrix is multi-OS (`ubuntu-latest, macos-latest, windows-latest` per `.github/workflows/ci.yml:20`). The OSError-skip clauses defend against Windows/macOS filesystem behaviour and are load-bearing. Dropped from scope.
- **T3.10** (collapse `SettingsPage.test.tsx:506-587` DAT-confirm cluster) — the four tests assert different aspects of the confirm-flow and a structural collapse risks regression. The file remains over the hard cap and is covered by the conditional `[mame-curator-1034]` roadmap follow-up.
- **Three conditional roadmap follow-ups** (`[mame-curator-1034/1035/1036]`) opened at DS04-spec-time for files that might stay over-cap after the sweep. Post-DS04 sizes: `SettingsPage.test.tsx` 686→665, `tests/copy/test_runner.py` 528→526, `tests/parser/test_dat.py` 453→447. All three stay over-cap (685 → 665 still > 500; 526 still > 500; 447 still > 300 soft cap). Entries remain `📋` for a future sweep.

**Acceptance result:** 552 backend tests → 546 (-6 net: -2 FP25-C, -2 from parametrize collapses, -1 dup KeyboardInterrupt, -2 dup CopyError __str__, -1 pytest.skip placeholder, +2 from added retroarch core_only case + various). Frontend 280 → 278 (-2 from EscOverlayBehavior deletion; T1.8 + T2.12 + T3 net neutral). Coverage 86.94% (unchanged within tolerance). Three file caps still over hard cap, tracked as conditional follow-ups.

### FP27 — Tier 1 review fold-in: zombie features + data integrity (closed 2026-05-14)

16 sub-bullets sourced from the 2026-05-14 11-lane `/indie-review`
Tier 1 partition: 9 zombie-feature reconciliations (with A6 split
a/b/c = 11 sub-fixes), 5 data-integrity hardening fixes, 2 doc-drift
fixes, plus closing-review Cluster R1 (4 fixes on the FP27 surface
itself). Spec at [`docs/specs/FP27.md`](docs/specs/FP27.md);
cold-eyes review converged on loop 5 (0 residual findings). Shipped
across 5 commits (`cfe612c..976b119`).

**T1a — A1/A2/A7/A9/C1/C2 mechanical batch** `cfe612c`:

- A1: `filter.ConfigError` deleted (no `raise` sites in `src/`;
  Pydantic `ValidationError` covers reachable validation).
- A2: `copy.PreflightError` deleted (FP07:101 flagged it three
  releases ago; no `raise` sites have appeared).
- A7: `--version` wired (`argparse action="version"`); `cli/spec.md`
  caveat dropped.
- A9: `parse_listxml_bios_chain` + `BIOSChainEntry` exported via
  `parser.__all__`; `parser/spec.md` documents both.
- C1: `CLAUDE.md` arch diagram drops stale `(P04 — next)`; P04 +
  P05 + P07 marked ✅.
- C2: `help/` + `setup/` ghost-module rows removed from `CLAUDE.md`
  + `README.md` diagrams; one-line annotation points at the real
  surfaces (`api/routes/help.py` and `api/routes/stubs.py`).

**T1b — A3 recyclebin activity events** `65615fb`: `recycle_file` +
`purge_recycle` append `FILE_RECYCLED` / `RECYCLE_PURGED`
`ActivityEvent` rows via the existing `copy.activity.append_activity`
writer + typed `*Details` constructors. Sentinel
`session_id="_purge"` for system-scoped purge action. Append
failures `logger.exception` (soft failure; FS state is primary
contract).

**T1c — Frontend Tier 1 batch** `4c54be4`:

- A4: `useCopySession.resolveConflict` removed; `CopyModal`'s three
  conflict buttons become a single read-only banner pointing at
  abort + restart with updated `append_decisions` (the only real
  resolution path — there is no `/api/copy/resolve-conflict`
  endpoint and post-v1 work would add one).
- A5: CmdK `'games'` + `'settings'` sections dropped at four
  lockstep call-sites (type union, `SECTION_ORDER`, `grouped`
  initializer, `strings.cmdK.sections`); palette hosts only
  `'actions'` + `'help'`.
- A6a: design-spec `Esc` bullet credits Radix `<Dialog>` /
  `<AlertDialog>` primitives (which deliver the behavior
  ambiently). Regression-lock at `EscOverlayBehavior.test.tsx`
  pins the empirical behavior for both primitives.
- A6b: `/` wired in `App.tsx`; second `useKeyboard` binding focuses
  `#filters-search` on the library FiltersSidebar.
- A6c: design-spec chord cohort (`?`, `g …`, `j`/`k`, `o`/`Enter`,
  `a`, `n`) struck with a note pointing at a P14-class follow-up
  for the chord engine + focused-card model.
- A8: `strings.ts` orphan-key sweep cleared. Deleted
  `historyEmpty`, `resetConfig`, `launchNotConfigured`. New
  `frontend/src/__tests__/strings.test.ts` runs the sweep with a
  `DYNAMIC_ACCESS_PARENTS` allowlist enumerating 20 legitimate
  `strings.<parent>[<var>]` patterns so future drift gets caught.

**T2 — Tier 2 data integrity** `2d9078e`:

- B1: `copy_one` fsync gap closed. `_chunked_copy` adds
  `fout.flush(); os.fsync(fout.fileno())` inside the `with` block;
  both write paths funnel through `_chunked_copy`; adds
  `fsync_parent_dir(dst)` after `os.replace`.
- B2: `restore_snapshot` stage-then-promote. Snapshot bytes land in
  `<snap_dir>/_restore_staging/<name>` first; live-target replaces
  run only after every staging write succeeds.
- B3: `download()` streams chunks straight to `.tmp` sibling of
  `dest`. Sha256 incremental; on cap-abort or mismatch, close-then-
  unlink the `.tmp` (Windows-safe order); `fsync` + parent-dir
  fsync wrap the `os.replace`.
- B4: `fetch_with_cache` rejects non-http(s) schemes before any
  network call; adds `max_bytes` cap (default 16 MiB) via
  `client.stream("GET", url)` + `aiter_bytes(64*1024)` writing to
  `.tmp` sibling.
- B5: `GET /api/activity` streams the JSONL line-by-line. Replaces
  `read_text(...).splitlines()` with `open()` +
  `deque(maxlen=page * page_size)`; slice formula
  `list(reversed(deque))[start:start+page_size]`. Per-request RAM
  scales with the deque, not the file size.

**Cluster R1 — closing-review fold-in** `976b119`: closing
`/indie-review` on the FP27 surface surfaced four findings on the
changeset itself.

- R1a: `downloads.py` — hoisted `tmp` binding above the attempt
  loop + widened the cleanup `except` to `(httpx.HTTPError,
  OSError)` so a flush/fsync OSError on the success path can't
  orphan a `.tmp`.
- R1b: frontend `/` binding — `e.preventDefault()` hoisted to the
  first handler line so Firefox's typeahead-find never wins
  off-route (`/help`, `/settings`, …).
- R1c: drive-by — removed a redundant inner `import shutil` in
  `api/persist.py:_prune_old_snapshots` (the top-level `import
  shutil` added for B2 made it ruff F811-adjacent dead code).
- R1d: `EscOverlayBehavior.test.tsx` regression-lock tightened to
  cover plain `<Dialog>` in addition to `<AlertDialog>` — the
  design-spec line credits both Radix primitives.

Deferred (filed for follow-up, not Tier 1):

- `/api/activity` deque preallocation DoS on unbounded `page`
  parameter — file for FP28 / DS02.
- `ActivityLogError` observability — caller can't see audit-trail
  drop on append failure (spec acknowledged as soft failure;
  post-v1 follow-up if needed).
- `--version` subparser propagation — currently top-level only,
  matches A7 spec; subparser inheritance is a follow-up.

Gate at close: 551 backend tests + 279 frontend tests + ruff + ruff
format + mypy + bandit + eslint + tsc all green. Tag:
`FP27-complete`.

### FP21 — `/indie-review` Tier 2 hardening sweep (closed 2026-05-11)

20 sub-bullets across `filter/`, `copy/`, `api/`, `downloads.py`,
`run.sh`, and the frontend, sourced from the 2026-05-04 multi-agent
review's Tier 2 fold-in. Real-bug class — manifests on common paths
but not a security hole or silent-loss vector. Shipped across 5
commits:

- **Filter A/B/C** `8363996` — `picker.explain_pick` now records the
  FIRST decisive tiebreaker per opponent (with union across opponents)
  instead of every tiebreaker that returned `<0` against any opponent;
  `tests/snapshots/filter_smoke.json` regenerated. `drops._device`
  uses strict-identity `m.runnable is False` so a future widening to
  `bool | None` doesn't flip "unknown" into DEVICE. `filter/spec.md`
  clarifies the per-opponent first-decisive semantics and the typed-
  error contract (loader → `SessionsError`; direct construction →
  Pydantic `ValidationError`).
- **Copy D/E/F/G** `e7a88f1` — `recyclebin.recycle_file` writes a
  per-file `<basename>.manifest.json` (was a per-dir `manifest.json`
  that multiple files in the same session overwrote), and writes the
  manifest BEFORE moving the file so the source is intact under any
  single-step failure. `preflight.preflight` includes BIOS-chain zips
  in `total_needed` and subtracts `already_copied` so the free-space
  gap reflects what `run_copy` actually transfers. `purge_recycle`
  decides eligibility from the latest `recycled_at` across manifests
  (legacy `manifest.json` fallback supported), and accumulates
  `bytes_freed` only after a successful `rmtree`. `executor.copy_one`
  wraps the initial `src.stat()` in `try/except FileNotFoundError →
  SKIPPED_MISSING_SOURCE` instead of FAILED.
- **API H + J** `f24a458` — `routes/media.media_proxy` returns
  `FileResponse(path)` instead of sync `path.read_bytes()` so the
  asyncio event loop interleaves under thumbnail fan-out.
  `routes/games.launch_game` raises typed
  `RetroArchNotConfiguredError(422)` and `RomFileNotFoundError(404)`;
  `strings.ts` byCode entries land beside the new codes — closes
  FP22-D that was deferred so the strings.ts no-dead-entry contract
  held.
- **API I/K/L/M/N/O** `0311040` — lifespan shutdown logs a WARNING
  on `thread.is_alive()` after join timeout (was silent detach).
  `JobManager._events_iterator` snapshots history to local tuples
  before `heapq.merge` and registers the subscriber before draining
  — fixes a real `deque mutated during iteration` race and a "lost
  events between replay and append" gap. L investigated and ruled
  non-reachable; defensive guard pinned with a test.
  `persist.snapshot_files` prunes oldest siblings beyond
  `MAX_SNAPSHOTS = 200`. `routes/config.patch_config` validates the
  body through a new `AppConfigPatch` (extra='forbid') per spec line
  647, with `deep_merge` depth-capped at 10 as defence-in-depth.
  `routes/config.import_config` drops `data/import.in_progress`
  during the 4-file batch so a startup-time check can detect a
  half-applied import.
- **Downloads P + run.sh Q + frontend R/S/T** `b6c6728` —
  `downloads.download` streams via `client.stream` +
  `aiter_bytes`, summing against `DEFAULT_MAX_BYTES = 100 MB` with
  Content-Length pre-check. `run.sh` pins `curl --proto '=https'
  --tlsv1.2` on the uv installer pipe. `useAlternatives`'
  `useOverride` + `useLaunchGame` bake `toastApiError` into
  `onError`. `useKeyboard` stores bindings in a ref so the listener
  registers once per lifetime — chord shortcuts (`g l`) now survive
  re-renders. `LibraryGrid` adds composite-grid semantics:
  `role="grid"` + `role="row"` + `role="gridcell"` with roving
  `tabindex`, arrow / `j` / `k` / `o` / Enter / Home / End nav, and
  `virtualizer.scrollToIndex` on focus moves.

**FP25-C envelope superseded:** the move-then-rollback approach is
replaced by FP21-D's write-then-move ordering. `RecycleError.recycled_orphan`
remains as a vestigial field (never set under the new ordering) for
backward compat with FP26-P callers.

**Test totals:** 523 backend / 273 frontend pass; coverage 86.79%;
ruff + ruff format + mypy + bandit + eslint + tsc all clean.

### FP26 — FP25 closing-review fold-in + UX e2e walkthroughs (closed 2026-05-11)

21 sub-bullets sourced from FP25's closing `/audit` + 4-lane
`/indie-review` (5 Tier 1 + 12 Tier 2 + 15+ Tier 3) plus the user's
mid-session Playwright UX walkthrough scope-add. Shipped across
five commits:

- **Tier 3 (Playwright UX walkthroughs)** `dddae88` — new
  `frontend/e2e/fp25-ux-walkthrough.spec.ts` (4 cases): cold-start
  outage → one Sonner toast (FP25-G); LibraryErrorPanel sticky-
  panel + Retry-disabled flow (FP25-H, captured FP26-V buggy
  behavior); HelpPage scoped DOMPurify end-to-end (FP25-I/J — no
  `<script>` survives, `target="_blank"` carries
  `rel="noopener noreferrer"`, `data:` URL stripped); settings
  restore failure persistent alert (FP25-K(12) UX shape).
- **FP26-V (NEW Tier 1)** `8b70f34` — `LibraryPage` keeps the
  error panel mounted while a refetch from an errored state is
  in flight. React Query v5 resets `isError` to false during
  refetch; the old `{games.isError ? <Panel/> : <Grid/>}` ternary
  unmounted the panel, so FP25-H's `disabled={isFetching}` /
  "Retrying…" affordance never reached the user's screen. Fix:
  `games.isError || (games.isFetching && errorUpdatedAt >
  dataUpdatedAt)`. The Playwright walkthrough caught it; unit
  tests didn't because they rendered the panel directly with
  `isFetching=true`, bypassing the host's conditional.
- **Tier 1 + L + H batch** `a54dd10` — FP26-A strengthened
  world_lock test sufficiency via the `asserted_set_world`
  monkey-patch (per-route + cross-route concurrent test both
  assert `tracker.held` at every `set_world` call); FP26-B
  wrapped `mkdir(parent)` in `ActivityLogError` envelope; FP26-C
  fixed FP25-F's vacuous assertions (now `rglob` over the whole
  recycle tree); FP26-D extended FP25-E skipif to "skip unless
  linux" (macOS fork hazard); FP26-H added the 0-byte-write
  defensive-branch test; FP26-L dropped the dead FP25-K(12)
  `restore.isPending ? null : ...` conditional (React Query 5
  already clears `error` on `mutate()`).
- **Tier 2 batch** `1653737` — FP26-E P04 spec `_deactivate`
  enumeration; FP26-F best-effort parent-dir fsync on first
  activity append (`_atomic._fsync_parent_dir` renamed to public
  `fsync_parent_dir` per Rule of Three); FP26-G `copy/spec.md`
  drift cleanup (FP25-C "open" stale text rewritten, broken
  `§ Errors envelope` reference fixed, `ActivityLogError` added
  to enum); FP26-I `queryClient.test.tsx` calls
  `_resetApiErrorToastDedupForTests()` in beforeEach; FP26-J/K
  apiErrorToast docblock acknowledges deliberate unboundedness +
  names the rejected `toast({id})` alternative; FP26-M
  allowlist-004 line citation refreshed to grep-instruction +
  `helpSanitizer.sanitize(...)` wording; FP26-N `_TrackingLock`
  duck-type rationale; FP26-P `RecycleError.recycled_orphan`
  attribute for double-failure machine-readable signal.

Final five-gate close: 504 backend tests (1 skipped) / 273
frontend tests / 9 e2e specs / coverage 87% / ruff + ruff format +
mypy + bandit (0 findings all severities) / ESLint + tsc clean.
`frontend/dist/` rebuilt.

Workflow lesson saved: e2e walkthroughs catch a class of bug unit
tests miss — host-component conditionals that unmount the child
during the very state the child is meant to handle. Filed via the
user's mid-session "use Playwright to walk through features"
direction; FP26-V is the canonical example. Pattern: any feature
whose user contract is "X becomes visible while Y is pending"
needs an e2e walkthrough exercising the HOST's render condition,
not just the child component in isolation.

### FP20 — `/indie-review` Tier 1 security + data-loss fold-in (closed 2026-05-11)

The 2026-05-04 multi-agent indie-review surfaced 12 sub-bullets across
10 lanes — parser XXE/zip-bomb (A), copy non-atomic writes (B), API
mutation lock not installed (C), sandbox allowlist admits stale paths
(D), help-dir env-override symlink (E), download URL scheme allowlist
(F), useApiQuery silent-failure path (G), GameCard aria-label clobber
(H), LibraryPage error-panel gap (I), SnapshotsTab restore-error
surface (J), FsBrowser Esc-closes-everything (K), HelpPage DOMPurify
config hardening (L). All 12 shipped across 14 commits on 2026-05-11:

- **A** `c3ee50c` — parser/dat.py + parser/listxml.py + tests; explicit
  `resolve_entities=False / no_network=True / huge_tree=False /
  load_dtd=False` hardened-iterparse kwargs at all four call sites,
  plus a 256 MiB cap on `zf.getinfo(member).file_size` before
  extraction.
- **B** `6a12a93` — copy/activity.py (`os.open + os.write` bypasses the
  BufferedWriter split risk); copy/recyclebin.py + copy/playlist.py
  routed through `_atomic.atomic_write_text` (Rule-of-Three honoured).
- **C** `61fbc68` — `app.state.world_lock = asyncio.Lock()` installed
  in `api/app.py` lifespan; `patch_config`, `restore_config_snapshot`,
  `import_config`, `fs_grant_root`, `fs_revoke_root` converted to
  `async` and wrapped in `async with`.
- **D** `52a112c` — `compose_allowlist` filters `granted_roots` to
  entries that satisfy both `exists()` and `is_dir()`; dropped entries
  emit INFO log naming the resolved path.
- **E** `73f2df8` — `_help_dir()` resolves both branches (override +
  package-relative) so callers operate on the canonical path.
- **F** `c49225b` — `download()` rejects schemes outside `{http, https}`
  via `_check_scheme` applied to the primary URL and every mirror
  before any HTTP attempt. Typed `InvalidUrlError(DownloadError)`.
- **G** `76a3010` — `createAppQueryClient()` factory wires
  `queryCache: new QueryCache({ onError: toastApiError })` so every
  failing query funnels through the global toast helper.
- **H** `7cc8796` — GameCard drops the `aria-label` clobber on its
  wrapper; an `aria-labelledby` to a per-card `id`-bearing `<h3>` plus
  decorative `alt=""` on the box-art image.
- **I** `4b4faca` — new `LibraryErrorPanel` (alert role, title + hint +
  Retry button); LibraryPage renders the panel in place of the grid
  when `games.isError`, with `games.refetch()` on Retry.
- **J** `3bb01ef` — `SnapshotsTab.restoreError` prop renders a
  persistent alert above the snapshot list (mirrors `BackupTab.error`);
  `App.tsx` SettingsRoute derives the message from `restore.error`
  (ApiError.detail preferred).
- **K** `e149c1c` — `FsBrowser` renders only one dialog layer at a
  time — when sandbox-blocked, the browse Dialog is unmounted and the
  AlertDialog is the sole open layer.
- **L** `c9e61b5` + `d819181` — HelpPage DOMPurify hardened:
  `ALLOWED_URI_REGEXP = /^(?:https?|mailto):/i`, `FORBID_TAGS =
  ['style', 'form']`, `FORBID_ATTR = ['style']`, a `forceKeepAttr` hook
  preserving `target="_blank"`, an `afterSanitizeAttributes` hook
  setting `rel="noopener noreferrer"`, and a `data:` src strip for
  IMG/SOURCE/AUDIO/VIDEO/TRACK closing the `DATA_URI_TAGS` bypass.

Closing `/audit` (semgrep + gitleaks on the FP20 surface plus CI-clean
ruff/mypy/bandit/eslint/tsc) returned a single allowlist-004 re-
confirmation; the 5-lane `/indie-review` surfaced 1 Tier 1 spec-
violation (`world_lock` covers only 5 of 7 spec-required routes), 7
Tier 2 hardening gaps, and 10 Tier 3 polish items. All 11 batched into
`FP25` for the closing-review fold-in. FP20 stays open until FP25
closes; `FP20-complete` tag will fire then.

### FP25 — FP20 closing-review fold-in (closed 2026-05-11)

11 sub-bullets sourced from FP20's closing `/audit` + 5-lane
`/indie-review` (1 Tier 1 / 7 Tier 2 / 10 Tier 3 polish items grouped
into K). All 11 shipped per-sub-bullet TDD across 8 commits:

- **A** `d617cd6` — `world_lock` on the remaining 7 mutation routes
  (`api/routes/curate.py` overrides POST/DELETE + sessions POST/DELETE,
  activate, _deactivate; `api/routes/games.py:put_notes`). Converts
  each to `async def`, drops `Depends(get_world)`, re-reads
  `request.app.state.world` inside `async with
  request.app.state.world_lock`. New acceptance test fires two
  `asyncio.gather`-ed cross-route mutations and asserts both edits
  land. Closes the data-loss class on concurrent PATCH +
  sessions/overrides/notes races.
- **B** `87b32de` — `copy/activity.py` durability + typed
  `ActivityLogError`. `append_activity` now loops on short writes
  (POSIX permits short returns on regular files), issues a best-
  effort `os.fsync` (suppressed on tmpfs / some networked mounts),
  and wraps `os.open` / `os.write` failures in the new
  `ActivityLogError(CopyError)` envelope. `copy/spec.md` § Activity
  log updated to name the new semantic explicitly.
- **C** + **F** `f569953` — `copy/recyclebin.py` manifest atomicity
  envelope. The manifest write now runs inside try/except: on
  `OSError`, `shutil.move` rolls the recycled file back to its
  original path (all-or-nothing) and the empty target_dir is cleaned
  up if this call created it. FP25-F tests monkeypatch `os.replace`
  inside `atomic_write_text` to fail and assert no `manifest.json` /
  no `.tmp` files remain.
- **D** `d210aa6` — `_atomic.atomic_write_*` perm-mode pinned at
  0o644 via `os.fchmod(tmp.fileno(), 0o644)`. Parity with
  `copy/activity.py:append_activity`'s `os.open(..., 0o644)`; the
  pre-FP25-D 0o600 default left half the data dir owner-only.
- **E** `efd6b6b` — concurrent-append property test for the activity
  log. Fork two child processes each appending 20 × 6 KiB events,
  assert every resulting JSONL line parses cleanly and the per-child
  counts match. Exercises POSIX O_APPEND atomicity end-to-end.
- **G** `32d66cb` — `toastApiError` 1500 ms dedup window keyed on
  `(code, detail)`. Cold-start outages (9+ near-simultaneous query
  failures) now collapse to one toast; distinct errors still surface
  separately; >1.5 s later the same key re-toasts.
- **H** `84c55cb` — `LibraryErrorPanel` Retry disabled while
  `isFetching`. Optional `isFetching?: boolean` prop swaps the label
  to "Retrying…" and `disabled`s the button so a frustrated user
  can't queue redundant refetches.
- **I** + **J** `b21fe08` — HelpPage scoped DOMPurify instance via
  `DOMPurify(window)` so the `target="_blank"` `forceKeepAttr`, the
  rel-injection, and the data:-URL strip don't leak to the global
  singleton. **J** strengthens the FP20-L data-URL test to a
  deterministic outcome (either `<img>` absent OR `<img>` with no
  src) instead of the vacuous pre-FP25-J assertion.
- **K** `19cc9b2` — 12-item doc + comment cleanup batch: parser nosec
  rewrite (1), zip-bomb cap comment (2), Billion Laughs timing relax
  to 5 s (3), `_atomic.py` noqa SIM115 reason (4), `help.py` drop
  redundant `.resolve()` (5), `fs.py` dedupe FP20-D INFO log via
  module-level seen-stale set (6), GameCard `aria-labelledby` id
  uniqueness invariant doc (7), queryClient test
  `toHaveBeenCalledTimes(1)` (8), SnapshotsTab `restoreError` JSDoc
  lifetime contract (9), HelpPage tagName casing comment (10), drop
  dead `el.getAttribute?.` optional chain (11), App.tsx clear
  `snapshotRestoreError` while `restore.isPending` (12).

Tests at FP25 step 4 close: 502 backend (1 skipped) / 273 frontend /
coverage 87.x% / ruff + ruff format + mypy + bandit / eslint + tsc
clean. `frontend/dist/` rebuilt.

Closing `/audit` returned clean across ruff + ruff format + mypy +
bandit + semgrep (0 results on 65 Python files) + gitleaks (`[]`)
+ ESLint (errors=0 warnings=0) + tsc. **The 4-lane `/indie-review`
surfaced 5 Tier 1, 12 Tier 2, and 15+ Tier 3 findings**, focused
on test sufficiency (the FP25-A acceptance test passes even
without the lock; FP25-F asserts inside an always-false branch),
one typed-error envelope hole (`mkdir(parent)` in `activity.py`
escapes `ActivityLogError`), and a macOS-fork hazard in FP25-E.
User also added a fifth scope item: Playwright e2e walkthroughs
that validate the FP25 user-facing changes end-to-end. All 5
Tier 1 + 12 Tier 2 + Playwright walkthroughs batched into `FP26`;
FP25 stays open until FP26 closes.

### FP22 — Launch button gates on RetroArch config (closed 2026-05-08)

User reported a 422 on POST `/api/games/{name}/launch` after
clicking Launch with `paths.retroarch` / `paths.retroarch_core`
unset in `config.yaml`. The Launch button shipped unconditionally
(FP19) and the Setup banner didn't track RetroArch state, so the
gap only surfaced via a toast after click. FP22 closes that gap.

- **A** `/api/setup/check` now returns `retroarch_configured: bool`
  — the AND of the two paths being non-null. Pydantic + TS + Zod
  mirrors in lockstep; three new pytest cases cover default-false,
  one-of-two-set, and both-set.
- **B** AlternativesDrawer accepts a `retroarchConfigured?:
  boolean` prop. The Launch button disables when it's anything
  other than strictly `true` (so `undefined` while the
  `useSetupCheck` query loads also gates), and an inline hint
  links to `/settings?tab=paths` when the prop is `false`. Three
  new vitest cases.
- **C** Settings page Setup banner gains a "RetroArch: configured"
  / "RetroArch: not configured" line, mirroring the existing INI
  status line. Two new vitest cases.
- **D** Friendly toast copy for the 422 envelope was deferred to
  FP21 § J — the typed `RetroArchNotConfiguredError` from that
  fix-pass carries the `code` field; the byCode mapping lands
  there beside the code it describes (strings.ts forbids dead
  byCode entries).

Tests: 458 backend (1 skipped) / 246 frontend / coverage 87.00% /
ruff + mypy + bandit + types-sync clean / eslint + tsc clean.
`frontend/dist/` rebuilt.

### FP24 — P15 closing-review fold-in (closed 2026-05-08)

P15's closing `/audit` returned 4 actionable lint findings; the
8-lane `/indie-review` returned 30+ cross-cutting and per-lane
findings batched into three tiers. All Tier 1 (A–G + Q + S),
Tier 2 (H–Z), and Tier 3 (AA–LL) closed across 13 commits.

Tier 1 — user-visible blockers:

- **A** `JobEvent.payload` keys aligned with the typed contract
  (`files_total` / `bytes_total`); copy progress bar now updates.
- **B** CartBar's GB figure dropped — it showed the filtered
  library's bytes, not the cart's; per-cart byte sum is a
  v1-deferred concept (no per-row byte data on `GameCard`).
- **C** AppShell Cart NavLink (which shadowed Library on `/`)
  becomes a button; cart-expanded state lifts to
  `ShellWithPalette` so the button can open the panel from
  any route.
- **D** `OnboardingBanner` derives visibility from props instead
  of `setState` in `useEffect` (eslint hard error fixed).
- **E + Q** `GameCard`'s outer `<button>` becomes
  `role="button"` div + onKeyDown (Enter/Space); the
  focus-visible ring lives on the wrapper so it actually paints.
- **F** `ValidateRequest.short_names` bounded to 10,000 items at
  64 chars each; user-controlled lists can no longer pressure
  server memory.
- **G + S** `useCart` exposes `isStorageBroken` and `addAll`
  returns `{added, truncated}` so `LibraryPage` fires
  `storageUnavailableToast` and `maxCartReachedToast`.

Tier 2 — hardening:

- **H/I/J/K/L** SSE lifecycle in `useCopySession`: orphan
  stream closure on second start, transient-error reconnect
  preservation, unmount race guard, malformed-payload try/catch,
  conflict-resolve param logged not silently dropped.
- **M/N/T/U/V** `LibraryPage`: `handleBulkAdd` iterates all
  filter pages; double-click guard on Copy/Dry-run; cart auto-
  clear effect's eslint-disable now documents the stable-ref
  invariant; `fetchTileCount` routed through `apiRequest`;
  `cards` wrapped in `useMemo` so downstream identity stays
  stable.
- **O/P/R/W/X/Y/Z + AA partial** Cart UX + accessibility:
  AlertDialog confirm on Clear-all; tile button explicit
  `aria-label`; `useCart.readInitial` validates `chosenVariant`
  type; CartBar disclosure-pattern aria; "Add all 0" suppressed;
  banner roles fixed (ListxmlBanner → status, OnboardingBanner
  → none); tile counts no longer flash 0 during load;
  hardcoded strings for `+Add` and `Cart contents` extracted.

Tier 3 — debt:

- **BB** `listxml_available` zombie field deleted from
  `SetupCheck` schema + types + tests.
- **CC** `_probe_path`'s `kind` parameter now drives `is_dir`
  / `is_file` checks instead of being silently discarded.
- **DD** `Badge.BIOS_MISSING` now appended in `_badges()` when
  the machine's parent appears in `world.bios_chain`.
- **EE** `schemas.py` over the 500-line cap split into
  `schemas_setup.py` + `schemas_fs.py` with re-exports for
  back-compat.
- **FF** `dryRunConfirmDeferred` dead string deleted.
- **GG** `FeaturedTile` / `FeaturedTileQuery` types hoisted to
  `strings.ts` (single source of truth).
- **HH** Tile-count `page_size=1` rationale documented.
- **II** Cmd+K kbd label adapts to platform (⌘K on macOS,
  Ctrl+K elsewhere).
- **JJ** eslint `argsIgnorePattern: '^_'` accepts the project's
  underscore-prefix convention.
- **LL** `handleTileSelect` toggle-off preserves non-tile-driven
  filter state (search box, letter, only-X toggles).
- **KK partial** Cart-flow e2e adjusted to FP24-Y / FP24-B; five
  additional e2e cases deferred (Vitest unit coverage already
  pins those contracts; finding accepted Vitest-only).

Plus two ride-alongs: `HelpRoute` setState-in-effect (eslint
blocker that fell out of the FP24 lint sweep, not in the
original enumeration) — fixed by deriving `selectedSlug` from
the URL and routing onSelect through `setSearchParams`.

455 backend tests / 240 frontend tests / ruff + mypy + bandit
clean / eslint + tsc clean / coverage 86.93%.

### P15 — Cart and curated library (closed 2026-05-08)

User feedback 2026-05-07: opening the app showed 21,049 cards
with no clear path to pick a few games and copy them. P15 turns
the dead bottom-bar into a cart-first selection model with
per-game `+Add`, featured INI-derived tiles, sticky cart-bar
with expand-up panel, and a live SSE-driven Copy flow. Plan at
`docs/superpowers/plans/2026-05-07-cart-and-curated-library-plan.md`;
spec at `docs/superpowers/specs/2026-05-07-cart-and-curated-library-design.md`.

**Backend (B1–B5):**

- **B1** `tests/filter/test_runner.py::test_cloneof_map_empty_self_parents`
  + `tests/api/test_routes_games.py::test_cloneof_map_collapses_winners`
  pin the FP23 fix at the test level: non-empty `cloneof_map` ⇒
  winners strictly less than machines.
- **B2** `/api/setup/check` extended with `cloneof_map_size: int`
  on the existing `reference_files.listxml` block. (The
  `listxml_available` flag added during planning was deleted in
  FP24-BB once the empty-parse banner branch derived its state
  from `exists` + `cloneof_map_size` directly.)
- **B3** `GamesPage.total_bytes: int` populated server-side as
  the sum over the same `filtered` slice that produces `total`;
  bottom-bar GB figure now reflects post-collapse winners.
- **B4** `POST /api/games/validate` accepts
  `{ short_names: string[] }` (bounded 10,000 / 64-char per item
  via FP24-F) and returns `{ existing, missing }` against
  `world.machines` — set lookup, no pagination.
- **B5** `UiConfig.cart_clear_on_copy: Literal['always','on_success','never']`
  defaults to `'on_success'`.

**Frontend (F1–F14):**

- **F1** TypeScript mirrors for the five backend fields above.
- **F2** `useCart` — localStorage-backed (`mame-curator:cart:v1`),
  `add` / `remove` / `addAll` (returns `{added, truncated}` after
  FP24-S) / `setVariant` / `clear`, `isStorageBroken` probe (FP24-G)
  for private-browsing modes, MAX_CART_SIZE = 10,000 ceiling.
- **F3** `useValidateCart` mutation hook for pre-Copy reconcile.
- **F4** `strings.ts` additions: `FEATURED_TILES` catalogue
  (Capcom Classics / Beat 'em Ups / Run & Gun / Best of 1992 /
  SHMUPS Vertical), onboarding copy, cart strings, listxml banner
  copy.
- **F5** `OnboardingBanner` — dismissible, `localStorage`-keyed
  (`mame-curator:onboarding-dismissed:v1`); auto-dismisses on
  first add. Visibility derived from props (FP24-D).
- **F6** `FeaturedTilesRow` — horizontal tile buttons; each tile
  fetches its count via `/api/games?page_size=1` (page_size=0
  not supported by backend); 5-min react-query staleness.
- **F7** `CartBar` — replaces `ActionBar.tsx`; collapsed shows
  `🛒 N games · [Dry-run] [Copy] [⌃]`; `[Add all M]` appears when
  a featured tile is active. (Per-cart GB figure dropped in
  FP24-B — no per-row byte data on `GameCard`.)
- **F8** `CartPanel` — expand-up panel listing cart items with
  per-row `✕` remove + `Clear all` (AlertDialog confirm via
  FP24-O).
- **F9** `GameCard` `+Add` affordance + cart-aware "✓ Added"
  state. Outer `<button>` became `role="button"` div + onKeyDown
  in FP24-E/Q to avoid nested-button DOM.
- **F10** `useCopySession` SSE hook — job_started → progress →
  job_completed / job_failed lifecycle, transient-error reconnect
  preservation (FP24-I), unmount race guard (FP24-J),
  malformed-payload try/catch (FP24-K). Used by `LibraryPage`'s
  `onCopy` route.
- **F11** `LibraryPage` end-to-end cart wiring: `+Add` calls
  `cart.add`; featured tile click sets filter + `bulkAddTotal`;
  bulk-add paginates the full filter result (FP24-M); pre-Copy
  validate drops orphans with a single toast; cart auto-clear on
  `succeeded` (per `cart_clear_on_copy` config).
- **F11.1** `ListxmlBanner` empty-parse branch — banner now
  renders when listxml exists but `cloneof_map_size === 0`,
  closing the gap FP23 left.
- **F12** Top-nav reshape — left rail → horizontal nav with
  `Library | 🛒 N | Settings | Help | ⋯ More` (Sessions /
  Activity / Stats under "More"). URL paths preserved so deep
  links still work. Cart NavLink became a button in FP24-C
  (was shadowing Library on `/`).
- **F13** `SettingsPage` `cart_clear_on_copy` Select alongside
  `default_sort` in the Display Card.
- **F14** Playwright `cart-flow.spec.ts`: banner dismiss → tile
  filter → bulk-add → expand-panel → Copy. (Five additional E2E
  cases the FP24-KK finding named were deferred — Vitest unit
  coverage already pins those contracts.)

Closing `/audit` (4 actionable lint findings) + 8-lane
`/indie-review` (30+ findings across Tier 1/2/3) folded into
FP24, closed in 13 commits 2026-05-08. Plus two ride-alongs
(`HelpRoute` setState-in-effect, eslint argsIgnorePattern).

455 backend tests / 240 frontend tests / ruff + mypy + bandit
clean / eslint + tsc clean / coverage 86.93%.

### FP23 — Parent/clone collapse listxml fix + DryRun wiring (closed 2026-05-07)

Discovered during the P15 cart-and-curated-library brainstorm:
the running v1.2.0 app showed 21,049 cards in the Library bottom-
bar with the 1942 family appearing 7 times across regions /
revisions / bootlegs / hacks. Round 1 of the P15 spec cold-eyes
review caught the mis-diagnosis ("the picker isn't wired" —
wrong) and pointed at the real cause: `cloneof_map={}` at world-
load time, so `filter/runner.run_filter` groups by self and every
machine becomes its own winner.

Per [ADR-0002](docs/decisions/0002-cloneof-from-listxml.md),
parent/clone relationships are stripped from Pleasuredome DATs
and must come from MAME `-listxml`. The user's `config.yaml` had
`paths.listxml: null` since v1.0.0 — silent failure (FP18's
setup banner counts INIs but not listxml).

- **MAME 0.287 listxml installed** (302 MB, 27,604 cloneof
  entries; 3 versions newer than the user's 0.284 DAT — cloneof
  for old arcade titles is stable across this drift). Library
  bottom-bar drops 21,049 → 10,591 after restart;
  `/api/games/1942/alternatives` returns the parent + 7 clones,
  matching the original screenshot exactly.
- **`ListxmlBanner.tsx`** (3 unit tests) renders above the
  Library grid when
  `setupCheck.reference_files.listxml.exists === false` so future
  users see the silent-failure state explicitly. Closes the gap
  that let the bug ship for 23 days.
- **`useDryRun` hook** (`POST /api/copy/dry-run`) wired to the
  previously-no-op `onDryRun` handler in `LibraryPage`; opens
  the existing `DryRunModal` with the report on success. P15
  swaps the `selected_names` source from `cards` → `cart.items`
  — modal contract unchanged so the hook keeps working through
  the cart redesign.
- **`onCopy` stays a no-op stub** — full Copy lifecycle (SSE +
  conflict resolution) is genuinely P15-scale (~500 lines + tests)
  and fits naturally with the cart-driven input swap.

446 backend tests / 188 frontend tests / ruff + mypy + bandit
clean / coverage 86.66%.

### Planned — `DS03` Dependency freshness sweep

User request 2026-05-08: ensure every external library in
`pyproject.toml` and `frontend/package.json` is on its latest
stable release, per global rule § 5 ("Use the latest external-
library version, with current idioms"). DS03 is a dedicated
single-coordinated-bump sweep covering backend deps, frontend
deps, and pinned GitHub Actions versions; runs the full CI
matrix once for the whole bump rather than piecemeal upgrades.
Idiom-modernisation rewrites are out of scope (separate fix-
pass if a major version's new idioms surface drive-by). See
`ROADMAP.md` `DS03`.

### Planned — `FP22` Launch button gates on RetroArch config

User reported 2026-05-04 that clicking Launch on a game with
RetroArch unconfigured returns 422 with no in-app guidance to
fix. Roadmap'd as `FP22`: gate the Launch button on a setup-check
flag, surface RetroArch state in the Setup banner, and route the
422 through `strings.errors.byCode` for friendlier copy. See
`ROADMAP.md` `FP22`.

### Planned — `/indie-review` 2026-05-04 fold-in

10-lane multi-agent independent code review surfaced findings
batched into three tiered phases:

- **FP20** — Tier 1 (security + data-loss): parser XXE / zip-bomb
  hardening, copy activity-log + recyclebin manifest atomicity,
  missing `app.state.world_lock`, `compose_allowlist`
  non-existent-path admission, `help.py` env-override resolve,
  `download()` URL scheme allowlist, global `useApiQuery` toast,
  `GameCard` `aria-label` clobber, `LibraryPage` query-error
  surface, `SnapshotsTab` restore inline error, `FsBrowser`
  `Esc`-closes-everything, `HelpPage` DOMPurify config.
- **FP21** — Tier 2 (hardening): `explain_pick` decisive
  semantics, `Session` typed-error drift, recyclebin manifest
  per-file shape, preflight free-space includes BIOS, TOCTOU
  source-vanish → SKIPPED, `media.py` `FileResponse` event-loop
  unblock, `launch_game` typed `ApiException`, SSE
  register-before-replay race, late-progress drop, snapshot LRU,
  `AppConfigPatch` Pydantic, cross-file import staging, download
  streaming + cap, `useLaunchGame`/`useOverride` baked-in
  `onError`, `useKeyboard` ref-based handler, `LibraryGrid`
  WAI-ARIA grid pattern.
- **DS02** — Tier 3 (structural debt): file-cap splits across 5
  files, CI gate for caps, i18n leaks, a11y polish (skip-to-main,
  aria-busy on Launch, slider thumb labels), `parse_listxml_
  bios_chain` spec orphan, `_atomic` mkdir contract, Settings
  tab URL state, `apiRequestVoid` asymmetry, spec doc sync.

See `ROADMAP.md` `FP20`, `FP21`, `DS02` blocks for finding-level
detail with `file:line` cites.

## [1.2.0] — 2026-05-04

### FP19 — Launch games from the site (RetroArch integration)

User asked: "offer the option to launch the games from the site,
check /mnt/Games/Scripts/Linux/RetroDB/ (RetroDB project; was
`/mnt/Storage/...` at the time of the original request) for
references on doing that."

Studied RetroDB's launcher pattern (`subprocess.Popen(shell=False)`,
argv pre-built, token-based registry, stderr drained). Adapted to a
slim per-request spawn for v1 — no token registry, no kill API
(RetroArch is a foreground app the user closes themselves).

- **New `paths.retroarch` + `paths.retroarch_core`** fields in
  `PathsConfig`. Both required for launch; absent configuration
  surfaces a 422 with copy that names the fix.
- **POST `/api/games/{name}/launch`** spawns RetroArch via
  `subprocess.Popen` with `shell=False`. ROM-resolution order:
  `dest_roms/<name>.zip` → `source_roms/<name>.zip` (404 if neither
  exists).
- **Frontend "Launch in RetroArch" button** in AlternativesDrawer.
  `useLaunchGame` mutation; success toast + error toast via
  `toastApiError`.

To configure on your machine:

```yaml
paths:
  retroarch: /mnt/Emulators/Multi-System/RetroArch/RetroArch-Linux-x86_64.AppImage
  retroarch_core: /path/to/mame_libretro.so
```

446 backend tests / 86.66% coverage. 182 frontend tests / build
clean.

## [1.1.1] — 2026-05-04

### FP18 — refresh-inis auto-patches config.yaml + banner counts 5 INIs

User reported INIs downloaded to disk but the running server wasn't
using them — config.yaml's `paths.{catver,languages,bestgames,series,
mature}` were unset, so the lifespan parsed them as `None`. The
Settings → Setup banner reinforced the confusion by hardcoding "4 INIs
required" (FP16 § C) when v1.0.1 had already added mature.ini to the
default download set.

- **`refresh-inis` now patches `config.yaml`.** New `--config` flag
  (default `./config.yaml`); after a successful download, fields under
  `paths.*` that are currently unset are pointed at the downloaded
  files. Existing user-supplied paths are never clobbered. Atomic
  write via `_atomic.atomic_write_text`. Output ends with a "restart
  the server" hint. Pass `--no-config` to skip the patch.
- **Setup banner counts 5 INIs** (was 4). `mature.ini` joined the
  default download set in v1.0.1.

End-to-end smoke test: clean `/tmp/config-test.yaml`, run
`uv run mame-curator refresh-inis --dest /tmp/mame-ini-test --config
/tmp/config-test.yaml` → 5/5 downloaded + config patched + restart
hint shown.

446 backend tests / 88.16% coverage. 182 frontend tests / build
clean.

## [1.1.0] — 2026-05-04

### FP17 — Library filter expansion (closed 2026-05-04)

User-requested filter additions on the /library FiltersSidebar:

- **Letter filter** (A-Z + `#` for digit-prefixed games). Click a
  letter button to filter; click again to clear. Drawn from
  `/api/library/facets`'s `letters` (only buckets with games are
  shown).
- **Genre Select** dropdown — exact-match against
  `world.ctx.category`. Sentinel "(any)" first option clears.
- **Publisher Select** + **Developer Select** — same pattern.
- New endpoint `GET /api/library/facets` returns deduped sorted
  `{genres, publishers, developers, letters}` from the winners
  set. New `LibraryFacets` schema. New `useFacets` hook
  (60-second staleTime — facets only change on world rebuild).
- Backend `/api/games` route accepts new `letter` / `developer`
  query params alongside the existing `genre` / `publisher`.

446 backend tests / 88.16% coverage. 182 frontend tests / build
clean.

## [1.0.1] — 2026-05-04

### Fixed — INI default URLs (closed 2026-05-04)

The v1.0.0 default URLs for `mame-curator refresh-inis` returned
404 against AntoPISA's MAME_SupportFiles GitHub mirror. Root
cause: WebFetch indexing during P07 § B mistook the per-file
subdirectories (`catver.ini/`, `languages.ini/`, ...) for files.
Corrected to the `<file>/<file>` pattern; verified locally with
all 5 INIs downloaded successfully (~3 MB total). `mature.ini`
was discovered to be available at `catver.ini/mature.ini` and
added to defaults.

Test added: `test_default_sources_covers_five_mandatory_inis`
asserts the new 5-INI set + URL shape so a future regression
that drops the subdir pattern fails the suite.

### FP16 — Library shipping blockers + INI visibility (closed 2026-05-04)

User-reported bugs from real-data UAT during the v1.0.0 cut. All
four shipped before the v1.0.0 tag was re-cut at the same SHA.

- **Search and year-range filtering silently no-op'd in production.**
  Frontend `useGames` sent `search` / `year_from` / `year_to`, backend
  expects `q` / `year_min` / `year_max`. Renamed frontend params to
  match.
- **Clicking a game did nothing.** `LibraryPage.onOpen` was an FP11 §
  B6 placeholder comment that never got wired. Added
  `useAlternatives` + `useOverride` hooks; drawer now mounts on
  card click; override mutation invalidates queries + toast.
- **No UI signal of INI presence.** `useSetupCheck` hook added;
  `SettingsRoute` now passes `setupInfo` to SettingsPage; setup
  banner renders a per-INI status line listing missing files +
  the exact `mame-curator refresh-inis` command to fix them.
- **Stale `index.html` cached by browser hit 404s on deleted bundle
  hashes.** Added cache-control headers in `_SPAStaticFiles`:
  `assets/*` are immutable (Vite hash-keyed); `index.html` +
  fallback paths revalidate every load.
- **Sessions explainer text tightened** to clarify the v1 feature is
  filter-bookmark, not per-game review tracking.

Roadmap addition: **P14 candidate** — per-game review state
(reviewed / skipped / pending) for the user mental model that v1
Sessions doesn't fit.

446 backend tests / 89.07% coverage. 182 frontend tests / build clean.

## [1.0.0] — 2026-05-04

First public release. Everything below shipped under `[Unreleased]`
between 2026-04-27 and 2026-05-04 is rolled into this tag. The
phase-by-phase summary that follows captures the v1 scope.

### Phase summary

- **P00 — Scaffold + tooling baseline (2026-04-27).** Project skeleton,
  five-gate CI (ruff / format / mypy / bandit / pytest), Conventional
  Commits convention, MIT license.
- **P01 — `parser/` module (2026-04-27).** `parse_dat()` streams a
  ~48 MB / 43k-machine DAT in ~5 s via `lxml.iterparse`; the four
  mandatory progettoSnaps INIs (`catver` / `languages` / `bestgames` /
  `mature`); the official MAME `-listxml` for CHD detection +
  parent/clone joining (Pleasuredome strips `cloneof` / `romof`).
- **P02 — `filter/` module (2026-04-27).** Four-phase rule chain (drop
  → pick → override → session-slice). `Sessions` continuation-mode
  inclusion focus. 158 tests, 96%+ coverage.
- **P03 — `copy/` module (2026-04-30).** Atomic ROM copy + BIOS chain
  resolution + RetroArch `.lpl` writer + recycle-bin for replaced
  files + playlist conflict handling. 300 tests; 5 fix-passes folded
  in (FP01 / FP02 / FP04 / FP07 / FP08) + the pre-P04 debt sweep
  DS01.
- **P04 — `api/` module (2026-05-01).** FastAPI surface with 40 routes,
  SSE for live copy progress, sandbox + R29-R34 filesystem-browser
  endpoints. FP09 indie-review fold-in.
- **P05 — `media/` module (2026-05-02).** libretro-thumbnails URL
  builder + sha256-keyed lazy-fetch disk cache. FP10 fold-in.
- **P06 — Frontend MVP (2026-05-02).** Vite + React 19 + Tailwind v4 +
  shadcn/ui SPA: library grid (4 layouts), alternatives drawer,
  themes (Light / Dark / Double Dragon / Pac-Man / SF2 / Neo-Geo),
  Sessions / Activity / Stats / Settings / Help pages, Cmd-K palette,
  ErrorBoundary tree. FP11 closing-review fold-in (40 findings across
  10 clusters).
- **P07 — Reference-data refresh + in-app help (2026-05-04, slim).**
  `downloads.py` primitive (sha256-verified atomic download with
  retry + mirror fallback); `mame-curator refresh-inis` CLI;
  `cards_per_row_hint` UI Select; HelpPage DOMPurify; Cmd-K wired to
  bundled help topics. Self-update + INI diff-preview UI deferred to
  P12 (post-v1) per Karpathy 9 push-back.
- **P08 — Clone-and-run bootstrap (2026-05-04, slim).** `run.sh` /
  `run.bat` provision Python + uv + deps + interactive setup +
  serve + browser open in one idempotent script. In-browser wizard
  deferred post-v1.
- **P09 — Polish + v1.0.0 cut (2026-05-04).** Updated README with
  `./run.sh` quickstart; CHANGELOG bootstrapped with this entry; tag
  `v1.0.0`.

### Settings + UX fix-passes folded into v1.0.0

- **FP12 — Settings page list editors + path picker (2026-05-04).**
  `<ChipListEditor>`, `<DragReorderList>`, `<YearRangeEditor>`,
  vendored shadcn `<Select>`, full `<FsBrowser>` modal with sandbox
  grant flow, in-place editable Paths tab, Snapshots + Backup tabs.
  10 clusters A-J in 13 commits.
- **FP13 — FP12 closing-review fold-in (2026-05-04).** 22 findings
  from `/audit` (clean) + 3-lane `/indie-review` closed in 6 commits;
  SettingsPage extracted from 551 → 305 lines via 6 sibling
  components; new `lib/apiErrorToast.ts` translates ApiError → user
  copy.
- **FP14 — GameCard layout overflow (2026-05-04).** `aspect-[3/4]`
  pushed total card height past the virtualizer's row height,
  clipping the description heading. Replaced with `flex-1 min-h-0` +
  `object-contain`; image-fail placeholder shows the description so
  games without art are still identifiable; added shortname row for
  technical disambiguation (1942 Capcom vs Williams).
- **FP15 — Sessions UX (2026-05-04).** Wired the load-bearing no-op
  `LibraryPage.onSaveSession` (an FP11 placeholder that was never
  filled); added active-session pill in /library header; added
  one-line explainer above the Save button.

### Versioning policy

[Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html). v1
is the first stable contract. Breaking changes after v1 require a
major bump.

### FP15 — Sessions UX (closed 2026-05-04)

User reported sessions weren't discoverable from the Library page.
Investigation found three issues, all closed in one commit:

- **The "Save as session" button was a no-op.** `LibraryPage.tsx:65`'s
  `onSaveSession` was a placeholder comment that FP11 § B8 marked as
  wired but never actually was. Clicking opened the name dialog and
  silently did nothing. Now wires to `useSessionUpsert` with a Session
  derived from current year range + Settings → Picker tab chip lists.
  Success toast confirms the save.
- **Active-session pill** added to the /library header (between filters
  and LayoutSwitcher). Click navigates to /sessions. Shows
  "Session: <name>" when active, "No active session" when not.
- **One-line explainer** above the Save button in FiltersSidebar tells
  first-time users what a session is and what it captures.

182 frontend tests / build clean. No new tests — existing FiltersSidebar
tests cover the Dialog → callback contract; the mutation wiring is
exercised by manual UAT.

### P08 — Clone-and-run bootstrap scripts (closed 2026-05-04, slim)

Slim P08 ships only the bootstrap scripts; the original in-browser
wizard is deferred to post-v1 per Karpathy 9 push-back (the existing
terminal `mame-curator setup` + Settings page banner cover the same
ground for v1).

- **`run.sh` (Linux/macOS).** Python 3.12+ detection, uv auto-install,
  `uv sync`, runs `mame-curator setup` if config.yaml is missing,
  then `mame-curator serve` + browser open. Idempotent.
- **`run.bat` (Windows).** Same flow translated for cmd.exe.

### P07 — Reference-data refresh + in-app help (closed 2026-05-04)

Slim P07 (scope refined 2026-05-04 — self-update + INI diff-preview UI
deferred to P12 post-v1) shipped 5 clusters across 5 commits:

- **A — `downloads.py` primitive.** Async sha256-verified atomic
  download with exponential retry, mirror fallback, and
  `ManualFallback` sentinel. Used by P08 setup wizard.
- **B — `mame-curator refresh-inis`.** New CLI command that downloads
  the 4 mandatory progettoSnaps INIs (catver / languages / bestgames /
  series) from AntoPISA's GitHub mirror via `downloads.py`. Per-file
  outcome line on stdout; manual-fallback URL surfaced on failure.
- **C — `cards_per_row_hint` UI Select.** Closes P06 spec § 210
  deferral. New Select in Settings → UI tab, values
  `'auto' | 4 | 5 | 6 | 8`.
- **D — HelpPage DOMPurify.** Closes FP11 § H4 security debt. Adds
  `dompurify@3.4`; HelpPage memoises sanitized HTML before
  `dangerouslySetInnerHTML` to strip `<script>` and `javascript:` URLs.
- **E — Cmd-K help-topic search.** Help topics from `/api/help/index`
  merge into the palette as help-section items; selecting a topic
  navigates `/help?topic=<slug>` and HelpRoute pre-selects it.

446 backend tests / 89.04% coverage. 182 frontend tests / build clean.
No `/audit` or `/indie-review` on close per user direction
("less audit-intensive"); local gates were the close signal.

### FP14 — GameCard layout overflow + always-on identifier (closed 2026-05-04)

GameCard's `aspect-[3/4]` image area pushed total card height past
the virtualizer's 280px row, clipping the description heading via
`overflow-hidden` — game tiles rendered blank in production with
no way to identify games whose box art hadn't loaded. Replaced
the fixed-aspect image with `flex-1 min-h-0` + `object-contain`
so the image fills the remaining row space after CardContent
claims its natural height. Image-fail placeholder now shows the
description (instead of the generic "No artwork available"
string) so games are always identifiable. Added shortname
(`font-mono`) below the heading — what `mame-curator copy`
consumes; also disambiguates same-name re-releases
(1942 Capcom vs Williams).

### FP13 — FP12 closing-review fold-in (closed 2026-05-04)

22 actionable findings from FP12's closing `/audit` (clean) +
3-lane `/indie-review` (primitives / FsBrowser / SettingsPage
wiring) closed across 6 commits — one per cluster per FP11
cadence. SettingsPage went from 551 → 305 lines via 6 new
extractions (FiltersTab / PickerTab / UpdatesTab / MediaTab /
PrefSwitch / PathRow). New `lib/apiErrorToast.ts` helper
translates ApiError → strings.errors.byCode with detail
fallback; wired through useConfigPatch / useSnapshotRestore /
useFsGrantRoot. 177 frontend / 435 backend tests at close.
Closed at the same SHA as FP12 per P05+FP10 / P06+FP11
precedent.

Original fold-in summary follows: Cross-cutting theme
flagged by 2 of 3 lanes: silent react-query mutation errors —
`useFsGrantRoot` / `useConfigPatch` / `useSnapshotRestore` all
fire-and-forget without `onError`, so a 422/404/500 from the API
is invisible to the user. Plus: SettingsPage at 551 lines vs
coding-standards §2 hard-cap 350 (extract per-tab subcomponents);
WCAG announcement gaps on `<DragReorderList>` + `<ChipListEditor>`
chip semantics; destructive-confirm UX gaps in BackupTab Import +
DAT-swap cancel. See `ROADMAP.md § FP13` for the full cluster
breakdown. 1 deferred false positive (semgrep on HelpPage:67 —
P06/FP11 surface, folded into next debt-sweep).

### FP12 — Settings page list editors + path picker (closed 2026-05-04)

Replaces the FP11 spec-§-511 read-only Settings tabs with
edit-in-place primitives. One commit per cluster — all 10
shipped 2026-05-02..04.

Closed: A `<ChipListEditor>` (7 fields) · B `<DragReorderList>`
(arrow-button reorder; no dnd-kit per Karpathy rule 9) ·
C `<YearRangeEditor>` (paired Switch+number, null via switch) ·
D `default_sort` `<Select>` · E `updates.channel` `<Select>` ·
I Snapshots tab (R16 list + R17 restore via concrete-label
`ConfirmationDialog`; new `SettingsRoute` container per FP11 § B8) ·
J Backup tab (R18 export + R19 import; `BackupTab` primitive +
`useConfigExport` / `useConfigImport`; export does Blob →
`<a download>`, import does `File.text()` → `JSON.parse` →
mutate; ConfirmationDialog labels the file by name) ·
G `<FsBrowser>` modal (R29-R34 wired through self-contained
`useFs*` hooks; quick-jump for home / drive roots / allowed roots;
file vs directory mode; `fs_sandboxed` 403 surfaces grant prompt
that POSTs R33; first MSW-backed component test in the suite) ·
F editable `media.cache_dir` (Input on blur + Browse → FsBrowser;
mounted only when open so existing tests don't need MSW) ·
H Paths tab in-place editable (PathRow helper for source_roms /
dest_roms / source_dat / retroarch_playlist; DAT swap surfaces
destructive ConfirmationDialog "Swap DAT to <path>" before
patching since `replace_world` rebuilds the whole library).

Next: closing `/audit` + `/indie-review` (or CI-matrix-as-audit
per FP11 precedent) → fold any findings into a follow-on
fix-pass, otherwise close clean.

### P06 — Frontend MVP (closed 2026-05-02)

**P06 (`frontend/` SPA) — all 18 spec impl-steps shipped** across 19
commits since `P05-complete`. Vite + React 19 + TypeScript scaffold;
Tailwind v4 with 6 themes (`dark`, `light`, `double_dragon`,
`pacman`, `sf2`, `neogeo`) as `@theme inline` blocks keyed on
`data-theme`; 16 shadcn primitives (`button` / `card` / `sheet` /
`dialog` / `alert-dialog` / `tabs` / `switch` / `slider` /
`progress` / `sonner` / `tooltip` / `command` / `dropdown-menu` /
`radio-group` / `input` / `label`); runtime deps (`@tanstack/
react-query@^5.100`, `@tanstack/react-virtual@^3.13`, `react-router@^7.14`,
`framer-motion@^12.38`, `zod@^4.4`, `lucide-react@^1.14`, `clsx`,
`tailwind-merge`, `cva`, `@radix-ui/react-slot`); dev harness
(`vitest@^4.1` + `@testing-library/react@^16.3` + `msw@^2.14` +
`@playwright/test@^1.59`); `frontend/src/api/{types,client}.ts`
(57 hand-mirrored TypeScript interfaces + zod `.strict()` schemas
mirroring Pydantic `extra="forbid"` + `apiRequest()` fetch wrapper
with typed `ApiError` envelope handling); `tools/check_api_types_sync.py`
stdlib-only Python ↔ TS drift CI gate wired into `.github/workflows/
ci.yml`; `strings.ts` user-facing string catalogue (i18n-ready,
P06 ships English only); backend `_SPAStaticFiles` subclass on
`api/app.py` with conditional `frontend/dist/` mount + 2 backend
tests; 19 components/pages under TDD (`GameCard`, `LibraryGrid`
virtualized via react-virtual, `LayoutSwitcher`, `ThemeSwitcher`,
`FiltersSidebar` with 200ms-debounced search + Switch-only prefs,
`AlternativesDrawer` + `WhyPickedPanel` + `NotesEditor`, `ActionBar`,
`DryRunModal`, `CopyModal` with SSE state, `ConfirmationDialog`
with throw-on-OK invariant, `SessionsPage` / `ActivityPage` /
`StatsPage` / `SettingsPage` / `HelpPage`, `CmdKPalette` via cmdk,
`no-checkbox-for-prefs` invariant test); `useKeyboard` hook
(single-key + chord + meta-mode); `ErrorBoundary` class component
with reset-on-key + manual retry; `AppShell` + `ThemeProvider`;
`App.tsx` with `QueryClientProvider` + `BrowserRouter` + lazy-route
`Suspense`; production build at 152 KB gzipped entry (< 350 KB
budget); 1 Playwright smoke E2E + `e2e/fixtures/config.yaml`;
`frontend/dist/` committed (15 files, 152 KB total). Backend tests
425 pass with 89.12% coverage; frontend tests 71 pass across 21
Vitest files; all five Python CI gates + API type-sync gate clean.

### FP11 — P06 closing-review fold-in (closed 2026-05-02)

**FP11 spawned by /close-phase 2026-05-02** — P06's closing /audit
(eslint, tsc, gitleaks, trivy, semgrep, check_api_types_sync) +
/indie-review across 6 lanes (api-bridge / library-components /
alternatives-trio / pages / layout-+-hooks-+-app / backend-static-mount
/ test-infra) surfaced **~40 actionable findings** plus 2 vendored /
library-by-design false positives (added to
`docs/audit-allowlist.md` as allowlist-002 / 003).

Findings batched into 10 thematic clusters per the audit-fold
pattern: **A** critical bugs (palette hard-reload, SPA fallback
swallows `/api/*` + `/assets/*` 404s, CopyModal abort traps user,
LibraryGrid columns decoupled from CSS auto-fill grid); **B** spec
contract gaps (12 — `strings.ts` dead error codes, LibraryPage
`config.data!` crash, SettingsPage missing `snapshots`/`about` tabs,
ActivityPage URL state, AlternativesDrawer empty-state contradiction +
missing media, CmdKPalette keywords, App.tsx no-op stubs across 5
routes, ErrorBoundary single-depth vs spec's three); **C** drift-gate
hardening (regex truncation, `_inherits_basemodel` over-match,
duplicate-class fail-loud, 204 schema contract); **D** component
lifecycle / quality (10 — NotesEditor setState-in-effect + save
lifecycle + ThemeSwitcher Fast-Refresh break + GameCard div-as-button
+ emoji-as-functional-UI + FiltersSidebar year bounds + CopyModal
stranded states + ConfirmationDialog forbidden-set); **E** `strings.ts`
catalogue completeness sweep across 12+ surfaces with inlined English;
**F** standards/lint cleanups (TS strict-mode, bogus eslint-disable,
unused param); **G** zod ↔ Pydantic mirroring (Field bounds not
mirrored, `z.iso.datetime()` strictness, frozen-config drift,
`parse<T>` zod issues discarded); **H** acceptance + a11y (Inter
font reference, Node engines pin, pacman contrast, HelpPage XSS
FIXME, `aria-current` on selected topic, `<section aria-labelledby>`
links, `<time>` element on timestamps, AT-affecting strings); **I**
test infrastructure (dead `/api/health` mock, vitest `exclude`
defaults, playwright preview reuse); **J** spec sync (toolchain
versions, `parents[3]`, `_SPAStaticFiles` rationale, error-code
reconciliation).

All 10 clusters closed across ~25 commits since `e569214` (the
P06 final-ship commit). 428 backend tests + 85 frontend tests +
1 Playwright smoke pass; coverage 89.14% backend; all five Python
CI gates green on Ubuntu / macOS / Windows × 3.12 / 3.13.

**Notable post-close follow-up:** the `_SPAStaticFiles` carve-out
(A2) needed Windows backslash normalisation when CI surfaced two
Windows-only failures on the FP11 push. `path.replace("\\", "/")`
applied before the `_NO_FALLBACK_PREFIXES` startswith check;
Linux-runnable property test added to `test_static_mount.py` so
future regressions surface on Linux pytest without needing the
Windows runner. Commit `8918cb5`.

P06 closes at the same SHA as FP11 — both phases ship together.
See `docs/journal/P06.md` and `docs/journal/FP11.md`. Full
finding-by-finding bullet list in ROADMAP.md § FP11.

### P05 — Media subsystem (closed 2026-05-02)

**P05 (`media/` module) shipped** — `src/mame_curator/media/` (3 files, ~120 LoC) implementing the libretro-thumbnails URL builder + lazy-fetch sha256 disk cache per `docs/specs/P05.md`. `escape_libretro` applies the 10-character filename rule (`&*/:\<>?|"` → `_`); `urls_for(machine)` returns frozen `MediaUrls` with `boxart`/`title`/`snap` (no `video` field — design §6.3 routes video through progettoSnaps in P06+, MediaUrls absence is load-bearing for the R39 short-circuit). `fetch_with_cache(url, cache_dir, *, client)` returns the on-disk path on cache hit, downloads-then-atomic-writes on miss, returns `None` on upstream 404 (no negative caching), raises `MediaFetchError` on other upstream/network failures. `cache_path_for(url, cache_dir)` is a pure helper (no I/O); cache key = `sha256(url).hexdigest()` with the URL path's suffix appended. R39 (`/media/{name}/{kind}`) swapped from inline URL build + bare `client.get` to `urls_for` + `fetch_with_cache`; `kind=video` short-circuits with `media_upstream_not_found` BEFORE `urls_for` (load-bearing — `MediaUrls` has no `video` attribute). `app.state.media_client` migrated from bare `httpx.AsyncClient()` to `AsyncClient(timeout=10.0, follow_redirects=True)` so the 10s timeout moves from per-call to client construction and libretro CDN 301/302 redirects transit transparently.

**423 tests pass project-wide; coverage 89.12%; `media/` aggregate 100% (above 90% gate); all five gates green.** 47 net new tests (23 escape + 6 urls + 12 cache in `tests/media/` + 6 new integration tests in `tests/api/test_routes_media.py` + `media_cache_dir` fixture in `tests/api/conftest.py` for tmp_path-isolated per-test cache).

### FP10 — P05 indie-review fold-in (closed 2026-05-02)

P05's closing `/audit` returned clean across ruff / bandit / gitleaks; `/indie-review` against the P05 surface returned 5 actionable findings (1 Tier-1, 1 Tier-2, 3 Tier-3) → batched into FP10. FP10's own closing `/audit` returned clean across ruff / bandit / mypy / gitleaks (full src+tests+docs) / trivy (0 HIGH/CRITICAL) / semgrep (200 rules: p/security-audit + p/python + p/fastapi, 0 findings); `/indie-review --fix HEAD` returned **Accept** verdict (all 5 fixes close their findings; tests spec-anchored; no new bugs). One-round converge — by far the fastest fix-pass yet. **5 actionable items, 4 new regression tests:**

- **A1 (Tier 1):** `api/app.py:45` `httpx.AsyncClient` constructed with `follow_redirects=True` so libretro CDN 301/302 redirects transit transparently instead of surfacing as `MediaFetchError("upstream 301 ...")` → spurious 502s.
- **A2 (Tier 2):** `media/cache.py:73-77` raises `MediaFetchError("empty body for ...")` on 200 + empty body. `raw.githubusercontent.com` rate-limit interstitials and CDN edge cases occasionally return `200 + Content-Length: 0`; the guard prevents a zero-byte file from poisoning the cache slot forever.
- **A3 (Tier 3):** `routes/media.py:53` `MediaUpstreamError(str(exc))` (was `f"upstream error: {exc!r}"`). User-facing `detail` no longer leaks `MediaFetchError(...)` class name or carries the redundant prefix; chained `__cause__` carries the typed cause for logs.
- **A4 (Tier 3):** `media/cache.py:60-62` one-line invariant comment naming the append-only-via-`atomic_write_bytes` assumption that makes the `path.exists()` race benign. Future "verify checksum" or "delete corrupt entry" paths would reintroduce TOCTOU; the comment makes the contract visible.
- **A5 (Tier 3):** `media/cache.py:68` network-error message uses `{url!r}: {exc}` (single `!r`). `ConnectTimeout(...)` class name no longer leaks into the user-facing detail; chained `__cause__` already carries the typed exception.

`docs/specs/P05.md` updated for A1 + A2 (contract-touching). A3 / A4 / A5 are message/comment-only and need no spec change. No `docs/specs/FP10.md` per the "specs are for features, not fixes" rule. See [`docs/journal/FP10.md`](docs/journal/FP10.md) and [`docs/journal/P05.md`](docs/journal/P05.md). Next phase: **P06 — Frontend MVP.**

### P04 — HTTP API (closed 2026-05-01)

**P04 (`api/` module) shipped** — 14 source files in `src/mame_curator/api/` (~2200 LoC) implementing all 40 routes from design spec § 6.5: games + alternatives + explanation + notes + stats; overrides + sessions CRUD; config GET/PATCH + snapshots + export/import; copy dry-run + start/pause/resume/abort + SSE status + history; activity log; sandboxed `/api/fs/*` browser + grant API; setup + updates check stubs; help + minimal media-proxy. Singleton `JobManager` bridges sync `run_copy(on_progress=...)` to async SSE event consumers via a worker thread + `_ProgressSynthesizer` (`loop.call_soon_threadsafe` for cross-thread emission). Frozen `WorldState` blob on `app.state.world` swapped wholesale on writes. Strict filesystem allowlist (`Path.resolve` + `is_relative_to`) with runtime grant API. Atomic-write protocol on every config / overrides / sessions / notes / snapshots / copy-history write. New `serve` CLI subcommand. `_atomic.atomic_write_bytes` helper added (Rule of Three: third site after `executor.py` + `cli/`).

**376 tests pass project-wide; coverage 88.56%; api/ aggregate ~86% (above 80% gate); all five gates green.** 75 new tests in `tests/api/` (15 long-form behavioral L01–L15 + 40 per-route shape tests + 3 sandbox-grant + 1 P01 hypothesis property test (now passing) + 16 FP09 regression + Cluster-R tests).

### FP09 — P04 indie-review fold-in (closed 2026-05-01)

`/audit` returned clean across ruff / mypy / bandit / gitleaks / semgrep (p/security-audit + p/python + p/fastapi) + 9 project-specific grep gates. `/indie-review` against the P04 surface returned 13 actionable findings → batched into FP09. FP09's own closing `/indie-review` flagged 4 patch-introduced findings + 1 spec-vs-code drift → folded inline as Cluster R per the FP02 / DS01 / FP05 / FP06 / FP08 precedent. **18 actionable items total:**

- **Tier 1 (3 — A1, A2, A3):** A1 repr-quote `{exc}` at 5 sites (`state.py:75/86`, `routes/fs.py:60`, `routes/media.py:51`, `jobs.py:_on_worker_error`) — multi-line exception messages no longer break the FP06–FP08 single-line `detail` invariant. A2 `routes/copy.py:R27` typed CopyReport response via `model_validate_json` + `response_model=CopyReport`. A3 R19 import re-applies `_SESSION_NAME_RE` per imported session-name (was bypassing the R11 regex; reserved-name collision risk).
- **Tier 2 (9 — B1, B2, B3, B4, B5, B6, B7, B8, B9):** B3 lifecycle/progress storage split (Cluster R H1 widening — see below). B4 shared `httpx.AsyncClient` on `app.state.media_client` (lifespan-managed) eliminates per-request TLS handshake storms. B5 spec line 338 narrowed from 250 ms → 50 ms to match implementation. B6 `replace_world` skips `compose_allowlist` recompute when `config is None`; `patch_config` short-circuits no-op PATCH; P01 hypothesis xfail flipped to passing. B7 `fs_list` parent-resolution simplified + filtered against allowlist. B9 `_atomic.atomic_write_bytes` + `atomic_write_text` now `os.fsync` the parent directory after rename per spec § Atomic-write protocol step 4. B1 / B2 / B8 confirmed as reviewer-side false positives — Session validator forces non-default include rules (round-trip lossless on valid inputs); listxml-pass combine violates anti-jump rule 2; `_help_dir()` arithmetic verified correct (reviewer miscount).
- **Cluster R (5 — H1, H2, M1, M2, Open Q2):** H1 the original `Job.history: deque(maxlen=200_000)` could evict `job_started` on >200k-event jobs; replaced with `lifecycle_history: list` (unbounded but small — ~3N+5 events for an N-file copy) plus `progress_history: deque(maxlen=200_000)`. Replay merges via `heapq.merge(... key=lambda ev: ev.ts)`. New regression test synthesises >200k progress ticks and asserts `job_started` survives. H2 added load-bearing-invariant comment to `replace_world` documenting that `compose_allowlist` is a pure function of `config.paths` + `config.fs.granted_roots`. M1 split `JobNotFoundError(404)` from `CopyReportCorruptError(502)` in R27 so operators can distinguish "id unknown" from "filesystem rot". M2 corrected `app.py` shared-client comment (httpx defaults to HTTP/1.1 + keep-alive; HTTP/2 is a P05 concern). Open Q2 spec/code timing harmonised at 50 ms.

11 fixes (8 code + 3 doc) plus 16 new regression tests. **376 tests pass project-wide; coverage 88.56%; all five gates green.** No `docs/specs/FP09.md` per the "specs are for features, not fixes" rule. See [`docs/journal/FP09.md`](docs/journal/FP09.md) and [`docs/journal/P04.md`](docs/journal/P04.md). Next phase: **P05 — media subsystem.**

### Fixed — Windows CI test (2026-05-01)

`tests/parser/test_cli_parse.py::test_error_routes_to_stderr_with_path_prefix` was failing on Windows runners because `Path.__repr__` normalizes the path to POSIX slashes (`WindowsPath('C:/Users/...')`) while the assertion looked for the native-backslash form. The G9 contract is "the path appears in the error", not "in a specific separator style" — assertion now accepts either `str(bad_path)` or `bad_path.as_posix()`. Test-only change; production code unchanged. Bundles with the P04 commit so the next push restores green CI on the Windows matrix.

### FP04 — Parser hardening sweep (closed 2026-05-01)

Plumbed `OSError` into the typed-error contract at every CLI-visible parser exception path. Six surgical try-clause expansions across `parser/dat.py` (zipfile open + `_stream_machines` iterparse) and `parser/listxml.py` (three `parse_listxml_*` iterparse loops), plus one `try/finally` cleanup binding to eliminate the theoretical fd-leak window in `_resolve_xml`. All sites previously caught only the type-specific exception (`BadZipFile` / `XMLSyntaxError`), letting `OSError` (perm-denied, EIO, IsADirectoryError, file-disappeared race) propagate raw past the CLI's `ParserError` catch as a Python traceback — `cli/spec.md` violation. 5 regression tests added (`tests/parser/test_dat.py` + `tests/parser/test_listxml.py`). 300 tests pass; coverage 95.11%; all five gates green. Closes the deferred items from DS01 (originally surfaced in pre-P03 indie-review 2026-04-27); the audit also caught 4 sibling `iterparse`-only-catches-`XMLSyntaxError` sites in `listxml.py` + `_stream_machines` (same threat model, same fix shape — folded into the same fix-pass). No `docs/specs/FP04.md` per the "specs are for features, not fixes" rule. Follow-up: P04 (HTTP API).

### FP08 — `runner.py` warning path-quoting (closed 2026-05-01)

The smallest fix-pass yet — 2 source edits + 2 regression tests. FP07 closing `/indie-review` flagged `copy/runner.py:233`'s recycle-failure warning interpolating `old_zip.name` raw (same threat model as FP06 B3 / FP07 A4: DAT machine short-name flows through to a JSON-serialised warning + CLI status line). FP08's own closing review caught a sibling site at `runner.py:92` that the initial audit's `warnings.append(f"...")` grep missed — the list-comprehension form `warnings: list[str] = [f"{w.name}: {w.kind}" for w in bios_warnings]`. Same value-flow class, same fix shape. **One-round cold-eyes spec review** (clean → READY TO SIGN OFF — by far the fastest converge yet). Closing audit + indie-review caught the R1 scope error; folded inline as Cluster R per the FP06 R2 precedent.

- **Tier 1 (1 — A1):** `copy/runner.py:233` warning emit now interpolates `{old_zip.name!r}`. The `{exc}` portion is a `CopyError` subclass already repr-quoted post-FP07 A4.
- **Cluster R (1 — R1):** `copy/runner.py:92` BIOS-warning list-comp now interpolates `{w.name!r}: {w.kind}`. Audit-pattern lesson logged: `warnings.append(f"...")` grep doesn't find the list-comp form; future fix-passes should trace value-flow into `CopyReport.warnings` rather than relying on a single grep pattern.

2 new regression tests added to `tests/copy/test_fp01_fixes.py` covering both sites end-to-end via `run_copy` (LF-bearing winner short-name for R1; LF-bearing existing-zip basename for A1). **295 tests pass project-wide; coverage 95.03%; all five gates green.** Long-form contract: [`docs/specs/FP08.md`](docs/specs/FP08.md). Follow-ups: FP04 (parser hardening, unchanged); P04 (HTTP API).

### FP07 — `cli/` + typed-error path-quoting sweep (closed 2026-05-01)

Completes the path-quoting sweep that FP06 scoped to `filter/`. Five surgical edits land the `repr`-quoted-path contract uniformly across `cli/`, `copy/`, and `parser/` error rendering. **Two rounds of cold-eyes spec review** (round 1: 1 critical — A1 test had dead `try/except OSError` around a non-syscall — plus 2 medium clarifications folded; round 2: clean → READY TO SIGN OFF). Closing `/audit` returned clean; closing `/indie-review` flagged 1 medium (M1: CLI test assertions too loose — fold inline as Cluster R) + 1 medium on surrounding code (M2: `runner.py:233` warning — spawn FP08).

- **Tier 1 (5 — A1, A2, A3, A4, A5):** A1-A3 quote `args.dat`, `args.out`, `args.filter_report` via `{!r}` at three error-message f-strings in `cli/__init__.py:139, 200, 249`. A4 fixes `CopyError.__str__` at `copy/errors.py:26` to render `(path={self.path!r})` — single rendering site covers every CopyError subclass (`RecycleError`, `PlaylistError`, `CopyExecutionError`, `PreflightError`) at every raise site without 7+ duplicate edits. A5 mirrors the fix in `parser/errors.py:14` `ParserError.__init__` for every ParserError subclass (`DATError`, `INIError`, `ListxmlError`). Strategy is a deliberate single-point-of-change at the base class — future raise sites added to either module inherit the fix automatically; this is the right level of abstraction for a contract change of this shape (Rule of Three's intent — when 5+ near-identical sites would be touched, fix at the base instead).
- **Cluster R (1 — R1):** Closing-review M1 — original CLI test assertion `assert "\n" not in err.rstrip("\n")` only strips trailing LFs; if any future `{exc}` value contains an embedded LF (e.g. multi-line `ValidationError.__str__`) the assertion fires on the exception body, not on the path. Narrowed the three CLI test assertions to `assert "evil\nname.<ext>" not in err` (literal-LF form of the path) — directly tests the contract without over-claiming about the rest of the message.

**Out of scope (deferred to FP08):** `copy/runner.py:233` `warnings.append(f"recycle of {old_zip.name} failed: ...")` — `old_zip.name` flows from DAT machine short names (user-data path); same threat model. One-line edit + regression test next fix-pass. 9 new tests across `tests/copy/test_errors.py` (NEW), `tests/parser/test_errors.py` (NEW), `tests/parser/test_cli_parse.py`, `tests/filter/test_cli_filter.py`, `tests/copy/test_cli_copy.py` — plus 1 updated test in `tests/copy/test_fp01_fixes.py` for the new repr-quoted shape. **293 tests pass project-wide; coverage 94.93%; all five gates green.** Long-form contract: [`docs/specs/FP07.md`](docs/specs/FP07.md). Follow-ups: FP08 (one-line `runner.py:233` warning fix); FP04 (parser hardening, unchanged).

### FP06 — FP05 closing-review fold-in (closed 2026-05-01)

Closing `/indie-review` on FP05 surfaced 4 actionable findings in surrounding code (`cli/__init__.py`, `filter/sessions.py`, `filter/_io.py`, `filter/overrides.py`) — folded as FP06. **Four rounds of cold-eyes spec review** (round 1: 1 critical + 3 high + 4 medium + 5 low — Pydantic v2 `__cause__` claim wrong; round 2: 1 critical + 2 high + 4 medium — B3a/B3b assertion clarity, "4 vs 5" header inconsistency; round 3: 1 critical + 1 high + 2 medium — `sessions.py:115` is static-string not name-quoting site, Pydantic version-pin constraint; round 4: clean → READY TO SIGN OFF). Closing `/audit` + `/indie-review` after implementation flagged one missed name-quoting site at `sessions.py:81` (`self.active` from YAML interpolated raw — reproduced LF leak through `ValidationError.__str__`); folded inline as Cluster R per the FP02 / DS01 / FP05 precedent. **7 actionable items total:**

- **Tier 1 (1 — A1):** wrap `--purge-recycle` short-circuit at `cli/__init__.py:215-225` in its own `try/except OSError`; surfaces a clean `error:` line + exit 1 instead of a Python traceback when the recycle directory is unreadable. The DS01 C6 / FP05 B9 contract (`cli/spec.md` § "Errors the CLI catches but never raises") was broken on this single early-return path.
- **Tier 2 (3 — B1, B2, B3):** B1 lock-in tests for `Sessions` exception-shape contract (direct construction → `ValidationError` with `errors()[0]['ctx']['error']` shape; loader path → `SessionsError` with path-prefixed message). B2 `Sessions._active_must_reference_a_defined_session` flipped from `raise SessionsError(...)` to `raise ValueError(...)`, restoring Pydantic's `ValidationError` wrapping and matching `Session._validate_session`'s convention; loader's existing `try: Sessions(...) except ValidationError → SessionsError(f"{path!r}: ...")` rewrap now fires correctly. B3 quote user-controlled strings via `repr()` at 13 sites total (10 path + 3 name post-R2): `_io.py:32, 35, 40`; `sessions.py:50, 81, 86, 93, 107, 119, 138, 150`; `overrides.py:35, 41, 45`. Defends single-line error contract against control-byte spoofing in filenames or YAML keys (newlines, ANSI escapes).
- **Cluster R (3 — R1, R2, R3):** R1 fixes the misleading `__cause__` docstring at `sessions.py:27-30` (Pydantic v2 leaves `__cause__=None`; the original `ValueError` is at `validation_error.errors()[0]['ctx']['error']`) and adds a parallel comment block above `_active_must_reference_a_defined_session` documenting the same wrap behavior post-B2. R2 — closing-review caught a B3 scope error: `sessions.py:81` interpolates `self.active` (loaded from YAML) without `repr` quoting; the bare interpolation leaks raw LF bytes through `ValidationError.__str__`. Reproduced at the prompt: `Sessions(active="evil\nname", sessions={"other": Session(include_genres=("X*",))})` produces a multi-line error message. Fixed inline as Cluster R per fix-pass precedent. New `test_active_with_control_char_quoted_in_error` pins. R3 — closing-review M1 caught that the original B1b path-context assertion `assert repr(f) in msg or repr(str(f)) in msg` was satisfied both pre-fix and post-fix on a clean fixture path because `repr` of a clean string-path coincidentally produces the same single-quote characters a bare interpolation would. Strengthened to a fixture path with literal LF (`tmp_path / "evil\nname.yaml"`) plus strict "no LF in head" assertion that survives a future "I'll just simplify the f-string" refactor.

**Out of scope (deferred to FP07):** `cli/__init__.py:139, 187, 200, 225, 233, 240, 260` and `copy/recyclebin.py` path-quoting (different module surface; FP06 deliberately scoped to `filter/`'s loaders so each fix-pass keeps a cohesive audit surface). 8 new tests across `tests/filter/test_io.py` (NEW), `test_overrides.py`, `test_sessions.py`, plus the A1 monkeypatched-OSError test in `tests/copy/test_cli_copy.py` and the R2 control-char test. **284 tests pass project-wide; coverage 94.63%; all five gates green.** Long-form contract: [`docs/specs/FP06.md`](docs/specs/FP06.md). Follow-ups: FP07 (cli/ + copy/recyclebin.py path-quoting); FP04 (parser hardening, unchanged).

### FP05 — DS01 closing-review fold-in (closed 2026-05-01)

DS01's closing `/indie-review` returned 14+ surrounding-code findings; FP05 absorbed 20 actionable sub-bullets across Tier 1 (3 real bugs: recycle_partial=True implementation, empty-string `active` rejection, `MemoryError` swallow narrowing), Tier 2 (8 hardening items + 2 reclassified after empirical investigation: B1 transitive-missing-warning conflated with leaf BIOS machines; B4 pause/cancel race didn't apply because `pause()` already short-circuits on `_cancel_flag`), Tier 3 (3 refactors: `_io.read_capped_text` + `_atomic.atomic_write_text` helper extraction; EXDEV handling), and 6 minor LOWs. Three rounds of cold-eyes spec review preceded sign-off (round 1: 8 issues; round 2: 5 + 2 contradictions; round 3: clean). FP05's own closing review surfaced 6 FP05-introduced drift items (Cluster R per the FP02 precedent), all closed inside FP05: recycle_root path mismatch, residual self-reference guard in bios.py, lingering BIOSResolutionError spec mention, dead OSError clause in _atomic.py, atomic_write_text call outside the try block, and cli/spec.md exit-code table out of sync with B10. 275 tests pass; coverage 94.67%; all five gates green. Long-form contract: [`docs/specs/FP05.md`](docs/specs/FP05.md). Follow-ups: FP06 (4 findings in surrounding code from FP05 closing review); FP04 (parser hardening, unchanged).

### DS01 — Pre-P04 debt-sweep fold-in (closed 2026-05-01)

`/debt-sweep` 2026-05-01 (scope `P02-complete..HEAD`) surfaced findings; four rounds of cold-eyes spec review converged on **20 actionable sub-bullets** (with C9 retained in the spec body as a footnoted stale-finding entry — flags already had `help=` strings at HEAD; shipped silently in DOC01/P03). D3 was added during cold-eyes review to prune two stale Tier-3 entries from this same `[Unreleased]` block. Folded into one fix-pass per the App-Build "every audit finding is tracked" hard rule. Prefix is `DS##` (debt-sweep) per the App-Build ID scheme — sourced from `/debt-sweep`, even though many sub-bullets are recovered FP-shaped findings (FP01 deferrals that did not actually close in FP02; pre-P03 sweep `[Unreleased]` Tier-2/3 hardening items; the `runner.py:258` swallow that FP02 deferred forward; record drift on commit `179325a`). Long-form contract: [`docs/specs/DS01.md`](docs/specs/DS01.md). Roadmap: [`ROADMAP.md` § DS01](ROADMAP.md). 20 sub-bullets across four clusters:

- **Cluster A — `copy/` spec+code drift (5):** `data/copy-history` persistence claim drop (3 sites: per-module spec + long-form roadmap); `session_id` ULID claim narrow; unused `self_reference` enum arm drop; `wait_if_paused` race-safety comment; `logger.exception()` on `runner.py:258` bare `except`.
- **Cluster B — Test gaps (4):** Hypothesis property tests for `resolve_bios_dependencies`; `test_cancel_with_keep_partial` strengthened to mid-session cancel; `test_lpl_no_bom` strengthened to UTF-8 round-trip; `source_dir` fixture widened to `scope="module"`.
- **Cluster C — `filter/` + `cli/` hardening (8):** `Sessions(active=...)` `model_validator`; `FilterResult.dropped` to tuple (with enumerated test rewrites at `tests/filter/test_runner.py:71-75`); YAML 1 MB cap; explicit `None` checks over `or {}` falsy-coalesce; `try/except OSError` around `read_text`; CLI `_cmd_filter` `OSError` wrap; atomic report write; sentinel-path antipattern removal.
- **Cluster D — Allowlist + record (3):** `_preferred_score` substring-vs-fnmatch allowlisted (see `docs/audit-allowlist.md` allowlist-001); commit `179325a` (2026-04-30) credited as a body bullet (below) — closes the FP01-deferred macOS/Windows path-separator entry; stale Tier-3 entries struck through with dated footnote.

**Body bullets — DS01 record-keeping closures**

- **`179325a` (2026-04-30)** — cross-platform path-separator fix in `tests/copy/test_fp01_fixes.py` and `tests/copy/test_playlist.py`. The FP01 deferred-list entry for the macOS/Windows path-separator known-issues note was uncredited until DS01.

**Out of scope (deferred to FP04):** `parser/dat.py` `_resolve_xml` `OSError` non-catch + theoretical fd-leak. Tracked as `FP04 — Parser hardening sweep` in ROADMAP, opened by DS01 cold-eyes review so the items are tracked as a roadmap entry rather than CHANGELOG-only prose.

### FP02 — FP01 round-2 fold-in (2026-04-30)

Round-2 indie-review on FP01-patched code surfaced 3 fresh-eyes Tier-2 + 6 Tier-3 findings on the surrounding `copy/` code (not regressions on FP01 fixes themselves). Folded into FP02; closing audit + indie-review pass on FP02 itself surfaced spec drift introduced by the FP02 changes (duplicate `AppendDecision` definition in `copy/spec.md`; stale `recycle_file` docstring), folded into the same FP02 round and closed. Highlights:

- **Tier 2** — `OverwriteRecord.parent` field dropped (always equalled `old_short`; the runner has no `cloneof_map` to compute the actual parent — FP01 #4 design contract); `AppendDecision` widened from a `StrEnum` to a Pydantic model `(kind: AppendDecisionKind, replaces: str | None)` so multi-conflict sessions steer to the right existing entry instead of relying on a brittle "first existing-but-not-winner" heuristic; recycle directories now keyed on `session_id` (`data/recycle/<session_id>/`) instead of just the timestamp, so two sessions recycling within the same second can no longer collide on the directory and overwrite each other's `manifest.json`.
- **Tier 3** — spec typo `mid-copy3` → `mid-copy`; `_chd_missing(plan)` helper extracted (was duplicated across `run_copy` and `_finalize`); `make_cb` closure factory replaced by `functools.partial`; playlist entries filtered to `SUCCEEDED` + `SKIPPED_IDEMPOTENT` (pre-FP02 the builder included `SKIPPED_MISSING_SOURCE` outcomes whose `dst` was never written, producing `mame.lpl` entries pointing at non-existent files); `KeyboardInterrupt` test extended to cover the `progress=callback` branch (previously only `progress=None`); recycle 3+ same-name same-session collision test added.

### FP01 — P03 indie-review fold-in (2026-04-30, closed)

Indie-review pass against fresh P03 surfaced 6 Tier-1 spec/code drift + atomicity bugs that `/audit` (ruff/mypy/bandit/pytest-cov/grep) missed. P03 stays open until FP01 closes; tag `P03-complete` will land after FP01 close. Findings folded into ROADMAP under `## FP01`. Highlights:

- Tier 1 — `copy_one` signature drift (spec lists `progress=None` only; code requires `short_name`/`role` kwargs); missing `KeyboardInterrupt` cleanup in `copy_one`; `OverwriteRecord` allocated but never appended; `PlaylistError` not raised on missing append decision (spec mandates); broken `recycle_file` collision logic (`for _ in [None]` is a 1-shot generator); `read_lpl` doesn't tolerate the legacy 6-line format spec promised — narrowing spec to v1.5+ JSON only.
- Tier 2 — six `# type: ignore[arg-type]` without rationale (root-cause fix: type the work list as `tuple[str, Literal["winner","bios"]]`); FAILED-branch + OVERWRITE+delete coverage gaps; `self_reference` warning enum arm unused; `wait_if_paused` race comment; `O_APPEND` 4 KiB atomicity comment; chunked-path failure test; cancel-keeps-partial test strengthening; hypothesis property tests for `resolve_bios_dependencies`.
- Tier 3 — `errors.py` `__str__` test; `playlist.py` error-branch tests; `session_id` ULID claim narrowed; `data/copy-history` persistence claim dropped (out of v1 scope); known-issues note for cross-platform path separators; `test_lpl_no_bom` strengthened.

### DOC01 — Phase D documentation audit fold-in (2026-04-30)

Five-lane cold-eyes documentation review across standards consistency, workflow integration, spec ↔ architecture alignment, phase-history accuracy, and discoverability/onboarding. Round 1 batched 3 Tier-1 / 17 Tier-2 / 7 Tier-3 actionable findings (after deduplicating cross-lane overlaps and one Tier-1 demoted to Tier-3 on re-read). Round 2 surfaced 2 Tier-1 / 7 Tier-2 / 4 Tier-3 follow-on findings — round-1 patches that did not propagate fully to sibling files (long-form roadmap step 7/8, `pick_winner` / `explain_pick` signatures in spec, layer-diagram order between README and CLAUDE.md, `DOC##` glossary gap). Both rounds folded into the same `DOC01` fix-pass; loop closes when one re-review pass returns zero actionable findings. Highlights:

- **Tier 1** — long-form roadmap acceptance checkboxes for shipped
  phases (P00/P01) ticked; fabricated closing-commit citations in
  `docs/journal/{P00,P01,P02}.md` corrected against `git log`
  (P00 + P01 shipped together in `56449c6`); README front-page
  status flipped (P02 ✅, advance "next" indicator to P03).
- **Tier 2** — standards slot `coding.md` adds §8; spec ↔ code
  drift fixes in `filter/spec.md` (`tuple` not `list`, no
  `apply_overrides()` standalone, no Mature-category fallback,
  `pick_winner` documented); `parser/spec.md` listxml-acquisition
  cross-reference fixed; `cli/spec.md` `filter` flipped to
  shipped; README adds links to authoritative docs, Conventional
  Commits note, inline layer diagram, real clone URL; glossary
  adds "non-merged ROM set"; `[Unreleased]`-until-v1.0.0 policy
  documented.
- **Tier 3** — §15 scope note added; CLAUDE.md PR-vs-direct-push
  policy stated; design § 12 wizard parenthetical; P02 journal
  fix-commit subjects un-truncated; SHA prefixes added to
  closing-commit citations.

### Pre-Phase-3 independent-review sweep — pass 3 (2026-04-27)

Third multi-agent sweep, dispatched after Phase 2 shipped. Four lanes
(filter rule chain / filter YAML I/O / CLI surface / parser deltas).
Two CRITICAL spec violations and one HIGH zombie field surfaced — folded
into the roadmap as Phase 2 → Phase 3 gate criteria (see roadmap §Phase 2
"Pre-Phase-3 indie-review findings"). Tier 2 hardening + Tier 3 structural
findings tracked here per the project's CHANGELOG-as-sweep-log convention.

#### Tier 2 — hardening (deferred until Tier 1 ships)

- 🔒 **filter rule chain** — `_score_preferred` uses substring `in` match where
  spec implies `fnmatch` (drops + sessions both use fnmatch).
  (`filter/picker.py:40-52`)
- 🔒 **filter rule chain** — `explain_pick` reports any non-uniform tiebreaker;
  spec says "tiebreakers that actually decided the winner." The strict reading
  is "would removing this tiebreaker change the winner?" — implementation
  over-reports. (`filter/picker.py:121-126`)
- 🔒 **filter rule chain** — `Sessions(active=...)` model construction bypasses
  validation; only `load_sessions` enforces `active in sessions`. Programmatic
  callers crash with `KeyError` at `runner.py:100` instead of `SessionsError`.
  Move into a Pydantic `model_validator`.
- 🔒 **filter rule chain** — `_score_region` returns `-1` for both `Region.UNKNOWN`
  and the second-priority region (USA at index 1). Spec says UNKNOWN ranks last.
  (`filter/picker.py:67-74`)
- 🔒 **filter rule chain** — `FilterResult.dropped` is `dict[str, DroppedReason]`
  (mutable in-place despite `frozen=True`). All other fields are tuples.
  (`filter/types.py:51-59`)
- 🛡️ **filter YAML I/O** — `yaml.safe_load` defends against CWE-502 deserialization
  but not against alias-bombs; loaders also read entire file into memory before
  parse. Threat is low for self-authored configs but escalates when Phase 7's
  `setup/` ships preset downloads. Cap file size now (1 MB suggested).
  (`filter/overrides.py:31`, `filter/sessions.py:59`)
- 🛡️ **filter YAML I/O** — `sessions: null` (and `[]`, `0`, `""`) silently coerced
  to empty by `raw.get("sessions") or {}`. Same falsy-coalesce bug at
  `body or {}` for individual session bodies. Replace with explicit `None`
  + `isinstance` checks. (`filter/sessions.py:66,71`)
- 🛡️ **filter YAML I/O** — TOCTOU between `path.exists()` fast-path and
  `path.read_text()` lets `OSError` (file deleted, NFS hiccup) escape as
  untyped exception. Wrap `read_text` in `try/except OSError`.
  (`filter/overrides.py:28-31`, `filter/sessions.py:56-59`)
- 🛡️ **filter YAML I/O** — non-string YAML keys silently coerced to strings by
  Pydantic (`overrides: { 123: foo }` → `{"123": "foo"}`); empty key (`: x`)
  becomes `{"None": "x"}`. Spec says "non-empty strings"; no `min_length=1`
  constraint enforces it. (`filter/overrides.py:23`)
- 🛡️ **CLI** — `_cmd_filter` doesn't catch `OSError` from `--catver`/`--listxml`/etc.
  pointing at a directory or unreadable file; raw Python traceback reaches the
  user, violating cli/spec.md §"Errors the CLI catches but never raises."
  (`cli/__init__.py:126`)
- 🛡️ **CLI** — non-atomic write of report JSON. `args.out.write_text(...)` left
  half-written on Ctrl-C / OOM. Phase 3's `copy/` will consume this report;
  use tmp-file + `Path.replace` for atomicity. (`cli/__init__.py:131`)
- 🛡️ **CLI** — sentinel-path antipattern: when `--overrides` / `--sessions` are
  unset, the loader is called with `Path("/nonexistent/overrides.yaml")` to
  trigger the missing-file fast path. Brittle (someone creates the path,
  loaded silently); fails six-month test. Replace with direct `Overrides()` /
  `Sessions()` construction. (`cli/__init__.py:115-124`)
- 🛡️ **parser deltas** — `_resolve_xml` doesn't catch `OSError` from
  `zipfile.ZipFile(...)` (perm-denied, EIO, broken symlink). Same root cause
  as the CLI finding; spec line 138 says every CLI-visible error path stays
  inside `ParserError`. Tier-2 BadZipFile fix scoped narrowly; this completes
  the hardening. (`parser/dat.py:48-50`)
- 🛡️ **parser deltas** — fd leak window in `_resolve_xml`: `zip_ctx = zipfile.ZipFile(path)`
  binds before the `with` block, so a future `__enter__` failure leaks the fd.
  Theoretical (CPython `__enter__` is `return self`) but the idiomatic fix is
  one-line: move `ZipFile(path)` inside the `with` and the `try` around it.
  (`parser/dat.py:49-56`)

#### Tier 3 — structural / spec-tightening

- 🧹 **filter rule chain** — `contested_groups` and `warnings` ordering depends
  on Python dict iteration order; sort by `parent` / canonical key before
  tupling for byte-identical determinism. (`filter/runner.py:43-46,64`)
- 🧹 **filter rule chain** — `_cmd_filter` is 39 lines, conflates four concerns
  (build context, overrides, sessions, run + report). Extract `_build_context`.
  (`cli/__init__.py:99-138`)
- <del>🧹 **CLI** — module docstring (used as `--help` description) lists `copy` as a
  shipped subcommand; only `parse` and `filter` are. (`cli/__init__.py:1-7`)</del>
  — *closed silently in DOC01/P03 (2026-04-30); confirmed stale in DS01 cold-eyes review 2026-05-01*
- <del>🧹 **CLI** — `--catver`, `--dat`, `--languages`, `--bestgames`, `--overrides`,
  `--sessions` lack `help=` strings. (`cli/__init__.py:48-54`)</del>
  — *closed silently in DOC01/P03 (2026-04-30); confirmed stale in DS01 cold-eyes review 2026-05-01*
- 🧹 **CLI** — `args.out.parent.mkdir(parents=True, exist_ok=True)` silently
  materializes arbitrary directory trees from a typo. Document or constrain.
  (`cli/__init__.py:130`)
- 🧹 **CLI** — no INFO log lines for milestones; `-v / --verbose` flips the
  level but the CLI itself emits nothing. Add `logger.info()` at parse and
  load steps for slow-DAT visibility.
- 📝 **spec — filter** — pin: `preferred_*` is `fnmatch` (or `in`); session
  None-value behavior on year/publisher/developer; `lo == hi` is single-year-OK;
  listxml-vs-DAT `<machine>`-name strictness asymmetry is intentional.
- 📝 **spec — filter** — `populate_by_name=True` on `Overrides` is dead weight
  given the loader doesn't accept the alternate key; remove or document the
  alternate YAML key.
- 📝 **spec — parser** — listxml-vs-DAT strictness asymmetry: DAT raises
  `DATError` on missing `<machine name>`; listxml silently skips. Defensible
  but spec is silent.

### Phase 2 complete — filter rule chain (2026-04-27)

Implemented the four-phase filter pipeline: drop (Phase A) → pick
(Phase B) → override (Phase C) → session-slice (Phase D). 154 tests
pass at 97.4% overall coverage; every `filter/` submodule sits at
≥97% (per-phase floor 95% met). All five CI gates green.

#### Added
- **`filter/spec.md`** — full audit-surface contract: 13 typed
  drop reasons, 7-step tiebreaker chain, override + session
  semantics, YAML schemas for `overrides.yaml` / `sessions.yaml`,
  region + revision-key heuristic regexes.
- **`filter/config.py`** — `FilterConfig` (frozen Pydantic, defaults
  match design spec §6.2).
- **`filter/overrides.py`** — `Overrides` model + `load_overrides`
  with `populate_by_name=True` so callers can use either the
  in-memory `entries=` form or the YAML `overrides:` alias.
- **`filter/sessions.py`** — `Session` / `Sessions` models +
  `load_sessions` with empty-session and reversed-year-range guards.
- **`filter/heuristics.py`** — `region_of` (15 region tags + UNKNOWN)
  and `revision_key_of` (family ranks: v-version > rev-letter >
  set-number > unmarked).
- **`filter/types.py`** — `DroppedReason` (StrEnum), `TiebreakerHit`,
  `ContestedGroup`, `FilterResult`, `FilterContext` (all frozen
  Pydantic models with `extra="forbid"`).
- **`filter/drops.py`** — 13 Phase A predicates evaluated in spec
  order; `drop_reason()` returns the first matching reason.
- **`filter/picker.py`** — 7-step Phase B tiebreaker chain composed
  via tuple sort key; `pick_winner()` + `explain_pick()`.
- **`filter/runner.py`** — `run_filter()` orchestrator composing
  Phases A → B → C → D. Override warnings (unknown parent / target /
  cross-group) surface in `FilterResult.warnings` rather than
  crashing.
- **`parser/listxml.py`** — added `parse_listxml_cloneof()` to
  reconstruct parent/clone relationships that Pleasuredome DATs
  strip. Same lxml fast-iter streaming pattern as the existing
  `parse_listxml_disks`.
- **`cli/__init__.py`** — `mame-curator filter` subcommand reads
  DAT + listxml + 5 INIs + overrides + sessions, runs the pipeline,
  writes a JSON `report.json`, prints a one-line summary per result
  group. Honors the cli/spec.md error-routing + exit-code-1 contract.
- **`tests/filter/`** — 90 new tests covering: config schema (4),
  overrides (7), sessions (10), heuristics (17), listxml-cloneof (4),
  drop predicates (16), picker tiebreakers (10), runner end-to-end
  (10), Hypothesis property determinism + idempotency (2),
  30-machine snapshot regression (1), CLI filter (2). Snapshot
  fixture exercises every drop reason, every tiebreaker, the
  override path, and the session slicer.

### Pre-Phase-2 Tier 2 hardening (2026-04-27)

Closed the three Tier 2 items deferred from the first indie-review sweep, plus
their associated spec gaps. 72 tests pass at 95% coverage; all five CI gates
green.

#### Code fixes
- 🐛 **H2** — `_parse_simple_ini` required `]` to be the last character, so
  `[Section] ; trailing comment` and `[Section]# comment` were silently dropped.
  A real-world consequence: an inline-commented `[FOLDER_SETTINGS]` header would
  fail to filter and its keys (`RootFolderIcon=...`) would leak into the parsed
  output as fake machines. Switched to truncating at the first `]`.
  (`parser/ini.py:_parse_simple_ini`)
- 🐛 **M2** — `_resolve_xml` opened `zipfile.ZipFile` without catching
  `zipfile.BadZipFile`. A corrupt or truncated `.zip` would propagate that
  exception out of the parser, slip past the CLI's `ParserError` catch, and
  surface as a Python traceback in the user's terminal — a `cli/spec.md`
  contract violation. Wrapped to `DATError` with the path attached.
  (`parser/dat.py:_resolve_xml`)
- 🛡️ **M3** — `run()` had `return 1` as an "unreachable" fall-through after
  the dispatch chain. Argparse's `required=True` makes that branch unreachable
  from any real argv, so reaching it would mean the dispatch table is out of
  sync with `build_parser()`. Returning `1` would silently hide the bug
  (looks like a runtime error); raising `AssertionError` surfaces it loudly in
  tests. (`cli/__init__.py:run`)

#### Spec edits
- **`parser/spec.md`** — pinned: INI section headers with inline comments
  (`[Mature] ; old format`) are tolerated by truncating at the first `]`;
  corrupt/truncated DAT zips raise `DATError`, never propagate `BadZipFile`.
- **`cli/spec.md`** — added the "unreachable fall-through discipline" clause
  to the dispatch-pattern section: `run()`'s default branch MUST raise
  `AssertionError`, not return a runtime-error exit code.

### Pre-Phase-2 independent-review sweep — pass 2 (2026-04-27)

Second multi-agent sweep after Tier 1 fixes landed. Reframed around spec
accuracy: "where is the spec unclear, not the code wrong?" Every finding
classified as (a) code-not-following-spec → fix code, (b) spec gap → tighten
spec, or (c) code-quality → backlog. Closed nine spec gaps (G1–G10) and
created `cli/spec.md` (C1) so the CLI surface has a contract per standards §7.

#### Spec edits
- **`parser/spec.md`** — pinned: empty `<rom>`/`<biosset>` `name` → DATError;
  `<year>` outside `[1970, 2100]` → None; DriverStatus is open-membership
  (warn + None on unknown, never DATError); INI encoding policy (strict
  UTF-8 with latin-1 fallback warning, never silent U+FFFD); zip-slip
  protection on `.zip` wrappers; `Rom.size` non-negative; `_META_SECTIONS`
  filter applies to all five INI parsers.
- **`coding-standards.md`** — §9 now mandates errors → stderr, success/summary
  → stdout, and that errors at trust boundaries MUST include the offending
  input identifier (path, URL, key, line). §8 adds phase-staged dependency
  declaration: phase-N runtime deps live in `[project.optional-dependencies]`
  until the importing code ships.
- **`cli/spec.md` (new)** — pins subcommand inventory, exit codes (1 runtime,
  2 reserved for argparse), output routing, error-message contract, logging
  configuration discipline, and the `set_defaults(func=...)` migration plan
  for Phase 2/3.

#### Code fixes (one commit per gap)
- 🛡️ **G1+G6** — empty `<rom>`/`<biosset>` `name` and negative `Rom.size`
  raise DATError via Pydantic Field constraints.
- 🛡️ **G2** — `<year>` outside `[1970, 2100]` → None.
- 🛡️ **G3** — unknown `<driver status>` warning rate-limited to once per
  unique status string (avoids 43k log lines on a single MAME schema bump).
- 🛡️ **G4** — INI encoding: try strict UTF-8, fall back to latin-1 with a
  warning. Never silent corruption.
- 🛡️ **G5** — zip-slip protection: `.zip` member with absolute path or `..`
  component → DATError.
- 🛡️ **G7** — `_META_SECTIONS` filter applied to `parse_languages`,
  `parse_bestgames`, `parse_mature` (was: only catver + series).
- 🛡️ **G8+G9** — CLI errors route to stderr with the input path prefixed.
- 📦 **G10** — `fastapi` / `uvicorn` / `httpx` / `sse-starlette` moved from
  `[project.dependencies]` to `[project.optional-dependencies].api`. Phase 1
  end users no longer pull the web stack.

### Pre-Phase-2 independent-review sweep (2026-04-27)

Three-lane multi-agent review (parser / CLI / filter spec). 6 actionable Tier 1
findings, 5 Tier 2, 3 Tier 3. Tier 1 fixed in this batch.

#### Tier 1 — fixed
- 🐛 **parser**: `<rom size>` non-numeric value raised bare `ValueError` instead
  of `DATError`, breaking the spec's typed-exception contract. (`dat.py:_rom_from_element`)
- 🐛 **parser**: `lxml.iterparse` sibling cleanup was incomplete — `Element.clear()`
  empties an element but doesn't detach it from its parent, so the spine of the
  43k-machine DAT accumulated empty `<machine>` siblings throughout the parse,
  defeating streaming. Applied the canonical lxml fast-iter idiom. (`dat.py`, `listxml.py`)
- 🐛 **parser**: `parse_series` accepted progettoSnaps' `[FOLDER_SETTINGS]` /
  `[ROOT_FOLDER]` metadata sections as if they were series names. Added a
  metadata-section deny-list. (`ini.py:parse_series`)
- 🐛 **parser**: spec promised duplicate-key INI emits `logger.warning`;
  implementation silently overwrote. (`ini.py:_parse_simple_ini`)
- 🐛 **cli**: runtime errors returned exit code 2, conflicting with argparse's
  reserved meaning (usage error). Changed to 1. (`cli.py:_cmd_parse`)
- 🐛 **cli**: `logging.basicConfig(...)` ran at module import time, mutating
  global root-logger state for any process importing `mame_curator.main`. Moved
  into `main()` and gated level on a new `--verbose` flag. (`main.py`)

#### Tier 2 — deferred (hardening, pre-Phase-2)
- INI section headers with inline `;` comments silently dropped (parser H2).
- Unknown driver-status warning fires per element instead of once per status (parser M5).
- CLI errors should go to stderr, not stdout, with path-prefixed messages (cli M1).
- `_cmd_parse` doesn't catch `BadZipFile` (cli M2).
- Replace unreachable fall-through in `run()` with an explicit assertion (cli M3).

#### Tier 3 — structural backlog
- Adopt `parse_cmd.set_defaults(func=...)` dispatch pattern for Phase 2/3 subcommands.
- Add at least one `tests/parser/test_real_dat_fixture.py` with a truncated
  Pleasuredome-style DAT to anchor tests against external behavior, not internal modules.
- Add `--version` flag.

### Added
- **Phase 1 complete** — DAT and INI parsers (`parser/`):
  - Streaming DAT parser (`lxml.iterparse`) tolerant of `.xml` or `.zip` input.
  - Five INI parsers (catver / languages / bestgames / mature / series) sharing a single small walker.
  - CHD detector via official MAME `-listxml`.
  - `Machine` Pydantic model (frozen, validated) with `Rom`, `BiosSet`, and `DriverStatus`.
  - Manufacturer split for `"Foo (Bar license)"` → `(publisher, developer)`.
  - CLI subcommand `mame-curator parse <dat>` prints summary stats.
  - Smoke run against the user's real 43,579-machine 0.284 DAT: parsed in 4.6 s.
  - Empirical finding: Pleasuredome DATs strip `cloneof` / `romof` — Phase 2's filter joins parent/clone info from official MAME `-listxml` instead.
- **Phase 0 complete** — project scaffolding: uv-managed Python ≥ 3.12 venv,
  src/ layout, ruff (lint + format), mypy (strict), pytest (with coverage + ≥85%
  enforced gate), bandit, pre-commit hooks (mirroring CI), GitHub Actions CI matrix
  on Linux/macOS/Windows × Python 3.12/3.13, MIT license, README skeleton,
  example yaml configs (config / overrides / sessions).
- Release workflow gated on green CI: tagging `vX.Y.Z` triggers a re-run of
  all CI checks against the tag; only if every check passes is a GitHub
  Release created with the built sdist + wheel attached.

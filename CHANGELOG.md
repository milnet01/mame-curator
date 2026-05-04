# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Versioning policy.** This project is pre-alpha. **All shipped
> work stays under `[Unreleased]` until the v1.0.0 cut at P09.**
> No intermediate `v0.0.X` / `v0.Y.0` tags are produced — the
> first git release tag will be `v1.0.0`. Phase-closing
> `<ID>-complete` annotated tags (`P00-complete`, `P01-complete`,
> `P02-complete`, …) mark per-phase ship landmarks but are
> distinct from semver-versioned releases. The CHANGELOG is the
> authoritative record of what shipped per phase; consult
> `git tag --list 'P*-complete'` to map phases to commits.

## [Unreleased]

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

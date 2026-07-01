# MAME Curator — Workflow state

## §1. Status header

| Field | Value |
|-------|-------|
| **Project phase** | P10 active 2026-05-17 — Media coverage expansion (Step 3: chunks 3a + 3b + 4 + 5 shipped 2026-05-18 — progettoSnaps pair + ArcadeDB + Wikipedia-image bundle). FP31 test-audit fold-in shipped 2026-05-18 (second sweep, 6 HIGH + 21 MEDIUM inline; 11 LOW/INFO clusters deferred as mame-curator-1046..1056; the backend-test refactor sub-bundle (1046/1050/1051/1054/1055/1056, same kind+lane) closed 2026-06-10 — 5 remain open: 1047 (FsBrowser prefetch SUT decision), 1048/1049 (frontend-test migrations), 1052/1053 (fix-kind: vacuous pause/resume test + coverage gaps). **1054(b) deliberately not done** — see its ROADMAP Resolved note). Test-audit sweep 2026-05-20 — 14 inline fixes (count-neutral correctness/assertion/slow-marker/parametrize + 1 pre-existing red arch-diagram test root-caused) + 6 deferred clusters mame-curator-1065..1070 (all closed 2026-06-10: 1065/1066 dedup+parametrize, then 1067 coverage / 1068 assertion-hardening / 1069 fixture-scope perf / 1070 noqa doc-fix — test-audit-2026-05-20 section fully closed). FP29 closed 2026-05-17 (RetroArch executable + core PathRows on Settings → Paths; ships the UI half of FP22-C). P14 closed 2026-05-17 — per-game review state. Docs bundle (mame-curator-1029 + 1030) closed 2026-05-16. DS03 closed 2026-05-16. DS05 closed 2026-05-16. DS02 closed 2026-05-15 + R2 hot-fix. FP28 closed 2026-05-15. DS04 closed 2026-05-15. FP27 closed 2026-05-14. Queue continues **post-v1**. |
| **Active item ID** | P10 (mame-curator-1005) |
| **Active step** | 3 — tests-first per App-Build. Step 1 ✅, Step 2 ✅, Step 3 in progress (chunks 1 + 2 + 3a + 3b + 4 + 5 ✅; chunk 6 ✅ 2026-07-01 — cover-fetch deferred to mame-curator-1079; **chunk 7 registry + orchestrator ✅ 2026-07-01** — convergence checkpoint cleared by user; **chunk 8 Wikipedia extract endpoint ✅ 2026-07-01**). Next: chunk 9 (readiness API) → 10 (Settings→Media UI) → 11 (AboutSection). |
| **Blocked on** | nothing — user authorised the P10 back half (chunks 8–11, one chunk per commit). |
| **Last update** | 2026-07-01 (**P10 chunk 8 — Wikipedia extract endpoint** — user cleared the chunk-7 convergence checkpoint ("continue to chunk 8"). Shipped `media/wikipedia.py`: `WikipediaExtract` (frozen title/extract/url/license model) + `resolve_wikipedia_extract(machine, *, cache_dir, client, limiter)` — reuses the chunk-5 `_canonicalise_wikipedia_title` + REST-summary base, shares the `wikipedia_limiter` bucket AND the `fetch_text_with_cache` slot with `WikipediaImageSource` (same URL → same key → one lookup warms both), parse-before-trust unlink on bad JSON, returns None on 404 / missing-fields. New route `GET /media/{name}/wiki` registered **before** `/media/{name}/{kind}` (else `wiki` binds `kind`); catches `MediaError` → `null` (non-essential About text never 500s on rate-limit/network). Spec amendment cold-eyes'd 2 loops (0 CRITICAL/HIGH; resolved the `limiter`-injection gap — spec signature omitted it while the rate-limit test needed it — and the rate-limit-→-null route contract; fixed a `GameNotFoundError(...)` stub + count drifts). `WikipediaExtract` added to `PYTHON_SOURCES` in the api-types-sync gate + mirrored in `types.ts` + Zod `schemas.ts` (frontend consumer is chunk 11). 12 new pytest decls (8 wikipedia incl. 2 error-branch + 4 route; DS05 pin 645→657). Gates: 826 backend @ 87.83% / 0 ruff / 0 format / 0 mypy / 0 bandit; 323 frontend vitest / 0 eslint / tsc + vite build clean; api-types-sync 64 interfaces. **Prior:** 2026-07-01 (**P10 chunk 7 — registry + orchestrator + route wiring** — the media source-chain converges. Shipped `MediaSourceRegistry` (`media/sources.py`; per-request pure filter/orderer: unknown-name drop with process-wide-deduped WARNING, libretro baseline append, kind filter, disabled-source filter) + NEW `media/resolve.py` (`resolve_image` orchestrator — walks the chain, swallows per-source `MediaRateLimited`/`MediaFetchError` and falls through, `file://` short-circuit for the local snap pack via `url2pathname` for Windows-correctness; + `build_registry` composition root injecting the app-state limiters + `SourceDisabledFlag`, constructing only configured sources so dropping mobyGames suppresses its keyless WARNING). Route `GET /media/{name}/{kind}` swapped inline URL build → `resolve_image`; **502 `media_upstream_error` retired for media** (single-source 5xx/transport error now falls through → 404 when the whole chain misses); dropped the `MediaUpstreamError` import. New `media.sources` config field (default 5-source order) mirrored in `types.ts` + Zod `schemas.ts` + 2 frontend fixtures. Chunk-7 also added a process-wide dedup guard to the keyless-MobyGames WARNING (per-request reconstruction would otherwise spam) and fixed two shipped MobyGames tests filtering the wrong caplog logger (`media.sources`→`media.mobygames`). **Spec amendment cold-eyes'd 5 loops to a clean, implementable contract** (0 CRITICAL throughout; fixed stale `_enabled`-flag prose across 4 sites, bare-string-vs-`SourceDisabledFlag` holder drift, injectable `secrets_dir` + POSIX-only mode-gate docs, `{"release":[]}`→`{"release":0,"result":[]}` test shape, false "shipped" heading, registry `available`-map contract gap, snap_dir phrasing, 502→404 tense, line-count/logger-name accuracy). 17 new pytest decls (registry 7 + resolve 9 + mobygames dedup 1; DS05 pin 628→645). Gates: 814 backend @ 87.78% / 0 ruff / 0 format / 0 mypy / 0 bandit; 323 frontend vitest / 0 eslint / tsc + vite build clean; api-types-sync ok. Route tests: the 3 P05-era 502-asserting tests rewritten to fall-through-then-404; `config_file` fixture pinned `media.sources: [libretro]` for deterministic single-source route tests (multi-source fall-through unit-tested in `test_resolve.py`). Follow-ups logged: **mame-curator-1081** (`media.snaps_dir` field binding source read-path to `refresh-snaps --dest`), **1082** (Starlette `httpx2` deprecation warning). **PAUSED at the convergence checkpoint** — user check-in due before chunks 8–11. **Prior:** 2026-07-01 (**P10 chunk 6 — MobyGames key-handling half** — user elected "key-handling now, fetch later" at the chunk-6 gate, since the cover-image fetch needs a real MobyGames API key to verify the response field path (none on this machine; no anonymous API access; the spec's `cover_url` guess is unverified). Shipped: `MobyGamesSource` in new `src/mame_curator/media/mobygames.py` (env-var / mode-0600-dotfile key resolution, missing-key + 401/403 disable, 429/404 auth branches, key-redacted errors, rate-limit) + `SourceDisabledFlag` holder (refines the spec's bare-`app.state` string — `media/` is HTTP-agnostic so the process-wide reason rides an injected holder). Deliberate divergence: `prepare` does its own `client.get` (not `fetch_text_with_cache`) to tell 401 from 429 apart AND keep the keyed URL out of logs. Extracted to its own module because `sources.py` + MobyGames = 596 > 500 hard cap. Schema field `media.mobygames_rate_limit_per_min` (default 5) + `mobygames_limiter`/`mobygames_disabled` on `app.state`. 17 new pytest decls (DS05 pin 613→628). Frontend: `MediaConfig` field mirrored in `types.ts` + Zod `schemas.ts` + 2 test fixtures (tsc/eslint/vitest 323/build green). **Cover-URL parse + JSON-body caching DEFERRED to mame-curator-1079** (post-P10 fix-pass; MobyGames is last in the fallback order so zero user-visible regression). Spec amended inline (chunk-6 notes); `/cold-eyes` re-loop on the divergences deferred to the chunk-7 convergence checkpoint per the spec's risk-register clause. Gates: 797 backend @ 87.73% / 0 ruff / 0 format / 0 mypy / 0 bandit; api-types-sync ok. **Prior:** 2026-06-30 (**Cleanup/debt bundle** — closed mame-curator-1077 (split `LibraryPage.tsx` 579→314 under the §2 frontend component hard cap of 350; non-render logic → new `pages/useLibraryController.ts` 318-line hook + pure `pages/libraryPageHelpers.ts` 61; JSX kept in the page so the `?raw` source-text structural tests stay valid; behaviour-preserving) + 1078 (Snapshots review-state exclusion caveat — `snapshotsStateExclusionNote` string per P14 spec §875, rendered in both empty + populated states; +2 vitest). Same `frontend` lane, both surfaced 2026-06-30 from the P14 docs work. 1076 (chore/ci macOS-26 pin) left for its own pass. 2 commits `3b0321b..d82c491` — **CI went red on the first push** (`test_ds05_test_count_stable` is a *pytest* test counting frontend `it()` decls; +2 SnapshotsTab tests tripped 304→306; local frontend gate doesn't run pytest), fixed by `d82c491` bumping the pin; final CI all 8 jobs green. 323 frontend vitest / 0 eslint / `tsc -b` + `vite build` clean; no other `.py` touched. Active P10 item unchanged.) **Prior:** 2026-06-30 (**P14 docs bundle** — closed mame-curator-1060 (P14 phase journal) + 1061 (review-state contract promoted to co-located `src/mame_curator/filter/review_state_spec.md`; user elected the separate-file option; `/cold-eyes` clean at 3 loops — fixed a world-lock over-claim, an unshipped-caption claim, a GET-can't-404 nit, and a coupled `copy/spec.md` `ReviewStateDetails` `str`-not-enum type bug) + 1064 (amended the CLAUDE.md "fix-passes don't get specs" rule to bless long-form specs for multi-tier fold-ins, matching the FP05/FP27/FP28/DS01–DS05 reality). **Parked 1058** (media spec — P10 still in flight, chunk 6+ unshipped; re-checked + annotated). Surfaced + roadmapped **1077** (`LibraryPage.tsx` 579-line file-size cap breach) and **1078** (unshipped Snapshots "review state not snapshotted" caption). 3 commits `2037993..cb6d8c7`; docs gate 96 green (no `.py`/frontend touched); pushed. Active P10 item unchanged.) **Prior:** 2026-06-10 (**FP31 second-sweep backend-test refactor bundle** — closed mame-curator-1046/1050/1051/1054/1055/1056 (same kind+lane: refactor / backend-tests). 1046 split `test_sources.py` 554→4 per-source files + `tests/media/conftest.py`, and `test_fp01_fixes.py` 423→272 + new `test_fp01_error_branches.py`; 1050 dropped 15 redundant `@pytest.mark.asyncio`; 1051 pinned 5 `pytest.raises` to `ValidationError` + `match=`; 1054 (a/c/d/e/f) helper/conftest dedup — **(b) deliberately declined** (cross-tree fixture move would collide `source_dir`/`dest_dir` names); 1055 all 15 sub-items a–o (incl. +1 X_OK test, makeGameCard factory, preflight two-run delta); 1056 `asyncio.run`→`async def`. Gates green: **770 backend** @ 87.40% / 0 ruff / 0 format / 0 mypy / 0 bandit; **320 frontend** vitest / 0 eslint / `tsc -b` + `vite build` clean; api-types-sync ok. Net +1 backend test (1055b); all else count-neutral. Open FP31 remainder: 1047/1048/1049/1052/1053.) **Prior:** 2026-06-10 (**test-audit 2026-05-20 coverage/reliability bundle** — closed mame-curator-1067 (flag-disabled `=False` keeps-them locks for the 4 remaining togglable drop predicates + explicit zip-slip test), 1068 (deterministic B7 allowlist-parent assertion + catch-all-respx no-HTTP proof for the two `prepare_is_noop` tests), 1069 (7 read-only api/conftest Path fixtures → `scope="session"`), 1070 (prose `# noqa: E402` reworded — `ruff check --no-cache` clean). +2 pytest decls (DS05 pin 608→610); 769 backend green @ 87.51%; ruff/format/mypy/bandit clean. Zip-slip + no-HTTP locks mutation-verified.) **Prior:** 2026-05-20 (**test-audit sweep** — full `/test-audit` across all 18 dimensions / all severities / 167 files (113 backend + 54 frontend = 50 vitest + 4 Playwright) → ~33 raw findings → 14 fixed inline (all count-neutral: 5 backend assertion/correctness, 2 slow-marker, 1 parametrize, 5 frontend correctness/reliability, + **1 pre-existing red test root-caused** — `test_arch_diagrams.py` lacked the `frontend/` exception its README sibling carried; `main` was red at HEAD `7ff03ec` from the 2026-05-18 cold-eyes docs sweep). 6 deferred clusters mame-curator-1065..1070; many lower nits re-confirmed already-open FP31 items (1046/1048/1050/1052/1054c/1055a,b,i) and were not re-filed. No new allowlist entry — the `@pytest.mark.asyncio` "FP" turned out to be the existing mame-curator-1050 cleanup. Test-count pin unchanged (611 backend / 305 frontend — every fix count-neutral). Gates green: 761 backend / 0 ruff / 0 mypy / 0 bandit; 320 frontend vitest / 0 eslint. Pre-existing `tsc` errors in `src/test/handlers.ts` + `renderWithClient.tsx` left untouched.) |
| **Next gate** | Chunk 9 — Readiness API (`GET /api/media/sources` + `PUT /api/media/sources/{name}/secret`; new `SourceReadinessRow`/`SourceReadiness`/`SourceSecret` schemas). Open verification item #5 (secret-route auth: token-gate vs loopback-trust) needs a decision before/at chunk 9. Then 10 (Settings→Media UI) → 11 (AboutSection). MobyGames cover-fetch stays deferred to mame-curator-1079. |
| **Convergence checkpoint** | 5 (pause and check in with user after this many fix-passes in a row) |
| **Debt-sweep phase threshold** | 5 (auto-prompt for `/debt-sweep` after this many phases without one) |
| **Last debt sweep** | 2026-05-01 (scope `P02-complete..HEAD`; 4 rounds of cold-eyes spec review converged on 20 actionable sub-bullets — C9 retained as footnoted stale entry, D3 added during review; folded into DS01) |
| **Repo visibility** | PUBLIC (cached 2026-04-30 via `gh repo view --json visibility`) |

### Step progress

While an item is active, Claude marks the current step 🚧;
completed steps flip to ✅. Resets to all ⬜ when a new item
becomes active.

**DS03 — Dependency freshness sweep (closed 2026-05-16)**

All 9 steps ✅. 8 clusters (A: Python pins; B: frontend pins;
C: GitHub Actions GITLEAKS_VERSION; D: pre-commit revs + coupling
+ Step 3 docs-tests; E: engines.node 20→24 LTS; F: transitive
refresh + opportunistic mypy 1→2; G: new frontend-lint-types-test
CI job; H: pnpm→npm spec corrections) + R1 closing-review fold-in
(7 corrections across 6 files) across 10 commits
(`1916cd7..f9be074`). Journal at `docs/journal/DS03.md`. Tag
`DS03-complete`. Cross-pin coupling test `test_dep_pin_coupling.py`
fires on every commit since `02a80e4` (Cluster D).

**FP28 — Tier 2 review fold-in: hardening + correctness (closed 2026-05-15)**

All 9 steps ✅. 14 contract sub-fixes + 3 closing-review corrections shipped across 6 commits (`cb35f26..72505d8`). Journal at `docs/journal/FP28.md`. Tag `FP28-complete`. Two follow-ups deferred to DS02 / later hardening pass (C2-sibling negative-cache headers; A2 lockfile timeout cap).

**DS05 — Test-file seam-split sweep (closed 2026-05-16)**

All 9 steps ✅. 4 clusters (A: SettingsPage 742→336+301+104;
B: test_runner 526→240+277; C: test_dat 447→112+121+255;
D: pre-commit wiring for the DS02 R2 permanent fix) + R1
closing-review fold-in across 7 commits (`738b418..d9c6817`).
Journal at `docs/journal/DS05.md`. Tag `DS05-complete`. New
`check-api-types-sync` local pre-commit hook fires on every
commit since `aa2ded0`.

**DS02 — Tier 3 structural debt sweep (closed 2026-05-15)**

All 9 steps ✅. 18 sub-bullets across 7 clusters (A1-A5 + B1-B2 +
C1-C4 + D1 + E1-E2 + F1-F2 + G1-G2) + 3 closing-review corrections
shipped across 4 commits (`c0a6ad6..eb000e4`) + R2 post-close
hot-fix `ccb90a6` (api-type-sync gate missed A5 sibling modules).
Journal at `docs/journal/DS02.md`. Tag `DS02-complete`. Three
exceptions acknowledged in spec § "Deliberately not in scope":
`copy/runner.py` 540 > 500, `strings_internal.ts` 646 > 500,
`frontend/src/api/schemas.ts` 591 > 500 (R1c spec amendment).

**FP27 — Tier 1 review fold-in: zombie features + data integrity (closed 2026-05-14)**

- ✅ Step 1 — spec at `docs/specs/FP27.md`; cold-eyes review loop ran 5
  passes (29 findings loop 1 → 0 at loop 5).
- ✅ Step 2 — plan inlined in spec body (FP05/07/08 precedent).
- ✅ Step 3 — tests-first. 19 new + 1 modified tests across
  `tests/filter/`, `tests/copy/`, `tests/parser/`, `tests/api/`,
  `tests/cli/`, `tests/docs/` (new), `tests/media/`, plus
  `frontend/src/**/__tests__/`. RED batched into per-tier
  `@pytest.mark.xfail(strict=True)` markers; each batch's
  implementation drops its own xfail.
- ✅ Step 4 — implementation across 4 commits + cluster R1 fold-in:
  T1a `cfe612c` (A1/A2/A7/A9/C1/C2), T1b `65615fb` (A3),
  T1c `4c54be4` (frontend A4-A8), T2 `2d9078e` (B1-B5),
  R1 `976b119` (closing-review cluster).
- ✅ Step 5/6 — closing `/audit` already green from pre-commit
  pipeline; closing `/indie-review` ran 2 lanes (backend + frontend)
  on the FP27 surface. Surfaced 2 HIGH on the changeset itself
  (downloads.py OSError gap; frontend `/` preventDefault hoist) +
  2 minor regression-lock tightening — all folded as Cluster R1.
- ✅ Step 7 — Cluster R1 fold-in (`976b119`): 4 sub-fixes on the
  FP27 surface itself (R1a downloads.py OSError; R1b frontend `/`
  preventDefault; R1c drive-by inner `import shutil`; R1d
  EscOverlayBehavior plain-Dialog regression-lock).
- ✅ Step 8 — final five-gate green: 551 backend / 0 ruff /
  0 ruff-format / 0 mypy / 0 bandit; 279 frontend / 0 eslint /
  0 tsc.
- ✅ Step 9 — closed (tag `FP27-complete` annotated at this commit).

**FP26 — FP25 closing-review fold-in + UX e2e walkthroughs (closed 2026-05-11)**

- ✅ Step 1 — spec (sub-bullets A–U in `ROADMAP.md § FP26`)
- ✅ Step 2 — plan (per-sub-bullet TDD)
- ✅ Step 3 — tests-first (every Tier 1 fix landed with a failing test)
- ✅ Step 4 — implementation (Tier 3 Playwright `dddae88`; V `8b70f34`;
  Tier 1 batch `a54dd10`; Tier 2 batch `1653737`)
- ✅ Step 5/6 — closed on five-gate green per FP10's "recursive on
  fix-pass returns zero" lesson + the explicit user-elected
  precedent from FP11. No further audit dispatch warranted.
- ✅ Step 7 — n/a (no findings, no fix-pass)
- ✅ Step 8 — final five-gate green: 504 backend / 0 ruff /
  0 ruff-format / 0 mypy / 0 bandit (all severities); 273 frontend /
  0 eslint / 0 tsc; 9 e2e green.
- ✅ Step 9 — closed (tag `FP26-complete` annotated at this commit).
  Cascade re-run of `/close-phase FP25` + `/close-phase FP20`
  follows in the same session — see Phase history table.

**FP25 — parent phase (closed 2026-05-11):**
Sub-bullets A–K shipped across 8 commits (`d617cd6..19cc9b2`).
Closing `/audit` clean; 4-lane `/indie-review` surfaced findings
folded into FP26; FP26 closed clean → FP25 has zero remaining
findings → clean close at this SHA. Tag `FP25-complete` annotated.

**FP20 — grandparent phase (closed 2026-05-11):**
12 sub-bullets A–L shipped 2026-05-11 (`c3ee50c..d819181`). Closing
`/audit` + 5-lane `/indie-review` produced FP25; FP25 closed clean →
FP20 has zero remaining findings → clean close at this SHA. Tag
`FP20-complete` annotated.

**FP20 — parent phase (Step 4 complete, Step 5/6 ran, awaiting FP25):**
Sub-bullets A–L all landed across 14 commits (`c3ee50c..d819181`).
Closing `/audit` + `/indie-review` ran cleanly — 18 findings (1 Tier 1
spec-violation, 7 Tier 2 hardening, 10 Tier 3 polish) folded into FP25.
Phase remains 🚧 until FP25 closes.

### Active item details

**FP25 — FP20 closing-review fold-in.** 11 sub-bullets sourced from the
5-lane `/indie-review` plus semgrep+gitleaks on the FP20 surface:

- **A** (Tier 1) — wire `world_lock` on `curate.py` (6 routes) +
  `games.py:put_notes` per P04 spec §104-115
- **B** activity-log durability + typed errors (fsync, short-write,
  `ActivityLogError`)
- **C** recyclebin manifest atomicity envelope
- **D** `_atomic.py` perm-mode parity (`0o644` not `0o600`)
- **E** concurrent-write property test for activity log
- **F** manifest-atomicity test for recyclebin (monkeypatched failure)
- **G** `toastApiError` dedup window for cold-start outages
- **H** `LibraryErrorPanel` `disabled={isFetching}` on Retry
- **I** DOMPurify hooks scope guard / scoped instance
- **J** strengthen data-URL test (deterministic outcome)
- **K** 12-item doc + comment cleanup batch (see ROADMAP § FP25 for the
  enumeration)

**FP20 — parent (12/12 sub-bullets shipped — see ROADMAP § FP20).**
Sub-bullets A–F backend; G–L frontend. All landed across 14 commits
on 2026-05-11. Closing `/audit` + `/indie-review` findings funnel into
FP25 above.

(Prior step-progress blocks for FP12 / FP11 / P06 — preserved
across earlier sessions as audit context — were retired during
the P15 close. Their commit-level history lives in
`docs/journal/` and the phase-history table below.)

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
| FP19 | — | ✅ | 2026-05-04 | 2026-05-04 | Launch in RetroArch — paths.retroarch config + POST /api/games/{name}/launch + Launch button in alternatives drawer; v1.2.0 |
| FP23 | — | ✅ | 2026-05-07 | 2026-05-07 | Parent/clone collapse listxml fix — diagnosed during P15 brainstorm; user's `paths.listxml: null` made `cloneof_map={}` so every machine became its own winner (21,049 → 10,591 after fix). Installed MAME 0.287, generated listxml; new `ListxmlBanner` surfaces missing-listxml state for future users; new `useDryRun` hook + DryRunModal wired (onCopy stays no-op, full Copy lifecycle scoped to P15). |
| FP24 | — | ✅ | 2026-05-08 | 2026-05-08 | P15 closing-review fold-in — all Tier 1 (A–G + Q + S, 7 commits) + Tier 2 (H–Z, 3 commits) + Tier 3 (AA–LL, 3 commits) closed across 13 commits. Plus HelpRoute setState-in-effect ride-along. 455 backend / 240 frontend tests green / coverage 86.93%. |
| P15 | — | ✅ | 2026-05-08 | 2026-05-08 | Cart-first selection + curated featured tiles + live Copy — B1–B5 backend + F1–F14 frontend + Playwright cart-flow shipped 2026-05-07 to 2026-05-08; closing `/audit` + 8-lane `/indie-review` folded into FP24 (13 commits). `P15-complete` and `FP24-complete` tag distinct SHAs (FP24 closed first, then P15 close-flip in its own docs commit). |
| FP22 | — | ✅ | 2026-05-08 | 2026-05-08 | Launch button gates on RetroArch config — A `/api/setup/check` returns `retroarch_configured`, B AlternativesDrawer disables the button + inline hint to /settings?tab=paths when the flag is anything other than strictly true, C SettingsPage Setup banner surfaces the same line. D deferred to FP21 § J (typed RetroArchNotConfiguredError will carry the byCode-mapping needed for friendly toast). 458 backend / 246 frontend tests green / coverage 87.00%. |
| FP20 | — | ✅ | 2026-05-11 | 2026-05-11 | Indie-review Tier 1 — security + data-loss fixes (parser XXE/zip-bomb, copy non-atomic writes, API mutation lock, sandbox stale paths, help-dir symlink, download URL scheme, useApiQuery silent-failure, GameCard aria-label clobber, LibraryPage error-panel gap, SnapshotsTab restore-error, FsBrowser Esc-closes-everything, HelpPage DOMPurify config). 12 sub-bullets A–L shipped 14 commits; closing audit produced FP25 → FP26 cascade; all closed clean 2026-05-11. |
| FP25 | — | ✅ | 2026-05-11 | 2026-05-11 | FP20 closing-review fold-in — `world_lock` on remaining 7 mutation routes (A); activity-log durability + typed ActivityLogError (B); recyclebin manifest atomicity envelope (C); 0o644 perm-mode parity (D); concurrent-append property test (E); manifest-atomicity test (F); toastApiError 1.5s dedup window (G); LibraryErrorPanel Retry isFetching gate (H); HelpPage scoped DOMPurify (I); deterministic data-URL test (J); 12-item doc + comment cleanup (K). 11 sub-bullets shipped 8 commits; closing audit produced FP26; closed clean at this SHA. |
| FP26 | — | ✅ | 2026-05-11 | 2026-05-11 | FP25 closing-review fold-in + UX e2e walkthroughs — Tier 1 test sufficiency (A: world_lock asserted_set_world; B: mkdir envelope; C: vacuous FP25-F asserts; D: macOS-fork skip; V: sticky LibraryErrorPanel during refetch — surfaced by user's Playwright walkthrough direction, NOT by unit tests); Tier 2 doc/test polish (E P04 _deactivate spec; F parent-dir fsync; G copy/spec.md drift; I queryClient reset; J/K apiErrorToast docblock; L drop FP25-K(12) no-op; M allowlist-004 refresh; N tracking-lock duck-type note; P RecycleError.recycled_orphan); Tier 3 Playwright UX walkthroughs (Q/R/S/T) + LOW polish (U). 21 sub-bullets shipped 5 commits; closed on five-gate green per FP11 precedent. **Workflow lesson:** e2e walkthroughs catch host-conditional unmount bugs that unit tests miss when the test renders the child directly. |
| FP21 | — | ✅ | 2026-05-11 | 2026-05-11 | `/indie-review` Tier 2 hardening sweep — 20 sub-bullets across filter (A picker decisive / B sessions typed-error spec / C drops strict-identity), copy (D recyclebin per-file manifest write-first / E preflight BIOS chain / F purge_recycle manifest-keyed / G executor TOCTOU), api (H FileResponse / I shutdown logging / J typed launch errors + FP22-D byCode / K SSE register-before-replay snapshot / L non-reachable analysis + guard / M snapshot LRU / N AppConfigPatch + deep_merge depth cap / O import sentinel), downloads (P streaming + 100 MB cap), run.sh (Q curl tls), frontend (R bake toastApiError / S useKeyboard ref-based / T LibraryGrid grid semantics). Shipped 5 commits; closed on five-gate green per FP10/FP11 precedent (narrow-scope per-bullet TDD made multi-agent closing audit low-yield). **Workflow lesson:** write-first ordering for atomicity envelopes is simpler than move-then-rollback and produces stronger source-intact invariants under failure. |
| P09 | Phase 9 | 📋 | — | — | Polish + v1.0.0 release |
| P10 | — | 📋 | — | — | Media coverage expansion (progettoSnaps + ArcadeDB + Wikipedia + Mobygames; post-v1 by default — § A promotable ahead of P07 on user say-so) |
| P11 | — | 📋 | — | — | Contribute missing thumbnails to libretro-thumbnails (post-v1; depends on P05 ✅, composes with P10) |
| P12 | — | 📋 | — | — | In-app self-update + INI diff-preview UI (post-v1; deferred from P07 2026-05-04 to keep v1 budget tight; depends on P07 / P09) |
| P15 | — | 📋 | — | — | Cart and curated library — spec drafted 2026-05-07 (`docs/superpowers/specs/2026-05-07-cart-and-curated-library-design.md`); 7-round cold-eyes-review APPROVE; awaiting writing-plans handoff. |

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

### 2026-07-01 — P10 chunk 6: MobyGames key-handling half (mame-curator-1005; deferred → 1079)

User said "continue with P10." Session-orient showed P10 Step 3, next
chunk 6 (MobyGames). Read the spec: chunk 6 is genuinely gated on a real
MobyGames API key — the cover-fetch needs a 200 response to verify the
field path, and there's no key on this machine (no env var, no
`data/secrets/`, no anonymous API access). The spec even flags its own
`cover_url` field name as unverified. Per global rules 8 + 13 (surface
the unavoidable assumption, don't guess a field path), I paused and asked
the user with `AskUserQuestion`. They chose **"key-handling now, fetch
later."**

**Built (tests-first, RED→GREEN):** `MobyGamesSource` in a NEW
`src/mame_curator/media/mobygames.py` —
- Key resolution: `MOBYGAMES_API_KEY` env var first, then a mode-0600
  `<secrets_dir>/mobygames.key` dotfile (a group/other-readable file is
  rejected with a WARNING; treated as no key).
- Missing key → `disabled_reason` + exactly one WARNING at construction.
- `prepare` validates the key against the lookup endpoint: 401/403 →
  flip the injected process-wide `SourceDisabledFlag` (one WARNING) +
  self-disable; 429 → `MediaRateLimited`; 404 → no candidate; 200 →
  **deferred** (cover parse not yet implemented; `url_for` → None);
  network/other-non-200 → `MediaFetchError` with the key redacted.

**Three deliberate divergences from the spec (all documented inline in
docs/specs/P10.md § "4. MobyGames" → "Chunk 6 implementation notes"):**

1. **`SourceDisabledFlag` holder, not a bare `app.state` string.** `media/`
   is HTTP-agnostic (no `api/` import) and `prepare` only gets an httpx
   client — it can't write back through a bare string. So the process-wide
   reason rides an injected mutable holder, exactly like the token buckets.
2. **`prepare` does its own `client.get`, not `fetch_text_with_cache`.**
   That helper flattens every non-200/404 into one generic error
   *embedding the full URL* — fatal here (must tell 401 from 429 apart;
   the API key rides in the query string and must never reach a log).
   `_redact` masks the key in every message.
3. **Own module, not `sources.py`.** Adding it inline pushed `sources.py`
   to 596 > the 500-line hard cap; extracted to `mobygames.py` (in-lane —
   my change caused the breach). Pre-empts the chunk-7 split.

**Deferred → [mame-curator-1079]:** the 200-path cover-URL parse +
JSON-body caching (needs a real-key fixture). Locked by
`test_mobygames_source_200_does_not_populate_cover_yet` (the delete-point).
MobyGames is last in the default fallback order → zero user-visible
regression while keyless.

**Wiring:** schema field `media.mobygames_rate_limit_per_min` (default 5)
+ `mobygames_limiter` / `mobygames_disabled` on `app.state` (lifespan).
Frontend: mirrored the field in `types.ts`, Zod `schemas.ts`, and 2 test
fixtures (the api-types-sync gate + tsc caught all three). 17 new pytest
decls → DS05 pin 613→628.

**Gates green:** 797 backend @ 87.73% (media/ ≈95%, mobygames.py 96%) /
0 ruff / 0 format / 0 mypy / 0 bandit; api-types-sync ok; frontend tsc 0 /
eslint 0 / vitest 323 / build clean.

**Next:** chunk 7 (registry + orchestrator) — the convergence checkpoint;
pause for user check-in before chunks 8–11, and run `/cold-eyes` on the
chunk-6 divergences then (per the spec's risk-register clause).

### 2026-06-30 — Cleanup/debt bundle (mame-curator-1077 + 1078)

User said "continue with the next bundle of similar roadmap items" +
"use Ants MCP where appropriate." `roadmap_query(section="cleanup-debt")`
showed three open items: 1076 (chore/ci — macOS-26 runner pin review),
1077 (refactor/frontend — split `LibraryPage.tsx`), 1078 (fix/frontend —
Snapshots review-state caveat). The natural bundle per
`feedback_bundle_similar_items` (same lane) was **1077 + 1078** — both
`frontend`, both surfaced 2026-06-30 during the P14 docs work. 1076 is a
different lane (ci) and a date-gated "review" task; left for its own pass.
P10 (the 🚧 active phase) is blocked on a real MOBYGAMES_API_KEY for
chunk 6, so the cleanup bundle was the actionable next unit.

**Shipped — 2 commits:**

- **3b0321b** `refactor(frontend): split LibraryPage under cap +
  Snapshots review-state caveat` — the bundle.
- **d82c491** `test(docs): bump vitest declaration pin 304→306` — CI
  follow-up (see lesson below).

**1078 (fix):** added `settings.snapshotsStateExclusionNote` (text per
P14 spec §875) + rendered it as a caption in `SnapshotsTab.tsx` (both
empty + populated states). Used the **flat** `snapshotsStateExclusionNote`
key to match the existing `snapshotsXxx` convention, NOT the spec's
dotted `settings.snapshots.stateExclusionNote` (global rule 11 — match
the file's style). +2 vitest cases.

**1077 (refactor):** split `LibraryPage.tsx` 579→314 lines. Canonical
cap resolved up front: `coding-standards.md` §2 (= authoritative under
§15 precedence) says frontend **components** are hard-capped at 350; the
bullet's "350 vs 500" doubt was DS02's working number for data files
(`strings_internal.ts` 676, `schemas.ts` 591 are acknowledged
exceptions), not the component cap. Extraction seam chosen to KEEP the
JSX in the page: both LibraryPage tests assert against `?raw` source
text (`LibraryPage_error_boundary` checks `<AlternativesDrawer>` /
`<CopyModal>` are wrapped in `<ErrorBoundary>`; `landmark_labels` checks
the `FiltersSidebar` aside aria-label). So I extracted only the
non-render logic → new `pages/useLibraryController.ts` (318 lines, a
controller hook returning ~37 members) + pure helpers →
`pages/libraryPageHelpers.ts` (61 lines: DEFAULT_FILTERS, walkthrough
pref, fetchTileCount). Behaviour-preserving; 323 frontend tests green.

**Mid-session decisions:**

- **No new failing test for the refactor (1077).** Per Karpathy
  surgical-changes + the project's "TDD for non-trivial *logic*" rule, a
  pure code-motion refactor adds no logic — the existing LibraryPage
  source-text + full vitest suite ARE the regression net. Verified by
  keeping all 50 frontend test files green.
- **Single bundle commit for both items.** CHANGELOG (one feature-style
  subsection covering both), ROADMAP (one `flip_batch`), and the
  `frontend/dist` rebuild all span both items; splitting source across
  two commits while those are shared would be messier than one honest
  bundle commit. Matches the P10 chunks-4+5 bundle precedent.
- **CHANGELOG hand-edited, not via `changelog_log`.** The tool's
  dry_run correctly flagged that `[Unreleased]` uses feature-grouped
  `###` subsections (not flat `### Category` blocks) but would still
  insert a flat `### Fixed` — inconsistent with the file's style. Filed
  as a minor Ants-MCP observation; hand-added a matching subsection.

**Workflow lesson — the local frontend gate has a backend-enforced
blind spot:**

- CI went **red** on the first push: `tests/docs/test_ds05_test_count_stable.py::test_vitest_declaration_count_stable` (a *pytest* test that
  counts frontend `it()` declarations) expected 304, found 306. The
  local frontend gate (vitest/eslint/tsc/build) does NOT run pytest, so
  +2 vitest tests passed locally and only the Python CI matrix caught
  the stale pin. **My pre-push grep for the pin used the wrong number
  ("320/321" from a prior journal) and missed the real constant (304).**
  Fix: `d82c491` bumped 304→306 with rationale. Lesson saved: when
  adding/removing frontend `it()`/`test()` declarations, the count pin
  to bump lives in `tests/docs/test_ds05_test_count_stable.py`
  (`EXPECTED_VITEST_DECLARATIONS`) — a *backend* test — and must be
  updated in the same change; grep that file by name, not by a
  remembered number. Final CI: all 8 jobs green.

- **Ants MCP this session:** `session_orient` (state + index + roadmap
  in one call), `roadmap_query` (section read), `read_region` (§2 cap
  lookup), `roadmap_log op:flip_batch` (both bullets closed in one
  call), `feedback_query`/`feedback_log` (read tracking + file new
  findings). One new friction filed: `roadmap_query`'s `status` filter
  rejects `"planned"` (roadmap_log's own status vocabulary) with no
  valid-values hint.

### 2026-05-18 — P10 chunks 4 + 5 bundle (ArcadeDB + Wikipedia-image)

User said "continue with the next bundle of similar roadmap items"
and "use Ants MCP where appropriate." `roadmap_query(status="active")`
returned 4 bullets — P10 🚧 (in-progress) plus three post-v1 items
(mame-curator-1040 test-audit refactor, FP30 auto-save indicator,
P15 UI polish). The natural bundle inside the in-progress P10 was
chunks 4 (ArcadeDBSource) + 5 (WikipediaImageSource) — both add a
new `*Source` class with a per-source `TokenBucket`, both feed the
chunk-7 orchestrator, both share the same lanes (`media`, `tests`)
and same Kind (`implement`). Per memory `feedback_bundle_similar_items`:
same kind + same lanes ⇒ bundle.

**Shipped — 1 commit:**

- **2c1f76f** `feat(media): P10 chunks 4 + 5 bundle — ArcadeDBSource
  + WikipediaImageSource` — both source classes land together; same
  shape (new class + lifespan limiter + re-export), no inter-chunk
  dependency. Diverges from the 3a/3b split (those committed
  separately because 3b consumed 3a's CLI output); chunks 4 and 5
  are mutually independent so a single bundle commit reads better
  in `git log`.

**Chunk 4 — ArcadeDBSource:**

- Two-step JSON lookup via `fetch_text_with_cache` against
  `http://adb.arcadeitalia.net/service_scraper.php?ajax=query_mame&game_name={name}`.
  Lifespan client's `follow_redirects=True` (FP10 A1) handles the
  301 → HTTPS transparently; cache key is SHA-256 of the original
  http:// URL so cache slot is deterministic.
- Parse-before-trust: `json.JSONDecodeError` unlinks the bad cache
  slot via `cache_path_for(url, cache_dir).unlink(missing_ok=True)`
  and raises `MediaFetchError` chained from the JSONDecodeError —
  transient bad upstream doesn't permanently disable the source
  for this machine; next request re-fetches.
- Empty `result` array → uniform negative-cache shape (
  `_url_cache[name]` stays absent; `url_for` returns None) so the
  registry's "no hit" branch in chunk 7 doesn't need to
  distinguish "404 from upstream" vs "200 with empty array".
- New `MediaConfig.arcadedb_rate_limit_per_min: int = 30` field;
  mirrored in `frontend/src/api/types.ts` + `schemas.ts` + two
  test fixtures so the `check-api-types-sync` pre-commit hook
  (DS05 Cluster D) stays green.

**Chunk 5 — WikipediaImageSource:**

- `kinds = frozenset({"boxart"})` only. Wikipedia REST summary's
  only image field with a documented location is `thumbnail.source`
  (the infobox image); title and snap aren't reliably present.
  Silently degrading those kinds to the infobox image would let
  the wrong-shape image win over a legit downstream candidate —
  the frozenset prevents this at registry-build time.
- `license_compatible = False` conservatively. Wikipedia hosts
  mixed-license images; P10 only displays, never redistributes.
  P11's contribute-back flow would need per-image inspection.
- Title canonicalisation: `re.sub(r"\s*\([^)]*\)\s*$", "", desc).strip()`
  strips trailing parenthesised qualifier — "Pac-Man (Midway)"
  → "Pac-Man". No fuzzy match, no second attempt: the source's
  value is the head of the catalog, not full coverage. The
  canonicalisation test pins this with two respx routes (one for
  the canonicalised form, one for the raw form) + a
  call-count assert.
- New `_build_user_agent()` helper in `media/__init__.py`. Returns
  `mame-curator/{__version__} (+https://github.com/milnet01/mame-curator)`
  per Wikipedia's API:Etiquette. Underscore-prefixed because it's
  an implementation helper, not a stable consumer API — callers
  let the lifespan client own the header.
- Hardcoded 60-req/min courtesy cap (no config field; spec § "3.
  Wikipedia (image) Rate limit" doesn't request one).

**Mid-session decisions:**

- **Single bundled commit, not 4-then-5.** The 3a/3b precedent
  split commits because 3b's `ProgettoSnapsSource` consumed the
  on-disk pack 3a's CLI wrote — the diff hunks naturally split
  along that boundary. Chunks 4 and 5 are mutually independent
  (both feed chunk-7's registry but neither feeds the other), so
  one bundle commit reads cleanly.
- **`MediaConfig` field add fanout caught early.** Adding
  `arcadedb_rate_limit_per_min` triggered the `check-api-types-sync`
  hook's parity rule — required mirroring in `types.ts` + Zod
  schema + two pre-existing test fixtures (`no-checkbox-for-prefs`
  + `_settingsPageFixtures`). Caught at the local `tsc` step
  before commit; would otherwise have failed CI on the
  api-types-sync gate.
- **Pre-existing `tsc` errors in `src/test/handlers.ts` +
  `renderWithClient.tsx` left alone.** Stashed-then-rebased to
  confirm they exist on clean `main` (3 errors: TS2345 `unknown`-
  to-`JsonBodyType`, two TS2503 `Cannot find namespace 'JSX'`).
  Global rule 11 (stay in your lane) — these are test
  infrastructure, not the code I'm shipping; surfacing them in
  the journal instead of drive-by fixing. The frontend CI gate
  doesn't run `tsc -b` directly (only `eslint` + `vitest` per
  the new DS03 Cluster G CI job); the errors don't gate this
  bundle.
- **Used Ants MCP for state-recovery, not implementation.**
  `roadmap_query(status="active")` for the queue read,
  `git_state(op=status/log)` for VCS state — saved ~12 K tokens
  vs equivalent Bash. Tool-side feedback addendum logged to
  `MAME_Curator_Ants_MCP_Feedback.md` per user request.

**Workflow lessons:**

- **"Same kind + same lanes" memory heuristic still applies
  inside an in-progress phase, but the chunk dependency graph
  is the tiebreaker.** P10's chunk graph (spec § "Chunk
  dependency graph") makes 4 and 5 mutually independent — both
  add a source class, both fan into chunk-7. Bundling them
  matches the natural unit. The 3a→3b serial pair was the
  exception (because 3b *consumed* 3a's output); 4||5 is the
  parallel-bundle rule.
- **Prior MCP feedback verification pass returns the
  fulfillment dividend.** Three of the six items from the
  2026-05-18 evening addendum landed: ANTS-1520 (`caller_cwd`
  required everywhere), ANTS-1521 (`headline_oneline` field),
  ANTS-1522 (`git_state` `files[]` unified envelope). The
  session used all three transparently. The MCP-side CC
  session evidently shipped the relevant fixes in the
  ~24 h since the feedback was filed — short feedback loop.

### 2026-05-18 — P10 chunk 3 bundle (3a + 3b — progettoSnaps pair)

User said "continue with the next bundle of similar roadmap items"
and "use Ants MCP where appropriate." `roadmap_query(status="active")`
returned four bullets — P10 in-progress with chunks queued, plus three
post-P10 items (mame-curator-1040 test-audit FP01, FP30, P15). The
natural bundle was the next pair inside the in-progress P10 — chunks
3a + 3b are the only serial pair in the dependency graph (everything
else 3b-onwards fans out), and together they ship end-to-end
progettoSnaps support: 3a downloads the pack, 3b consumes it from
disk.

**Mid-bundle drift surfaced and re-scoped:**

Pre-impl prep for chunk 3a probed the live progettoSnaps site to pin
the pack-URL discovery method (the last unresolved Open Verification
Item). The probe surfaced a second pivot beyond what commit a25cadc
caught: Flyers, Marquees, VideoSnaps are `toolbar_item_disabled` in
the site navigation (no href; legacy-pulled); Titles isn't in the
toolbar at all; the historic `pS_titles_fullset_287.zip` filename
shows up on the Snapshots index but is sized "(000Mb)" — placeholder
for an unmaintained pack; Cabinets are hosted externally on terabox
(not CLI-fetchable). Only `pS_snap_fullset_<NNN>.zip` is actively
published per MAME release.

Stopped before writing code (App-Build hard rule #1: never silently
drift) and surfaced three options to the user. User picked (A): shrink
progettoSnaps to `kinds = frozenset({"snap"})`. The chain's kind
filter (chunk 7 `MediaSourceRegistry`) routes boxart + title to
ArcadeDB / Wikipedia / MobyGames naturally; no special-cases needed.

**Shipped — 3 commits:**

- **ac010fe** `feat(media): P10 step 1 amendment — progettoSnaps
  shrinks to snap kind (upstream pivot)` — surgical edits to § 1
  progettoSnaps (`kinds` shrinks, local layout collapses to
  `data/snaps/snap/`, estimate halves), § refresh-snaps CLI (drops
  `--kinds`, pins pack URL + discovery, adds `--url` override,
  600 MB body cap), § Source-layer tests, § Chunk table 3a/3b, §
  Open verification items (item 4 marked resolved). Pre-impl-prep
  status note added.

- **487b30e** `feat(media): P10 chunk 3a — refresh-snaps CLI +
  snap-pack downloader` — new `mame_curator.updates.snaps`
  (`INDEX_URL`, `PACK_URL_PATTERN`, `SNAP_PACK_MAX_BYTES`,
  `SnapsRefreshReport`, `discover_snap_pack_url`, `refresh_snaps`),
  new `cli/commands/refresh_snaps.py` handler (FP28-D3 import-guard
  pattern; rich-console output), `cli/__init__.py` subparser
  registration with `--dest --url --force`. Disk-space gate (HEAD
  probe + `shutil.disk_usage`, refuses if free < 2× content-length);
  ZIP extraction with flat-layout guard (subdirectory entries
  ignored) and `.png` filter; force-or-skip collision handling. 9
  tests under `tests/updates/test_snaps.py` including the
  `PACK_URL_PATTERN` regression-lock.

- **b43d450** `feat(media): P10 chunk 3b — ProgettoSnapsSource
  (file:// model, snap kind only)` — `ProgettoSnapsSource` class
  added to `media/sources.py` + re-exported from `media/__init__.py`.
  Per-instance existence cache (`_present` + `_missing` sets); URL
  via `Path.as_uri()` resolved to absolute path so the chunk-7
  orchestrator file:// short-circuit works regardless of CWD;
  `disabled_reason` set at construction if dir absent or empty
  (registry filter drops disabled sources before any
  prepare/url_for call). 10 tests under `tests/media/test_sources.py`.

**Mid-session decisions:**

- **User said "use Ants MCP where appropriate"** — routed
  `roadmap_query(status="active")` for the queue read,
  `git_state(op=status/log)` for VCS state, and `session_memory`
  for cache surface. Cost was ~200 tokens vs ~12K for the
  equivalent Bash read of ROADMAP.md + git status + git log.
- **Followed precedent for spec amendment as standalone commit** —
  P10 step 1 had already been amended once (commit 5efd511), so
  the snap-only pivot landed as its own commit before any code.
  Keeps the spec-vs-code commit graph clean: each amendment is a
  surgical contract change reviewable in isolation.
- **HEAD-probe disk-space gate refactored to a `_mount_pack` test
  helper** — first run hit `AllMockedAssertionError` because the
  HEAD probe wasn't mocked. Added a 3-line helper that mounts both
  HEAD and GET routes at once; cleaner than per-test boilerplate.
- **`shutil.disk_usage` monkey-patched via the module object, not
  via the dotted-string path through `snaps_mod.shutil.disk_usage`** —
  the latter triggers mypy `attr-defined` (snaps.py has no `__all__`
  exporting `shutil`); patching the `shutil` module attribute
  directly is cleaner and effective the same way (since
  `snaps.shutil is shutil`).
- **Two test-count pin bumps in this bundle** (580 → 589 in chunk 3a,
  589 → 599 in chunk 3b). Per `docs/standards/testing.md` the pin
  enforces "tests added intentionally bump the constant in the same
  commit" — both bumps include a `# Bumped 2026-05-18 (P10 chunk
  Nx):` rationale line.

**Workflow lessons:**

- **"Next bundle of similar roadmap items" inside an in-progress
  phase = the next paired chunks in the dependency graph.** When an
  item is already 🚧 (here P10) with chunks queued, the bundle is
  the next chunks that ship together logically — not the *next
  planned roadmap item*. Memory's "same kind + same lanes"
  heuristic applies to the *planned queue*; for in-progress work
  the chunk graph wins. 3a→3b is the only serial pair in the P10
  graph (everything else is parallel), so the pair is the natural
  unit.
- **Live-probe Open Verification Items before assuming spec is
  current.** Commit a25cadc resolved 4 of 5 items but deferred the
  progettoSnaps pack-URL discovery "to chunk 3." That deferral is a
  trap if the implementer doesn't actually run the probe — the spec
  reads complete and the assumed contract looks shippable. The
  probe surfaced a substantive scope change that *would* have
  shipped silently otherwise (writing `flyers/<name>.png` paths
  that never resolve). Pattern: any pre-impl-prep item with status
  "Pending" or "deferred" must be probed before tests-first.
- **App-Build hard rule #1 (never silently drift) saves a rewrite
  cycle.** The cheap stop-and-ask cost ~5 minutes of probing + one
  AskUserQuestion round-trip. The avoided cost is the next session
  realising progettoSnaps's chain falls through silently for two
  of three kinds and needing to rip out three test files + amend
  the registry + amend the orchestrator short-circuit logic.

### 2026-05-16 — Docs bundle closed (mame-curator-1029 + 1030)

User said "continue with the next bundle of similar roadmap items"
followed by "use Ants MCP where appropriate." `roadmap_query` (active
filter) returned three queued bullets: P14 (large feature, single
item) and two `kind: doc` items deferred from P09 slim. The natural
"bundle of similar items" was the two doc bullets — paired and
closed together.

**Shipped:**

- `CONTRIBUTING.md` — top-level contributor guide covering local-dev
  quickstart, bug-report template, the local CI gate (backend five
  + frontend three), the TDD policy with per-module coverage floors,
  the per-feature `spec.md` requirement, Conventional Commits, a
  summary of the App-Build 9-step phase loop, and a "things this
  project deliberately does not do" section.
- `README.md` hero shot at the top + new `## Screenshots` 2×2 grid
  (alternatives drawer, filters tab, sessions panel, capture-recipe
  pointer). README's short Contributing stub now points at the new
  CONTRIBUTING.md.
- `frontend/screenshots/` — dedicated Playwright config + capture
  spec independent of the e2e suite. Points at the real `config.yaml`
  so screenshots show real games / real cover art. Regen recipe:
  `cd frontend && npx playwright test --config screenshots/playwright.config.ts`.

**Mid-session decisions:**

- **User said "use Ants MCP where appropriate"** — switched the
  ROADMAP read from a Bash `grep ROADMAP.md` to
  `roadmap_query(status="active")`, which returned the same three
  bullets in ~150 tokens vs ~12K for the raw file.
- **User said "Let's try a Playwright session to capture the
  screenshots"** — created a dedicated config + spec rather than
  bolting onto `frontend/e2e/` (the e2e suite uses the 6-machine
  fixture DAT for determinism; the hero shot wants real data).
  Reused the existing `npm run preview` pattern + bumped Chromium
  to 1223 via `npx playwright install chromium` (one-time download).
- **Dropped settings-paths capture.** First pass produced
  `settings-paths.png` showing the user's real `/mnt/Games/...` and
  `/mnt/Emulators/Multi-System/RetroArch/...` paths. Removed the
  test rather than commit a personal-paths image to a public repo;
  README is fine without it. Decision noted in the spec body + the
  CHANGELOG Notes section so future re-captures don't quietly add
  it back.
- **`?tab=` URL param didn't switch the tab in the first pass.** The
  initial spec used `goto('/settings?tab=filters')` and asserted the
  tab trigger was *visible* (always true). The shot rendered the
  default Paths tab. Fix: navigate to `/settings` then click the
  target tab — robust against React Router hydration timing.

**Workflow lessons:**

- **"Bundle of similar items" = same kind + same lanes.** The natural
  pairing of mame-curator-1029 (`kind: doc / lanes: docs`) and
  mame-curator-1030 (`kind: doc / lanes: docs`) was obvious from the
  `roadmap_query` output without needing the long-form READMEs.
  Pattern saved: when the user asks for a bundle, sort the active
  queue by `kind` + `lanes` first.
- **`fullPage: false` + a `waitForTimeout` beat for lazy-loaded
  images.** The library hero shot needed ~3s after first card
  visibility for cover-art lazy-fetch to populate tiles — without
  the wait, every tile shows a blank placeholder. Pattern saved:
  for hero shots of UIs with async media, treat "first widget
  visible" as the start of capture wait, not the end.
- **Doc items skip `/audit` + `/indie-review`.** `kind: doc` items
  don't have a `spec.md` contract and don't ship code with security
  surface, so the multi-agent closing audit returns near-zero
  findings. Closed on five-gate green (frontend gates only; no
  backend code touched). No `<ID>-complete` tag since these are
  per-bullet docs, not phase IDs.

Frontend gates at close: 301 vitest passed (48 files) / 0 eslint /
0 tsc. Backend untouched, no Python files changed. No tag — these
are individual `mame-curator-NNNN` bullets, not phase IDs.

### 2026-05-11 — FP21 closed (Tier 2 hardening sweep, 20 sub-bullets)

User said "Can we continue with the oldest uncompleted work from the
roadmap please." That was FP21 per the queued order. Step 1
verification swept all 20 sub-bullets against current code in
parallel reads — found 19 real bugs + 1 (L) ruled non-reachable on
analysis. Step 3+4 ran per-bullet TDD across 5 themed batches.

**Mid-session events:**

- User asked "Does this project have a FUNDING.yml file?" — yes,
  `.github/FUNDING.yml` with `github: [milnet01]`. One-question
  detour; FP21 resumed.
- User requested a ROADMAP format refactor (adopt Ants_Terminal
  conventions). Folded into the queue as the next item AFTER FP21
  close, since the format refactor touches ~2800 lines and is
  conceptually separate from the fix-pass.

**Workflow lessons saved:**

- **Write-first beats move-then-rollback for atomicity.** FP25-C
  shipped a move-then-rollback envelope on recycle_file with
  defensive logic for rollback failure (the orphan-file case).
  FP21-D's swap-the-order ordering removes the worst case entirely:
  a write failure means the source never moved, so there's nothing
  to roll back. Pattern saved: when designing crash-safety
  envelopes, prefer "do the easily-reversible thing first" over
  "do the hard thing first with rollback."
- **`call_soon_threadsafe` FIFO from same thread.** This ruled out
  FP21-L (late-progress-after-terminal) as a reachable bug. The
  worker thread sequentially queues progress callbacks then the
  terminal callback; the loop processes them in queue order; no
  reorder possible. Pattern saved: when analysing concurrent
  dispatch races, check the producer-side ordering guarantees
  before assuming the consumer needs special handling.
- **Per-opponent first-decisive is observable.** FP21-A's snapshot
  delta touched every contested group in the smoke fixture — the
  prior over-reporting was actually being read by tests, not just
  spec-internal. Snapshot regeneration was the right move; the
  alternative (re-engineering tests around the new shape) would
  have left the spec promise unfulfilled.
- **Closing on per-bullet TDD instead of /close-phase audits.**
  For narrow-scope per-bullet fix-passes, the multi-agent closing
  audit returns near-zero findings (FP10 precedent confirmed
  twice). FP21 followed FP10/FP11's user-elected close-on-five-gate
  green path rather than dispatching /audit + /indie-review. The
  per-bullet TDD discipline plus the snapshot-regenerated picker
  test plus the 8 new regression tests in tests/api/test_fp21_fixes.py
  + tests/copy/test_recyclebin.py + tests/copy/test_preflight.py
  + tests/copy/test_executor.py provide tight coverage of the
  changed surface.

Tag: `FP21-complete` (annotated) at this commit.

### 2026-05-08 — FP22 closed (Launch button RetroArch gate)

User said "Let's continue with roadmap items from here: FP22
(RetroArch launch gate, smallest UX item) → FP20 / FP21 / DS02
(indie-review tiered fold-in) → DS03 (dependency freshness) →
P09 polish → post-v1 ladder." Picked up FP22 first per the
user-stated order.

**Sub-bullets shipped:**

- **A — `/api/setup/check` returns `retroarch_configured`.** New
  derived bool on `SetupCheck` (Pydantic `schemas_setup.py` +
  route `stubs.py:setup_check` + TS `types.ts` mirror + Zod
  `SetupCheckSchema`). Three new pytest cases under
  `tests/api/test_routes_stubs.py`: default-false (no retroarch
  paths in fixture), one-of-two-set (only `retroarch`), both-set
  → true. Helper `_write_config_with_retroarch` splices into the
  conftest YAML's `paths:` block before `\nserver:\n` so the
  Pydantic `extra="forbid"` on `FsConfig` doesn't reject mid-
  block insertions.
- **B — Launch button gates on flag.** `AlternativesDrawer.tsx`
  takes a new optional `retroarchConfigured?: boolean` prop. The
  button disables when the prop is anything other than strictly
  `true` (so `undefined` while the `useSetupCheck` query is
  loading also gates — no race-into-422). When the prop is
  `false`, an inline `<p role="status">` hint surfaces under the
  button: "Configure RetroArch in Settings → Paths to enable
  launching." with a react-router `<Link>` mid-sentence. Three
  new vitest cases (false / true / undefined) plus the existing
  six all rewrapped in `MemoryRouter` since the Link needs a
  router context. LibraryPage threads
  `setupCheck.data?.retroarch_configured` through.
- **C — Setup banner surfaces state.** `SettingsPage.tsx` Setup
  banner gains a third `<span>` after the INI status line:
  "RetroArch: configured." or "RetroArch: not configured — set
  paths.retroarch and paths.retroarch_core in the Paths tab to
  enable launching." Two new vitest cases.
- **D — friendly 422 toast copy.** **Deferred to FP21 § J.** The
  spec said "A/B/C ship without it" and adding the byCode entry
  here without the typed `RetroArchNotConfiguredError` from FP21
  would have left a dead string-table entry — strings.ts'
  contract is "no `byCode` entry is dead." Folded D into FP21 § J
  with explicit cross-references in ROADMAP.

**Workflow lessons saved:**

- **`<Link>` in components forces test-side router context.**
  Adding the inline hint with a `<Link to="/settings?tab=paths">`
  broke six existing AlternativesDrawer tests that didn't render
  inside any router. Wrapping every render in `MemoryRouter`
  (via a small `renderWithRouter` helper) was cheaper than
  switching to a plain `<a href>` and gave free `href` assertion
  via `expect(link).toHaveAttribute('href', ...)`. Same pattern
  ListxmlBanner tests already use.
- **"undefined while loading" is a meaningful gating state.** The
  drawer takes `retroarchConfigured?: boolean` — three values:
  `true` enables, `false` disables with hint, `undefined` (still
  loading) disables silently. A boolean default (`= true` or `=
  false`) loses the loading-vs-known distinction; the cost of
  carrying `undefined` is one explicit comparison
  (`!== true`) and is worth it because the alternative is a
  user racing the query into the same 422 the fix is meant to
  prevent.
- **Lane discipline beats dead code.** FP22-D could have shipped
  the byCode entry now (no CI gate enforces dead-code on
  strings.ts; `tools/check_error_codes_sync.py` doesn't exist
  yet) but the strings.ts comment-as-contract says no dead
  entries. Honouring the implicit contract by deferring D to
  the natural FP21 § J landing keeps the diff legible and
  prevents a string from sitting idle for several days.
  Pattern saved: when a sub-bullet says "Pairs with FP## § X"
  and the pair would land just one fix-pass later, defer rather
  than land both halves staggered.

Tests at close: 458 backend (1 skipped) / 246 frontend / coverage
87.00% / ruff + ruff format + mypy + bandit + types-sync clean /
eslint + tsc clean. `frontend/dist/` rebuilt.

Tag: `FP22-complete` (annotated) at this commit. Public repo →
push prompt deferred to user.

### 2026-05-08 — P15 closed (clean close at FP24's SHA)

User said "Let's continue with the next outstanding roadmap
item" picking up from yesterday's FP24 close. Status-header
recap surfaced state drift: workflow.md said "P15 awaiting
implementation plan" but the ROADMAP was 🚧, the implementation
plan was already at `docs/superpowers/plans/2026-05-07-cart-and-curated-library-plan.md`,
all P15 implementation commits had landed (`cbd8af6..bf9a956`),
and FP24 had absorbed the full closing-review fold-in. The
right move was the clean-close path of the per-phase 9-step
loop, not a new writing-plans pass.

User picked **"Close P15 now (clean-close path)"** out of
three options surfaced. Then:

- **Sanity check.** Confirmed all spec deliverables landed via
  grep against `api/schemas.py` (`cart_clear_on_copy`,
  `total_bytes`, `cloneof_map_size` mirror), `api/routes/games.py`
  (`@router.post("/api/games/validate")`), and
  `tests/api/test_routes_games.py` (cloneof regression test).
  Ran the full test suites: 455 backend / 240 frontend / 86.93%
  coverage / ruff + mypy + bandit clean / eslint + tsc clean.
- **ROADMAP P15 flip.** `🚧 → ✅`, header `(planned)` → `(closed
  2026-05-08)`, bullet expanded with B1–B5 backend + F1–F14
  frontend + e2e + docs summary, Source/Dependencies preserved,
  back-reference to `docs/journal/P15.md`.
- **CHANGELOG fold.** `Planned — P15 Cart and curated library`
  block converted to `### P15 — Cart and curated library
  (closed 2026-05-08)` summarising what shipped per-task with
  FP24 cross-references where the closing fold-in changed the
  shape (B vs. GB display, D vs. setState-in-effect, E/Q vs.
  nested button, G vs. isStorageBroken, S vs. addAll truncation
  return). Test totals at close stamped at the bottom.
- **Journal.** `docs/journal/P15.md` rewritten — the existing
  file held the 2026-05-08 close-attempted entry that documented
  what triggered FP24; preserved that as a trailing section and
  prepended the close-clean entry with closing landmarks, what
  changed, what was learned, what was deferred. FP24's per-
  cluster breakdown lives in this journal entry rather than a
  per-FP file (consistent with FP15+ practice — recent FPs have
  no `docs/journal/FP##.md`).
- **workflow.md refresh.** Status header rewritten (no active
  item, queue suggests FP22 next). Step-progress blocks for
  FP12 / FP11 / P06 retired — they'd been preserved across
  ~13 phases as audit context but the per-journal files are the
  durable record. Phase history table extended with the P15 row
  (✅ 2026-05-08).

**Workflow lessons:**

- **State drift surfaces fast when you summarise back to the
  user.** The CLAUDE.md rule "summarise back, wait for confirm
  or redirect" caught the workflow.md staleness on the first
  pass — would have wasted ~30 minutes on a duplicate
  writing-plans run otherwise. Pattern reaffirmed: never skip
  the summary step, even when the next move "looks obvious".
- **Splitting fix-passes out of feature phases pays off.** FP23
  shipped the picker fix early (2026-05-07) once the cold-eyes
  review caught the misdiagnosis; P15 then absorbed only the
  regression-test + setup-check-field part of § 4.3.1. If the
  fix had stayed inside P15, the spec → tests → impl ladder
  would have had to interleave with the user's running app
  showing a broken count for several more days. Same shape
  the project's used since DS01 → FP05 → FP06: split when the
  finding is independent and time-pressing; fold when the
  finding is contract-touching and small.
- **Journal-as-cross-reference works when fix-passes don't get
  per-FP files.** P15.md's "FP24's per-cluster breakdown lives
  in workflow.md § 3" is honest about where the FP24 narrative
  actually is. Better than writing a `docs/journal/FP24.md`
  stub that just points back at the workflow journal — saves a
  file and a duplicated narrative.

Tag: `P15-complete` (annotated) at the docs-close commit
(today). `FP24-complete` already tags yesterday's FP24 close
commit — distinct SHAs, since FP24 closed in its own commit
(`aaa4dae`) before P15 could close clean. Pattern differs from
P06+FP11's combined-ship same-SHA tagging because FP24 absorbed
30+ findings across 13 commits, and folding the close-flip
into the last fix-pass commit would have buried it.

Public repo → push prompt deferred to user.

### 2026-05-08 — FP24 closed (P15 closing-review fold-in)

User said "let's please continue with where you think we need to
continue" picking up from FP24's pre-implementation state.
Summarised back, started Step 1 (verify findings vs code), then
swept all three tiers in 13 commits across the day:

**Tier 1 — user-visible blockers (7 commits, A–G + Q + S):**

- A: `JobEvent` `total_files`/`total_bytes` → `files_total`/`bytes_total`
  in the backend `_emit` literal, matching the typed contract
  everywhere else (JobStatus model + `_Job` dataclass + frontend
  api/types.ts). One-line fix that unblocked the copy progress bar
  pinned at 0/0 since v1.2.0.
- B: dropped misleading GB figure from CartBar (was passing the
  filtered library's `total_bytes`, not the cart's). `useCart.totalBytes`
  is v1-deferred — drop rather than mislead.
- C: AppShell Cart NavLink-to-`/` shadowed Library; converted to a
  button + lifted cart-expanded state to ShellWithPalette.
- D: OnboardingBanner derive visibility (`!explicitlyDismissed && !cartHasItems`)
  instead of setState in effect.
- E + Q: GameCard outer `<button>` → `role="button"` div + onKeyDown +
  visible focus ring. Restored Enter/Space activation manually.
- F: `ValidateRequest.short_names` bounded (10,000 / 64-char per item).
- G + S: `useCart.isStorageBroken` returned to caller; `addAll` returns
  `{added, truncated}`; LibraryPage fires the two cart toasts.

**Tier 2 — hardening (3 commits):**

- H/I/J/K/L SSE lifecycle in `useCopySession`: orphan-stream close on
  re-start, transient-error reconnect preservation (readyState===CLOSED
  guard), unmount race via cancelledRef, malformed-payload try/catch,
  conflict-resolve param logged not silently dropped. Mock EventSource
  grew readyState + emitTransient/Terminal helpers.
- M/N/T/U/V LibraryPage: `handleBulkAdd` paginates the full filter
  result; double-click guard via CartBar.copyDisabled prop;
  fetchTileCount routed through apiRequest; `cards` wrapped in
  useMemo; cart-clear effect's eslint-disable now documents the
  stable-ref invariant.
- O/P/R/W/X/Y/Z + AA partial cart UX + a11y: Clear-all confirm dialog,
  tile aria-label, `chosenVariant` type validation, disclosure aria,
  zero-state guards, banner-role corrections, hardcoded strings.

**Tier 3 — debt (3 commits):**

- BB/CC/DD/HH backend: `listxml_available` zombie field deleted;
  `_probe_path kind` parameter now drives is_dir/is_file checks;
  `Badge.BIOS_MISSING` finally appended in `_badges()`; tile-count
  `page_size=1` rationale documented.
- FF/GG/II/JJ/LL frontend: dead string deleted; FeaturedTile types
  hoisted to strings.ts; Cmd+K kbd label adapts to platform; eslint
  argsIgnorePattern `^_` accepts the project convention;
  `handleTileSelect` toggle-off preserves non-tile filter state.
  Plus HelpRoute setState-in-effect ride-along (URL is the source of
  truth; `setSearchParams` replaces the useEffect sync).
- EE: schemas.py over the 500-line cap (574) split into
  `schemas_setup.py` + `schemas_fs.py` with `__all__` re-exports for
  back-compat. tools/check_api_types_sync.py PYTHON_SOURCES extended
  to walk the new files.
- KK partial: cart-flow e2e adjusted to FP24-Y (no `role="status"` on
  OnboardingBanner) and FP24-B (no GB figure on CartBar). Five
  additional e2e cases the original finding named deferred — Vitest
  unit coverage already pins those contracts and the finding
  explicitly accepted Vitest-only.

**Workflow lessons:**

- **Verify findings against code before patching, even when they look
  obvious.** Finding A explicitly said "verify the actual payload shape
  before patching" — and the verify-step found the typed contract on
  schemas.py line 341 / types.ts:721 used `files_total`/`bytes_total`
  while the backend `_emit` literal had drifted to `total_files`/
  `total_bytes`. The fix was therefore the inverse direction the
  finding suggested as one of two options: backend, not frontend.
- **Per-finding TDD pays off in fix-passes too.** Every cluster (or
  pair of clusters) had a failing test landing first; `pytest -xvs`
  + `vitest run` confirmed red, then green, then committed. No
  surprise regressions across 13 commits.
- **Per-file-ignore is the right shape for sibling-extracted modules.**
  schemas.py had `[tool.ruff.lint.per-file-ignores]` for D101/D106;
  schemas_setup.py + schemas_fs.py needed the same treatment after
  extraction. Same logic applies to mypy's no_implicit_reexport —
  schemas.py needs an explicit `__all__` to keep being a re-export
  hub for the new sibling modules.
- **Pre-existing eslint blockers can hide behind older clusters.** The
  HelpRoute setState-in-effect was not in the original FP24
  enumeration but surfaced during the Tier 1 lint run after cluster D
  cleared the OnboardingBanner case. Folded into the Tier 3 frontend
  commit since it's the same shape and the same fix pattern (URL as
  source of truth).

Tests: 455 backend (1 skipped) / 240 frontend / coverage 86.93% /
ruff + mypy + bandit clean / eslint + tsc clean. `frontend/dist/`
rebuilt.

### 2026-05-07 — FP23 closed (parent/clone collapse listxml fix)

Discovered during the P15 brainstorm — user screenshot of the
running v1.2.0 app showed `21,049 games` in the Library bottom
bar, with the 1942 family appearing 7 times (all clones), 1941
× 4, 1943 × 5, 18 Wheeler × 5, etc. The first cold-eyes review
of the P15 spec caught my mis-diagnosis (I'd asserted "the
picker isn't wired", which was wrong) and pointed me at the
real cause: `cloneof_map={}` at world-load time, so
`runner.run_filter` group-by-parent collapses to group-by-self
and every machine becomes its own winner.

Per ADR-0002, parent/clone relationships flow from MAME
`-listxml`, not from the Pleasuredome DAT (which strips
`cloneof`). User's `config.yaml` had `paths.listxml: null` —
silent failure since v1.0.0; FP18's setup banner counts INIs
but not listxml.

**Fix shape (revised mid-session after I underestimated the
modal-wiring scope):**

- Installed openSUSE's `mame` package (0.287, 3 versions newer
  than user's 0.284 DAT — cloneof for old arcade titles is
  stable across this drift).
- Generated listxml: `mame -listxml > /mnt/Games/MAME/listxml-0.287.xml`
  (302 MB, 27,604 cloneof relationships).
- Set `paths.listxml` in user's `config.yaml`. Verified app
  restart drops `/api/games?total` from 21,049 → 10,591;
  /api/games/1942/alternatives returns 8 family members
  (parent + 7 clones, exactly matching the screenshot's count).
- New `components/library/ListxmlBanner.tsx` (3-test pass) +
  rendering in `LibraryPage` above the grid when
  `setupCheck.reference_files.listxml.exists === false`.
- New `hooks/useDryRun.ts` (POST /api/copy/dry-run mutation)
  + handler in `LibraryPage` that opens the existing
  `DryRunModal` with the report on success. P15 swaps the
  `selected_names` source from `cards` → `cart.items` —
  modal contract unchanged so this hook keeps working.
- `onCopy` stays a no-op stub for now: full Copy lifecycle
  wiring (SSE, conflict resolution) is genuinely P15-scale
  (~500 lines + tests) and fits naturally with the cart-driven
  input swap. Scope reset surfaced to user mid-session after
  initial under-estimate; sign-off taken on the smaller shape.

**Workflow lessons saved:**

- **Cold-eyes review on every spec catches mis-diagnoses, not
  just typos.** Round 1 of the P15 cold-eyes review surfaced
  F1 ("the picker isn't wired" — wrong) which would have led
  to a no-op fix. The reviewer cross-checked `state.py` /
  `runner.py` / `picker.py` and found the actual code path,
  saving a wasted FP. Pattern reaffirmed.
- **Scope-reset honesty mid-session is cheaper than over-
  promising.** Initial sign-off was for "wire onCopy/onDryRun
  to filter result"; on inspection, Copy needed full SSE +
  conflict-resolve wiring (~500 lines). Surfaced this back to
  the user with a revised three-option scope question; they
  picked the middle option. Saves both author and user from
  a mid-implementation discovery + scope creep.
- **Gitignored `config.yaml` is the right shape for per-user
  secrets-adjacent config.** The fix to `paths.listxml`
  doesn't enter the commit; user's environment is fixed
  locally. Future sessions of /audit / /indie-review etc.
  should not propose committing user-local paths.

Tests: 3 new ListxmlBanner unit tests; 446 backend / 188
frontend pass; ruff / mypy / bandit clean; coverage 86.66%
(above 85% gate). `frontend/dist/` rebuilt.

CHANGELOG / ROADMAP entries deferred to user-driven commit:
the working tree contains pre-existing FP20/FP21/FP22/DS02
planning blocks the user drafted before this session;
combining their planning prose with this fix-pass's commit
narrative would muddle authorship. Counter at 1023 reflects
FP23's stable ID (mame-curator-1023).

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

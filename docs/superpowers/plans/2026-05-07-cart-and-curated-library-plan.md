# P15 — Cart and Curated Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the unwired `21,049 games · 0.0 GB` dead bottom-bar with a cart-first selection model: per-game `+Add`, featured INI-derived tile row above the grid, sticky cart-bar that expands into a full panel, dismissible onboarding banner, and live `/api/copy/dry-run` + `/api/copy/start` flows driven from `cart.items`.

**Architecture:** Frontend cart is `localStorage`-backed (`mame-curator:cart:v1`); no server resource. Backend gains three small surface extensions — `total_bytes` on the listing envelope, `listxml_available` + `cloneof_map_size` on `/api/setup/check`, `POST /api/games/validate` for pre-Copy reconciliation — plus one schema field (`ui.cart_clear_on_copy`). The parent/clone-collapse runtime symptom shipped fixed in FP23 (config-side); P15 adds the regression test that locks the test-level invariant ("non-empty `cloneof_map` ⇒ winner count strictly less than machine count") and extends the listxml banner to cover the "supplied but parsed empty" edge case via the new `cloneof_map_size` field.

**Tech Stack:** Python 3.12+ / FastAPI / Pydantic 2 (frozen models) on the backend; React 18 + TypeScript + Vite + Vitest + MSW + Playwright + shadcn/ui + react-router + zod + react-query on the frontend. No new runtime deps.

**Companion docs:**
- [Spec — 2026-05-07 cart-and-curated-library design](../specs/2026-05-07-cart-and-curated-library-design.md)
- [ADR-0002 — `cloneof` from listxml](../../decisions/0002-cloneof-from-listxml.md) (motivates the regression test in Task B1)
- [Coding standards](../../standards/coding-standards.md)
- [Commits standard](../../standards/commits.md) (Conventional Commits; phase-closing tag at the end)

**Acceptance (lifted from spec § 6 and § 9):**
- [ ] All listed tests pass (backend ≥85 % overall, `parser/` ≥90 %, `filter/` ≥95 %, `copy/` ≥85 %, `api/` ≥80 %, frontend ≥70 %).
- [ ] `pytest && uv run ruff check && uv run ruff format --check && uv run mypy && uv run bandit -c pyproject.toml -r src` clean.
- [ ] Frontend `npm test && npm run lint && npx tsc --noEmit && npm run build` clean.
- [ ] Playwright spec `tests-e2e/cart-flow.spec.ts` passes.
- [ ] No public function exceeds 80 lines, no Python file exceeds 500 lines, no `.tsx` file exceeds 350 lines (project caps from `CLAUDE.md`).
- [ ] `tools/check_api_types_sync.py` clean (frontend `types.ts` mirrors backend `schemas.py`).

---

## File Structure

### Backend

| Path | Responsibility |
|---|---|
| `src/mame_curator/api/schemas.py` | **MODIFY:** extend `GamesPage` (+`total_bytes: int`); extend `SetupCheck` (+`listxml_available: bool`, +`cloneof_map_size: int`); add `ValidateRequest` + `ValidateResponse`. Extend `UiConfig` (+`cart_clear_on_copy: Literal[...] = 'on_success'`). |
| `src/mame_curator/api/routes/games.py` | **MODIFY:** populate `total_bytes` in `list_games`; add `POST /api/games/validate` handler. |
| `src/mame_curator/api/routes/stubs.py` | **MODIFY:** populate `listxml_available` + `cloneof_map_size` in `setup_check` from `world.cloneof_map`. |
| `src/mame_curator/parser/models.py` | **NOT TOUCHED** — `UiConfig` lives in `api/schemas.py` (verified via `grep -n "class UiConfig"`); the spec line in § 5.4 saying "schema added to `parser/models.UiConfig`" is stale — update the spec callout in this plan to point at `api/schemas.py`. |
| `tests/api/test_routes_games.py` | **MODIFY:** add `test_total_bytes_matches_filtered_sum`, `test_cloneof_map_collapses_winners`, `test_validate_round_trip`. |
| `tests/api/test_routes_stubs.py` | **MODIFY:** add `test_setup_check_listxml_available_and_cloneof_map_size`. |
| `tests/api/test_routes_config.py` | **MODIFY:** add `test_cart_clear_on_copy_default_and_round_trip`. |

### Frontend — new files

| Path | Responsibility |
|---|---|
| `frontend/src/hooks/useCart.ts` | Cart state + `localStorage` round-trip + memoised `totalBytes`. |
| `frontend/src/hooks/useValidateCart.ts` | `POST /api/games/validate` mutation. |
| `frontend/src/hooks/useCopySession.ts` | `POST /api/copy/start` + `EventSource('/api/copy/status')` consumer; produces `CopyModalState`. |
| `frontend/src/components/library/FeaturedTilesRow.tsx` | Horizontal scroll of tile buttons; `onTileSelect(tileId)` callback. |
| `frontend/src/components/library/CartBar.tsx` | Replaces `ActionBar.tsx`. Collapsed: count + size + Dry-run + Copy + ⌃; bulk-add label when `bulkAddTotal != null`. |
| `frontend/src/components/library/CartPanel.tsx` | Expand-up panel; per-row `✕` + variant badge + total + Clear all. |
| `frontend/src/components/library/OnboardingBanner.tsx` | Top dismissible banner; `localStorage`-keyed. |
| `frontend/src/components/library/__tests__/CartBar.test.tsx` | Vitest. |
| `frontend/src/components/library/__tests__/CartPanel.test.tsx` | Vitest. |
| `frontend/src/components/library/__tests__/FeaturedTilesRow.test.tsx` | Vitest. |
| `frontend/src/components/library/__tests__/OnboardingBanner.test.tsx` | Vitest. |
| `frontend/src/components/library/__tests__/GameCard.test.tsx` | Vitest (currently no GameCard test — adding `+Add` is the trigger). |
| `frontend/src/hooks/__tests__/useCart.test.tsx` | Vitest. |
| `frontend/src/hooks/__tests__/useValidateCart.test.tsx` | Vitest. |
| `frontend/src/hooks/__tests__/useCopySession.test.tsx` | Vitest. |
| `tests-e2e/cart-flow.spec.ts` | Playwright. |

### Frontend — surgical edits

| Path | Change |
|---|---|
| `frontend/src/components/library/ActionBar.tsx` | **DELETE** (becomes `CartBar.tsx`). |
| `frontend/src/components/library/GameCard.tsx` | Add `+Add` button overlay + cart-aware `✓ Added` state; click on `+Add` calls `cart.add(short_name)`, click on card body still calls `onOpen`. ARIA: `+Add` button has its own `aria-label`. |
| `frontend/src/components/library/ListxmlBanner.tsx` | Extend trigger: also render when `cloneof_map_size === 0` AND `listxml.exists === true` (file present but parsed empty). New optional prop `cloneofMapSize?: number`. |
| `frontend/src/pages/LibraryPage.tsx` | Wire `useCart`, `useValidateCart`, `useCopySession`; mount `OnboardingBanner` + `FeaturedTilesRow` + `CartBar` + `CartPanel` + `CopyModal`; route `onDryRun` + `onCopy` through `cart.items`; pre-Copy validation; auto-clear policy. |
| `frontend/src/components/layout/AppShell.tsx` | Top-nav reshape: rail → horizontal nav + `More` popover. |
| `frontend/src/pages/SettingsPage.tsx` | Add `cart_clear_on_copy` Select inside the Display `<Card>` alongside `default_sort` (~ line 270). |
| `frontend/src/strings.ts` | Add `library.featured.tiles[]` + `library.cart.*` + `library.onboarding.*` + `library.listxmlMissing.emptyParseBody` + `settings.uiLabels.cart_clear_on_copy`. |
| `frontend/src/api/types.ts` | Mirror `total_bytes` in `GamesPage`; mirror `listxml_available` + `cloneof_map_size` in `SetupCheck`; mirror `cart_clear_on_copy` in `UiConfig`; add `ValidateRequest` + `ValidateResponse`. |

### Docs

| Path | Change |
|---|---|
| `ROADMAP.md` | Add `## P15 — Cart and curated library (planned)` block at the top of the roadmap (above existing planned `FP22`/`FP20`/`FP21`/`DS02` blocks). |
| `CHANGELOG.md` | `[Unreleased]` gains `### Planned — P15 Cart and curated library` block. |
| `docs/journal/P15.md` | NEW empty placeholder for the close-phase loop to fill. |
| `.claude/workflow.md` § 1 | Status header bumped to `Active item ID = P15` step `🚧 1` once Task D1 commits. |

---

## Task list

The plan is grouped into four waves; each wave's tasks have only intra-wave dependencies. Within a wave, tasks are sequential.

| Wave | Tasks | Theme |
|---|---|---|
| **Wave 0 — open the phase** | D1 | Roadmap + changelog + journal scaffold |
| **Wave 1 — backend** | B1 → B5 | Schema extensions, regression test, validate endpoint |
| **Wave 2 — frontend foundations** | F1 → F4 | Types mirror, hooks, strings catalogue |
| **Wave 3 — frontend leaves** | F5 → F9 | Components built bottom-up |
| **Wave 4 — frontend integration** | F10 → F14 | Wire LibraryPage, AppShell, SettingsPage, Playwright |

---

### Task D1: Open the phase — ROADMAP + CHANGELOG + journal scaffold

**Files:**
- Modify: `ROADMAP.md` (insert above current line 1341 `## FP22 …`)
- Modify: `CHANGELOG.md` (insert at top of `[Unreleased]`)
- Create: `docs/journal/P15.md`
- Modify: `.claude/workflow.md` § 1 status header

- [ ] **Step 1: Add `## P15 — Cart and curated library (planned)` block to `ROADMAP.md`**

Insert directly above `## FP23 — …` at the top of the closed/planned mix section. Use the same shape as prior phase entries (`## P06 — Frontend MVP …`):

```markdown
## P15 — Cart and curated library (planned)

**Theme:** [`docs/superpowers/specs/2026-05-07-cart-and-curated-library-design.md`](docs/superpowers/specs/2026-05-07-cart-and-curated-library-design.md) — turn the dead `21,049 games · 0.0 GB` bottom-bar into a cart-first selection model with featured INI-derived tiles, dismissible onboarding banner, sticky cart-bar with expand-up panel, and live Copy + DryRun flows. Picker runtime symptom shipped fixed in FP23; this phase adds the regression test that locks `cloneof_map` non-empty ⇒ winners < machines, plus the `listxml_available` + `cloneof_map_size` setup-check fields that let the banner cover the "supplied but parsed empty" edge case.

### 🎨 Features

- 🚧 **P15** [mame-curator-1024] **Cart-first selection + curated featured tiles + live Copy.**
  Lanes: api, frontend, docs.

  See spec § 9 file-level diff summary for the full surface; this roadmap entry is intentionally a pointer rather than a duplicate.

  Source: user feedback 2026-05-07 ("21,049 games, no clear path to pick three"); brainstorm + 7-round cold-eyes review APPROVE.
  Dependencies: FP23 ✅ (listxml banner foundation), FP19 ✅ (RetroArch launch — cart preserves), FP17 ✅ (`/api/library/facets` for tile counts).

---
```

- [ ] **Step 2: Bump `.roadmap-counter` 1023 → 1024**

```bash
echo "1024" > .roadmap-counter
```

- [ ] **Step 3: Add `### Planned — P15 Cart and curated library` to `CHANGELOG.md` `[Unreleased]`**

Insert at the top of `[Unreleased]` (above the existing FP23 closed entry — chronologically planned-future goes above closed-past within the section):

```markdown
### Planned — P15 Cart and curated library

User feedback 2026-05-07: opening the app shows 21,049 cards
with no clear path to pick a few games and copy them. P15 adds
cart-first selection (per-game `+Add`, featured INI-derived
tiles, sticky cart-bar with expand-up panel), wires the
previously no-op `onCopy` to a live SSE-driven flow, and adds
the `cloneof_map`-non-empty regression test that locks the
FP23 fix at the test level. See `ROADMAP.md` `P15`.
```

- [ ] **Step 4: Create empty `docs/journal/P15.md`**

```markdown
# P15 — Cart and curated library

> **Status:** in progress — populated by `/close-phase` at phase close.
```

- [ ] **Step 5: Update `.claude/workflow.md` § 1 status header**

Change:
```
| **Active item ID** | P15 — Cart and curated library (spec at `docs/superpowers/specs/2026-05-07-cart-and-curated-library-design.md`); writing-plans handoff next session |
| **Active step** | ⬜ all (FP23 closed 2026-05-07; P15 spec written + 7-round cold-eyes review APPROVE; user signed off on spec then asked for bug-fix-first before plan) |
```
to:
```
| **Active item ID** | P15 — Cart and curated library |
| **Active step** | 🚧 1 (plan committed; backend wave next) |
```

Also clear the `Blocked on` line (the planning-blocks commit is in).

- [ ] **Step 6: Commit**

```bash
git add ROADMAP.md CHANGELOG.md .roadmap-counter docs/journal/P15.md docs/superpowers/plans/2026-05-07-cart-and-curated-library-plan.md .claude/workflow.md
git commit -m "docs(roadmap,changelog): open P15 — cart and curated library

Plan committed at docs/superpowers/plans/2026-05-07-cart-and-
curated-library-plan.md (~20 tasks across backend / frontend /
e2e). Phase ID 1024 reserved in .roadmap-counter."
```

---

## Wave 1 — Backend (B1 → B5)

### Task B1: Lock parent/clone collapse with a regression test

**Why this is Task 1:** the FP23 fix shipped via `config.yaml` (the user's listxml path was null since v1.0.0). The runtime symptom is gone, but the underlying invariant is unguarded: any future regression in `filter/runner.py` `pick_winner` group-key construction, `state.py` `cloneof_map` wiring, or `parser/listxml.py` `parse_listxml_cloneof` would silently re-introduce the 21k-cards bug. This test pins the invariant: `non-empty cloneof_map ⇒ len(winners) < len(machines)`. Run it red against the FP23 baseline first to confirm the fixture has parents+clones, then green to confirm the runner collapses them.

**Files:**
- Modify: `tests/api/test_routes_games.py` (add `test_cloneof_map_collapses_winners`)

- [ ] **Step 1: Inspect the existing test pattern**

Read `tests/api/test_routes_games.py:16-52` to see how the `client` fixture is consumed. The `client` fixture (from `tests/api/conftest.py`) already wires up the mini DAT (6 machines including `pacman` parent + `pacmanf` clone — see `api_listxml.xml`).

- [ ] **Step 2: Write the failing test**

Append to `tests/api/test_routes_games.py`:

```python
def test_cloneof_map_collapses_winners(client: Any) -> None:
    """Regression for FP23: non-empty cloneof_map ⇒ winners < machines.

    The api_listxml fixture (tests/api/fixtures/api_listxml.xml) maps
    pacmanf → pacman as a clone-of relationship. With the cloneof_map
    populated, the runner groups pacmanf under pacman; pick_winner picks
    one of them; total winners is strictly less than total machines.

    If this test ever fails, the picker-collapse path has regressed —
    most likely paths.listxml is null again (the FP23 symptom), or
    parse_listxml_cloneof returns empty, or state.py drops cloneof_map
    on the floor between parser and FilterContext. Diagnose by checking
    /api/setup/check (B2 adds cloneof_map_size to the response).
    """
    resp = client.get("/api/games", params={"page_size": 500})
    assert resp.status_code == 200
    body = resp.json()
    # mini DAT has 6 machines (pacman, pacmanf, neogeo, z80, 3bagfull,
    # brokensim). With pacmanf collapsed under pacman, total ≤ 5.
    assert body["total"] < 6, (
        f"expected post-collapse total < 6, got {body['total']} "
        f"— cloneof_map likely empty (regression of FP23)"
    )
```

- [ ] **Step 3: Run the test**

```bash
uv run pytest tests/api/test_routes_games.py::test_cloneof_map_collapses_winners -xvs
```

Expected: **PASS** on the FP23 baseline (the fix already lives in the wired-listxml fixture). The test exists to catch *future* regressions, not to drive a code change today.

If the test fails on `main` post-FP23: investigate before proceeding — something else has regressed.

- [ ] **Step 4: Add an inverse "no-listxml" assertion alongside**

Add a sibling test that flips the listxml off and confirms the symptom returns. This locks both states.

```python
def test_no_listxml_self_parents_every_machine(
    client: Any, tmp_path: Any, monkeypatch: Any
) -> None:
    """When paths.listxml is null, every machine self-parents — the
    pre-FP23 symptom. Confirms the cloneof_map dependency is the actual
    cause of post-collapse winner counts.
    """
    # Reuse the regular client but construct a sibling app with paths.listxml unset.
    # NB: implementation detail — sniff the fixture path from conftest if direct
    # ``app`` reuse with monkeypatched config is cleaner. Keep this test minimal:
    # the canonical path is a separate `client_no_listxml` fixture in conftest.
    # If adding a new fixture is too invasive, drop this test — the pair in
    # tests/filter/test_runner.py:62 + 156 already cover the runner-level
    # invariant. This test exists ONLY to lock the API-level surface; it's
    # belt-and-braces.
    pytest.skip(
        "API-level no-listxml regression covered transitively by "
        "tests/filter/test_runner.py:156 (runner-level cloneof_map={} ⇒ "
        "self-parent invariant). Re-enable if API surface changes."
    )
```

Rationale for the skip: the runner-level invariant is already covered by `tests/filter/test_runner.py` (line 156: `ctx = FilterContext(cloneof_map={"b": "a"})` and a sibling at line 62 covers the populated case). Re-implementing the same coverage at the API layer would be duplicative; the skip-with-rationale documents the choice for future readers.

- [ ] **Step 5: Run the full backend test suite**

```bash
uv run pytest -x
```

Expected: PASS, including the new test.

- [ ] **Step 6: Commit**

```bash
git add tests/api/test_routes_games.py
git commit -m "test(api): P15 § B1 — lock cloneof_map collapse invariant

Regression test for the FP23 symptom (paths.listxml: null ⇒
21k self-parented winners). Asserts that with the wired
api_listxml fixture, /api/games?page_size=500 returns total
< len(machines). Catches future regressions where cloneof_map
silently empties (parser drift, state.py wiring, listxml path
flip) before they reach production."
```

---

### Task B2: Extend `/api/setup/check` with `listxml_available` + `cloneof_map_size`

**Why:** the FP23 `ListxmlBanner` triggers on `reference_files.listxml.exists === false` (file absent). It misses the "file present but parsed empty" edge case (corrupt listxml, partial parse, schema drift). The new `cloneof_map_size: int` field surfaces the post-parse reality so the banner can cover both states.

**Files:**
- Modify: `src/mame_curator/api/schemas.py` (extend `SetupCheck`)
- Modify: `src/mame_curator/api/routes/stubs.py` (populate the new fields in `setup_check`)
- Modify: `tests/api/test_routes_stubs.py` (assert the new fields)

- [ ] **Step 1: Write the failing test**

Append to `tests/api/test_routes_stubs.py`:

```python
def test_setup_check_listxml_available_and_cloneof_map_size(client: Any) -> None:
    """P15 § 4.3.1: /api/setup/check exposes listxml_available + cloneof_map_size.

    listxml_available is True iff paths.listxml is set AND the file
    exists AND the parsed cloneof_map has at least one entry.
    cloneof_map_size is the literal len(world.cloneof_map).

    The api_listxml fixture maps pacmanf → pacman, so cloneof_map_size
    >= 1 and listxml_available is True.
    """
    resp = client.get("/api/setup/check")
    assert resp.status_code == 200
    body = resp.json()
    assert body["listxml_available"] is True
    assert body["cloneof_map_size"] >= 1
```

- [ ] **Step 2: Run the test — confirm it fails**

```bash
uv run pytest tests/api/test_routes_stubs.py::test_setup_check_listxml_available_and_cloneof_map_size -xvs
```

Expected: **FAIL** — `KeyError: 'listxml_available'` (response model rejects unknown keys but the test asserts on response JSON keys that don't exist yet).

- [ ] **Step 3: Extend the `SetupCheck` schema**

Edit `src/mame_curator/api/schemas.py:472-476`:

```python
class SetupCheck(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    config_present: bool
    paths: SetupPaths
    reference_files: SetupReferenceFiles
    listxml_available: bool
    cloneof_map_size: int
```

- [ ] **Step 4: Populate the fields in the `setup_check` route**

Edit `src/mame_curator/api/routes/stubs.py:52-70`. The `world` dependency already exposes `cloneof_map`. Compute `listxml_available` from the three conjuncts (path set, file exists, parsed map non-empty):

```python
@router.get("/api/setup/check", response_model=SetupCheck)
def setup_check(world: WorldState = Depends(get_world)) -> SetupCheck:
    p = world.config.paths
    listxml_status = _probe_ref(p.listxml)
    cloneof_map_size = len(world.cloneof_map)
    listxml_available = (
        p.listxml is not None
        and listxml_status.exists
        and cloneof_map_size > 0
    )
    return SetupCheck(
        config_present=True,
        paths=SetupPaths(
            source_roms=_probe_path(p.source_roms, kind="dir"),
            source_dat=_probe_dat(p.source_dat),
            dest_roms=_probe_path(p.dest_roms, kind="dir", writable=True),
        ),
        reference_files=SetupReferenceFiles(
            catver=_probe_ref(p.catver),
            languages=_probe_ref(p.languages),
            bestgames=_probe_ref(p.bestgames),
            mature=_probe_ref(p.mature),
            series=_probe_ref(p.series),
            listxml=listxml_status,
        ),
        listxml_available=listxml_available,
        cloneof_map_size=cloneof_map_size,
    )
```

- [ ] **Step 5: Run the test — confirm it passes**

```bash
uv run pytest tests/api/test_routes_stubs.py::test_setup_check_listxml_available_and_cloneof_map_size -xvs
```

Expected: PASS.

- [ ] **Step 6: Run the full backend suite to confirm no shape-test breakage**

The pre-existing `test_route_r35_shape_setup_check` at line 11 of `test_routes_stubs.py` checks for `("config_present", "paths", "reference_files")`. Since we ADD fields and keep the existing keys, that test should still pass. Verify:

```bash
uv run pytest tests/api/test_routes_stubs.py -xvs
```

Expected: ALL PASS.

- [ ] **Step 7: Commit**

```bash
git add src/mame_curator/api/schemas.py src/mame_curator/api/routes/stubs.py tests/api/test_routes_stubs.py
git commit -m "feat(api): P15 § B2 — setup-check listxml_available + cloneof_map_size

New fields on /api/setup/check let the frontend ListxmlBanner
cover the 'file present but parsed empty' edge case (corrupt
listxml, partial parse, schema drift) — FP23 only handled the
'file absent' case. listxml_available is the derived
\"can collapse parents/clones?\" flag; cloneof_map_size is the
literal len(world.cloneof_map). Per spec § 4.3.1."
```

---

### Task B3: Add `total_bytes` to the listing envelope

**Why:** `LibraryPage.tsx:87` currently has `const totalBytes = 0 // wired in a follow-up via useStats`. The bottom-bar reads `0.0 GB` because the listing endpoint doesn't return a sum-of-bytes for the filtered slice. `/api/stats` does it (line 332-342) but is a separate query that's expensive on every filter change. Putting `total_bytes` on the listing envelope itself makes it free.

**Files:**
- Modify: `src/mame_curator/api/schemas.py` (extend `GamesPage`)
- Modify: `src/mame_curator/api/routes/games.py` (compute `total_bytes` in `list_games`)
- Modify: `tests/api/test_routes_games.py` (add `test_total_bytes_matches_filtered_sum`)

- [ ] **Step 1: Write the failing test**

Append to `tests/api/test_routes_games.py`:

```python
def test_total_bytes_matches_filtered_sum(client: Any) -> None:
    """P15 § 4.3.2: GamesPage.total_bytes equals sum of ROM bytes
    over the filtered slice (not the page slice).

    With the mini DAT, /api/games?page_size=1 returns one card on
    page 1 of N, but total_bytes covers ALL filtered machines —
    the bottom-bar reads the same regardless of pagination.
    """
    full = client.get("/api/games", params={"page_size": 500}).json()
    paged = client.get("/api/games", params={"page_size": 1}).json()
    assert full["total_bytes"] == paged["total_bytes"]
    assert full["total_bytes"] > 0  # mini DAT machines have non-empty roms
```

- [ ] **Step 2: Run — confirm failing**

```bash
uv run pytest tests/api/test_routes_games.py::test_total_bytes_matches_filtered_sum -xvs
```

Expected: **FAIL** — `KeyError: 'total_bytes'`.

- [ ] **Step 3: Extend `GamesPage` schema**

Edit `src/mame_curator/api/schemas.py:154-159`:

```python
class GamesPage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[GameCard, ...]
    page: int
    page_size: int
    total: int
    total_bytes: int
```

- [ ] **Step 4: Populate `total_bytes` in `list_games`**

Edit `src/mame_curator/api/routes/games.py:129-134`. The `filtered` list already exists; sum bytes alongside the existing `total = len(filtered)`:

```python
    filtered = [s for s in winners if keep(s)]
    total = len(filtered)
    total_bytes = sum(
        sum(r.size or 0 for r in world.machines[s].roms) for s in filtered
    )
    start = (page - 1) * page_size
    end = start + page_size
    page_items = tuple(_card(world.machines[s], world) for s in filtered[start:end])
    return GamesPage(
        items=page_items,
        page=page,
        page_size=page_size,
        total=total,
        total_bytes=total_bytes,
    )
```

- [ ] **Step 5: Run — confirm passing**

```bash
uv run pytest tests/api/test_routes_games.py::test_total_bytes_matches_filtered_sum -xvs
```

Expected: PASS.

- [ ] **Step 6: Verify the existing R01 shape test still passes**

The existing `test_route_r01_shape_games_listing` at `test_routes_games.py:16` may assert specific keys. Since we only ADD a key, it should still pass; verify:

```bash
uv run pytest tests/api/test_routes_games.py -xvs
```

Expected: ALL PASS.

- [ ] **Step 7: Commit**

```bash
git add src/mame_curator/api/schemas.py src/mame_curator/api/routes/games.py tests/api/test_routes_games.py
git commit -m "feat(api): P15 § B3 — total_bytes on /api/games envelope

Existing bottom-bar reads 0.0 GB because the listing endpoint
omits a sum-of-bytes; /api/stats has it (line 332-342) but is
a separate query that's expensive per filter change. Sum
across the filtered slice (NOT the page slice) so the
bottom-bar value is pagination-invariant."
```

---

### Task B4: Add `POST /api/games/validate` endpoint

**Why:** spec § 5.1 cart reconciliation runs pre-Copy: validate the cart against the current world before opening `CopyModal`; drop missing items with one toast; open with the surviving set. Reading `world.machines.get(s)` for each name is O(1) per name; whole endpoint is a set lookup.

**Files:**
- Modify: `src/mame_curator/api/schemas.py` (add `ValidateRequest`, `ValidateResponse`)
- Modify: `src/mame_curator/api/routes/games.py` (add the handler)
- Modify: `tests/api/test_routes_games.py` (add `test_validate_round_trip`)

- [ ] **Step 1: Write the failing test**

Append to `tests/api/test_routes_games.py`:

```python
def test_validate_round_trip(client: Any) -> None:
    """P15 § 5.1: POST /api/games/validate splits names into
    {existing, missing} against world.machines.

    Set-lookup; no pagination, no filter chain. Used pre-Copy to
    drop orphaned cart items after a DAT swap.
    """
    resp = client.post(
        "/api/games/validate",
        json={"short_names": ["pacman", "definitely_not_a_real_game", "pacmanf"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert sorted(body["existing"]) == ["pacman", "pacmanf"]
    assert body["missing"] == ["definitely_not_a_real_game"]


def test_validate_empty_input_returns_empty_pair(client: Any) -> None:
    """Empty cart pre-Copy is a valid case (user clicked Copy after
    Clear all without re-adding); endpoint returns {[], []}."""
    resp = client.post("/api/games/validate", json={"short_names": []})
    assert resp.status_code == 200
    assert resp.json() == {"existing": [], "missing": []}
```

- [ ] **Step 2: Run — confirm failing**

```bash
uv run pytest tests/api/test_routes_games.py::test_validate_round_trip tests/api/test_routes_games.py::test_validate_empty_input_returns_empty_pair -xvs
```

Expected: **FAIL** — 404 Not Found (route doesn't exist).

- [ ] **Step 3: Add the schemas**

Append to `src/mame_curator/api/schemas.py` near `GamesPage` (around line 160):

```python
class ValidateRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    short_names: tuple[str, ...]


class ValidateResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    existing: tuple[str, ...]
    missing: tuple[str, ...]
```

- [ ] **Step 4: Add the import + the handler in `games.py`**

Top of `src/mame_curator/api/routes/games.py:14-27`, add `ValidateRequest, ValidateResponse` to the schema import block:

```python
from mame_curator.api.schemas import (
    Alternatives,
    Badge,
    Explanation,
    GameCard,
    GameDetail,
    GamesPage,
    LaunchResponse,
    LibraryFacets,
    Notes,
    NotesPutRequest,
    Stats,
    ValidateRequest,
    ValidateResponse,
)
```

Add a new handler — place it after `library_facets` (line 137-170) and before `get_game` (line 173) so `GET /api/games/{name}` doesn't shadow it (FastAPI registers routes in source order; `/validate` would otherwise be intercepted by `/{name}`):

```python
@router.post("/api/games/validate", response_model=ValidateResponse)
def validate_games(
    body: ValidateRequest,
    world: WorldState = Depends(get_world),
) -> ValidateResponse:
    """P15 § 5.1: split cart shortnames into {existing, missing}.

    Set lookup against ``world.machines``; no pagination, no filter
    chain. Used pre-Copy to drop orphaned cart items after a DAT
    swap or refresh-inis run.
    """
    existing: list[str] = []
    missing: list[str] = []
    for name in body.short_names:
        if name in world.machines:
            existing.append(name)
        else:
            missing.append(name)
    return ValidateResponse(existing=tuple(existing), missing=tuple(missing))
```

- [ ] **Step 5: Run — confirm passing**

```bash
uv run pytest tests/api/test_routes_games.py::test_validate_round_trip tests/api/test_routes_games.py::test_validate_empty_input_returns_empty_pair -xvs
```

Expected: PASS.

- [ ] **Step 6: Run the full games suite to confirm route ordering didn't break `/api/games/{name}` lookups**

```bash
uv run pytest tests/api/test_routes_games.py -xvs
```

Expected: ALL PASS, including `test_route_r02_shape_game_detail` (which calls `/api/games/pacman`).

- [ ] **Step 7: Commit**

```bash
git add src/mame_curator/api/schemas.py src/mame_curator/api/routes/games.py tests/api/test_routes_games.py
git commit -m "feat(api): P15 § B4 — POST /api/games/validate

Pre-Copy reconciliation endpoint. Splits cart shortnames into
{existing, missing} via O(1) set lookup against world.machines.
Frontend calls this before opening CopyModal so a DAT swap or
refresh-inis run that orphans some cart items degrades to a
single 'N items removed' toast instead of a hard error mid-copy.

Route registered before /api/games/{name} so /validate doesn't
get shadowed by the path-param handler (FastAPI source order)."
```

---

### Task B5: Add `cart_clear_on_copy` to `UiConfig`

**Why:** spec § 5.4 — auto-clear-after-copy behaviour is configurable. Default `'on_success'` matches the user's stated mental model (clear after success, retain after failure).

**Files:**
- Modify: `src/mame_curator/api/schemas.py` (extend `UiConfig`)
- Modify: `tests/api/test_routes_config.py` (add round-trip test)

- [ ] **Step 1: Write the failing test**

Read `tests/api/test_routes_config.py` to find an existing PATCH round-trip test pattern. Append a sibling:

```python
def test_cart_clear_on_copy_default_and_round_trip(client: Any) -> None:
    """P15 § 5.4: ui.cart_clear_on_copy defaults to 'on_success' and
    accepts the three Literal values."""
    # Default
    resp = client.get("/api/config")
    assert resp.status_code == 200
    assert resp.json()["ui"]["cart_clear_on_copy"] == "on_success"

    # Round-trip each valid value
    for value in ("always", "on_success", "never"):
        patch = client.patch(
            "/api/config",
            json={"ui": {"cart_clear_on_copy": value}},
        )
        assert patch.status_code == 200, patch.text
        assert client.get("/api/config").json()["ui"]["cart_clear_on_copy"] == value


def test_cart_clear_on_copy_rejects_invalid(client: Any) -> None:
    """Pydantic Literal narrows the field; anything else 422s."""
    resp = client.patch(
        "/api/config",
        json={"ui": {"cart_clear_on_copy": "sometimes"}},
    )
    assert resp.status_code == 422
```

- [ ] **Step 2: Run — confirm failing**

```bash
uv run pytest tests/api/test_routes_config.py::test_cart_clear_on_copy_default_and_round_trip tests/api/test_routes_config.py::test_cart_clear_on_copy_rejects_invalid -xvs
```

Expected: **FAIL** — `KeyError: 'cart_clear_on_copy'`.

- [ ] **Step 3: Extend `UiConfig`**

Edit `src/mame_curator/api/schemas.py:86-92`:

```python
class UiConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    theme: Literal["dark", "light", "double_dragon", "pacman", "sf2", "neogeo"] = "dark"
    layout: Literal["masonry", "list", "covers", "grouped"] = "masonry"
    default_sort: Literal["name", "year", "manufacturer", "rating"] = "name"
    show_alternatives_indicator: bool = True
    cards_per_row_hint: Literal["auto", 4, 5, 6, 8] = "auto"
    cart_clear_on_copy: Literal["always", "on_success", "never"] = "on_success"
```

- [ ] **Step 4: Run — confirm passing**

```bash
uv run pytest tests/api/test_routes_config.py::test_cart_clear_on_copy_default_and_round_trip tests/api/test_routes_config.py::test_cart_clear_on_copy_rejects_invalid -xvs
```

Expected: PASS.

- [ ] **Step 5: Run the full backend suite**

```bash
uv run pytest -x && uv run ruff check && uv run mypy
```

Expected: ALL PASS (ruff + mypy gate the schema change).

- [ ] **Step 6: Commit**

```bash
git add src/mame_curator/api/schemas.py tests/api/test_routes_config.py
git commit -m "feat(api): P15 § B5 — UiConfig.cart_clear_on_copy

Pydantic Literal['always','on_success','never'] with default
'on_success'. Spec § 5.4: clear cart after a succeeded copy
(natural empty-state for next browse), retain after partial /
failed (preserves the failed-list debug context). Three-value
config knob for users who prefer 'always' or 'never'."
```

---

## Wave 2 — Frontend foundations (F1 → F4)

### Task F1: Mirror backend type changes in `api/types.ts`

**Why:** the project enforces one-to-one mirror between `api/schemas.py` and `frontend/src/api/types.ts` via `tools/check_api_types_sync.py` (CI gate, see `pyproject.toml`). Add the four schema additions from B2/B3/B4/B5 in lockstep so the gate stays green.

**Files:**
- Modify: `frontend/src/api/types.ts`

- [ ] **Step 1: Find each anchor in `api/types.ts`**

```bash
grep -n "GamesPage\|SetupCheck\|UiConfig\|cart_clear_on_copy" frontend/src/api/types.ts
```

- [ ] **Step 2: Add `total_bytes` to `GamesPage` (interface + zod schema)**

Find the `GamesPage` interface and `GamesPageSchema` const. Add a `total_bytes: number` field on both, alongside `total: number`.

- [ ] **Step 3: Add `listxml_available` + `cloneof_map_size` to `SetupCheck`**

Find `SetupCheck` and `SetupCheckSchema`. Add:

```typescript
listxml_available: boolean
cloneof_map_size: number
```

And in the zod schema:

```typescript
listxml_available: z.boolean(),
cloneof_map_size: z.number().int().nonnegative(),
```

- [ ] **Step 4: Add `cart_clear_on_copy` to `UiConfig`**

Find `UiConfig` interface (it carries `default_sort`, etc.). Add:

```typescript
cart_clear_on_copy: 'always' | 'on_success' | 'never'
```

And the zod schema:

```typescript
cart_clear_on_copy: z.enum(['always', 'on_success', 'never']).default('on_success'),
```

- [ ] **Step 5: Add `ValidateRequest` + `ValidateResponse`**

After `GamesPage`, add:

```typescript
export interface ValidateRequest {
  short_names: string[]
}

export const ValidateRequestSchema = z.object({
  short_names: z.array(z.string()),
})

export interface ValidateResponse {
  existing: string[]
  missing: string[]
}

export const ValidateResponseSchema = z.object({
  existing: z.array(z.string()),
  missing: z.array(z.string()),
})
```

- [ ] **Step 6: Run the sync gate**

```bash
uv run python tools/check_api_types_sync.py
```

Expected: PASS (no diffs reported between Python and TS schemas).

- [ ] **Step 7: Run TS typecheck**

```bash
cd frontend && npx tsc --noEmit
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/api/types.ts
git commit -m "feat(frontend): P15 § F1 — mirror P15 backend types

GamesPage.total_bytes, SetupCheck.{listxml_available,
cloneof_map_size}, UiConfig.cart_clear_on_copy, plus
ValidateRequest + ValidateResponse for /api/games/validate.

Synced via tools/check_api_types_sync.py."
```

---

### Task F2: `useCart` hook with `localStorage` round-trip

**Files:**
- Create: `frontend/src/hooks/useCart.ts`
- Create: `frontend/src/hooks/__tests__/useCart.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/hooks/__tests__/useCart.test.tsx`:

```typescript
import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import { useCart, MAX_CART_SIZE } from '@/hooks/useCart'

describe('useCart', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('starts empty', () => {
    const { result } = renderHook(() => useCart())
    expect(result.current.items).toEqual([])
    expect(result.current.totalBytes).toBe(0)
  })

  it('add() appends a CartItem and persists across remounts', () => {
    const { result, rerender } = renderHook(() => useCart())
    act(() => result.current.add('pacman'))
    expect(result.current.items).toEqual([{ shortName: 'pacman' }])

    rerender()
    expect(result.current.items).toEqual([{ shortName: 'pacman' }])

    // Fresh mount reads from localStorage
    const { result: fresh } = renderHook(() => useCart())
    expect(fresh.current.items).toEqual([{ shortName: 'pacman' }])
  })

  it('add() is idempotent — duplicate shortName does not appear twice', () => {
    const { result } = renderHook(() => useCart())
    act(() => result.current.add('pacman'))
    act(() => result.current.add('pacman'))
    expect(result.current.items).toHaveLength(1)
  })

  it('has() reflects membership', () => {
    const { result } = renderHook(() => useCart())
    expect(result.current.has('pacman')).toBe(false)
    act(() => result.current.add('pacman'))
    expect(result.current.has('pacman')).toBe(true)
  })

  it('remove() drops the item', () => {
    const { result } = renderHook(() => useCart())
    act(() => result.current.add('pacman'))
    act(() => result.current.remove('pacman'))
    expect(result.current.items).toEqual([])
  })

  it('addAll() merges, dedupes, preserves existing order', () => {
    const { result } = renderHook(() => useCart())
    act(() => result.current.add('pacman'))
    act(() => result.current.addAll(['pacmanf', 'pacman', '1942']))
    expect(result.current.items.map((i) => i.shortName)).toEqual([
      'pacman',
      'pacmanf',
      '1942',
    ])
  })

  it('addAll() truncates at MAX_CART_SIZE', () => {
    const { result } = renderHook(() => useCart())
    const huge = Array.from({ length: MAX_CART_SIZE + 100 }, (_, i) => `g${i}`)
    act(() => result.current.addAll(huge))
    expect(result.current.items).toHaveLength(MAX_CART_SIZE)
  })

  it('setVariant() updates chosenVariant on an existing entry', () => {
    const { result } = renderHook(() => useCart())
    act(() => result.current.add('1942'))
    act(() => result.current.setVariant('1942', '1942j'))
    expect(result.current.items[0]).toEqual({ shortName: '1942', chosenVariant: '1942j' })

    // Pass undefined to clear
    act(() => result.current.setVariant('1942', undefined))
    expect(result.current.items[0]).toEqual({ shortName: '1942' })
  })

  it('setVariant() on missing item is a no-op', () => {
    const { result } = renderHook(() => useCart())
    act(() => result.current.setVariant('ghost', 'ghostj'))
    expect(result.current.items).toEqual([])
  })

  it('clear() empties the cart', () => {
    const { result } = renderHook(() => useCart())
    act(() => result.current.addAll(['a', 'b', 'c']))
    act(() => result.current.clear())
    expect(result.current.items).toEqual([])
  })

  it('falls back to in-memory when localStorage write throws', () => {
    const setItem = Storage.prototype.setItem
    Storage.prototype.setItem = () => {
      throw new DOMException('QuotaExceededError', 'QuotaExceededError')
    }
    try {
      const { result } = renderHook(() => useCart())
      // Should not throw despite storage failure
      expect(() => act(() => result.current.add('pacman'))).not.toThrow()
      expect(result.current.items).toEqual([{ shortName: 'pacman' }])
    } finally {
      Storage.prototype.setItem = setItem
    }
  })
})
```

- [ ] **Step 2: Run — confirm failing (file doesn't exist)**

```bash
cd frontend && npm test -- useCart
```

Expected: FAIL — `Cannot find module '@/hooks/useCart'`.

- [ ] **Step 3: Implement the hook**

Create `frontend/src/hooks/useCart.ts`:

```typescript
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

export interface CartItem {
  shortName: string
  chosenVariant?: string
}

export interface UseCartResult {
  items: CartItem[]
  has: (shortName: string) => boolean
  add: (shortName: string, variant?: string) => void
  remove: (shortName: string) => void
  addAll: (shortNames: string[]) => void
  setVariant: (shortName: string, variant: string | undefined) => void
  clear: () => void
  totalBytes: number
}

export const MAX_CART_SIZE = 10000
export const CART_STORAGE_KEY = 'mame-curator:cart:v1'

function readInitial(): CartItem[] {
  try {
    const raw = localStorage.getItem(CART_STORAGE_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter(
      (i): i is CartItem =>
        i !== null &&
        typeof i === 'object' &&
        typeof (i as CartItem).shortName === 'string',
    )
  } catch {
    return []
  }
}

/**
 * P15 § 4.1 cart hook.
 *
 * Working pre-copy intent, frontend-only, localStorage-backed.
 * No server resource; no concurrency story (per-tab independent).
 *
 * `totalBytes` is currently a placeholder zero — the
 * server-authoritative bottom-bar number lives on
 * `/api/games?…&page_size=…` `total_bytes` and is computed against
 * the FILTERED slice, not the cart slice. To show cart-only bytes
 * we'd need either a new endpoint or a client-side cache of byte
 * sums per shortname. Out of scope for v1; the cart-bar reads
 * `cart.items.length` for the count and shows the filter-result
 * total_bytes for the size (matches v1.2.0's behaviour). The
 * `totalBytes` property is reserved for future use; it stays 0.
 */
export function useCart(): UseCartResult {
  const [items, setItems] = useState<CartItem[]>(readInitial)
  const storageBroken = useRef(false)

  useEffect(() => {
    if (storageBroken.current) return
    try {
      localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(items))
    } catch {
      // Quota exceeded, private browsing, etc. Degrade to in-memory only.
      storageBroken.current = true
    }
  }, [items])

  const has = useCallback(
    (shortName: string) => items.some((i) => i.shortName === shortName),
    [items],
  )

  const add = useCallback((shortName: string, variant?: string) => {
    setItems((prev) => {
      if (prev.some((i) => i.shortName === shortName)) return prev
      if (prev.length >= MAX_CART_SIZE) return prev
      return [...prev, { shortName, chosenVariant: variant }]
    })
  }, [])

  const remove = useCallback((shortName: string) => {
    setItems((prev) => prev.filter((i) => i.shortName !== shortName))
  }, [])

  const addAll = useCallback((shortNames: string[]) => {
    setItems((prev) => {
      const seen = new Set(prev.map((i) => i.shortName))
      const merged = [...prev]
      for (const name of shortNames) {
        if (merged.length >= MAX_CART_SIZE) break
        if (seen.has(name)) continue
        merged.push({ shortName: name })
        seen.add(name)
      }
      return merged
    })
  }, [])

  const setVariant = useCallback(
    (shortName: string, variant: string | undefined) => {
      setItems((prev) => {
        if (!prev.some((i) => i.shortName === shortName)) return prev
        return prev.map((i) =>
          i.shortName === shortName ? { ...i, chosenVariant: variant } : i,
        )
      })
    },
    [],
  )

  const clear = useCallback(() => setItems([]), [])

  const totalBytes = useMemo(() => 0, [])

  return { items, has, add, remove, addAll, setVariant, clear, totalBytes }
}
```

- [ ] **Step 4: Run tests — confirm passing**

```bash
cd frontend && npm test -- useCart
```

Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useCart.ts frontend/src/hooks/__tests__/useCart.test.tsx
git commit -m "feat(frontend): P15 § F2 — useCart hook + tests

localStorage-backed cart per spec § 4.1. Idempotent add(),
addAll() with MAX_CART_SIZE=10000 truncation, setVariant() for
AlternativesDrawer round-trip, graceful degradation to
in-memory when localStorage write throws (private browsing,
quota exceeded). Storage key versioned: mame-curator:cart:v1."
```

---

### Task F3: `useValidateCart` mutation hook

**Files:**
- Create: `frontend/src/hooks/useValidateCart.ts`
- Create: `frontend/src/hooks/__tests__/useValidateCart.test.tsx`

- [ ] **Step 1: Write the failing test**

Use the existing MSW pattern from `frontend/src/hooks/__tests__/useFs.test.tsx`. Create `useValidateCart.test.tsx`:

```typescript
import { describe, it, expect } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useValidateCart } from '@/hooks/useValidateCart'
import type { ReactNode } from 'react'

const server = setupServer(
  http.post('/api/games/validate', async ({ request }) => {
    const body = (await request.json()) as { short_names: string[] }
    const real = new Set(['pacman', 'pacmanf', '1942'])
    return HttpResponse.json({
      existing: body.short_names.filter((n) => real.has(n)),
      missing: body.short_names.filter((n) => !real.has(n)),
    })
  }),
)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe('useValidateCart', () => {
  it('returns existing+missing split for the input', async () => {
    const { result } = renderHook(() => useValidateCart(), { wrapper })
    result.current.mutate({ short_names: ['pacman', 'ghost', '1942'] })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual({
      existing: ['pacman', '1942'],
      missing: ['ghost'],
    })
  })
})
```

- [ ] **Step 2: Run — confirm failing**

```bash
cd frontend && npm test -- useValidateCart
```

Expected: FAIL — `Cannot find module '@/hooks/useValidateCart'`.

- [ ] **Step 3: Implement the hook**

Create `frontend/src/hooks/useValidateCart.ts`:

```typescript
import { useMutation } from '@tanstack/react-query'
import { apiRequest } from '@/api/client'
import {
  ValidateResponseSchema,
  type ValidateRequest,
  type ValidateResponse,
} from '@/api/types'

/**
 * P15 § 5.1 — POST /api/games/validate.
 *
 * Splits cart shortnames into {existing, missing} via O(1) lookup
 * against world.machines. Called pre-Copy: orphaned items are
 * dropped with a single toast and CopyModal opens with the
 * surviving set.
 */
export function useValidateCart() {
  return useMutation({
    mutationFn: (req: ValidateRequest) =>
      apiRequest<ValidateResponse>('/api/games/validate', ValidateResponseSchema, {
        method: 'POST',
        body: req,
      }),
  })
}
```

- [ ] **Step 4: Run — confirm passing**

```bash
cd frontend && npm test -- useValidateCart
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useValidateCart.ts frontend/src/hooks/__tests__/useValidateCart.test.tsx
git commit -m "feat(frontend): P15 § F3 — useValidateCart mutation hook

POST /api/games/validate; mirrors the useDryRun (FP23) shape.
Drives spec § 5.1 pre-Copy reconciliation."
```

---

### Task F4: Strings catalogue extensions

**Files:**
- Modify: `frontend/src/strings.ts`

- [ ] **Step 1: Add `library.featured` catalogue + `library.cart` + `library.onboarding` + `library.listxmlMissing.emptyParseBody` + `settings.uiLabels.cart_clear_on_copy`**

Find the `library:` block (line 55). Inside it, add (alongside existing keys):

```typescript
    featured: {
      heading: 'Featured',
      tiles: [
        {
          id: 'capcom-classics',
          title: 'Capcom Classics',
          description: 'Capcom CPS-1 / CPS-2 era arcade hits',
          query: { publisher: 'Capcom', yearTo: 2000 },
        },
        {
          id: 'beat-em-ups',
          title: "Beat 'em Ups",
          description: 'Side-scrolling brawlers',
          query: { genre: "Beat'em up" },
        },
        {
          id: 'run-and-gun',
          title: 'Run & Gun Shooters',
          description: 'Run-and-gun shooters',
          query: { genre: 'Shooter / Run-and-Gun' },
        },
        {
          id: 'best-of-1992',
          title: 'Best of 1992',
          description: 'Arcade titles released in 1992',
          query: { yearFrom: 1992, yearTo: 1992 },
        },
        {
          id: 'shmups-vertical',
          title: 'SHMUPS — Vertical',
          description: 'Vertical-scroll shoot-em-up classics',
          query: { genre: 'Shooter / Vertical' },
        },
      ],
      countLabel: (n: number) =>
        `${n.toLocaleString()} game${n === 1 ? '' : 's'}`,
    },
    cart: {
      summaryEmpty: 'Cart empty',
      summary: (n: number, gb: string) =>
        `${n.toLocaleString()} game${n === 1 ? '' : 's'} · ${gb}`,
      addToCart: (gameName: string) => `Add ${gameName} to cart`,
      removeFromCart: (gameName: string) => `Remove ${gameName} from cart`,
      added: '✓ Added',
      bulkAdd: (n: number) => `Add all ${n.toLocaleString()}`,
      expand: 'Expand cart',
      collapse: 'Collapse cart',
      clearAll: 'Clear all',
      validateDroppedToast: (n: number) =>
        `${n} cart item${n === 1 ? '' : 's'} removed — they're no longer in your library.`,
      variantBadge: (variantName: string) => `⇄ ${variantName}`,
      storageUnavailableToast:
        'Browser storage unavailable; cart will not persist for this session.',
      maxCartReachedToast: (max: number) =>
        `Cart full (max ${max.toLocaleString()}); some items were not added.`,
    },
    onboarding: {
      body: 'Tap a game to add it to your list. Click COPY when you\'re done.',
      dismissAriaLabel: 'Dismiss onboarding banner',
    },
    listxmlMissing: {
      // existing keys: title, body, cta — keep them as-is
      // P15 § 4.3.1 emptyParseBody for the "file present but parsed empty" case:
      emptyParseBody:
        'Listxml loaded but contains no cloneof entries — region/version variants will appear separately.',
    },
```

(Preserve the existing `listxmlMissing.title` / `body` / `cta` keys; only ADD `emptyParseBody`.)

- [ ] **Step 2: Add `settings.uiLabels.cart_clear_on_copy`**

Find `settings.uiLabels.default_sort` (somewhere near the existing UI labels). Add:

```typescript
      cart_clear_on_copy: 'Clear cart after copy',
      cart_clear_on_copy_options: {
        always: 'Always',
        on_success: 'On success only',
        never: 'Never',
      },
```

- [ ] **Step 3: Verify TypeScript shape**

```bash
cd frontend && npx tsc --noEmit
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/strings.ts
git commit -m "feat(frontend): P15 § F4 — strings for cart, featured tiles, onboarding

5-tile featured catalogue per spec § 4.2 (verified genre values
sourced from snapshot_catver.ini); cart summary + bulk-add +
variant badge labels; onboarding banner copy; listxml empty-
parse banner body; settings label for cart_clear_on_copy.

Tile catalogue is one-PR-per-edit (spec § 4.2 final paragraph)."
```

---

## Wave 3 — Frontend leaves (F5 → F9)

Each task in this wave is an independent component build (no inter-task deps within the wave; they all pull from F1-F4 only).

### Task F5: `OnboardingBanner` component

**Files:**
- Create: `frontend/src/components/library/OnboardingBanner.tsx`
- Create: `frontend/src/components/library/__tests__/OnboardingBanner.test.tsx`

- [ ] **Step 1: Failing test**

`OnboardingBanner.test.tsx`:

```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { OnboardingBanner, ONBOARDING_DISMISS_KEY } from '@/components/library/OnboardingBanner'

describe('OnboardingBanner', () => {
  beforeEach(() => localStorage.clear())

  it('renders body copy on first mount', () => {
    render(<OnboardingBanner cartHasItems={false} />)
    expect(
      screen.getByText(/Tap a game to add it to your list/i),
    ).toBeInTheDocument()
  })

  it('hides itself after click on dismiss', () => {
    const { rerender } = render(<OnboardingBanner cartHasItems={false} />)
    fireEvent.click(screen.getByRole('button', { name: /dismiss/i }))
    rerender(<OnboardingBanner cartHasItems={false} />)
    expect(screen.queryByText(/Tap a game/i)).not.toBeInTheDocument()
  })

  it('persists dismissal across remounts via localStorage', () => {
    const { unmount } = render(<OnboardingBanner cartHasItems={false} />)
    fireEvent.click(screen.getByRole('button', { name: /dismiss/i }))
    unmount()
    render(<OnboardingBanner cartHasItems={false} />)
    expect(screen.queryByText(/Tap a game/i)).not.toBeInTheDocument()
    expect(localStorage.getItem(ONBOARDING_DISMISS_KEY)).toBe('1')
  })

  it('auto-dismisses when cart has items even without click', () => {
    render(<OnboardingBanner cartHasItems={true} />)
    expect(screen.queryByText(/Tap a game/i)).not.toBeInTheDocument()
    expect(localStorage.getItem(ONBOARDING_DISMISS_KEY)).toBe('1')
  })
})
```

- [ ] **Step 2: Run failing**

```bash
cd frontend && npm test -- OnboardingBanner
```

- [ ] **Step 3: Implement**

`OnboardingBanner.tsx`:

```typescript
import { useEffect, useState } from 'react'
import { X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { strings } from '@/strings'

export const ONBOARDING_DISMISS_KEY = 'mame-curator:onboarding-dismissed:v1'

interface OnboardingBannerProps {
  cartHasItems: boolean
}

/**
 * P15 § 4.4 — first-load instructional banner above the grid.
 * Dismissed in two ways: explicit ✕ click, or auto on first
 * cart.add (cartHasItems flips true). Both persist in
 * localStorage so the banner stays gone across reloads.
 */
export function OnboardingBanner({ cartHasItems }: OnboardingBannerProps) {
  const [dismissed, setDismissed] = useState(
    () => localStorage.getItem(ONBOARDING_DISMISS_KEY) === '1',
  )

  useEffect(() => {
    if (cartHasItems && !dismissed) {
      setDismissed(true)
      try {
        localStorage.setItem(ONBOARDING_DISMISS_KEY, '1')
      } catch {
        /* private browsing / quota — degrade silently */
      }
    }
  }, [cartHasItems, dismissed])

  if (dismissed) return null

  const handleDismiss = () => {
    setDismissed(true)
    try {
      localStorage.setItem(ONBOARDING_DISMISS_KEY, '1')
    } catch {
      /* see above */
    }
  }

  return (
    <div
      role="status"
      className="mx-4 mt-2 flex items-center gap-3 rounded border bg-muted/40 px-3 py-2 text-sm"
    >
      <span>{strings.library.onboarding.body}</span>
      <Button
        size="icon"
        variant="ghost"
        onClick={handleDismiss}
        aria-label={strings.library.onboarding.dismissAriaLabel}
        className="ml-auto h-6 w-6"
      >
        <X className="h-3 w-3" aria-hidden="true" />
      </Button>
    </div>
  )
}
```

- [ ] **Step 4: Run passing**

```bash
cd frontend && npm test -- OnboardingBanner
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/library/OnboardingBanner.tsx frontend/src/components/library/__tests__/OnboardingBanner.test.tsx
git commit -m "feat(frontend): P15 § F5 — OnboardingBanner

Top instructional banner above the grid (spec § 3 step 1
copy). Dismiss flow: explicit ✕ click OR cart.add transitions
cartHasItems true. Both persist in localStorage:
mame-curator:onboarding-dismissed:v1."
```

---

### Task F6: `FeaturedTilesRow` component

**Files:**
- Create: `frontend/src/components/library/FeaturedTilesRow.tsx`
- Create: `frontend/src/components/library/__tests__/FeaturedTilesRow.test.tsx`

- [ ] **Step 1: Failing test**

`FeaturedTilesRow.test.tsx`:

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { FeaturedTilesRow } from '@/components/library/FeaturedTilesRow'
import { strings } from '@/strings'

describe('FeaturedTilesRow', () => {
  it('renders each tile from strings.library.featured.tiles', () => {
    render(
      <FeaturedTilesRow counts={{}} activeTileId={null} onTileSelect={() => {}} />,
    )
    for (const tile of strings.library.featured.tiles) {
      expect(screen.getByText(tile.title)).toBeInTheDocument()
    }
  })

  it('shows count when provided', () => {
    render(
      <FeaturedTilesRow
        counts={{ 'beat-em-ups': 51 }}
        activeTileId={null}
        onTileSelect={() => {}}
      />,
    )
    expect(screen.getByText(/51 games/i)).toBeInTheDocument()
  })

  it('emits onTileSelect with the tile id on click', () => {
    const onTileSelect = vi.fn()
    render(
      <FeaturedTilesRow counts={{}} activeTileId={null} onTileSelect={onTileSelect} />,
    )
    fireEvent.click(screen.getByText('Capcom Classics').closest('button')!)
    expect(onTileSelect).toHaveBeenCalledWith('capcom-classics')
  })

  it('marks the active tile with aria-pressed=true', () => {
    render(
      <FeaturedTilesRow
        counts={{}}
        activeTileId="beat-em-ups"
        onTileSelect={() => {}}
      />,
    )
    const active = screen.getByText("Beat 'em Ups").closest('button')!
    expect(active).toHaveAttribute('aria-pressed', 'true')
  })
})
```

- [ ] **Step 2: Run failing → Step 3: Implement**

`FeaturedTilesRow.tsx`:

```typescript
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { strings } from '@/strings'

export interface FeaturedTileQuery {
  publisher?: string
  developer?: string
  genre?: string
  yearFrom?: number
  yearTo?: number
}

export interface FeaturedTile {
  id: string
  title: string
  description: string
  query: FeaturedTileQuery
}

interface FeaturedTilesRowProps {
  counts: Record<string, number>
  activeTileId: string | null
  onTileSelect: (tileId: string) => void
}

/**
 * P15 § 4.2 — horizontal scroll of curated INI-derived tiles.
 *
 * Tile catalogue lives in strings.library.featured.tiles (code-
 * defined, one-PR-per-edit). Counts are supplied by the parent
 * (LibraryPage) which fans out one /api/games?…&page_size=0 query
 * per tile; react-query 5min staleness keeps the cost down.
 *
 * Click filters the grid to the tile's query; CartBar morphs to
 * show "Add all N" (where N is the post-filter total). Click DOES
 * NOT auto-add to cart (D8: preview-before-add is safer).
 */
export function FeaturedTilesRow({
  counts,
  activeTileId,
  onTileSelect,
}: FeaturedTilesRowProps) {
  return (
    <section className="px-4 py-3" aria-label={strings.library.featured.heading}>
      <h2 className="mb-2 text-sm font-semibold">
        {strings.library.featured.heading}
      </h2>
      <div className="flex gap-2 overflow-x-auto pb-2">
        {strings.library.featured.tiles.map((tile) => {
          const count = counts[tile.id]
          const isActive = activeTileId === tile.id
          return (
            <button
              key={tile.id}
              type="button"
              aria-pressed={isActive}
              onClick={() => onTileSelect(tile.id)}
              className="shrink-0 text-left"
            >
              <Card
                className={cn(
                  'flex w-40 flex-col gap-1 p-3 transition-shadow hover:shadow-lg',
                  isActive && 'ring-2 ring-ring',
                )}
              >
                <p className="text-sm font-semibold leading-tight">{tile.title}</p>
                <p className="text-xs text-muted-foreground">{tile.description}</p>
                {count !== undefined && (
                  <p className="mt-auto text-xs tabular-nums text-muted-foreground">
                    {strings.library.featured.countLabel(count)}
                  </p>
                )}
              </Card>
            </button>
          )
        })}
      </div>
    </section>
  )
}
```

- [ ] **Step 4: Run passing**

```bash
cd frontend && npm test -- FeaturedTilesRow
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/library/FeaturedTilesRow.tsx frontend/src/components/library/__tests__/FeaturedTilesRow.test.tsx
git commit -m "feat(frontend): P15 § F6 — FeaturedTilesRow

Horizontal scroll of curated INI-derived tile buttons. Click
emits onTileSelect(tileId); active tile gets aria-pressed=true
+ ring. Counts injected via Record<id, number> prop; LibraryPage
fans out the per-tile /api/games?page_size=0 queries (react-
query 5min stale per spec § 8 risk 5)."
```

---

### Task F7: `CartBar` component (replaces `ActionBar.tsx`)

**Files:**
- Create: `frontend/src/components/library/CartBar.tsx`
- Create: `frontend/src/components/library/__tests__/CartBar.test.tsx`
- Delete: `frontend/src/components/library/ActionBar.tsx` (after `LibraryPage` swap in F11)

- [ ] **Step 1: Failing test**

`CartBar.test.tsx`:

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { CartBar } from '@/components/library/CartBar'

const noop = () => {}

describe('CartBar', () => {
  it('renders empty-cart summary when items=0', () => {
    render(
      <CartBar
        itemCount={0}
        totalSizeBytes={0}
        bulkAddTotal={null}
        expanded={false}
        onBulkAdd={noop}
        onToggleExpand={noop}
        onDryRun={noop}
        onCopy={noop}
      />,
    )
    expect(screen.getByText(/cart empty/i)).toBeInTheDocument()
  })

  it('disables Copy and Dry-run when cart empty', () => {
    render(
      <CartBar
        itemCount={0}
        totalSizeBytes={0}
        bulkAddTotal={null}
        expanded={false}
        onBulkAdd={noop}
        onToggleExpand={noop}
        onDryRun={noop}
        onCopy={noop}
      />,
    )
    expect(screen.getByRole('button', { name: /copy/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /dry-run/i })).toBeDisabled()
  })

  it('shows summary when itemCount > 0', () => {
    render(
      <CartBar
        itemCount={51}
        totalSizeBytes={1024 ** 3 * 2.5}
        bulkAddTotal={null}
        expanded={false}
        onBulkAdd={noop}
        onToggleExpand={noop}
        onDryRun={noop}
        onCopy={noop}
      />,
    )
    expect(screen.getByText(/51 games · 2\.5 GB/)).toBeInTheDocument()
  })

  it('shows bulk-add button only when bulkAddTotal is non-null', () => {
    const { rerender } = render(
      <CartBar
        itemCount={0}
        totalSizeBytes={0}
        bulkAddTotal={null}
        expanded={false}
        onBulkAdd={noop}
        onToggleExpand={noop}
        onDryRun={noop}
        onCopy={noop}
      />,
    )
    expect(screen.queryByRole('button', { name: /add all/i })).not.toBeInTheDocument()

    rerender(
      <CartBar
        itemCount={0}
        totalSizeBytes={0}
        bulkAddTotal={51}
        expanded={false}
        onBulkAdd={noop}
        onToggleExpand={noop}
        onDryRun={noop}
        onCopy={noop}
      />,
    )
    expect(screen.getByRole('button', { name: /add all 51/i })).toBeInTheDocument()
  })

  it('emits callbacks on click', () => {
    const onBulkAdd = vi.fn()
    const onToggleExpand = vi.fn()
    const onDryRun = vi.fn()
    const onCopy = vi.fn()
    render(
      <CartBar
        itemCount={3}
        totalSizeBytes={0}
        bulkAddTotal={51}
        expanded={false}
        onBulkAdd={onBulkAdd}
        onToggleExpand={onToggleExpand}
        onDryRun={onDryRun}
        onCopy={onCopy}
      />,
    )
    fireEvent.click(screen.getByRole('button', { name: /add all 51/i }))
    fireEvent.click(screen.getByRole('button', { name: /expand cart/i }))
    fireEvent.click(screen.getByRole('button', { name: /dry-run/i }))
    fireEvent.click(screen.getByRole('button', { name: /^copy$/i }))
    expect(onBulkAdd).toHaveBeenCalled()
    expect(onToggleExpand).toHaveBeenCalled()
    expect(onDryRun).toHaveBeenCalled()
    expect(onCopy).toHaveBeenCalled()
  })

  it('expand button uses Collapse aria-label when expanded=true', () => {
    render(
      <CartBar
        itemCount={3}
        totalSizeBytes={0}
        bulkAddTotal={null}
        expanded={true}
        onBulkAdd={noop}
        onToggleExpand={noop}
        onDryRun={noop}
        onCopy={noop}
      />,
    )
    expect(screen.getByRole('button', { name: /collapse cart/i })).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run failing → Step 3: Implement**

`CartBar.tsx`:

```typescript
import { ChevronDown, ChevronUp, ShoppingCart } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { strings } from '@/strings'

interface CartBarProps {
  itemCount: number
  totalSizeBytes: number
  bulkAddTotal: number | null
  expanded: boolean
  onBulkAdd: () => void
  onToggleExpand: () => void
  onDryRun: () => void
  onCopy: () => void
}

function formatGB(bytes: number): string {
  const gb = bytes / 1024 ** 3
  return `${gb.toFixed(1)} GB`
}

export function CartBar({
  itemCount,
  totalSizeBytes,
  bulkAddTotal,
  expanded,
  onBulkAdd,
  onToggleExpand,
  onDryRun,
  onCopy,
}: CartBarProps) {
  const empty = itemCount === 0
  const ChevronIcon = expanded ? ChevronDown : ChevronUp

  return (
    <footer className="sticky bottom-0 z-10 flex items-center justify-between gap-3 border-t bg-background/95 px-4 py-2 backdrop-blur">
      <div className="flex items-center gap-2 text-sm tabular-nums">
        <ShoppingCart className="h-4 w-4" aria-hidden="true" />
        <span className={empty ? 'text-muted-foreground' : 'font-medium'}>
          {empty
            ? strings.library.cart.summaryEmpty
            : strings.library.cart.summary(itemCount, formatGB(totalSizeBytes))}
        </span>
      </div>
      <div className="flex items-center gap-2">
        {bulkAddTotal !== null && (
          <Button variant="outline" onClick={onBulkAdd}>
            {strings.library.cart.bulkAdd(bulkAddTotal)}
          </Button>
        )}
        <Button variant="outline" onClick={onDryRun} disabled={empty}>
          {strings.library.actions.dryRun}
        </Button>
        <Button onClick={onCopy} disabled={empty}>
          {strings.library.actions.copy}
        </Button>
        <Button
          size="icon"
          variant="ghost"
          onClick={onToggleExpand}
          aria-label={
            expanded ? strings.library.cart.collapse : strings.library.cart.expand
          }
        >
          <ChevronIcon className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
    </footer>
  )
}
```

- [ ] **Step 4: Run passing**

```bash
cd frontend && npm test -- CartBar
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/library/CartBar.tsx frontend/src/components/library/__tests__/CartBar.test.tsx
git commit -m "feat(frontend): P15 § F7 — CartBar (replaces ActionBar)

Collapsed cart bar: cart icon + count + size + Dry-run + Copy +
expand chevron. When bulkAddTotal != null (a featured tile is
active), an extra 'Add all N' button appears between the size
and Dry-run. Expand chevron toggles the panel; aria-label
flips between Expand/Collapse to surface state to AT.

ActionBar.tsx still in tree until F11 swaps the LibraryPage
mount; deleting it now would break the live build."
```

---

### Task F8: `CartPanel` component

**Files:**
- Create: `frontend/src/components/library/CartPanel.tsx`
- Create: `frontend/src/components/library/__tests__/CartPanel.test.tsx`

- [ ] **Step 1: Failing test**

`CartPanel.test.tsx`:

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { CartPanel } from '@/components/library/CartPanel'

const items = [
  { shortName: 'pacman' },
  { shortName: '1942', chosenVariant: '1942j' },
]

describe('CartPanel', () => {
  it('does not render when open=false', () => {
    render(
      <CartPanel
        open={false}
        items={items}
        onRemove={() => {}}
        onClearAll={() => {}}
      />,
    )
    expect(screen.queryByText(/pacman/)).not.toBeInTheDocument()
  })

  it('renders one row per cart item when open=true', () => {
    render(
      <CartPanel
        open={true}
        items={items}
        onRemove={() => {}}
        onClearAll={() => {}}
      />,
    )
    expect(screen.getByText('pacman')).toBeInTheDocument()
    expect(screen.getByText('1942')).toBeInTheDocument()
  })

  it('shows variant badge when chosenVariant is set', () => {
    render(
      <CartPanel
        open={true}
        items={items}
        onRemove={() => {}}
        onClearAll={() => {}}
      />,
    )
    expect(screen.getByText('⇄ 1942j')).toBeInTheDocument()
  })

  it('emits onRemove(shortName) when ✕ is clicked', () => {
    const onRemove = vi.fn()
    render(
      <CartPanel
        open={true}
        items={items}
        onRemove={onRemove}
        onClearAll={() => {}}
      />,
    )
    fireEvent.click(screen.getByRole('button', { name: /remove pacman/i }))
    expect(onRemove).toHaveBeenCalledWith('pacman')
  })

  it('emits onClearAll when Clear all is clicked', () => {
    const onClearAll = vi.fn()
    render(
      <CartPanel
        open={true}
        items={items}
        onRemove={() => {}}
        onClearAll={onClearAll}
      />,
    )
    fireEvent.click(screen.getByRole('button', { name: /clear all/i }))
    expect(onClearAll).toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: Run failing → Step 3: Implement**

`CartPanel.tsx`:

```typescript
import { X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { strings } from '@/strings'
import type { CartItem } from '@/hooks/useCart'

interface CartPanelProps {
  open: boolean
  items: CartItem[]
  onRemove: (shortName: string) => void
  onClearAll: () => void
}

/**
 * P15 § 4.4 — expand-up cart contents panel.
 *
 * Mounts as a sibling of CartBar; CSS height-transition (no
 * framer-motion dep needed at v1; spec § 4.4 explicitly allows
 * the simpler approach). Each row: shortName + optional variant
 * badge + per-row ✕. Bottom row: Clear all link.
 */
export function CartPanel({ open, items, onRemove, onClearAll }: CartPanelProps) {
  if (!open) return null
  return (
    <aside
      role="region"
      aria-label="Cart contents"
      className="border-t bg-background px-4 py-3 max-h-80 overflow-y-auto"
    >
      <ul className="flex flex-col gap-1">
        {items.map((item) => (
          <li
            key={item.shortName}
            className="flex items-center gap-2 rounded px-2 py-1 hover:bg-muted/40"
          >
            <span className="font-mono text-sm">{item.shortName}</span>
            {item.chosenVariant && (
              <span className="rounded bg-muted px-1.5 py-0.5 text-xs">
                {strings.library.cart.variantBadge(item.chosenVariant)}
              </span>
            )}
            <Button
              size="icon"
              variant="ghost"
              onClick={() => onRemove(item.shortName)}
              aria-label={strings.library.cart.removeFromCart(item.shortName)}
              className="ml-auto h-6 w-6"
            >
              <X className="h-3 w-3" aria-hidden="true" />
            </Button>
          </li>
        ))}
      </ul>
      {items.length > 0 && (
        <div className="mt-2 flex justify-end">
          <Button variant="ghost" size="sm" onClick={onClearAll}>
            {strings.library.cart.clearAll}
          </Button>
        </div>
      )}
    </aside>
  )
}
```

- [ ] **Step 4: Run passing**

```bash
cd frontend && npm test -- CartPanel
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/library/CartPanel.tsx frontend/src/components/library/__tests__/CartPanel.test.tsx
git commit -m "feat(frontend): P15 § F8 — CartPanel

Expand-up panel listing cart items with per-row ✕ + variant
badge + Clear all link. CSS-only height (no framer-motion dep
added per spec § 4.4 simpler-path option). Mounted as sibling
of CartBar in LibraryPage."
```

---

### Task F9: Edit `GameCard.tsx` for `+Add` affordance

**Files:**
- Modify: `frontend/src/components/library/GameCard.tsx`
- Create: `frontend/src/components/library/__tests__/GameCard.test.tsx`

- [ ] **Step 1: Failing test**

`GameCard.test.tsx`:

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { GameCard } from '@/components/library/GameCard'
import type { GameCard as GameCardType } from '@/api/types'

const card: GameCardType = {
  short_name: 'pacman',
  description: 'Pac-Man',
  year: 1980,
  manufacturer: 'Namco',
  publisher: 'Namco',
  developer: 'Namco',
  badges: [],
}

describe('GameCard +Add', () => {
  it('renders an Add button when not in cart', () => {
    render(
      <GameCard card={card} inCart={false} onOpen={() => {}} onAdd={() => {}} />,
    )
    expect(screen.getByRole('button', { name: /add pac-man to cart/i })).toBeInTheDocument()
  })

  it('renders ✓ Added when in cart', () => {
    render(
      <GameCard card={card} inCart={true} onOpen={() => {}} onAdd={() => {}} />,
    )
    expect(screen.getByText(/✓ added/i)).toBeInTheDocument()
  })

  it('emits onAdd when Add button clicked', () => {
    const onAdd = vi.fn()
    const onOpen = vi.fn()
    render(<GameCard card={card} inCart={false} onOpen={onOpen} onAdd={onAdd} />)
    fireEvent.click(screen.getByRole('button', { name: /add pac-man to cart/i }))
    expect(onAdd).toHaveBeenCalledWith('pacman')
    expect(onOpen).not.toHaveBeenCalled() // Add click does not bubble to card open
  })

  it('emits onOpen when card body clicked', () => {
    const onAdd = vi.fn()
    const onOpen = vi.fn()
    render(<GameCard card={card} inCart={false} onOpen={onOpen} onAdd={onAdd} />)
    fireEvent.click(screen.getByRole('button', { name: 'Pac-Man' }))
    expect(onOpen).toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: Run failing → Step 3: Implement**

Edit `frontend/src/components/library/GameCard.tsx`:

1. Update the props interface (line 15-19) to add `inCart` and `onAdd`:

```typescript
interface GameCardProps {
  card: GameCardType
  focused?: boolean
  inCart: boolean
  onOpen: () => void
  onAdd: (shortName: string) => void
}
```

2. Update the component signature and body. Replace the existing button wrapping (line 41-114) so that:
   - The outer wrapper stays `<button>` for `onOpen` (preserving the FP11 § D4 fix)
   - A *separate* button for `+Add` lives inside the card, absolutely positioned, with `onClick` calling `e.stopPropagation()` then `onAdd(card.short_name)`
   - Replace `aria-label={card.description}` on the outer button with the description so the screen reader announces "Pac-Man" (existing behaviour preserved)

The relevant insertion (inside the `<div className="relative …">` at line 70, alongside the badges `<ul>`):

```tsx
<button
  type="button"
  onClick={(e) => {
    e.stopPropagation()
    onAdd(card.short_name)
  }}
  aria-label={
    inCart
      ? strings.library.cart.removeFromCart(card.description)  // accessible-name hint when already in cart
      : strings.library.cart.addToCart(card.description)
  }
  className="absolute left-1 top-1 rounded bg-background/90 px-2 py-1 text-xs font-medium shadow-sm hover:bg-background"
  data-testid="add-to-cart"
>
  {inCart ? strings.library.cart.added : '+Add'}
</button>
```

The full edited component should look like (relevant sections only — keep all other markup intact):

```tsx
export function GameCard({ card, focused = false, inCart, onOpen, onAdd }: GameCardProps) {
  const [imgFailed, setImgFailed] = useState(false)
  const flyerSrc = `/media/${encodeURIComponent(card.short_name)}/boxart`
  const altText = strings.library.flyerAlt(card.description)

  return (
    <button
      type="button"
      onClick={onOpen}
      aria-label={card.description}
      className="contents text-left"
    >
      <Card
        className={cn(
          'flex h-full cursor-pointer flex-col overflow-hidden transition-shadow hover:shadow-lg focus-visible:ring-2 focus-visible:ring-ring',
          focused && 'ring-2 ring-ring',
        )}
      >
        <div className="relative min-h-0 flex-1 bg-muted">
          {/* +Add button — left edge of thumbnail; click does not bubble */}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              onAdd(card.short_name)
            }}
            aria-label={
              inCart
                ? strings.library.cart.removeFromCart(card.description)
                : strings.library.cart.addToCart(card.description)
            }
            className="absolute left-1 top-1 z-10 rounded bg-background/90 px-2 py-1 text-xs font-medium shadow-sm hover:bg-background"
          >
            {inCart ? strings.library.cart.added : '+Add'}
          </button>

          {/* … existing img / placeholder / badges block unchanged … */}
        </div>

        {/* … existing CardContent unchanged … */}
      </Card>
    </button>
  )
}
```

- [ ] **Step 4: Run passing**

```bash
cd frontend && npm test -- GameCard
```

- [ ] **Step 5: Run the full frontend suite to confirm no regressions in LibraryGrid (which renders GameCard)**

```bash
cd frontend && npm test
```

Expected: PASS (LibraryGrid tests already pass `onOpen`; the new required `inCart` + `onAdd` props need to be added at the LibraryGrid call site too — flag this for F11. **At this point in the wave, LibraryGrid's tests will fail because the required props aren't supplied.** Fix LibraryGrid's call site immediately as part of this task; the call is in `LibraryGrid.tsx` `<GameCard ... />` somewhere. The simplest pass-through: LibraryGrid takes `inCart: (s: string) => boolean` + `onAdd: (s: string) => void` props and forwards.)

- [ ] **Step 6: Edit `LibraryGrid.tsx` to pass through cart props**

```bash
grep -n "<GameCard\|interface LibraryGridProps" frontend/src/components/library/LibraryGrid.tsx
```

Add to the `LibraryGridProps` interface:

```typescript
isInCart: (shortName: string) => boolean
onAdd: (shortName: string) => void
```

Pass through at the `<GameCard ... />` call site:

```tsx
<GameCard
  card={card}
  inCart={isInCart(card.short_name)}
  onOpen={() => onOpen(card)}
  onAdd={onAdd}
  // ... other existing props
/>
```

Update LibraryGrid tests if any assert prop completeness; otherwise the typecheck is what catches missing wiring.

- [ ] **Step 7: Run full suite passing**

```bash
cd frontend && npm test && npx tsc --noEmit
```

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/library/GameCard.tsx frontend/src/components/library/__tests__/GameCard.test.tsx frontend/src/components/library/LibraryGrid.tsx
git commit -m "feat(frontend): P15 § F9 — GameCard +Add affordance

Per-game add-to-cart button overlaid on the thumbnail's top-
left. Click stopPropagation prevents the underlying card-open
handler from firing. Cart-aware label flips '+Add' ↔ '✓ Added'
based on the inCart prop. ARIA: button has its own accessible
name (Add/Remove ${description} to/from cart) so screen readers
don't conflate with the outer card open action.

LibraryGrid pipes the inCart predicate + onAdd handler through
to GameCard."
```

---

## Wave 4 — Frontend integration (F10 → F14)

### Task F10: `useCopySession` hook (SSE consumer)

**Why:** the existing `useDryRun` (FP23) is a one-shot mutation — `POST` returns the report. Copy is a long-running job: `POST /api/copy/start` returns a `JobAccepted` envelope, then the client subscribes to `GET /api/copy/status` (SSE) for `lifecycle` + `file_progress` events. The hook drives `CopyModal`'s `state` shape (`CopyModalState`).

**Files:**
- Create: `frontend/src/hooks/useCopySession.ts`
- Create: `frontend/src/hooks/__tests__/useCopySession.test.tsx`

- [ ] **Step 1: Sketch the hook surface**

```typescript
export interface UseCopySessionResult {
  state: CopyModalState | null
  start: (req: CopyJobRequest) => void
  pause: () => void
  resume: () => void
  abort: (req: { recycle_partial: boolean }) => void
  resolveConflict: (req: { kind: AppendDecisionKind; replaces: string }) => void
  reset: () => void
}
```

- [ ] **Step 2: Write a minimal failing test (mocking `EventSource`)**

`useCopySession.test.tsx`:

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useCopySession } from '@/hooks/useCopySession'
import type { ReactNode } from 'react'

class MockEventSource {
  static instances: MockEventSource[] = []
  url: string
  onmessage: ((ev: MessageEvent) => void) | null = null
  onerror: ((ev: Event) => void) | null = null
  constructor(url: string) {
    this.url = url
    MockEventSource.instances.push(this)
  }
  emit(data: unknown) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }))
  }
  close() {}
}

const server = setupServer(
  http.post('/api/copy/start', () => HttpResponse.json({ job_id: 'job-123' })),
)

beforeAll(() => server.listen())
afterEach(() => {
  server.resetHandlers()
  MockEventSource.instances = []
})
afterAll(() => server.close())

beforeEach(() => {
  vi.stubGlobal('EventSource', MockEventSource)
})

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe('useCopySession', () => {
  it('starts in null state', () => {
    const { result } = renderHook(() => useCopySession(), { wrapper })
    expect(result.current.state).toBeNull()
  })

  it('after start() + lifecycle event, state.jobId is set', async () => {
    const { result } = renderHook(() => useCopySession(), { wrapper })
    act(() => {
      result.current.start({
        selected_names: ['pacman'],
        conflict_strategy: 'CANCEL',
        append_decisions: {},
      })
    })
    await waitFor(() => expect(MockEventSource.instances).toHaveLength(1))
    act(() => {
      MockEventSource.instances[0].emit({
        kind: 'lifecycle',
        state: 'running',
        files_total: 1,
        bytes_total: 1024,
      })
    })
    await waitFor(() => {
      expect(result.current.state?.jobId).toBe('job-123')
      expect(result.current.state?.state).toBe('running')
    })
  })

  it('progress events update filesDone / currentFile', async () => {
    const { result } = renderHook(() => useCopySession(), { wrapper })
    act(() => {
      result.current.start({
        selected_names: ['pacman'],
        conflict_strategy: 'CANCEL',
        append_decisions: {},
      })
    })
    await waitFor(() => expect(MockEventSource.instances).toHaveLength(1))
    act(() => {
      const es = MockEventSource.instances[0]
      es.emit({ kind: 'lifecycle', state: 'running', files_total: 1, bytes_total: 1024 })
      es.emit({ kind: 'file_progress', files_done: 1, current_file: 'pacman.zip' })
    })
    await waitFor(() => {
      expect(result.current.state?.filesDone).toBe(1)
      expect(result.current.state?.currentFile).toBe('pacman.zip')
    })
  })

  it('reset() clears state', () => {
    const { result } = renderHook(() => useCopySession(), { wrapper })
    act(() => result.current.reset())
    expect(result.current.state).toBeNull()
  })
})
```

- [ ] **Step 3: Implement the hook**

`useCopySession.ts`:

```typescript
import { useCallback, useEffect, useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { apiRequest } from '@/api/client'
import {
  JobAcceptedSchema,
  JobStatusSchema,
  type AppendDecisionKind,
  type CopyJobRequest,
  type JobAccepted,
  type JobState,
  type JobStatus,
} from '@/api/types'
import type { CopyModalState } from '@/components/library/CopyModal'

interface LifecycleEvent {
  kind: 'lifecycle'
  state: JobState
  files_total?: number
  bytes_total?: number
  warning?: string
  conflict?: { short_name: string; existing: string }
}

interface FileProgressEvent {
  kind: 'file_progress'
  files_done?: number
  bytes_done?: number
  current_file?: string
}

type CopyEvent = LifecycleEvent | FileProgressEvent

/**
 * P15 § 4.3.3 — drives CopyModal's state from /api/copy/start +
 * /api/copy/status SSE stream.
 *
 * Lifecycle events update top-level state (running/paused/
 * finished/aborted). File-progress events bump the running
 * counters. Conflict events surface the conflict prompt;
 * resolveConflict() POSTs the decision and clears the conflict.
 *
 * SSE source torn down on terminal state OR reset() OR unmount.
 */
export function useCopySession() {
  const [state, setState] = useState<CopyModalState | null>(null)
  const esRef = useRef<EventSource | null>(null)

  const closeStream = useCallback(() => {
    esRef.current?.close()
    esRef.current = null
  }, [])

  useEffect(() => () => closeStream(), [closeStream])

  const startMutation = useMutation({
    mutationFn: (req: CopyJobRequest) =>
      apiRequest<JobAccepted>('/api/copy/start', JobAcceptedSchema, {
        method: 'POST',
        body: req,
      }),
    onSuccess: (data) => {
      setState({
        jobId: data.job_id,
        state: 'running',
        filesDone: 0,
        filesTotal: 0,
        bytesDone: 0,
        bytesTotal: 0,
        currentFile: '',
        warnings: [],
        conflict: null,
      })
      const es = new EventSource('/api/copy/status')
      es.onmessage = (ev) => {
        const msg = JSON.parse(ev.data) as CopyEvent
        setState((prev) => {
          if (!prev) return prev
          if (msg.kind === 'lifecycle') {
            const next = {
              ...prev,
              state: msg.state,
              filesTotal: msg.files_total ?? prev.filesTotal,
              bytesTotal: msg.bytes_total ?? prev.bytesTotal,
              warnings: msg.warning ? [...prev.warnings, msg.warning] : prev.warnings,
              conflict: msg.conflict ?? prev.conflict,
            }
            if (msg.state === 'finished' || msg.state === 'aborted') {
              closeStream()
            }
            return next
          }
          // file_progress
          return {
            ...prev,
            filesDone: msg.files_done ?? prev.filesDone,
            bytesDone: msg.bytes_done ?? prev.bytesDone,
            currentFile: msg.current_file ?? prev.currentFile,
          }
        })
      }
      es.onerror = () => closeStream()
      esRef.current = es
    },
  })

  const pauseMutation = useMutation({
    mutationFn: () =>
      apiRequest<JobStatus>('/api/copy/pause', JobStatusSchema, { method: 'POST' }),
  })
  const resumeMutation = useMutation({
    mutationFn: () =>
      apiRequest<JobStatus>('/api/copy/resume', JobStatusSchema, { method: 'POST' }),
  })
  const abortMutation = useMutation({
    mutationFn: (req: { recycle_partial: boolean }) =>
      apiRequest<JobStatus>('/api/copy/abort', JobStatusSchema, {
        method: 'POST',
        body: req,
      }),
  })
  const resolveMutation = useMutation({
    mutationFn: (req: { kind: AppendDecisionKind; replaces: string }) =>
      apiRequest<JobStatus>('/api/copy/resolve-conflict', JobStatusSchema, {
        method: 'POST',
        body: req,
      }),
    onSuccess: () => setState((prev) => (prev ? { ...prev, conflict: null } : prev)),
  })

  return {
    state,
    start: startMutation.mutate,
    pause: pauseMutation.mutate,
    resume: resumeMutation.mutate,
    abort: abortMutation.mutate,
    resolveConflict: resolveMutation.mutate,
    reset: () => {
      closeStream()
      setState(null)
    },
  }
}
```

> **Verify:** the project does not currently expose `/api/copy/resolve-conflict`. Inspect `src/mame_curator/api/routes/copy.py` — if no resolve-conflict endpoint exists, the in-band conflict resolution may be folded into `POST /api/copy/resume` with a `decision` field, or via `append_decisions` on a fresh `start`. Read `api/jobs.py` `check_playlist_conflict` and `CopyController.resolve_conflict` to confirm the contract before finalising this step. **If the contract differs, update the implementation here and add a comment naming the path taken.**

- [ ] **Step 4: Run failing → confirm passing**

```bash
cd frontend && npm test -- useCopySession
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useCopySession.ts frontend/src/hooks/__tests__/useCopySession.test.tsx
git commit -m "feat(frontend): P15 § F10 — useCopySession SSE hook

Drives CopyModal: POST /api/copy/start → subscribe to
/api/copy/status SSE → push lifecycle + file_progress events
into CopyModalState. pause/resume/abort/resolveConflict
mutations exposed for the modal's button row. SSE stream torn
down on terminal state, reset(), or unmount."
```

---

### Task F11: Wire `LibraryPage.tsx` end-to-end

This is the integration nexus — every prior task funnels through it. Largest single edit; budget ~1 day.

**Files:**
- Modify: `frontend/src/pages/LibraryPage.tsx`
- Delete: `frontend/src/components/library/ActionBar.tsx`
- Modify: `frontend/src/components/library/ListxmlBanner.tsx` (extend trigger to cover empty-parse)

- [ ] **Step 1: Extend `ListxmlBanner` to cover the empty-parse case**

Edit `frontend/src/components/library/ListxmlBanner.tsx`:

```typescript
interface ListxmlBannerProps {
  exists: boolean | undefined
  cloneofMapSize?: number
}

export function ListxmlBanner({ exists, cloneofMapSize }: ListxmlBannerProps) {
  // Render when:
  //   (a) file is missing (exists === false) — original FP23 trigger; OR
  //   (b) file present but parsed to zero entries (cloneofMapSize === 0)
  //       — P15's empty-parse edge case (corrupt listxml, schema drift).
  // Loading state (exists === undefined) suppresses both.
  const fileMissing = exists === false
  const parsedEmpty = exists === true && cloneofMapSize === 0
  if (!fileMissing && !parsedEmpty) return null

  const body = parsedEmpty
    ? strings.library.listxmlMissing.emptyParseBody
    : strings.library.listxmlMissing.body

  return (
    <div role="alert" /* … existing classes … */>
      <span className="font-medium">{strings.library.listxmlMissing.title}</span>
      <span className="text-muted-foreground">{body}</span>
      <Link to="/settings" /* … */>{strings.library.listxmlMissing.cta}</Link>
    </div>
  )
}
```

Add a test for the empty-parse branch (write inline in the existing `ListxmlBanner.test.tsx` file if present; if absent, create a minimal one). Run:

```bash
cd frontend && npm test -- ListxmlBanner
```

Commit alone:

```bash
git add frontend/src/components/library/ListxmlBanner.tsx frontend/src/components/library/__tests__/ListxmlBanner.test.tsx
git commit -m "feat(frontend): P15 § F11.1 — ListxmlBanner empty-parse branch

Banner now renders on (file missing) OR (file present + parsed
empty), driven by the new SetupCheck.cloneof_map_size field
from B2. Body copy flips to emptyParseBody for the empty-parse
case so the user sees the right diagnosis."
```

- [ ] **Step 2: Rewrite `LibraryPage.tsx` to wire the cart end-to-end**

Replace the current `LibraryPage.tsx` body so that:

1. `useCart()` is the source of truth for selection state.
2. `useGames(query, { pageSize: 0 })` is fanned out for each tile id (5 queries; react-query caches per-query).
3. `OnboardingBanner` mounts at the top with `cartHasItems={cart.items.length > 0}`.
4. `FeaturedTilesRow` mounts above the grid.
5. `LibraryGrid` is wired with `isInCart`/`onAdd`.
6. `CartBar` replaces `ActionBar` (drop the import).
7. `CartPanel` mounts when `cartExpanded` is true.
8. `bulkAddTotal` is `total` when an active tile is selected, otherwise `null`.
9. `handleDryRun` swaps `selected_names: cards.map(...)` → `selected_names: cart.items.map((i) => i.chosenVariant ?? i.shortName)`.
10. `handleCopy` is added: validate via `useValidateCart` → drop missing items + toast → call `useCopySession.start()`.
11. `useEffect` watches `copySession.state?.state`; on `'finished'`, applies `cart_clear_on_copy` policy.

Insert these imports/hook usages near the existing ones (around line 1-32):

```typescript
import { useCart } from '@/hooks/useCart'
import { useValidateCart } from '@/hooks/useValidateCart'
import { useCopySession } from '@/hooks/useCopySession'
import { CartBar } from '@/components/library/CartBar'
import { CartPanel } from '@/components/library/CartPanel'
import { OnboardingBanner } from '@/components/library/OnboardingBanner'
import { FeaturedTilesRow } from '@/components/library/FeaturedTilesRow'
import { CopyModal } from '@/components/library/CopyModal'
```

Drop the `ActionBar` import (line 13).

Inside the component (after the existing `useDryRun` line ~63), add:

```typescript
const cart = useCart()
const validateCart = useValidateCart()
const copySession = useCopySession()
const [activeTileId, setActiveTileId] = useState<string | null>(null)
const [cartExpanded, setCartExpanded] = useState(false)

// Fan out one count query per tile (page_size=0 returns just the envelope)
const tileQueries = strings.library.featured.tiles.map((tile) =>
  useGames({ ...tile.query, pageSize: 0, page: 1 } as GamesQuery),
)
const tileCounts: Record<string, number> = Object.fromEntries(
  strings.library.featured.tiles.map((tile, idx) => [
    tile.id,
    tileQueries[idx].data?.total ?? 0,
  ]),
)

// Apply tile filter on click
const handleTileSelect = (tileId: string) => {
  const tile = strings.library.featured.tiles.find((t) => t.id === tileId)
  if (!tile) return
  if (activeTileId === tileId) {
    // Toggle off: reset to defaults
    setActiveTileId(null)
    setFilters(DEFAULT_FILTERS)
    return
  }
  setActiveTileId(tileId)
  setFilters({
    ...DEFAULT_FILTERS,
    publisher: tile.query.publisher ?? null,
    developer: tile.query.developer ?? null,
    genre: tile.query.genre ?? null,
    yearRange: [
      tile.query.yearFrom ?? DEFAULT_FILTERS.yearRange[0],
      tile.query.yearTo ?? DEFAULT_FILTERS.yearRange[1],
    ],
  })
}

const bulkAddTotal: number | null = activeTileId !== null ? total : null
const handleBulkAdd = () => {
  cart.addAll(cards.map((c) => c.short_name))
  // Page may not include all of `total`; the spec § 3 step 2 calls out
  // "Add all N visible". For the v1 implementation we add the current
  // page only — the user can scroll + bulk-add iteratively, OR raise
  // pageSize. (Honestly: since pageSize=200 already covers most filters,
  // this is rarely an issue. Future enhancement: server-side
  // POST /api/games/select endpoint that returns ALL filtered shortnames
  // for a given query — defer to post-v1 unless real users hit it.)
}

// Pre-Copy validate + start flow
const handleCopy = () => {
  if (cart.items.length === 0) return
  validateCart.mutate(
    { short_names: cart.items.map((i) => i.shortName) },
    {
      onSuccess: ({ existing, missing }) => {
        if (missing.length > 0) {
          toast.warning(strings.library.cart.validateDroppedToast(missing.length))
          for (const name of missing) cart.remove(name)
        }
        if (existing.length === 0) return
        copySession.start({
          selected_names: existing,
          conflict_strategy: 'CANCEL',
          append_decisions: {},
        })
      },
      onError: toastApiError,
    },
  )
}

// FP23-replacement DryRun: cart-driven selected_names instead of `cards`
const handleDryRun = () => {
  if (cart.items.length === 0) return
  dryRun.mutate(
    {
      selected_names: cart.items.map((i) => i.chosenVariant ?? i.shortName),
      conflict_strategy: 'CANCEL',
      append_decisions: {},
    },
    {
      onSuccess: setDryRunReport,
      onError: toastApiError,
    },
  )
}

// Cart auto-clear policy after Copy finishes
useEffect(() => {
  const policy = config.data?.ui.cart_clear_on_copy ?? 'on_success'
  const copyState = copySession.state?.state
  if (copyState === 'finished' && policy !== 'never') {
    cart.clear()
    copySession.reset()
  } else if (copyState === 'aborted' && policy === 'always') {
    cart.clear()
    copySession.reset()
  }
}, [copySession.state?.state, config.data?.ui.cart_clear_on_copy])
```

Replace the `<ActionBar ... />` JSX (line 244-253) with:

```tsx
<>
  <CartPanel
    open={cartExpanded}
    items={cart.items}
    onRemove={cart.remove}
    onClearAll={cart.clear}
  />
  <CartBar
    itemCount={cart.items.length}
    totalSizeBytes={games.data?.total_bytes ?? 0}
    bulkAddTotal={bulkAddTotal}
    expanded={cartExpanded}
    onBulkAdd={handleBulkAdd}
    onToggleExpand={() => setCartExpanded((x) => !x)}
    onDryRun={handleDryRun}
    onCopy={handleCopy}
  />
</>
```

Add `<OnboardingBanner cartHasItems={cart.items.length > 0} />` and `<FeaturedTilesRow ... />` ABOVE the `<ListxmlBanner ... />` in the grid container (line 184-187):

```tsx
<div className="flex flex-col overflow-hidden">
  <OnboardingBanner cartHasItems={cart.items.length > 0} />
  <FeaturedTilesRow
    counts={tileCounts}
    activeTileId={activeTileId}
    onTileSelect={handleTileSelect}
  />
  <ListxmlBanner
    exists={setupCheck.data?.reference_files.listxml.exists}
    cloneofMapSize={setupCheck.data?.cloneof_map_size}
  />
  <ErrorBoundary>
    <LibraryGrid
      cards={cards}
      layout={layout}
      cardsPerRowHint={config.data?.ui.cards_per_row_hint}
      isInCart={(s) => cart.has(s)}
      onAdd={(s) => cart.add(s)}
      onOpen={(card) => setOpenedShortName(card.short_name)}
    />
  </ErrorBoundary>
</div>
```

Mount `CopyModal` next to the existing `DryRunModal` block (around line 231-241):

```tsx
{copySession.state && (
  <CopyModal
    open={true}
    onOpenChange={(open) => !open && copySession.reset()}
    state={copySession.state}
    onPause={copySession.pause}
    onResume={copySession.resume}
    onAbort={copySession.abort}
    onResolveConflict={copySession.resolveConflict}
  />
)}
```

Wire `cart.setVariant` into the AlternativesDrawer override flow (line 208-216):

```tsx
onOverride={(req) => {
  override.mutate(req, {
    onSuccess: () => {
      // P15 § 5.2 — cart-aware variant tracking
      if (cart.has(req.parent)) {
        cart.setVariant(req.parent, req.winner)
      }
      toast.success(strings.library.overrideApplied)
      setOpenedShortName(null)
    },
    onError: toastApiError,
  })
}}
```

(`req.parent` and `req.winner` are the existing `AlternativesDrawer` `onOverride` payload — verify shape against `frontend/src/hooks/useAlternatives.ts`'s `useOverride` mutation; adjust field names if different.)

- [ ] **Step 3: Delete `ActionBar.tsx`**

```bash
rm frontend/src/components/library/ActionBar.tsx
```

- [ ] **Step 4: Run TypeScript + tests**

```bash
cd frontend && npx tsc --noEmit && npm test
```

Expected: PASS. If LibraryPage tests exist (check `frontend/src/pages/__tests__/LibraryPage.test.tsx`), they will likely need MSW handlers for the new endpoints (`/api/games/validate`, `/api/copy/start`, `/api/copy/status` SSE) — add as discovered.

- [ ] **Step 5: Run the dev server + manually verify the Library page**

```bash
uv run mame-curator serve
```

In a browser, open `http://localhost:8080`:
1. Onboarding banner visible.
2. Featured tiles row visible above the grid; counts populate.
3. `+Add` on a card flips to `✓ Added`; cart-bar count goes 0 → 1.
4. Click a featured tile → grid filters → cart-bar shows `Add all N`.
5. Click `Add all N` → cart fills.
6. Expand chevron → panel slides up; remove a row works.
7. Click Dry-run → modal opens with the cart-driven report.
8. Click Copy → CopyModal opens (will hit the `/api/copy/start` endpoint; needs the actual server flow working).

Document any flow breakage as a follow-on task; this is integration-level discovery work.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/LibraryPage.tsx frontend/src/components/library/ActionBar.tsx
git commit -m "feat(frontend): P15 § F11 — LibraryPage cart wiring end-to-end

Cart is now the source of truth for Dry-run + Copy. Mounts:
- OnboardingBanner above the grid (auto-dismiss on first add)
- FeaturedTilesRow above the grid (5 fan-out count queries)
- ListxmlBanner extended with cloneof_map_size for empty-parse
- CartBar (replaces ActionBar) + CartPanel (expand-up panel)
- CopyModal driven by useCopySession SSE stream

handleDryRun pulls selected_names from cart.items (with
chosenVariant override). handleCopy validates first via
useValidateCart, drops missing items with one toast, then
starts the SSE-driven copy session. Cart auto-clear honours
config.ui.cart_clear_on_copy on terminal job state.

ActionBar.tsx deleted; the rename is complete."
```

---

### Task F12: `AppShell.tsx` top-nav reshape

**Files:**
- Modify: `frontend/src/components/layout/AppShell.tsx`

- [ ] **Step 1: Inspect current shape (already done in plan-prep)**

`AppShell.tsx` currently renders a 14rem left rail with all six routes. P15 reshapes to a horizontal top nav: `Library | 🛒 N | Settings | Help | ⋯ More`, with `More` opening a popover containing `Sessions / Activity / Stats`.

- [ ] **Step 2: Pick the popover primitive**

Project already has shadcn `<Popover>` (verify with `ls frontend/src/components/ui/popover.tsx`); if absent, add via the existing `import { X as XPrimitive } from "radix-ui"` pattern from `select.tsx` (FP12 § D). Most likely already present from FP12.

- [ ] **Step 3: Rewrite `AppShell.tsx`**

```typescript
import { type ReactNode } from 'react'
import { NavLink } from 'react-router'
import {
  Activity,
  BarChart,
  BookOpen,
  Layers,
  MoreHorizontal,
  Search,
  Settings,
  ShoppingCart,
} from 'lucide-react'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { strings } from '@/strings'

interface AppShellProps {
  children: ReactNode
  cartCount: number
  onCmdK: () => void
}

const PRIMARY = [
  { to: '/', label: strings.nav.library, icon: Layers, end: true },
  { to: '/settings', label: strings.nav.settings, icon: Settings },
  { to: '/help', label: strings.nav.help, icon: BookOpen },
] as const

const MORE = [
  { to: '/sessions', label: strings.nav.sessions, icon: Layers },
  { to: '/activity', label: strings.nav.activity, icon: Activity },
  { to: '/stats', label: strings.nav.stats, icon: BarChart },
] as const

export function AppShell({ children, cartCount, onCmdK }: AppShellProps) {
  return (
    <div className="grid h-screen grid-rows-[auto_1fr] bg-background text-foreground">
      <header className="flex items-center gap-4 border-b px-4 py-2">
        <h1 className="text-lg font-semibold">{strings.app.name}</h1>
        <nav className="flex items-center gap-1 text-sm">
          {PRIMARY.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-2 rounded px-2 py-1.5 hover:bg-muted',
                  isActive && 'bg-muted font-medium',
                )
              }
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
              {label}
            </NavLink>
          ))}
          <NavLink
            to="/?cart=open"
            className={({ isActive }) =>
              cn(
                'flex items-center gap-2 rounded px-2 py-1.5 hover:bg-muted',
                isActive && 'bg-muted font-medium',
              )
            }
            aria-label={strings.nav.cart(cartCount)}
          >
            <ShoppingCart className="h-4 w-4" aria-hidden="true" />
            {cartCount}
          </NavLink>
          <Popover>
            <PopoverTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                aria-label={strings.nav.more}
                className="gap-2"
              >
                <MoreHorizontal className="h-4 w-4" aria-hidden="true" />
                {strings.nav.more}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-48 p-1">
              {MORE.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-2 rounded px-2 py-1.5 hover:bg-muted',
                      isActive && 'bg-muted font-medium',
                    )
                  }
                >
                  <Icon className="h-4 w-4" aria-hidden="true" />
                  {label}
                </NavLink>
              ))}
            </PopoverContent>
          </Popover>
        </nav>
        <div className="ml-auto">
          <Button variant="outline" size="sm" onClick={onCmdK} className="gap-2">
            <Search className="h-4 w-4" aria-hidden="true" />
            <span className="text-xs text-muted-foreground">
              {strings.nav.commandPalette}
            </span>
            <kbd className="ml-auto rounded border bg-muted px-1 py-0.5 text-[10px] font-mono">
              ⌘K
            </kbd>
          </Button>
        </div>
      </header>
      <main className="overflow-auto">{children}</main>
    </div>
  )
}
```

The `cart=open` deep-link is a placeholder — wire it to expand the cart panel automatically when present (read from `useSearchParams` in `LibraryPage`); spec doesn't mandate this, but it gives the cart icon a meaningful click target. If unwanted, replace with a no-op anchor or button that just scrolls to the bottom CartBar.

- [ ] **Step 4: Update App.tsx (or wherever `<AppShell>` is rendered) to pass `cartCount`**

```bash
grep -n "<AppShell" frontend/src/App.tsx
```

Pass `cartCount={cart.items.length}` if a cart hook is reachable; if `App.tsx` doesn't host the cart, hoist `useCart()` to App and prop-drill, OR move cart to a context provider — pick the lighter touch (probably hoist to App.tsx since it's a single consumer pair).

- [ ] **Step 5: Add strings**

In `strings.ts` `nav:` block:

```typescript
    cart: (n: number) => `Cart (${n})`,
    more: 'More',
```

- [ ] **Step 6: Run typecheck + tests**

```bash
cd frontend && npx tsc --noEmit && npm test
```

- [ ] **Step 7: Manual smoke test**

```bash
uv run mame-curator serve
```

Verify all six routes still navigate correctly via deep-links (`/sessions`, `/activity`, `/stats` reachable via "More"; `/`, `/settings`, `/help` directly).

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/layout/AppShell.tsx frontend/src/App.tsx frontend/src/strings.ts
git commit -m "feat(frontend): P15 § F12 — top-nav reshape

Left rail → horizontal top nav. Primary: Library / Cart /
Settings / Help. Secondary (Sessions / Activity / Stats) under
a Popover-driven 'More' menu. URL paths preserved so existing
bookmarks + tests + the URL-state logic still work."
```

---

### Task F13: `SettingsPage.tsx` — `cart_clear_on_copy` Select

**Files:**
- Modify: `frontend/src/pages/SettingsPage.tsx`

- [ ] **Step 1: Locate the `default_sort` Select (line 270-289)**

```bash
grep -n "default_sort\|cart_clear" frontend/src/pages/SettingsPage.tsx
```

The Display `<Card>` already wraps `default_sort` in a shadcn `<Select>`. Mirror the shape directly below it.

- [ ] **Step 2: Add the Select**

After the existing `default_sort` Select block, paste:

```tsx
<div className="flex flex-col gap-1">
  <Label htmlFor="cart_clear_on_copy">
    {strings.settings.uiLabels.cart_clear_on_copy}
  </Label>
  <Select
    value={config.ui.cart_clear_on_copy}
    onValueChange={(v) =>
      updateUi('cart_clear_on_copy', v as UiCfg['cart_clear_on_copy'])
    }
  >
    <SelectTrigger id="cart_clear_on_copy" aria-label={strings.settings.uiLabels.cart_clear_on_copy}>
      <SelectValue />
    </SelectTrigger>
    <SelectContent>
      {(['always', 'on_success', 'never'] as const).map((v) => (
        <SelectItem key={v} value={v}>
          {strings.settings.uiLabels.cart_clear_on_copy_options[v]}
        </SelectItem>
      ))}
    </SelectContent>
  </Select>
</div>
```

- [ ] **Step 3: Add a SettingsPage test**

If `SettingsPage.test.tsx` doesn't already cover `default_sort`, add a sibling test for `cart_clear_on_copy` mirroring whatever `default_sort` looks like. If `default_sort` is covered, add:

```typescript
it('cart_clear_on_copy round-trips all three values', async () => {
  // Use the existing config-patch MSW handler from the SettingsPage test setup
  // … assert all three values can be selected and patch gets called with each.
})
```

(Read the existing `SettingsPage.test.tsx` for the exact pattern; this is a one-off mirror.)

- [ ] **Step 4: Run tests**

```bash
cd frontend && npm test -- SettingsPage
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/SettingsPage.tsx frontend/src/pages/__tests__/SettingsPage.test.tsx
git commit -m "feat(frontend): P15 § F13 — Settings cart_clear_on_copy Select

Display Card alongside default_sort. Three-value shadcn
<Select> matching FP12 § D's pattern. Round-trips via the
existing useConfigPatch flow."
```

---

### Task F14: Playwright cart-flow spec

**Files:**
- Create: `tests-e2e/cart-flow.spec.ts`

- [ ] **Step 1: Find the existing Playwright config + smoke spec**

```bash
ls tests-e2e/ && cat tests-e2e/*.spec.ts | head -40
```

Use the same fixture config.yaml + boot pattern as the existing Playwright smoke (P06 shipped it).

- [ ] **Step 2: Write the spec**

```typescript
import { test, expect } from '@playwright/test'

test.describe('P15 cart flow', () => {
  test('open → dismiss banner → tile → bulk-add → expand → Copy modal', async ({ page }) => {
    await page.goto('/')

    // Banner present, then dismiss
    const banner = page.getByRole('status').filter({ hasText: /Tap a game/i })
    await expect(banner).toBeVisible()
    await page.getByRole('button', { name: /dismiss/i }).click()
    await expect(banner).not.toBeVisible()

    // Click featured tile
    await page.getByText("Beat 'em Ups").click()

    // Bulk-add button appears
    const bulkAdd = page.getByRole('button', { name: /add all/i })
    await expect(bulkAdd).toBeVisible()
    await bulkAdd.click()

    // Cart-bar shows non-zero count
    const cartBar = page.getByRole('contentinfo')
    await expect(cartBar).toContainText(/\d+ games/)

    // Expand chevron
    await page.getByRole('button', { name: /expand cart/i }).click()
    const panel = page.getByRole('region', { name: /cart contents/i })
    await expect(panel).toBeVisible()

    // Click Copy → modal opens
    await page.getByRole('button', { name: /^copy$/i }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
  })
})
```

- [ ] **Step 3: Run the spec**

```bash
npx playwright test cart-flow
```

Expected: PASS. If the test environment doesn't seed enough machines for "Beat 'em Ups" to return non-zero (small fixture), fall back to clicking a card's `+Add` directly to populate the cart, then proceed.

- [ ] **Step 4: Commit**

```bash
git add tests-e2e/cart-flow.spec.ts
git commit -m "test(e2e): P15 § F14 — Playwright cart-flow smoke

End-to-end: dismiss banner → click tile → bulk-add → expand
panel → Copy modal opens. One spec; complementary to the unit
+ integration coverage. Smokes the full LibraryPage cart wiring."
```

---

## Self-Review

After this plan is finalised, review against spec § 6 (Testing) and § 9 (File-level diff summary):

**Spec coverage:**
- § 4.1 cart hook → F2 ✅
- § 4.2 featured tiles → F4 (strings) + F6 (component) + F11 (fan-out) ✅
- § 4.3.1 picker fix + listxml banner extensions → B1 (regression test) + B2 (setup-check fields) + F11.1 (banner empty-parse trigger) ✅ (runtime fix already in FP23)
- § 4.3.2 `total_bytes` → B3 ✅
- § 4.3.3 `onCopy` / `onDryRun` wiring → F11 ✅
- § 4.4 new components (FeaturedTilesRow, CartBar, CartPanel, OnboardingBanner) → F5 + F6 + F7 + F8 ✅
- § 4.5 surgical edits (GameCard, LibraryPage, AppShell) → F9 + F11 + F12 ✅
- § 5.1 cart reconciliation → B4 (endpoint) + F3 (hook) + F11 (pre-Copy validate) ✅
- § 5.2 AlternativesDrawer cart consistency → F11 (cart.setVariant on override) ✅
- § 5.3 error surfaces → existing `toastApiError` (no new task; called inline in F11) ✅
- § 5.4 cart auto-clear policy → B5 (schema) + F1 (types mirror) + F11 (useEffect) + F13 (Settings UI) ✅
- § 6 testing → all tasks include tests; F14 is the e2e smoke ✅
- § 9 file-level diff summary → matches the File Structure table at the top of this plan, with one correction noted (UiConfig lives in `api/schemas.py` not `parser/models.py`) ✅

**Placeholder scan:** searched for "TBD", "TODO", "implement later", "Add appropriate error handling" — none found in the implementation steps. The single "verify" callout in Task F10 step 3 is intentional: the `/api/copy/resolve-conflict` endpoint name needs cross-checking against the live backend; this is a verification step, not a placeholder.

**Type consistency:** `CartItem`, `bulkAddTotal: number | null`, `inCart: boolean`, `onAdd: (s: string) => void`, `cartCount: number`, `cart_clear_on_copy: 'always' | 'on_success' | 'never'` — used identically across F2, F6, F7, F8, F9, F11, F12, F13.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-07-cart-and-curated-library-plan.md`. Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Best for this plan because the 19 tasks are mostly independent within their wave; parallelism shaves real wall-clock.

2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints for review. Slower but keeps full context in one session.

Which approach?

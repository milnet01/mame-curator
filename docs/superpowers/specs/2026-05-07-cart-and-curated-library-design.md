# Cart & Curated Library — Design

> **Status:** Draft, awaiting user review.
> **Date:** 2026-05-07
> **Brainstorm:** [`superpowers:brainstorming`](~/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/skills/brainstorming/SKILL.md) flow with the user on 2026-05-07.
> **Phase ID candidate:** `P15` — the next monotonic slot. Already taken in `ROADMAP.md`: `P10` (media coverage expansion), `P11` (thumbnails contribution), `P12` (in-app self-update + INI diff preview), `P14` (per-game review state). `P13` is currently an unclaimed gap (`P08`-era in-browser-setup-wizard candidate, never committed to `ROADMAP.md`); the spec uses `P15` rather than reaching back into the gap to keep monotonicity. Final ID will be confirmed when the implementation plan opens the roadmap entry.
> **Depends on:** `v1.2.0` baseline. Specifically uses FP17's `/api/library/facets` and FP19's `POST /api/games/{name}/launch`. FP18's `/api/setup/check` is extended (new `listxml_available` and `cloneof_map_size` fields, see § 4.3.1). No dependency on FP20 / FP21 / DS02 (those are post-`v1.2.0` hardening; this phase is parallel).
> **Supersedes:** the no-op `onCopy` / `onDryRun` handlers in `frontend/src/pages/LibraryPage.tsx:191-196`.

---

## 1. Why this phase exists

User feedback while running the `v1.2.0` build on 2026-05-07: opening the app shows **21,049** game cards with no clear path to "select games I want and copy them to my console". Three concrete failures, surfaced with a screenshot anchor:

1. **Parent/clone collapse isn't reaching the user.** Bottom-left counter reads `21,049 games · 0.0 GB · 0 BIOS deps` — close to the raw DAT machine count, far from the post-collapse winner count expected when `cloneof` relationships are applied. The picker is wired (`api/routes/games.py:85` reads `world.filter_result.winners`, populated by `filter/runner.py:run_filter` which calls `pick_winner` per parent group at line 51). Yet the screenshot shows the full multi-variant fan-out:
   - `1942` appears 7 times (Revision A / Revision B / First Version / Williams Electronics license / Tecfri PCB bootleg / Itisa bootleg / Supercharger 1942 hack).
   - `1941: Counter Attack` appears 4 times (World 900227 / Japan / World / USA 900227).
   - `1943: The Battle of Midway` appears 5 times (Euro / bootleg, hack of japan set / Midway Kaisen bootleg / Midway Kaisen Japan no-protection-hack / Mark II US).
   - `18 Wheeler: American Pro Trucker` appears 5 times (deluxe / deluxe Rev A / deluxe Rev T / standard / upright).
   - `10-Yard Fight` appears 3 times across regions; `100 Lions` 2 times across regions.

   Per ADR-0002, parent/clone relationships are **not** carried in Pleasuredome DATs — they're stripped — and must be supplied via MAME `-listxml`'s `cloneof_map`. The runner uses this map at `filter/runner.py:45`: `parent = ctx.cloneof_map.get(machine.name, machine.name)`. **If the cloneof_map is empty, every machine self-parents** — `groups[machine.name] = [machine]` — and the per-group picker returns each machine as its own winner. Result: 21k "winners". The bug is therefore one of: (a) user's `config.yaml` doesn't reference a `listxml.xml` (UX/setup gap; FP18 setup banner only counts INIs, not listxml); (b) listxml is configured but `parse_listxml_cloneof` fails silently or returns empty; (c) low-probability third line: cloneof_map is built and `state.py` wires it into `FilterContext` (constructor reads `cloneof_map=cloneof_map`) — verify this third line opportunistically; the ADR-0002-mandated wiring has been in place since P02 and would be surprising as a regression. Diagnosis must precede the fix.

2. **No primary call-to-action above the fold.** Copy is rendered bottom-right in footer styling; first-time eye lands on the grid with no instruction. Worse, clicking it does nothing — the handler is a literal no-op stub:

   ```tsx
   onCopy={() => {
     /* Copy modal wiring follow-up. */
   }}
   ```

3. **No selection mechanism.** No checkbox, no heart, no "+Add" affordance. The intended (but unwired) behaviour of the bottom-bar Copy button was "copy every game matching the current filters" — meaning a user wanting three specific games has no path to that goal short of crafting filters that resolve to exactly those three.

The redesign answers all three with one coherent phase: diagnose and fix the parent/clone-collapse failure (and surface the listxml-availability state to the user), add a cart-first selection model, upgrade the dead bottom-bar to a sticky cart-bar with expand-up panel, and surface curated INI-derived starting points as a featured-tile row above the grid.

---

## 2. Decisions made during the brainstorm

These were settled through user conversation on 2026-05-07; recording them so the implementation plan and any later revisions can trace each call back to its motivation.

| # | Decision | Rejected alternative(s) |
|---|---|---|
| D1 | **Persona is a usability lens, not a literal kid user.** All `v1.2.0` capability stays accessible; the *primary path* (browse → pick → copy) becomes the screen, everything else moves to corners. | Literal target (kid actually operates the app — would imply hide Settings entirely behind a PIN). Both-mode dual-UI (kid mode + admin mode). |
| D2 | **Cart-first selection with "Add all visible" shortcut.** Per-game `+Add` is the primary mental model; bulk-add covers the "everything in this filter" case. INIs (`genre.ini`, `category.ini`, etc.) provide the curation power for the bulk-add path. | Filter-only ("everything visible gets copied"). Star/favourite as a separate persistence layer. |
| D3 | **Picker fix is part of this spec, not a prior FP.** Brainstorm both the backend wiring and the UX redesign as one ship; the design depends on picker output reaching the listing endpoint. | Fix the picker first as `FP##` then design on the corrected baseline. Treat picker fix as a sequencing detail of the implementation plan rather than a spec requirement. |
| D4 | **Browse-first first-load with instructional banner + featured INI tiles.** Open straight into the grid (with dismissible banner + featured row above); no wizard, no hub screen. | Wizard-first onboarding (3-step: where do games go → what kind → review). Hub screen with chooser tiles. |
| D5 | **Franchise variants stay flat.** sf2 / sf2t / ssf2 / ssf2t = four cards, not one expandable group. Trust the picker to collapse clones; trust filters + featured tiles for navigation. | Heuristic franchise grouping (collapse 3+ shared-base-title parents). Sidebar Series chip for navigation-only filtering. |
| D6 | **Top-nav: Library + Cart + Settings + Help; rest under "More".** Sessions / Activity / Stats stay reachable but move out of the primary rail. URL paths preserved (`/sessions`, `/activity`, `/stats` still work) so bookmarks and tests don't break. | Keep all six visible with restyling. Drop Activity + Stats entirely (merge into a Settings → Diagnostics tab). |
| D7 | **Cart placement: sticky bottom-bar with expand-up panel.** Upgrade the existing `ActionBar.tsx` in place; collapsed shows count + size + Copy + Dry-run + expand chevron; expanded slides a panel up. | Top-bar drawer (cart hidden by default). Right-side persistent sidebar (compounds with the existing 16rem left FiltersSidebar — squeezes the grid). |
| D8 | **Featured tile click filters the grid, does not auto-add to cart.** The `[Add all 51 visible]` button in the cart-bar is the explicit second click. Previewing before bulk-adding is safer. | Auto-add on tile click (no preview). |
| D9 | **Cart auto-clear policy after Copy: clear on success, retain on partial/failed.** New config field `ui.cart_clear_on_copy: 'always' \| 'on_success' \| 'never'` (default `'on_success'`). | Always clear (loses partial-failure context). Never clear (cart fills indefinitely). |

---

## 3. The 30-second user journey

What a fresh user (or you, after the redesign) sees and does, opening the app cold:

```
┌─ MAME Curator ────────────────────────────── Library  [🛒 0]  Settings  Help  ⋯ ┐
│                                                                                  │
│  ╭ ❶ Tap a game to add it to your list. Click COPY when you're done.  ✕ ╮       │
│                                                                                  │
│  Featured                                                                        │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐    │
│  │ Capcom     │ │ Beat 'em   │ │ Run & Gun  │ │ Best of    │ │ SHMUPS —   │    │
│  │ Classics   │ │ Ups        │ │ Shooters   │ │ 1992       │ │ Vertical   │    │
│  │ 38 games   │ │ 51 games   │ │ 27 games   │ │ 64 games   │ │ 50 games   │    │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └────────────┘    │
│                                                                                  │
│  ┌─[filters]──┐  All games (6,847)              ◯ Masonry  ◯ Grid  ◯ List       │
│  │ Search…    │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐        │
│  │ Year ◀…▶   │  │ [img]  │ │ [img]  │ │ [img]  │ │ [img]  │ │ [img]  │        │
│  │ A B C…     │  │ 1942   │ │ 1943   │ │ Bubble │ │ Burger │ │ Cadi…  │        │
│  │ Genre ▾    │  │ +Add   │ │ +Add   │ │ Bobble │ │ Time   │ │ +Add   │        │
│  │ Publisher▾ │  └────────┘ └────────┘ │ +Add   │ │ +Add   │ └────────┘        │
│  │ …          │  …                                                              │
│  └────────────┘                                                                  │
│                                                                                  │
│ ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔ │
│  🛒  0 games · 0.0 GB                              [Dry-run]  [Copy]   ⌃ expand  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

**Steps:**

1. Lands on Library. Featured-tiles row is the eye-catcher; banner explains what to do; grid of post-collapse winners below (count TBD against the real DAT once parent/clone collapse is correctly applied — order-of-magnitude expectation: a few thousand, not 21k).
2. **Path A — featured tile.** Click `Beat 'em Ups` → grid filters to those games → cart-bar morphs to show `[Add all N]` shortcut (where `N` is the filter result `total`, not the page size) → click → cart fills with all N → bottom bar reads `🛒 N games · X.Y GB`.
3. **Path B — browse.** Scroll grid, click a card's `+Add` → game enters cart, card flips to `✓ Added`. Repeat as needed. Banner dismisses on first add (persists dismissal across reloads via `localStorage`).
4. **Path C — refine variant.** Click a card *body* (not `+Add`) → `AlternativesDrawer` opens (existing `v1.2.0` surface) showing region clones for that parent ("oh, I want the Japanese version") → swap winner there → drawer closes → that variant is now in cart with `chosenVariant` set.
5. Click `⌃ expand` on the cart bar → cart panel slides up showing the 51 added games with per-row `✕` remove buttons + a `Clear all` link.
6. Click `Copy` → existing `CopyModal` opens (already coded; just wired into a real handler), confirms target paths, executes the copy session via the existing `copy/runner.py` machinery.
7. After copy: cart auto-clears on `succeeded`; retains on `partial` / `failed` (per D9).

---

## 4. Architecture

### 4.1 Cart state — frontend-only, `localStorage`-backed

```ts
// frontend/src/hooks/useCart.ts (NEW)
type CartItem = { shortName: string; chosenVariant?: string }
type Cart = { items: CartItem[]; addedAt: Record<string, number> }

// Persistence key (versioned for forward-compat):
//   localStorage["mame-curator:cart:v1"]

export function useCart(): {
  items: CartItem[]
  has(shortName: string): boolean
  add(shortName: string, variant?: string): void
  remove(shortName: string): void
  addAll(shortNames: string[]): void          // merge, no duplicates
  setVariant(shortName: string, variant: string | undefined): void
  clear(): void
  totalBytes: number                           // memoised sum
}
```

The cart is a working pre-copy intent, not a server resource. No new API endpoint, no server-side lock, no concurrency story. Implementation pattern: `useState` initialised from `localStorage`, `useEffect` writing back on every mutation. Matches the existing project idiom (zustand was rejected during P06 brainstorm; `useState` + custom hooks is the established pattern).

### 4.2 Featured tiles — client-defined, server-counted

```ts
// frontend/src/strings.ts (additions)
//
// IMPORTANT: genre values must match `catver.ini` exactly (case +
// punctuation). The seed list below uses values verified against
// `tests/filter/fixtures/snapshot_catver.ini`; growing the list
// must verify against the user's installed `catver.ini` and not
// invent strings.
export const FEATURED_TILES: FeaturedTile[] = [
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
    query: { genre: "Beat'em up" },     // verified
  },
  {
    id: 'run-and-gun',
    title: 'Run & Gun Shooters',
    description: 'Run-and-gun shooters',
    query: { genre: 'Shooter / Run-and-Gun' },     // verified
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
    query: { genre: 'Shooter / Vertical' },     // verified
  },
  // 5–8 total at v1; growing the list is a one-file PR.
  // Implementation step: pull the actual category-value distribution
  // from the user's `catver.ini` during the writing-plans phase to
  // pick the highest-value-per-tile cuts.
]
```

Tiles live in `strings.ts` colocated with copy text. Each tile fetches its count via `useGames(query, { pageSize: 0 })` — the existing `/api/games` already returns `total: int` in its envelope, so no new endpoint and no count-only short-circuit are needed. React-query caches counts keyed on the query object, with default 5-minute staleness.

### 4.3 Backend changes

Three coordinated changes inside this spec:

#### 4.3.1 Diagnose and fix parent/clone collapse failure

**Symptom:** `/api/games` returns ~21,049 cards instead of the expected post-collapse winner count. The picker is wired (`api/routes/games.py:85` reads `world.filter_result.winners`); the runner groups by `ctx.cloneof_map.get(machine.name, machine.name)` and picks one winner per group (`filter/runner.py:43-52`). Empty `cloneof_map` → every machine self-parents → every machine wins.

**Diagnosis (must run before patching):**

1. **Inspect runtime state.** Boot the app against the user's `config.yaml` and inspect `world.ctx.cloneof_map` size at world-load time (log it from `state.py` or expose it via a temporary debug endpoint). Naming note: `WorldState` exposes the same dict at two attribute paths — `world.cloneof_map` (the underlying field) and `world.ctx.cloneof_map` (the `FilterContext` view, which is what `runner.run_filter` reads); either reference resolves to the same data.
   - **0 entries** → listxml never reached the parser (path missing, file missing, parse failure, or wiring gap between `parse_listxml_cloneof` and `FilterContext`). Continue with diagnosis 2.
   - **>0 entries but small** → listxml partial-parse. Inspect `parser/listxml.py:parse_listxml_cloneof` for silent-error paths.
   - **Realistic count (~30-40k)** → the runner / picker is the cause; trace from `runner.run_filter` to where group keys are computed.
2. **Inspect `config.yaml`.** Does it set `paths.listxml` (or whatever the resolved field is)? Is the file present and readable?
3. **Run `parse_listxml_cloneof()` directly** against the user's listxml file from a test harness; assert it returns a non-empty mapping.

**Likely fix candidates** (write the actual fix once diagnosis points at the cause):

- **(a) Setup gap, not a code bug.** User skipped or never completed listxml acquisition. Surface this in the existing setup banner (FP18 added INI counting; extend it to count listxml) AND on the Library page itself: **a banner above the grid when `cloneof_map` is empty / suspiciously small**, e.g., `"⚠ MAME listxml not loaded. Region/version variants will appear separately. → Open Setup"`. Implementation: extend `/api/setup/check` (used by FP18 banner) with `listxml_available: bool` and `cloneof_map_size: int`; banner renders when conditions are met.
- **(b) Parse failure.** If `parse_listxml_cloneof` swallows exceptions, fix it to raise typed errors and surface them in the setup banner.
- **(c) Wiring bug.** If the cloneof_map is built but doesn't reach `FilterContext`, fix the world-load path in `state.py`.

**Whichever cause turns out to be operative, the spec mandates the listxml-availability banner from (a) ships regardless** — the user must always know when collapse won't happen, even after the underlying bug is fixed.

#### 4.3.2 Add `total_bytes` to the listing envelope

`v1.2.0` reports `0.0 GB` in the bottom bar because the listing response (`GamesPage` in `api/schemas.py`) doesn't carry an aggregate byte total — and `GameCard` (the per-row response model) deliberately has no `roms`/`size` field (it's a thin display projection). Sum-of-bytes is already computed server-side for the `Stats` route (`api/routes/games.py`'s `total_bytes` initialiser → per-row accumulator → assembled into the `Stats` response model); the same shape must surface in the listing envelope.

**Required change**: extend `GamesPage` with `total_bytes: int`, computed server-side as the sum over the same `filtered` slice that produces `total`. Frontend renders directly from the envelope; no client-side summing.

#### 4.3.3 Wire `onCopy` / `onDryRun` from no-op stubs

`LibraryPage.tsx:191-196` currently:

```tsx
onDryRun={() => { /* Dry-run modal wiring follow-up. */ }}
onCopy={() => { /* Copy modal wiring follow-up. */ }}
```

After this phase: both consume `cart.items` (not the visible-grid filter result) and feed `CopyModal` / `DryRunModal` — both components already exist and were imported from `@/components/library/CopyModal` and `@/components/library/DryRunModal` in `v1.2.0` but never reached. The modals' contracts unchanged; only the input set source changes.

### 4.4 New frontend components

| File | Role |
|---|---|
| `components/library/FeaturedTilesRow.tsx` | Horizontal scroll of tile buttons. Each click calls `onTileSelect(tileId)` which sets `LibraryPage` filter state to the tile's query and emits the tile id so `CartBar` can offer `Add all visible`. |
| `components/library/CartBar.tsx` | Replaces `ActionBar.tsx` (rename + extend). Collapsed: `🛒 N games · X.Y GB · [Dry-run] [Copy] [⌃]`. When a featured tile is active, also shows `[Add all M]` where the prop name is `bulkAddTotal: number \| null` (label: `"Add all {bulkAddTotal}"`). The integer is the filter result `total`, **not** the page-`items.length` — confirms the disambiguation in § 11 sub-q5. Click `⌃` opens the panel. |
| `components/library/CartPanel.tsx` | Expand-up panel listing cart items with per-row `✕` remove + total summary + `Clear all` link. Sliding behaviour: `framer-motion` is already a project dep (verify in `frontend/package.json`) and free to use; a CSS-only height transition is also fine and simpler — choose at implementation time based on whether motion polish is needed elsewhere in this phase. |
| `components/library/OnboardingBanner.tsx` | Top instructional banner with `✕` dismiss. `localStorage`-keyed: `mame-curator:onboarding-dismissed:v1`. Auto-dismisses on first `cart.add` regardless of whether the user clicked `✕`. |

### 4.5 Existing frontend components touched (surgical edits only)

| File | Change |
|---|---|
| `components/library/GameCard.tsx` | Add a `+Add` button (or heart icon) overlaying the card thumbnail. Cart-aware "✓ Added" state (consumes `useCart().has(shortName)`). Click on the button calls `cart.add()`; click on card body still opens `AlternativesDrawer`. ARIA: button has its own accessible name (`"Add 1942 to cart"`) so screen readers don't conflate. |
| `pages/LibraryPage.tsx` | Orchestration: holds `useCart()`, passes cart-state to `CartBar`, `GameCard`, and `FeaturedTilesRow`. Routes `onCopy` to `CopyModal` with `cart.items` as the input set. Pre-Copy: validates cart via `POST /api/games/validate` before opening `CopyModal` (per § 5.1); drops missing items with a single toast. |
| `components/layout/AppShell.tsx` | Top-nav reshape lives here (the `NAV_ITEMS` config array near the top of the file + the `NavLink` rendering further down — **not** in `App.tsx`). New shape: `Library \| 🛒 N \| Settings \| Help \| ⋯ More`. `More` menu (popover): Sessions / Activity / Stats. The current left-rail goes away in favour of a horizontal top nav. URL paths unchanged so deep links survive. `App.tsx` itself remains the route-definition site (no change). |

### 4.6 Existing surfaces preserved as-is

`AlternativesDrawer`, `CopyModal`, `DryRunModal`, `FiltersSidebar`, `LayoutSwitcher`, `ThemeSwitcher`, `SettingsPage`, `HelpPage`, `SessionsPage`, `ActivityPage`, `StatsPage`. No behavioural change in any of these. `CopyModal` and `DryRunModal` get new callers but their props stay identical.

---

## 5. Data flow & edge cases

### 5.1 Cart reconciliation on DAT changes

When the user runs `refresh-inis` or swaps the DAT (Settings → Paths → DAT), picker winners change. Some cart entries may point to shortnames that no longer exist (e.g., a clone that became a parent, or a name that was dropped).

**Strategy: deferred reconcile against an explicit validation endpoint.** The grid response is paged (`page_size: 50`) so reconciling against the visible page would orphan-drop legitimate cart entries that happen to live on later pages. Instead:

- A new endpoint `POST /api/games/validate` (or `GET` with a `?short_names=a,b,c` query param) accepts the cart's shortname list and returns `{ existing: string[], missing: string[] }`. Implementation reads `world.machines` directly — no pagination, no filter chain, just a set lookup against the in-memory map.
- Cart-side reconciliation runs in two situations only:
  1. **Pre-Copy.** When the user clicks Copy, `LibraryPage` validates the cart synchronously before opening `CopyModal`; missing items are dropped with a single toast (`"3 cart items removed — they're no longer in your library"`); modal opens with the surviving set.
  2. **DAT-swap signal.** If a future signal (e.g., `useConfigPatch`'s success on `paths.source_dat` change) tells the frontend the world has been rebuilt, the cart calls `validate` opportunistically.

No reconciliation on `LibraryPage` mount — page-load shouldn't toast at the user about cart hygiene. The eventual-consistency cost is one click of Copy that validates and degrades gracefully if some items are missing.

### 5.2 AlternativesDrawer interaction with cart

User has `1942` in the cart, opens `AlternativesDrawer`, picks `1942 (Japan)` instead. `AlternativesDrawer`'s existing `onOverride` mutation already POSTs to the server (FP19 contract). On top of that, the redesign calls `cart.setVariant('1942', '1942j')` so the cart's chosen variant tracks the pick.

**Conflict resolution** (cart variant vs. server-side override): the cart wins. Reasoning: the cart is the working intent; the server-side override persists across reloads as a fallback for items not in the cart. When `CartPanel` renders an item with a non-default variant, badge it (`"⇄ Japanese"`) so the override is visible at a glance.

### 5.3 Error surfaces

| Source | Failure mode | UI handling |
|---|---|---|
| `/api/games` (5xx, network) | Query rejects; cart state untouched | Existing `toastApiError` (FP20 § G global query toast — landing in this redesign or before). Empty state with "Retry" button. |
| `localStorage` quota / disabled (private-browsing modes, browser policy) | Cart silently drops on reload | Detect on mount via probe write. One-time banner: `"Browser storage unavailable; cart will not persist for this session"`. Cart degrades to in-memory only. |
| Picker returns 0 winners (DAT mis-parse, filter too aggressive) | Empty grid | Existing empty-state UI ("No games match your filters") + "Reset filters" button. |
| Featured tile query returns 0 (INI mis-mapping, filter typo) | Tile shows `0 games`. | Click still works (filters grid → empty); recoverable by resetting filters. Operational bug: open an issue to retune the tile query. |
| Cart copy fails mid-run (disk full, source vanished) | `CopyController` reports `FAILED` per `copy/spec.md` | `CopyModal` surfaces the failed list. Cart **does not auto-clear** on partial failure (D9). |

### 5.4 Cart auto-clear policy after Copy

Default: clear on `succeeded` copy session, retain on `partial` / `failed`. New config field:

```yaml
# config.yaml
ui:
  cart_clear_on_copy: 'on_success'   # 'always' | 'on_success' | 'never'
```

Schema added to `parser/models.UiConfig`; mirrored in `frontend/src/api/types.ts`; surfaced as a Select dropdown inline in `frontend/src/pages/SettingsPage.tsx` alongside the existing `default_sort` Select inside the "Display" `<Card>` (FP12 § D shipped `default_sort` there; the new field follows the same pattern in the same Card).

---

## 6. Testing

Per existing project gates: `pytest` backend ≥ 85 %, frontend Vitest ≥ 70 %, Playwright smoke. Each gate already has its own per-module cap.

| Layer | New tests |
|---|---|
| Backend (`pytest`) | (a) `/api/games` regression: against a fixture with a non-empty `cloneof_map`, `len(rows)` < `len(machines)` (parent/clone collapse pinned); (b) `total_bytes` in the `GamesPage` envelope matches the sum over the `filtered` slice for a 10-machine fixture; (c) `/api/setup/check` returns `listxml_available: bool` + `cloneof_map_size: int` populated from `world.ctx.cloneof_map`; (d) if § 4.3.1 diagnosis exposes a silent-failure path in `parse_listxml_cloneof`, a regression test for that specific input shape; (e) `parser/models.UiConfig` schema: `cart_clear_on_copy` defaults to `'on_success'` and rejects values outside the three-literal Union; (f) `POST /api/games/validate` round-trip: input `{ short_names: ['real', 'fake'] }` against a fixture returns `{ existing: ['real'], missing: ['fake'] }`. |
| Frontend unit (Vitest) | `useCart` — `add` / `remove` / `addAll` / `setVariant` / `clear`, plus `localStorage` round-trip, plus quota-exceeded fallback; `FeaturedTilesRow` tile-click emits filter; `CartBar` shows `Add all N` only when `bulkAddTotal` is non-null; `OnboardingBanner` dismiss persists across mount/unmount; `GameCard` `+Add` button toggles "✓ Added" state; `SettingsPage`'s new `cart_clear_on_copy` Select (rendered in the existing Display Card alongside `default_sort`) round-trips all three values (`'always'` / `'on_success'` / `'never'`) and patches via `onPatch`. |
| Frontend integration | `LibraryPage`: click `+Add` on a card → cart count goes 0 → 1; click featured tile → filter applies + bulk-add button appears; click bulk-add → cart count goes 0 → N; `AlternativesDrawer` override on a cart-resident game → `cart.setVariant` called with chosen shortname. Also: pre-Copy validation via `POST /api/games/validate` drops orphans with a single toast and opens `CopyModal` with the surviving set. |
| E2E (Playwright, 1 spec) | Open app → dismiss banner → click "Beat 'em Ups" tile → click "Add all 51 visible" → click `⌃ expand` → assert 51 rows in panel → click `Copy` → assert `CopyModal` mounts. |

The parent/clone-collapse regression test (sub-bullet a) is the single most important test here — it pins the underlying bug closed by asserting that with a non-empty `cloneof_map`, the listing endpoint returns strictly fewer rows than the number of machines in the fixture. Future regressions where `cloneof_map` silently empties (the exact symptom reported on 2026-05-07) would fail this test before reaching production.

---

## 7. Non-goals

Things deliberately not part of this spec.

### 7.1 Forward-looking enhancements (in long-form roadmap "Future enhancements")

The following are already captured in `docs/superpowers/specs/2026-04-27-roadmap.md` § "Future enhancements" so they don't get lost:

- **Cart sync (multi-device)** — opt-in cloud sync of the in-progress copy cart, server-side state.
- **Featured-tile editor in Settings** — UI for managing the curated tile list (today: code-defined, one-PR-per-tile).
- **Mobile / responsive layout pass** — desktop-first today; cart-bar + sidebar + featured-tiles row need separate breakpoints before phones / tablets work.
- **Cart UI polish** — drag-to-reorder, cart export/import, in-cart-panel search.
- **Game-selection wizard** — guided multi-step onboarding flow ("where do games go → what kind do you like → review and copy"), considered and rejected for `v1` per D4 but kept in the backlog as a Help-page-launchable surface for new users.

### 7.2 Considered + rejected (spec-internal record)

- **Franchise grouping** (D5) — heuristic clustering of `sf2 / sf2t / ssf2 / ssf2t` into one expandable card. Rejected: no MAME data field for "franchise"; heuristics are brittle (regex on title? edit distance? hand-curated table?); user explicitly said "sequels are their own games"; post-picker-fix grid is small enough that filters + featured tiles already provide the navigation. Where franchise-aware curation does add value (e.g., "Street Fighter II era") it surfaces via featured tiles backed by hand-curated INI lists, not as a structural concept across the grid.
- **Wizard-first onboarding** (D4) — 3-step modal flow on first visit. Rejected: feels patronising on a frequently-revisited tool; the banner + featured tiles teach in-context without forcing modal flow; v1.2.0 already has filters so a wizard would duplicate them. Captured in long-form roadmap (§ 7.1) for later as an opt-in Help-page-launchable variant.
- **Star / favourite as a separate persistence layer** — durable per-game starring decoupled from the cart. Rejected: the cart already plays this role for the foreseeable use case; a second persistence mechanism would mean two state stores to keep consistent.
- **Hub screen replacing the grid as home** — (Q3 option C) chooser tiles ("Browse all" / "Pick from a category" / "Quick pick"). Rejected: redundant with the featured-tiles row, which gives the same affordance without hiding the grid behind a navigation step.
- **Filter-only selection model** (Q2 option 1) — copy whatever's visible without per-game pick. Rejected: doesn't match the "I want these three specific games" mental model; was the (unwired) `v1.2.0` intent that the user explicitly pushed back on.

### 7.3 Out of scope this phase, no roadmap entry

These are minor enough that they don't even need to be parked:

- Server-side cart sharing or read-only links (`/cart/abc123` URLs with state).
- Multi-cart (have several drafts at once).
- Cart-to-Session promotion (turn the current cart into a saved Session) — possibly natural, but not the primary path.

---

## 8. Risks & mitigations

All six risks have in-spec mitigations. None warrant pre-emptive roadmap entries; if any manifests post-ship, it becomes an `FP##` at that point.

1. **Picker output edge cases.** `pick_winner` has unit tests at the per-group level, but hasn't been exercised at full-DAT scale through the listing endpoint with a real `cloneof_map`. Mitigation: the regression test in § 6 (sub-bullet a) plus a one-time staging run against the user's actual ~21k-machine DAT once `cloneof_map` is correctly populated. If a winner is "wrong" (e.g., a worse parent picked over a better one), it surfaces in `AlternativesDrawer` and is a separate bug to chase via the existing override mechanism.
2. **AlternativesDrawer ↔ cart consistency.** When a cart item's `chosenVariant` differs from the server-side override, which wins? Cart wins (§ 5.2). Risk: confusing if the user expected server-override to be authoritative. Mitigation: `CartPanel` badges any item with a non-default variant (`"⇄ Japanese"`) so the override is visible at glance.
3. **`localStorage` unavailable.** Private-browsing modes, quota exceeded, browser policy. Cart silently breaks. Mitigation: feature-detect on mount via probe write; one-time toast warning; degrade to in-memory cart for the session.
4. **Top-nav reshape muscle memory.** `v1.2.0` users (you) have routes in a left rail; moving Sessions / Activity / Stats under "More" is a one-time disruption. Mitigation: keep URL paths (`/sessions`, `/activity`, `/stats`) so bookmarks still work; the reshape is purely visual.
5. **Featured-tile parallel fetch storm.** 5–8 concurrent `/api/games?pageSize=0` requests on every Library mount. Real cost is negligible (each is a count-only query that returns just `total`), but adds up for slow disks. Mitigation: react-query 5-minute staleness on tile counts; counts only re-fetch on DAT change.
6. **Cart capacity vs. localStorage.** Browser `localStorage` quota is typically 5 MB per origin. A worst-case full-DAT cart (~7k entries × ~80 bytes per `{shortName, chosenVariant?}` JSON = ~560 KB) is well under budget — no real exposure at v1. Defensive guard: `useCart` enforces `MAX_CART_SIZE = 10000` and logs a warning when the cart approaches it; `addAll` truncates with a one-time toast if a bulk-add would push past the cap. Mostly belt-and-braces; in practice the user runs out of disk space long before the cart runs out of `localStorage`.

---

## 9. File-level diff summary

A first-pass map for the implementation plan to refine.

### Backend

| File | Change |
|---|---|
| `src/mame_curator/api/routes/games.py` | (a) Extend `GamesPage` build at `list_games` to populate `total_bytes` (sum over `filtered`). (b) Add `POST /api/games/validate` endpoint accepting `{ short_names: string[] }` and returning `{ existing: string[], missing: string[] }` — set lookup against `world.machines`; no pagination, no filter chain (per § 5.1). (c) After diagnosis (§ 4.3.1): apply whichever fix the diagnosis points at. |
| `src/mame_curator/api/routes/stubs.py` (`@router.get("/api/setup/check")` at line 52) | Extend the response with `listxml_available: bool` and `cloneof_map_size: int` so the Library page can render the listxml banner from § 4.3.1. |
| `src/mame_curator/api/schemas.py` | Extend `GamesPage` with `total_bytes: int`. Extend the setup-check response model with the two new fields. |
| `src/mame_curator/parser/listxml.py` | If diagnosis points at silent parse failure, fix `parse_listxml_cloneof` to raise / log loudly and return `{}` only on genuine empty input. |
| `src/mame_curator/parser/models.py` | Add `cart_clear_on_copy: Literal['always','on_success','never'] = 'on_success'` to `UiConfig`. |
| `tests/api/test_games.py` (or sibling) | New regression tests: (a) `total_bytes` matches sum-over-`filtered`; (b) when `cloneof_map` is non-empty, `winners` count is strictly less than `machines` count for a fixture with known parents+clones — locks the collapse behaviour. |
| `tests/parser/test_listxml.py` | If § 4.3.1 fix lands in `parse_listxml_cloneof`: regression test for whatever silent-failure path the diagnosis exposed. |

### Frontend

| File | Change |
|---|---|
| `frontend/src/hooks/useCart.ts` | **NEW** — cart hook + localStorage round-trip. |
| `frontend/src/components/library/FeaturedTilesRow.tsx` | **NEW** — horizontal tile row. |
| `frontend/src/components/library/CartBar.tsx` | **NEW** — replaces `ActionBar.tsx`. (Old file deleted; component renamed.) |
| `frontend/src/components/library/CartPanel.tsx` | **NEW** — expand-up cart contents panel. |
| `frontend/src/components/library/OnboardingBanner.tsx` | **NEW** — dismissible top banner. |
| `frontend/src/components/library/ActionBar.tsx` | **DELETE** (becomes `CartBar.tsx`). |
| `frontend/src/components/library/GameCard.tsx` | Add `+Add` affordance + cart-aware "✓ Added" state. |
| `frontend/src/pages/LibraryPage.tsx` | Wire `useCart`; route `onCopy`/`onDryRun` to modals with cart input; pre-Copy cart validation via `/api/games/validate` (per § 5.1). Render listxml-availability banner above the grid when `setupCheck.cloneof_map_size === 0` (or below a sanity threshold). |
| `frontend/src/components/layout/AppShell.tsx` | Top-nav reshape: rail → horizontal nav with "More" menu. (`App.tsx` is unchanged.) |
| `frontend/src/strings.ts` | Add `FEATURED_TILES` constant + onboarding banner copy + listxml-availability banner copy (per § 4.3.1) + cart-related strings. |
| `frontend/src/api/types.ts` | Mirror `total_bytes` field; mirror `cart_clear_on_copy` config field. |
| `frontend/src/pages/SettingsPage.tsx` (Display `<Card>` near line 270 where `default_sort` lives) | Add `cart_clear_on_copy` Select control alongside `default_sort`, same shadcn `<Select>` shape. |
| `frontend/src/__tests__/...` | Tests per § 6. |
| `tests-e2e/cart-flow.spec.ts` | **NEW** — Playwright spec per § 6. |

### Docs

| File | Change |
|---|---|
| `ROADMAP.md` | Add `P15` entry pointing at this spec. |
| `CHANGELOG.md` | `[Unreleased]` section gains a `### Planned — P15 Cart and curated library` block. |
| `docs/journal/P15.md` | **NEW** at phase close — empty placeholder; populated during the close-phase loop. |

---

## 10. Estimated scope

This is a feature phase, not a fix-pass. Rough breakdown for the implementation plan to size against:

- **Backend** — 2–3 days. Picker wiring is a 5-line insertion + the regression test; size accumulator + envelope field is a half-day; `cart_clear_on_copy` schema is a half-day.
- **Frontend** — 5–7 days. Four new components, three surgical edits, integration tests, Playwright spec, top-nav reshape with deep-link survival, banner dismissal persistence.
- **Docs / spec sync** — 1 day. ROADMAP entry, CHANGELOG planned-block, journal scaffold, possibly an ADR for the `localStorage` choice if we want to record why server-side cart was rejected.

Single phase, single ship, single `P15-complete` tag. No mid-phase splits.

---

## 11. Open questions for the implementation plan

These don't block the spec but are decisions for the writing-plans skill (or for inline judgment during implementation):

1. **Tile catalogue size at v1** — five tiles? eight? Suggested seed list in § 4.2 is five; happy to grow it during implementation if a sixth INI category surfaces obvious value (e.g., "Mahjong" if the user's `mature.ini` shows scope for it).
2. **Onboarding banner copy in Strings catalogue** — the literal text `"Tap a game to add it to your list. Click COPY when you're done."` reads OK to me but the writing-plans skill or a visual review may want to refine.
3. **Top-nav layout for narrow viewports** — `<800px` width: should "More" expand to full-screen drawer? Acceptable to defer per § 7.1 mobile non-goal, but the current `AppShell.tsx` may already have a breakpoint we should match.
4. **Card `+Add` button vs. icon** — heart icon is a reasonable affordance ("save this") but conflates with "favourite as durable persistence" which we explicitly rejected (§ 7.2). Recommendation: literal `+Add` text or a `+` glyph; revisit during visual polish.
5. **"Add all" button label** — settled in § 4.4: prop is `bulkAddTotal: number | null` and label is `"Add all {bulkAddTotal}"` where the integer is the filter result `total` (not `items.length`). Wording could still be polished — "Add all 51" vs. "Add 51 to cart" vs. "Add filtered set" — but the data semantics are locked.

<!-- ants-spec-format: 1 -->
# mame-curator-1144 — Guide a new or partially sighted user through choosing and copying games

**Status:** spec draft (2026-10-30).
**Kind:** accessibility.
**Source:** ROADMAP mame-curator-1144 (user, 2026-10-30, on the Library page: "I am lost. I don't know where to begin.").

**Blocker for:** mame-curator-1145, mame-curator-1146, mame-curator-1147.

**Layman:** The first thing you see is a guide with one question per screen, in large text, that takes you from "what do you want?" to a finished copy. The Library page gets larger text and shows only the essentials, with everything else behind a More options button.

## 1. Goal

A user who opens MAME Curator for the first time sees one question at a time and can finish a copy without using the Library page. Text and controls are larger by default, and the size is the user's to change on every page. The Library page shows search, games and the copy bar until the user asks for more. Today's full page stays one click away.

## 2. Problem

1. **No starting point.** `LibraryPage` shows `FiltersSidebar`, a header of status chips and switches, `FeaturedTilesRow`, `OnboardingBanner` and `LibraryGrid` together. Nothing says which comes first.
2. **Text is small and fixed.** No root `font-size` is set in `frontend/src/index.css`, and no size preference exists. Most text uses `text-sm` or `text-xs`. Those classes are rem-based, so a root size would scale them.
3. **Enlarged text would clip the grid.** `LAYOUT_DEFAULTS` in `LibraryGrid.tsx` fixes each row height in pixels.
4. **"Walkthrough mode" is not a guide.** The `library-walkthrough-toggle` checkbox controls `walkthrough` in `useLibraryController`, which `LibraryGrid` uses for review navigation. Its label suggests help it does not give.
5. **A repeat copy is refused.** `handleCopy` sends `conflict_strategy: "CANCEL"`, and `check_playlist_conflict` raises a 409 when a playlist exists and any selected game is not yet at the destination. A guide reusing that request would fail on every repeat copy. The Library's own failure is mame-curator-1148.

## 3. Scope decisions (agreed with the user)

All made by the user, 2026-10-30, through the session's questions unless marked.

- **First screen:** a full-page guide, one question per screen, in large text, with a way out to the full page.
- **Library page:** larger text and controls by default, with a remembered size setting; advanced items behind a More options button.
- **Full page stays:** the user ticked "leave the page as it is" alongside those two. The author reads that as: today's full page stays reachable by a switch. **The user should confirm this reading** (§14).
- **Wizards:** the user chose four. This spec covers choosing and copying games, plus the shared screens. First-time setup, fixing a game's picture or version, and Settings are mame-curator-1145, mame-curator-1146 and mame-curator-1147. Splitting them is the author's call: each has its own design questions, and the shared screens must exist first.

Author's calls, open to the cold review and the user:

- **A repeat copy adds to the existing playlist.** The guide sends `APPEND` and offers no overwrite, because `OVERWRITE` discards the playlist and can recycle files. A user who wants that uses the Library.
- **The guide never reads or writes the cart.** A user's half-built cart must survive running the guide.

## 4. Design

### 4.1 Where the guide lives

```
frontend/src/pages/GuidePage.tsx            route /start; holds the step state
frontend/src/components/guide/GuideStep.tsx the shared screen, reused by 1145-1147
frontend/src/components/guide/steps/        one file per step
frontend/src/lib/guideState.ts              the "guide seen" flag
frontend/src/lib/fetchGameNames.ts          pages /api/games into a name list
frontend/src/strings_guide.ts               guide text, re-exported from strings.ts
```

`strings_internal.ts` is already past its size cap, so guide text gets its own module. `App.tsx` adds the `/start` route inside `ShellWithPalette`. `AppShell` adds "Start here" as the first `PRIMARY` entry, and `PALETTE_ITEMS` gains the same entry.

### 4.2 When it opens

```ts
export const GUIDE_SEEN_KEY = "mame-curator:guide-seen:v1";
```

- At `/`, when `GUIDE_SEEN_KEY` is unset, the app redirects to `/start`. No other route redirects, so a link to `/settings` still works.
- The flag is set when the user finishes the guide or leaves it by any exit, including a nav link. `GuidePage` sets it on unmount.
- "Start here" reopens the guide at any time, at the first step.
- If `localStorage` is unavailable, the guide still opens at `/` and the flag stays in memory for the page's life. This follows the `try`/`catch` pattern in `OnboardingBanner`.

### 4.3 The shared screen

`GuideStep` takes a heading, a body and its actions. Every step, in this and later wizards, renders through it.

```tsx
<GuideStep
  stepNumber={2} stepCount={5}
  heading={strings.guide.chooseGroup.heading}
  onBack={...}                 // absent on the first step
  exitLabel={strings.guide.exit}
>
  {children}
</GuideStep>
```

- It shows one `<h1>` heading, "Step N of M" as text, and one column of large actions no wider than `40rem`.
- Actions are at least `3rem` tall with `text-xl` labels.
- On every step change, focus moves to the heading (`tabIndex={-1}`) on the next animation frame, including on Back. Source: https://ezud.com/accessible-multi-step-wizard-forms/
- Every step has a Back action, except the first, and an exit labelled "Look around on my own", which goes to `/`.
- Colour is never the only signal. A failure is announced with `role="alert"` and worded text.

### 4.4 The steps

`GuidePage` holds a `GuideSelection`, one of: everything, a featured tile id, or a genre.

| Step | Asks | Actions and rules |
|---|---|---|
| Which games | "Which games would you like?" | "The best version of every game", "A ready-made group", "A type of game" |
| Group or type | "Which group?" or "Which type?" | Tiles from `strings.library.featured.tiles`, or genres from `useFacets`. Skipped for "every game" |
| What that finds | "This finds N games, about X." | "Copy these", "Look through them first" |
| Where | "Copy them here?" with `paths.dest_roms` as large text | "Yes, copy here", "Choose another folder" (`FsBrowser`) |
| Check | Plain-language report from `POST /api/copy/dry-run` | "Start copying", or a reason it cannot start |
| Copying | Progress from `useCopySession` | Pause, Resume, Stop, then "Copy more games" and "Go to the Library" |

N and X come from `GET /api/games` `total` and `total_bytes`. Every guide query omits the year filters, so undated games are included (mame-curator-1150 is the Library's version of this).

**Look through them first** navigates to `/` with the selection in router state. `useLibraryController` applies it once to `filters`, using the same filter values as `handleTileSelect`. The guide ends there.

**Choose another folder** saves through `useConfigPatch` with `{ paths: { dest_roms } }`, then invalidates `["setup", "check"]` and the config query. A save failure stays on the step and shows the API's message.

**Check** reads `DryRunReport`:

| Report value | The guide says | Effect |
|---|---|---|
| `counts.new` | "N games will be copied." | |
| `counts.already_copied` > 0 | "N are already there and will be left alone." | |
| `counts.missing_source` > 0 | "N could not be found in your ROM folder and will be skipped." | |
| `counts.bios` > 0 | "N BIOS files these games need will be included." | |
| `summary.existing_playlist` | "These will be added to your existing game list." | Request uses `APPEND` |
| `summary.dest_writable` false | "This folder cannot be written to." | Start is hidden; offers Back |
| `summary.free_space_gap_bytes` > 0 | "This needs X more free space." | Start is hidden; offers Back |
| `counts.new` is 0 and nothing is missing | "All of these are already copied." | Start is hidden; offers "Copy more games" |

### 4.5 The copy request

```ts
// lib/fetchGameNames.ts — pages at 500, the API's page_size maximum
export async function fetchGameNames(
  query: GuideQuery,
  onProgress?: (done: number, total: number) => void,
): Promise<string[]>;
```

The guide sends `{ selected_names, conflict_strategy, append_decisions: {} }`, where `conflict_strategy` is `APPEND` when the Check step's report has `existing_playlist`, otherwise `CANCEL`. An empty `append_decisions` adds winners beside existing entries, per `copy/spec.md`. The dry run and the start use the same names and strategy.

`fetchGameNames` returns the winners `/api/games` lists, which already carry any override. The guide does not use `useCart`, `MAX_CART_SIZE` or `handleCopy`.

`startMutation` has no `onError`, so the guide calls `copySession.start(request, { onError })` and shows the failure on the Check step.

### 4.6 Text size

```ts
// lib/textSize.ts
export const TEXT_SIZE_KEY = "mame-curator:text-size:v1";
export const TEXT_SIZES = { normal: "100%", large: "125%", larger: "150%", largest: "200%" };
export const DEFAULT_TEXT_SIZE = "large";
export function applyTextSize(): void; // sets document.documentElement.style.fontSize
```

- `main.tsx` calls `applyTextSize()` before `createRoot`, so the first paint is at the right size.
- The size lives in `localStorage`, not `UiConfig`, because `config` loads after first paint.
- `AppShell` gains a labelled "Text size" control, reachable on every page. An unknown stored value falls back to the default.
- `LibraryGrid` multiplies `rowHeightPx` by the root size over 16, and the virtualizer re-measures when the size changes.
- The `text-[10px]` uses in `AppShell` and the drawer placeholder become rem values. `h-[300px]` stays unless the review of this page shows it clips.

### 4.7 The simple Library

```ts
export const LIBRARY_VIEW_KEY = "mame-curator:library-view:v1"; // "simple" | "full"; default "simple"
```

| | Simple | Full (today's page) |
|---|---|---|
| Search box, game grid, `CartBar` | shown | shown |
| "Start here" button above the grid | shown | not shown |
| `FiltersSidebar`, session pill, progress chip, walkthrough toggle, `LayoutSwitcher`, `ThemeSwitcher`, `FeaturedTilesRow`, `OnboardingBanner` | hidden | shown |
| Layout | `covers` for this page only; config unchanged | `ui.layout` |

A "More options" button at the top of the page switches to full, and "Fewer options" switches back. The choice is remembered. Filters set in full view stay applied in simple view, and simple view says so with "Some filters are on" and a "Clear filters" action, so hidden filters cannot silently shrink the list. `ListxmlBanner` and error panels show in both views.

### 4.8 Setup mode

When `useSetupCheck` reports `setup_required`, the first step says "MAME Curator can't read your game list yet." and offers "Open Settings" (`/settings?tab=paths`). No other step is reachable. mame-curator-1145 replaces this with the setup wizard.

## 5. Invariants

- **INV-1** — Opening `/` with `GUIDE_SEEN_KEY` unset lands on `/start`; with it set, `/` stays. No other route redirects.
  *Test:* `frontend/src/pages/__tests__/GuidePage_entry.test.tsx`.
  *Breaks when:* the redirect fires on `/settings`, or fires again after the guide is left.

- **INV-2** — Every step change moves focus to that step's heading, on Next and on Back.
  *Test:* `frontend/src/components/guide/__tests__/GuideStep.test.tsx`, which fails if focus stays on `document.body` or the old button.
  *Breaks when:* a step renders without focusing its heading.

- **INV-3** — Every step has a working exit to `/`, and every step but the first has Back.
  *Test:* `frontend/src/pages/__tests__/GuidePage_steps.test.tsx`, walking each step.
  *Breaks when:* a step omits an action.

- **INV-4** — The guide never changes the cart. A cart with items is identical before and after a full run, including a copy.
  *Test:* `GuidePage_steps.test.tsx`, comparing `mame-curator:cart:v1` before and after.
  *Breaks when:* the guide calls `useCart` methods or `cart_clear_on_copy` reaches its copy.

- **INV-5** — The names sent to `/api/copy/start` are every game the selection found: all pages, with no year filter.
  *Test:* `frontend/src/lib/__tests__/fetchGameNames.test.ts`, with a handler serving three pages and asserting the name count equals `total`, and that the request URL has no `year_min`.
  *Breaks when:* paging stops early or the Library's default year range leaks in.

- **INV-6** — With an existing playlist, the guide's dry run and start both send `APPEND`, and a repeat copy starts. It never sends `OVERWRITE`.
  *Test:* `frontend/e2e/guide-flow.spec.ts` runs the guide twice against the fixture with different games, and asserts the second copy completes and the playlist holds both sets. `GuidePage_steps.test.tsx` asserts no request carries `OVERWRITE`.
  *Breaks when:* the strategy stays `CANCEL`, which only the 409 path rejects, so the fixture must have a game not yet copied.

- **INV-7** — A failed start, dry run or folder save shows its reason on the current step in a `role="alert"` element, and the user can go Back.
  *Test:* `GuidePage_steps.test.tsx`, with handlers returning 409 and 500 for each.
  *Breaks when:* a failure leaves the step silently unchanged.

- **INV-8** — Start is not offered when the destination cannot be written, when there is too little free space, or when nothing is new.
  *Test:* `GuidePage_steps.test.tsx`, one fixture report per case.
  *Breaks when:* any of the three reports shows Start.

- **INV-9** — The stored text size is applied before first paint, every size scales rem text, and an unknown stored value gives the default.
  *Test:* `frontend/src/lib/__tests__/textSize.test.ts`, for the root value and the fallback. A test on `main.tsx`'s call order, in the `?raw` style of `LibraryPage_error_boundary.test.ts`, fails if `applyTextSize` follows `createRoot`.
  *Breaks when:* the size is applied in an effect, or a bad stored value reaches the style.

- **INV-10** — At the largest size, in a window 1280 CSS pixels wide, the guide and the Library in both views scroll in one direction only, and no game card's title is cut off by its row.
  *Test:* `frontend/e2e/guide-flow.spec.ts`, comparing `scrollWidth` with `clientWidth` and each visible card's height with its row at `200%`.
  *Breaks when:* `rowHeightPx` is not scaled, or the nav does not wrap.

- **INV-11** — In simple view, the items §4.7 hides are absent from the page, and full view renders everything it does today.
  *Test:* `frontend/src/pages/__tests__/LibraryPage_view.test.tsx`, by test id and landmark for each view.
  *Breaks when:* a hidden item renders, or one goes missing from full view.

- **INV-12** — Filters that are on when the view is simple are stated on the page, and can be cleared there.
  *Test:* `LibraryPage_view.test.tsx`: set a genre in full, switch to simple, assert the notice, clear it, assert the query has no genre.
  *Breaks when:* a hidden filter narrows the grid with no notice.

- **INV-13** — The folder chosen in the guide passes the same server path validation as Settings, and the guide cannot browse outside the existing allowlist without the existing grant confirmation.
  *Test:* `GuidePage_steps.test.tsx` asserts the save goes through `PATCH /api/config` and a `fs_sandboxed` listing shows `FsBrowser`'s confirmation.
  *Breaks when:* the guide adds its own write route or skips the grant.

- **INV-14** — In setup mode, only the §4.8 step is reachable.
  *Test:* `GuidePage_entry.test.tsx`, with `setup_required: true`.
  *Breaks when:* the guide offers games that cannot load.

## 6. Failure modes

- **`/api/games` or a page of it fails mid-way:** no copy starts, the step shows the reason, and Back works (INV-7).
- **The library changes between the count and the copy:** the names are fetched when the user presses "Copy these". The Check step's counts are the ones they act on.
- **A copy is already running:** the start's error is shown (INV-7). The guide does not attach to the other job, because `useCopySession` has no resume.
- **The page is reloaded or closed during a copy:** the copy carries on at the server, and the guide restarts at the first step. This matches the Library's `CopyModal` today, and the guide says so on the Copying step: "You can close this page. The copy will carry on."
- **A playlist in the legacy format:** `APPEND` fails at the server, per `read_lpl`, and the reason shows through the copy's error state.
- **The destination is removed after the Where step:** the Check step reports it.
- **No genres, or an empty group:** a group with no games says so on "What that finds" and offers only Back.
- **`localStorage` unavailable:** size and view use defaults; the guide opens on each load.

## 7. Tests

| Invariant | Test |
|---|---|
| INV-1, INV-14 | `frontend/src/pages/__tests__/GuidePage_entry.test.tsx` |
| INV-2 | `frontend/src/components/guide/__tests__/GuideStep.test.tsx` |
| INV-3, INV-4, INV-7, INV-8, INV-13 | `frontend/src/pages/__tests__/GuidePage_steps.test.tsx` |
| INV-5 | `frontend/src/lib/__tests__/fetchGameNames.test.ts` |
| INV-6 | `GuidePage_steps.test.tsx` and `frontend/e2e/guide-flow.spec.ts` |
| INV-9 | `frontend/src/lib/__tests__/textSize.test.ts` |
| INV-10 | `frontend/e2e/guide-flow.spec.ts` |
| INV-11, INV-12 | `frontend/src/pages/__tests__/LibraryPage_view.test.tsx` |

**Existing tests that change:** the simple view is the default, so `_libraryPageFixtures.tsx` and `frontend/e2e/*.spec.ts` set `LIBRARY_VIEW_KEY` to `full` and `GUIDE_SEEN_KEY`, so they keep testing today's page. `LibraryPage_error_boundary.test.ts` and `landmark_labels.test.tsx` read `LibraryPage.tsx` as text, so its modals stay in that file.

Each new test must be seen to fail before its code exists. `frontend/e2e` does not run in `local-CI.sh` or CI, so INV-6 and INV-10 run by hand with `cd frontend && npm run e2e`; §10 says so.

## 8. Alternatives considered (and rejected)

- **A tour of pop-up notes over the current page.** The user rejected it on 2026-10-30. The clutter stays on screen, and pop-ups are hard to follow when magnified.
- **One big "copy everything" button.** The user rejected it as the first screen on 2026-10-30, because it gives no choice. It survives as the guide's first option.
- **Building the selection through the cart.** It would overwrite or mix with a user's own cart, and carries `MAX_CART_SIZE`. Rejected for INV-4.
- **Storing text size in `config.yaml`.** It would apply after first paint and flash small text. Rejected for INV-9. The cost is that the size does not travel in a Backup export.
- **Browser zoom alone.** It offers no starting size and must be set by someone who can already read the page. The app's own default is larger.
- **All four wizards in one spec.** Rejected because the picture half of mame-curator-1146 needs new backend work, and a merged spec would delay what the user needs first.

## 9. Out of scope

- First-time setup wizard — tracked by mame-curator-1145.
- Picture and version wizard — tracked by mame-curator-1146.
- Settings wizard — tracked by mame-curator-1147.
- The Library's silent copy refusal — tracked by mame-curator-1148.
- The Library's hidden undated games — tracked by mame-curator-1150.
- Add all's review-state gap — tracked by mame-curator-1151.
- Renaming the Walkthrough mode toggle — deferred; not yet queued. Simple view hides it.
- Screen-reader polish of the existing Library, `axe-core` in CI, and contrast themes — deferred; not yet queued.

## 10. What checks this

| Rule | What catches a breach |
|------|----------------------|
| INV-1, INV-14 | `GuidePage_entry.test.tsx` |
| INV-2 | `GuideStep.test.tsx` |
| INV-3, INV-4, INV-7, INV-8, INV-13 | `GuidePage_steps.test.tsx` |
| INV-5 | `fetchGameNames.test.ts` |
| INV-6 | Partial: `GuidePage_steps.test.tsx` catches a wrong strategy in CI; the real repeat copy is `guide-flow.spec.ts`, which no gate runs |
| INV-9 | `textSize.test.ts` |
| INV-10 | **nothing automatic** — `guide-flow.spec.ts` runs by hand, because no gate runs `frontend/e2e` |
| INV-11, INV-12 | `LibraryPage_view.test.tsx` |
| Large text and the one-column layout read well for this user | **nothing** — only the user can judge this, on the running app |

## 11. Cross-doc impact

- `CHANGELOG.md`: a user-facing entry.
- `docs/help/01-getting-started.md` and `02-choosing-games.md`: describe the guide and the simple view.
- `README.md`: screenshots and first-run description, if they show the old first screen.
- `docs/specs/P14-review-state.md` and `docs/specs/P15-cart-curated-library.md` name `LibraryPage.tsx`. Their behaviour holds in full view; no clause changes.
- `frontend/screenshots/`: set the same storage keys so screenshots stay stable.

## 12. Cold-eyes loop log

Rows live in `../reviews/mame-curator-1144-guided-library-loop-log.md`.

## 13. Migration / compatibility

Three new `localStorage` keys, no config or API change. An existing user sees the guide once, at the larger text size, in simple view. The `/start` route and the storage keys are the only new names other work binds to; mame-curator-1145 to mame-curator-1147 reuse `GuideStep`.

## 14. Open questions

- Does "leave the page as it is" mean today's full page should stay reachable by a switch? The design assumes yes. If it means the Library should not change at all, §4.7 goes and the size change stays.
- Should an existing user get the guide once, or only a new one? The design shows it once to everyone, since the user is that existing user.

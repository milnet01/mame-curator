**Line counts, subject files as read:**
- `frontend/src/App.tsx` 612
- `frontend/src/main.tsx` 14
- `frontend/src/index.css` 211
- `frontend/src/components/layout/AppShell.tsx` 193
- `frontend/src/lib/textSize.ts` 56
- `frontend/src/lib/guideState.ts` 23
- `frontend/src/components/library/LibraryGrid.tsx` 301
- `frontend/src/components/alternatives/AlternativesDrawer.tsx` 289

**Disagreement resolved:** the brief asks for my context first, and `review-lane` puts line counts first and does not let a brief change the opening. I followed `review-lane`.

**In context on arrival:**
- The global `~/.claude/CLAUDE.md`.
- The `review-lane` prompt.
- An Ants MCP session-start note.
- An email and environment note.
- No project `CLAUDE.md`, memory index or git snapshot.

**Tempted to open and did not:**
- Test files, including the INV-10 e2e spec.
- `docs/journal` and `docs/reviews`.
- `_shared/review-cost.md`.
- `LibraryFullHeader` and `FiltersSidebar`, which I treated as other lanes' subject.

Nothing here was run: no browser, build or tools. Every layout claim comes from reading the CSS and code. I ran no test-tree counts, because no 2b case needed them.

## Critical (0)

## High (5)

- [dim 2] `frontend/src/components/alternatives/AlternativesDrawer.tsx:150` — `const parent = winner.short_name;` — this sends the current winner as the override's parent.
  - `filter/spec.md` Phase C keys overrides by the **parent short name**. `filter/runner.py:70` then ignores any other key: `if parent not in groups:`.
  - So when the winner is a clone, which includes every game already overridden once, the pick is dropped. It still writes a dead entry to `overrides.yaml`.
  - The user still sees success. `LibraryPage.tsx` shows `toast.success(strings.library.overrideApplied)` and never reads the `warnings` in the response.
  - A second override of any game cannot take effect.
  - fix: send the family's real parent, which means carrying it on the card or the alternatives response, and show `warnings` instead of success.

- [dim 12] `frontend/src/components/library/LibraryGrid.tsx:278` — `data-active={isActive || undefined}` — the "active" card cannot be seen, and arrow keys never move focus.
  - My search found no CSS for `data-active`.
  - No `focused=` is passed to `GameCard`, so its `focused && "ring-2 ring-ring"` never applies.
  - No `.focus()` exists in the grid or in `useGameGridFocus`.
  - A keyboard user pressing arrows sees only scrolling. Enter, R, S and ? then act on a card nothing marks.
  - This fails the spec's Goal for a partially sighted user. Tab reaches every card regardless, so the roving tabindex does nothing.
  - fix: pass `focused={isActive}` and move DOM focus to the active cell.

- [dim 2] `frontend/src/components/library/LibraryGrid.tsx:163` — `const card = cards[activeIndex];` — Enter opens the wrong game.
  - `GameCard`'s wrapper (`tabIndex={0}`) calls `onOpen()` for the focused card and does not stop propagation.
  - The event then reaches this handler, which calls `onOpen` for `cards[activeIndex]`, and the last call wins.
  - Nothing syncs `activeIndex` with focus or clicks. So Tab to card 2 and press Enter opens card 1. R and S also change the wrong card.
  - Enter or Space on the inner Add button is caught the same way, by `GameCard`'s `handleKeyDown` (`e.preventDefault(); onOpen();`). Add therefore cannot be pressed from the keyboard, against the coding-standards rule "every interactive element keyboard-reachable".
  - fix: ignore events from nested controls and update `activeIndex` on focus-in.

- [dim 7] `frontend/src/components/library/LibraryGrid.tsx:170` — `case "r":` — the key switch never checks modifier keys.
  - With focus in the grid, Ctrl+R blocks the reload and writes `reviewed` to server state, and Ctrl+S writes `skipped`. With walkthrough on, focus also advances.
  - Ctrl+K also moves up a row (`case "k":`) as well as opening the palette, and Ctrl+O opens a card.
  - fix: return early on `e.ctrlKey || e.metaKey || e.altKey`.

- [dim 12] `frontend/src/components/alternatives/AlternativesDrawer.tsx:209` — `className="flex w-full max-w-md flex-col gap-4"` — the drawer cannot scroll.
  - `SheetContent` is `fixed inset-y-0 h-full`, with no overflow rule in `ui/sheet.tsx`. Under `components/alternatives/` the only `overflow` match is the thumbnail's `overflow-hidden` (line 94).
  - Each row is about 6.5rem. By my estimate only about four rows fit at the new 125% default in a 720px window, and about two at 200%.
  - Lower rows and the Launch button (`mt-auto`) then sit below the screen, with no way to reach them. Arrow-key highlighting does not scroll either.
  - This predates mame-curator-1144, but the larger default text makes it common.
  - fix: make the row area `overflow-y-auto` with `min-h-0`, and scroll the highlighted row into view.

## Medium (5)

- [dim 2] [dim 2b behaviour] `frontend/src/components/library/LibraryGrid.tsx:26` — `groupKey?: "genre" | "year" | "publisher";` — this prop is never read.
  - `docs/design.md:512` promises Grouped as "sectioned by genre… each section a horizontal scroller".
  - `LayoutSwitcher` offers it, and it renders exactly as masonry (line 67).
  - This is a zombie feature. fix: build it, or remove the option and correct the document.

- [dim 2] `frontend/src/components/library/LibraryGrid.tsx:94` — `const columns = resolveColumns(layout, cardsPerRowHint);` — rows grow with the text size, but column counts and widths do not.
  - At 200% in a 1280px window in full view, the 16rem sidebar takes 512px and five columns share the rest. By my estimate that leaves roughly 90px of text width per card at about 28px type.
  - `line-clamp-2` then cuts a title to around a dozen characters. INV-10's bottom-edge test would still pass, because the row does not cut it.
  - The cause is that the media queries behind Tailwind's breakpoints do not follow the root font size.
  - The document may share the blame: §4.6 scales rows only.
  - fix: reduce columns as `fontScale` grows, or use a minimum card width in rem.

- [dim 7] `frontend/src/App.tsx:384` — `if (!config.data) {` — a failed config load shows "Loading settings" forever, plus one toast that disappears.
  - This breaks coding-standards § 13, "No silent spinners that never resolve". The sibling routes all handle `error`.
  - It also matters for guide §4.8's "Open Settings" route.
  - fix: add the same error branch as the sibling routes.

- [dim 7] `frontend/src/App.tsx:308` — `topicHtml={topic.data?.html ?? ""}` — `topic.error` is dropped. A failed help topic leaves an empty pane after the toast disappears, which also breaks § 13.
  - fix: pass an error prop and render it.

- [dim 7] `frontend/src/App.tsx:176` — `onActivate={(name) => activate.mutate(name)}` — session failures are invisible.
  - The same applies to `deactivate.mutate()` (line 177) and `del.mutate(pendingDelete)` (line 199).
  - My search found no `onError` in `useSessions.ts`, and `queryClient.ts` says mutations have no global handler.
  - A failed delete closes the dialog and leaves the session in place, with no message.
  - fix: add `onError: toastApiError` in the hooks.

## Low / Info

- [dim 2] `docs/help/01-getting-started.md:43` — `` - `Ctrl-K` (`⌘K` on a Mac) — search games, settings and actions. `` — the document is wrong. `CmdKPalette.tsx` removed the `games` and `settings` sections under FP27, and the palette only offers navigation and help topics. fix: correct the help line.
- [dim 2] `docs/help/01-getting-started.md:44` — `` - `/` — jump to the library search box. `` — off the Library route the key silently does nothing (`App.tsx` comment, FP27). The document is incomplete; the code matches its own spec. fix: add "on the Library page".
- [dim 2] `frontend/src/components/layout/AppShell.tsx:81` — `<h1 className="text-lg font-semibold">{strings.app.name}</h1>` — this makes two `<h1>`s on every guide step, where §4.3 says "one `<h1>` heading". fix: render the app name as a non-heading.
- [dim 13] `frontend/src/App.tsx:89` — `label: "Go to Library",` — this hardcoded text breaks the single-strings-module rule. So do lines 95, 101, 107, 113 and 119, `App.tsx:196` (`: "Delete"`) and `AppShell.tsx:178` (`: "Ctrl+K"`). The Start-here entry beside them does use `strings`. fix: move them to `strings`.
- [dim 16] `frontend/src/lib/textSize.ts:46` — `window.addEventListener(CHANGE_EVENT, onChange);` — this only hears the same tab, because there is no `storage` listener. A second tab keeps the old size and an out-of-date selector until reloaded. No data is lost. fix: also listen for `storage`.
- [dim 4] `frontend/src/lib/guideState.ts:11` — `return localStorage.getItem(GUIDE_SEEN_KEY) !== null;` — if `getItem` works but `setItem` throws, for example when storage is full, `seenInMemory` is set and never read. The check runs once per load, so the in-memory flag has no visible effect in any case. fix: check it first or remove it.
- [dim 11] Resource limits: nothing found in this lane. Portability: nothing found in these files; I did not check packaged bundles.
- [dim 3] Nothing found. There is no HTML sink here, and `encodeURIComponent` is used on media and palette URLs.
- [dim 5] Nothing found. [dim 8] N/A. [dim 9] Nothing found. [dim 10] N/A, no contract named.
- [dim 15] Nothing found. The only state written by these files is the two `localStorage` keys, and no telemetry code appears in them.
- [dim 17] Nothing found. Stored keys are versioned, a bad stored value falls back to the default, and there is no config change.
- [INFO] I could not judge real layout, focus or screen-reader behaviour. All layout figures above are arithmetic from the classes, not measurements.

## Covered by spec and looks correct

I read these and they match, but did not run them:
- `App.tsx` redirect logic against §4.2 and INV-1: it fires once per load, only at `/`, and `*` is not redirected.
- `GuidePage.tsx` marks the guide seen only when `setup_required` is false (INV-14).
- `main.tsx` calls `applyTextSize` before `createRoot`, and `index.html` paints nothing earlier (INV-9).
- `textSize.ts` matches §4.6, and its guards and bad-value fallback are correct. `isTextSize` is not fooled by inherited property names.
- Fixed-pixel text: my search of `frontend/src` found no `text-[Npx]`. `h-[300px]` survives only as `max-h-[300px]` on the palette list, which scrolls, so it does not clip.
- `LibraryGrid` applies the scaled row height, the re-measure on size change and `min-h-[60vh]`, as §4.6 specifies.
- `GameCard` titles cannot be pushed out of a scaled row, because the flyer has `min-h-0 flex-1` and the text block does not shrink.
- `/start` survives a reload: `_SPAStaticFiles` in `api/app.py` falls back to `index.html`.
- `AppShell`'s Start-here entry and labelled Text size control are present, and the header wraps.

## Open questions

- At 200%, a `covers` row (720px) is taller than the grid area in a 720px window, so a whole card cannot be seen at once in simple view. Should flyers scale with text at all? §4.6 says multiply, and no invariant covers it.
- Changing text size keeps the scroll offset in pixels, so the user loses their place in the grid. No contract addresses this.
- I read `GameCard` only up to its title and did not open the type's interface fully. `types.ts:220` starts it, and the first `parent: string` is at line 257, outside what I confirmed is in `GameCard`. The override fix may need an API change.
- This assumes `groups` in `runner.py` is keyed as `filter/spec.md` says. I did not read the line that builds it.

## 3 items to fix first

1. **Override parent (`AlternativesDrawer.tsx:150`).** It silently discards the user's choice and reports success, and it writes a dead entry to disk.
2. **Invisible active card, plus Enter opening the wrong game (`LibraryGrid.tsx:278`, `:163`).** For this project's partially sighted user, the grid can't be trusted from the keyboard, and review keys can change the wrong game.
3. **Modifier keys and the unscrollable drawer (`LibraryGrid.tsx:170`, `AlternativesDrawer.tsx:209`).** Ctrl+R writes state instead of reloading, and the new default text size pushes versions and Launch off the screen.

**Files opened:**
- The eight subject files.
- The shared context.
- `docs/specs/mame-curator-1144-guided-library.md`.
- `docs/help/01-getting-started.md`.

**Slices:**
- `docs/standards/coding-standards.md` §§ 4 and 13
- `frontend/src/hooks/useKeyboard.ts`
- `frontend/src/hooks/useGameGridFocus.ts`
- `frontend/src/components/library/GameCard.tsx`
- `frontend/src/components/ui/sheet.tsx`
- `frontend/src/components/CmdKPalette.tsx`
- `frontend/index.html`
- `frontend/src/pages/LibraryPage.tsx`
- `frontend/src/pages/GuidePage.tsx`
- `frontend/src/components/guide/GuideStep.tsx`
- `frontend/src/lib/queryClient.ts`
- `frontend/src/api/types.ts`
- `src/mame_curator/api/routes/curate.py`
- `src/mame_curator/api/routes/games.py`
- `src/mame_curator/filter/runner.py`

**Seen as search rows only:**
- `src/mame_curator/api/app.py`
- `src/mame_curator/filter/spec.md`
- `docs/design.md`
- `docs/specs/P06-frontend-mvp.md`
- `frontend/src/hooks/useUpdates.ts`
- `frontend/src/hooks/useConfig.ts`
- `frontend/src/hooks/useSessions.ts`
- `frontend/src/pages/HelpPage.tsx`
- `frontend/src/components/library/LayoutSwitcher.tsx`
- `frontend/src/strings_internal.ts`
- `docs/help/02-choosing-games.md`

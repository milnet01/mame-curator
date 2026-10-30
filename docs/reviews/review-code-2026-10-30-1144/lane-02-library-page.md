**Line counts of the subject files as read (Read tool):**
- `LibraryPage.tsx` 369
- `useLibraryController.ts` 368
- `libraryPageHelpers.ts` 101
- `libraryView.ts` 25
- `LibraryFullHeader.tsx` 94
- `SimpleLibraryBar.tsx` 94
- `AbortCopyDialog.tsx` 67
- `CopyModal.tsx` 175
- `FiltersSidebar.tsx` 365
- `useCopySession.ts` 213
- `useGames.ts` 59
- Contract: spec 311, `02-choosing-games.md` 40

*Disagreement resolved:* the brief puts the context statement first, but my lane file fixes the return's opening as line counts, so counts come first.

**Already in context on arrival:** global `CLAUDE.md`, the user's email, the environment block, a SessionStart note about Ants MCP, and this lane's own prompt. There was no git snapshot, memory index or project `CLAUDE.md`. The shared context then added the module map, quoted project rules, the false-positive ledger and the allowlist.

**Tempted to open and did not:**
- `LibraryPage_view.test.tsx` and the other tests
- the FP27 spec
- `useCart.add`
- `GuidePage` and `CopyingStep`

**Exclusion disclosure:**
- Three searches ran with a narrower `exclude_glob`, or none: one over `src/mame_curator/copy`, one with a `frontend/src/{...}` glob, and the `simpleLibrary` search. None returned a test file.
- One search returned rows from `docs/plans/P15` and specs that name test functions. I read those rows but opened no test.
- I ran no test-wiring counts.

## Critical (0)

## High (4)

- [dim 2] `frontend/src/pages/useLibraryController.ts:291` — `if (st === "finished" && policy !== "never") {` — The `on_success` branch never looks at the outcome.
  - `jobs.py` `_on_worker_done` sends `PARTIAL_FAILURE` as `job_finished`, so the default policy clears the cart and closes the modal after a partial failure. The user loses the list of games to retry and sees nothing.
  - This violates P15 D9: "clear on success, retain on partial/failed". `finishedStatus` is read only by `CopyingStep`.
  - The code is wrong. Line 289's `?? "on_success"` also clears the cart of a `never` user whose config has not loaded.
  - fix: require `finishedStatus === "OK"` for `on_success`, and keep the modal open otherwise.

- [dim 12] `frontend/src/components/library/GameCard.tsx` (`handleKeyDown`) — `if (e.key === "Enter" || e.key === " ") {` — The Add button has no key handler of its own, and this wrapper handler does not check `e.target`.
  - Enter on Add bubbles up, is `preventDefault`ed, and opens the drawer instead of adding. `LibraryGrid.onKeyDown` then opens it again.
  - Simple view offers almost nothing else for building a cart, so this breaks the coding-standards bullet on keyboard use. Space is probably blocked too, but browser behaviour was not tested.
  - I did not check whether the drawer offers an Add.
  - fix: act only when `e.target === e.currentTarget`.

- [dim 2b] `frontend/src/components/library/CopyModal.tsx:95` — `{state.conflict && (` — The conflict banner cannot appear.
  - `useCopySession.ts:81` is the only assignment and always sets `null`. `JobEventNameSchema` has no conflict event, and P04 says conflicts "never become SSE events".
  - The hook's docstring (lines 28-29) still promises the banner.
  - The FP27 spec was not opened, so I rely on the comments here. The code comment and banner look stale, and the 409 path (mame-curator-1148) is the real one.
  - fix: remove the banner and comment, or wire it to a real signal.

- [dim 16] `frontend/src/pages/LibraryPage.tsx:325` — `onOpenChange={(open) => !open && copySession.reset()}` — Esc, an outside click or the close button during a copy discards all UI state while the job keeps running.
  - In the frontend, only this hook posts to `/api/copy/abort`, and nothing in it reattaches, so Pause and Cancel are lost. I did not check the backend or the CLI.
  - The cart policy never fires, Copy becomes enabled again, and a retry fails silently.
  - Spec §6 accepts this for a reload, not for a dismissal.
  - fix: block dismissal while running or paused, or let the user reopen the modal.

## Medium (8)

- [dim 7] `CopyModal.tsx:129` — `{(state.state === "finished" || state.state === "aborted") && (` — The Done button comment (FP11 D8) cannot hold on the default policy, because the effect resets as soon as the job finishes. A successful copy ends with the modal vanishing and no notice. Under `never`, `PARTIAL_FAILURE` reads as plain "finished", because the modal never reads `finishedStatus`. fix: add a toast, and show the status in the modal.

- [dim 7] `frontend/src/hooks/useCopySession.ts:208` — `pause: pauseMutation.mutate,` — Pause, Resume and Abort have no `onError`, and `queryClient.ts` says mutations have no global handler. A failed Cancel closes its dialog and looks done. fix: pass `onError: toastApiError` and keep the dialog open.

- [dim 16] `useCopySession.ts:172` — `if (es.readyState === EventSource.CLOSED) closeStream();` — After a server restart, `/api/copy/status` answers 404 (`routes/copy.py`), the stream closes, and the modal stays "running" forever. While the server is unreachable, nothing tells the user either. This breaks coding-standards §13, "No silent spinners". fix: set a visible lost-connection state.

- [dim 7] `useCopySession.ts:153` — `return { ...prev, state: "aborted" };` — `reason` is dropped, so a crashed worker (`_on_worker_error`) looks the same as the user's own Cancel. fix: keep `reason` and show it.

- [dim 2] `CopyModal.tsx:134` — `{state.state === "terminating" && (` — The hook never sets `terminating`, and the abort reply carrying it is discarded. After Cancel, Pause and Cancel stay live until the file boundary, so the copy looks like it ignored the request. fix: set `terminating` on abort success.

- [dim 2] `useCopySession.ts:128` — `return { ...prev, state: "paused" };` — The UI changes only on the `paused` event, and that is sent only from `_ProgressSynthesizer.__call__`. If Pause lands after a file's last progress tick, `runner.py` blocks at `wait_if_paused()` with no event. The modal then shows Pause with no Resume. The timing was not measured. fix: apply the state from the pause and resume replies.

- [dim 2] `frontend/src/strings_internal.ts:112` — `"Adjust the filters in the sidebar or clear them to see your full library.",` — This hint also shows in simple view, which is the default and has no sidebar, so it points a lost user at something that isn't there. `docs/help/02-choosing-games.md:18-19` says the same, so both the text and the help page are wrong for simple view. fix: use wording per view.

- [dim 16] `LibraryPage.tsx:99` — `? "grid h-full grid-cols-1 grid-rows-[auto_1fr_auto]"` — The comment at lines 144-146 says the bars "cannot crush" the grid, but the `1fr` track holding the scroll area can reach 0. The grid's `min-h-[60vh]` then sits inside a zero-height scroller.
  - My estimate, not measured, for 1280×800 at 200%: bar about 330px, `CartBar` about 100px, and `CartPanel` up to `max-h-80`, which is 640px. Opening the cart hides the games.
  - Full view has the same risk.
  - fix: `minmax(60vh,1fr)`, letting `#main` scroll.

## Low / Info

- [dim 4] `FiltersSidebar.tsx:102` — `onChange({ ...value, search: searchDraft });` — This closes over a stale `value`, so a filter or tile changed within 200 ms is reverted. `SimpleLibraryBar` uses `setFilters(prev => …)`, so the copies have diverged and the sidebar is the wrong one.
- [dim 7] `useCopySession.ts:67` — `if (cancelledRef.current) return;` — The unmount cleanup sets this and nothing clears it, and `main.tsx` uses `StrictMode`. In a dev build, every Library copy starts on the server and never shows. The comment also claims `reset()` sets it, which it does not.
- [dim 7] `useCopySession.ts:97` — `switch (msg.event) {` — A JSON `null` frame throws inside the state updater, despite the FP24-K comment.
- [dim 16] `useCopySession.ts:136` — `warnings: [` — A reconnect replays history (`_events_iterator`), so BIOS warnings are appended twice.
- [dim 2] `LibraryPage.tsx:364` — `copyDisabled={validateCart.isPending || copySession.state !== null}` — The lock is off between validate success and start success, despite the FP24-N comment. A second start fails silently.
- [dim 13] `CopyModal.tsx:77` — `State: {strings.copy.sessionState[state.state] ?? state.state}` — This hardcoded text, and "would replace" at line 113, sit outside the strings module.
- [dim 2] `AbortCopyDialog.tsx:33` — `<Dialog open={open} onOpenChange={onOpenChange}>` — The standard requires `AlertDialog` for destructive actions. The title is "Cancel", and `common.cancel` (value not read) sits beside it meaning "keep copying".
- [dim 2] `LibraryFullHeader.tsx:76` — `type="checkbox"` — The standard asks for `Switch` on binary preferences. This is today's page, so changing it needs care.
- [dim 7] `useLibraryController.ts:312` — `if (!config.data) return;` — Saving a session with no config does nothing, and the sidebar still closes its dialog.
- [dim 2] `libraryView.ts:23` — `/* localStorage unavailable; the choice lasts until the page closes. */` — This is false: `LibraryPage` re-reads on remount, so moving to another route loses the choice. The comment is wrong, and spec §6 is met.
- [dim 16] `SimpleLibraryBar.tsx:38` — `setDraft(search);` — A keystroke landing between the debounce firing and its commit could be overwritten. This comes from reasoning only and was not observed. A view switch within 200 ms also drops the pending text (line 44).
- **INFO:** no real browser, so all layout claims are estimates. INV-10, including title clipping in narrow full-view columns at 200%, was not judged.
- **INFO:** not refiled because the spec tracks them: 1148 (`CANCEL`, no start `onError`), 1150, and 1151 (`handleBulkAdd` lines 204-218 omit `review_state`).

**Other dimensions:**
- Dim 3: nothing found in these files.
- Dim 5: no contract named; nothing found.
- Dim 8: nothing beyond the stale closure above.
- Dim 9: only the cart-clear finding.
- Dim 10: N/A.
- Dim 11: no OS-specific paths in these files.
- Dim 15: nothing here sends data off the machine.
- Dim 17: unknown stored view falls back to simple, as §13 says.

## Covered by spec and looks correct

Read and confirmed against the code, not run:
- **INV-11:** each §4.7 item is gated on `simple`, both views have `filters-search` (one at a time), and `covers` is applied without touching config.
- **INV-12:** `filtersOn` compares with `DEFAULT_FILTERS`, Clear resets filters and `activeTileId`, the box follows `filters.search`, and the "first X of N" line is present.
- **§4.4 "Look through them first":** the selection is read once, with tile, genre and everything handled as specified, and state is cleared with `replace`. Add all appears only on the tile path.
- **INV-4, partly:** a search for `useCart(` returned only `App.tsx` and `useCart.ts`, with no truncation. `GuidePage` itself is not in this lane.
- **SSE wiring:** the server sends unnamed frames, so `onmessage` fires, and `file_finished` carries `files_done`.

## Open questions

- `GameCard`'s label says "remove" when `inCart`, but `LibraryPage.tsx:206` always calls `cart.add`. Does `add` toggle? `useCart.add` was not opened.
- Walkthrough stays active in simple view, so R, S and ? still change review state and move focus, and its toggle is hidden. Spec §9 hides the toggle and says nothing about the behaviour. Is that intended?
- More options and Fewer options remove the focused button, so focus falls to `<body>`. §4.3's focus rule names guide steps only. Is this bound?
- Typing a search shows "Some filters are on", as §4.7 literally requires. Was that meant for a visible search box?
- `handleSaveSession` saves config-preferred genres, not the selected genre. Help says "your current focus". I can't tell which side is wrong.
- The default year range still hides undated games without notice in simple view, despite the bar's "cannot silently shrink" comment. This is tracked (1150), and INV-12 as written is met.

## 3 items to fix first

1. **Partial failure clearing the cart (`useLibraryController.ts:291`):** it silently destroys the user's retry list on the default setting and breaks a written decision.
2. **Enter on Add opening the drawer (`GameCard`):** a keyboard user can't reliably build a cart in the view this feature made the default.
3. **Dismissing the copy modal (`LibraryPage.tsx:325`):** one Esc loses Pause and Cancel on a running copy, with no way back.

**Files opened:**
- `shared-context.md`
- the eleven lane files
- the spec
- `docs/help/02-choosing-games.md`
- slices of `docs/standards/coding-standards.md` (§§4, 9, 13)
- `frontend/src/components/library/LibraryGrid.tsx`
- `frontend/src/components/library/CartBar.tsx`
- `frontend/src/components/library/GameCard.tsx` (1-200)
- `frontend/src/components/library/CartPanel.tsx` (1-60)
- `frontend/src/components/layout/AppShell.tsx` (183-193)
- `frontend/src/App.tsx` (480-510)
- `frontend/src/api/schemas.ts` (501-512)
- `frontend/src/strings_guide.ts` (94-103)
- `frontend/src/lib/fetchGameNames.ts` (1-30)
- `src/mame_curator/api/jobs.py` (49-60, 107-153, 197-310, 325-482)
- `src/mame_curator/api/routes/copy.py` (74-113)

# close-findings: review-code on mame-curator-1144

Dated record, 2026-10-30. Source: `docs/reviews/review-code-2026-10-30-1144/`. Each finding's text is in its lane file. Locations are as the review cited them at dc8bb1c. An empty disposition means not yet closed.

User rulings, 2026-10-30:

- The large text is good; no layout changes wanted.
- Hide the exit while a copy is paused.
- Offer Start for games on disk but not in the playlist.

## Group 1: copy honesty

| Finding | Sev | Verified | Disposition | Was → now |
|---|---|---|---|---|
| `useCopySession.ts:153` and CopyingStep: `reason` dropped, a crash reads as Stop | MEDIUM | yes, read at dc8bb1c | fixed | Reason dropped, crash showed "The copy has stopped." → reason kept; only `CANCELLED` reads as Stop, anything else shows `role="alert"`, the reason and Activity. Red seen in `useCopySession.test.tsx`, `CopyingStep.test.tsx`. |
| `useCopySession.ts:172`: lost stream stays running | MEDIUM | yes, read | fixed | Frozen "Copying" → `connection: "lost"` shows an alert, no progress and no controls; a retrying stream shows "reconnecting" with controls kept. Red seen. |
| `useCopySession.ts:178`, `:208`: pause, resume, abort failures silent | MEDIUM | yes, read; no `onError` on any | fixed | Silent → `controlError` in plain words plus the API's message, `role="alert"` in the guide and the modal, cleared by the next attempt. Red seen. |
| `jobs.py:143`, `useCopySession.ts:128`: Pause before a tick leaves no Resume | MEDIUM | yes, measured: `test_pause_before_any_tick_reaches_the_stream` with the real `run_copy` showed the worker alive and held, with only `job_started` in history | fixed | Emitted only from a tick → `JobManager.pause` and `.resume` emit on the transition; the tick no longer does. Chosen over applying the replies because a reconnect replays events, so the stream stays the one truth. `api/spec.md` updated. Red seen. |
| `CopyingStep.tsx:50`: exit live while paused (user ruling: hide it) | MEDIUM | yes, read | fixed | Exit always shown → hidden while paused, back when running or if the stream is lost. Spec §4.3 and INV-3 amended to match the ruling. Red seen. |
| `CopyingStep.tsx:67`: warnings not shown | MEDIUM | yes, read | fixed | Never shown → plain lead sentence and list below the actions. Red seen. |
| `CopyingStep.tsx:79`: focus lost on Pause/Resume | MEDIUM | yes, red run showed focus on the heading | fixed | Two buttons in two branches → one button in both the guide and the modal; the hint is a `role="status"` region. A new "Stopping the copy…" heading moves focus when Stop removes the button. Red seen. |
| `CopyingStep.tsx:110`: dialog stays open after the job ends | MEDIUM | yes, read; `CopyModal` had the same line | fixed | `open={abortOpen}` → also needs the job running or paused, in both. Red seen. |
| `useLibraryController.ts:291`: cart cleared on partial failure | HIGH | yes, read against P15 D9 | fixed | Any finish cleared on `on_success`, and a not-yet-loaded config counted as `on_success` → only `OK` clears, nothing happens until the config loads, a lost stream never clears. `always` still clears, but a partial or crash stays on screen. Red seen in `LibraryPage_copy.test.tsx`. |
| `LibraryPage.tsx:325`: dismissing the modal during a copy loses control | HIGH | yes, read; Esc reset it in the red run | fixed | Esc, outside click and the close button reset the session → `CopyModal` ignores dismissal and hides the close button until the copy ends or its stream is lost. Fix sits in `CopyModal`, not at the cited line. Red seen. |
| `CopyModal.tsx:95`: conflict banner can never show | HIGH → LOW | yes: `conflict` was only ever set to `null`, and no event carries one | fixed | Dead banner, field, type, strings and test → removed. FP27 A4 specified the banner; it could never render, so no behaviour moves. No red run: nothing observable changes. |
| `CopyModal.tsx:129`: Done and status | MEDIUM | yes, read | fixed | Modal vanished with no notice, partial read as "finished" → a clean finish gives a success toast, or a status line under `never`; partial and crash show an alert with Activity and Done. Red seen. |
| `CopyModal.tsx:134`: `terminating` never set | MEDIUM | yes, read; abort reply was discarded | fixed | Pause and Cancel stayed live after Cancel → an accepted abort sets `terminating`, unless the job has already ended; a replay cannot undo it. Red seen. |
| LOW, lane 1: `CopyingStep.tsx:92`, `:70`, `:95`; `AbortCopyDialog.tsx:33`, `:38`; `useCopySession.ts:51` | LOW | yes, each read; `:51` red only with StrictMode outermost, as in `main.tsx` | fixed, all six | `:92` Cancel → Stop, and the dialog's way out says "Keep copying". `:70` Link → `GuideAction`. `:95` as `CopyModal.tsx:134`. `:33` `Dialog` → `AlertDialog`. `:38` no recycle or keep at 0 files, only "Stop copying". `:51` mount clears the flag, comments corrected. Red seen for each. |
| LOW, lane 2: `useCopySession.ts:67`, `:97`, `:136`; `CopyModal.tsx:77`; `AbortCopyDialog.tsx:33`; `LibraryPage.tsx:364` | LOW | yes, each read; `:97` threw in the red run | fixed, all six | `:67` as `:51`. `:97` a frame with no payload is discarded. `:136` `job_started` resets the warnings a replay resends. `:77` text moved to strings, and the line is hidden for a crash or lost stream, where it was untrue. `:33` as lane 1. `:364` Copy stays off until start answers. Red seen, except `:77`'s move to strings: no red run, nothing observable changes. |

Group 1 run-level, 2026-10-30:

- `cited_by`: old names searched as whole tokens: `conflictTitle`, `conflictReadOnlyBanner`, `conflictRegionAriaLabel`, `_was_paused`, `abortConfirm`, "drops a job_aborted", "nowhere else". Hits are in `swept`.
- `swept`:
  - `api/spec.md` Copy job lifecycle: fixed, gains the emit rule.
  - `docs/specs/P04-http-api.md` event table: fixed, carries a superseded note. Its `_was_paused` sketch is frozen under that note.
  - Spec 1144 §4.3, INV-3, §6: fixed. INV-2, INV-7: agree.
  - `docs/specs/P15-cart-curated-library.md` D9: agrees. Its failure table says the modal "surfaces the failed list": see `out_of_scope`.
  - `docs/specs/FP27-zombie-features-data-integrity.md` A4: frozen, a closed fix pass.
  - `jobs.py` `check_playlist_conflict` docstring and `test_routes_copy.py` docstring: fixed, both stale by these fixes.
  - `docs/help/01-getting-started.md` "at any time" and `03-copying-games.md`: fixed.
  - `.claude/code-pairs.json`: absent.
- `collateral`: the `CopyModal` and guide tests that fed `state: "aborted"` with no reason, and the guide test pressing the old label, were updated to what the server sends and the new label.
- `surfaced`: none.
- `out_of_scope`:
  - A worker crash writes no report and no `copy_aborted` Activity entry (`_on_worker_error`), so the crash alert's Activity link shows only that the copy started. Read, not run.
  - `JobManager.pause` and `.resume` answer "paused" and "running" even when a cancel made the controller refuse. The frontend ignores those replies.
  - The top menu and browser Back still leave a paused guide copy, and browser Back still leaves the Library during a copy. Both lose control of it.
  - `strings.copy.biosWarning` says "listxml", which is jargon.
  - P15's failure table says `CopyModal` surfaces the failed list; it shows an alert and an Activity link.
- `falsified`: none.

## Group 2: keyboard and reach

| Finding | Sev | Verified | Disposition | Was → now |
|---|---|---|---|---|
| `GameCard.tsx` `handleKeyDown`: Enter on Add opens the drawer | HIGH | yes, read; red run showed `onAdd` never called, for Enter and Space | fixed | Wrapper took every key that bubbled → acts only when the key was pressed on the card itself, and the grid's Enter does the same, so the Add button's own click runs. Red seen in `GameCard.test.tsx`, `LibraryGrid_keyboard.test.tsx`, `library-keyboard.spec.ts`. |
| `LibraryGrid.tsx:278`: active card invisible, arrows never move focus | HIGH | yes, read; red run showed focus stayed put | fixed | Nothing moved → arrows, Home, End and walkthrough move real focus; a `:focus-visible` ring, thick and in rem, on the card and on Add; one Tab stop per card; the active row stays drawn when scrolled away. The remedy `focused={isActive}` was not used: it paints a ring on the first card at page load, with no focus there. Red seen in vitest and Playwright; ring read from the computed style and seen in a screenshot. |
| `LibraryGrid.tsx:163`: Enter opens the wrong game | HIGH | yes, red run: opened twice, and R marked the first card after a click on another | fixed | `activeIndex` never followed focus → the cell's `onFocus` sets it, so Enter, R, S and ? act on the game with focus. Red seen. |
| `LibraryGrid.tsx:170`: modifier keys not checked | HIGH → MEDIUM | yes, red run: default prevented, state written | fixed | Any modifier ran the key → Ctrl, Cmd or Alt returns early. `useKeyboard` had the same defect for the drawer's R, S and ?, so its plain bindings now skip those too. Red seen. |
| `AlternativesDrawer.tsx:209`: drawer cannot scroll | HIGH | yes, Playwright at 1280x800, 200%: highlighted row at viewport ratio 0 | fixed | No overflow → the whole panel scrolls; arrows bring the highlighted row into view. The whole panel, not the remedy's row list alone: at 200% the About text and Launch take the height the list would need. Highlight ring is inset, because the panel now clips an outer ring. Closing returns focus to what opened it: Radix returns it only to a trigger, and P14 says it returns. What it sends is unchanged. Red seen, except the inset ring: visual, checked by screenshot. |
| `LibraryPage.tsx:99`: open cart at 200% may hide the games (measure first) | MEDIUM | yes, measured in Chromium, 1280x800, 200%, games area height: cart closed 273px simple, 283px full; cart open **0px** in both views, with 6 or 40 cart rows | fixed: a bug, and it touches the no-layout-changes ruling | Games unreachable → with the cart open only, the middle row is `minmax(60vh,1fr)`, measured against a floor of 480px, and `#main` scrolls; opening scrolls the cart bar into view, so the button pressed stays on screen. Cart closed: unchanged, and a test holds `#main` unscrolled. Red seen: 0px. |
| `LibraryGrid.tsx:94`: columns do not follow text size | MEDIUM | settled | dismissed: user ruling 2026-10-30, no layout changes | |
| LOW, lane 2: `FiltersSidebar.tsx:102`, `LibraryFullHeader.tsx:76`, `useLibraryController.ts:312`, `libraryView.ts:23`, `SimpleLibraryBar.tsx:38` | LOW | yes, each read; `:38` reproduced at the props level, not by real typing | fixed, four and most of the fifth; part of `:38` dismissed | `:102` stale `value` → the debounce reads the latest. `:76` checkbox → `Switch`, as the standard and P14 ask. `:312` silent return → error toast. `:23` comment corrected, no red run: nothing observable changes. `:38` a returning search overwrote newer typing → a search this box sent itself no longer resets it. Dismissed part of `:38`: a view switch within the debounce drops the pending text. The box visibly empties, and retyping loses nothing else. Red seen for the rest. |
| LOW, lane 3: `AppShell.tsx:81`, `textSize.ts:46`, `guideState.ts:11` | LOW | yes, each read; `:81` measured: 2 `h1`s on a guide step | fixed, all three | `:81` `h1` → `p`, same look. The remedy alone would leave the Library with no `h1`, so it gains a screen-reader `h1`. `:46` adds a `storage` listener that applies the size. `:11` the in-memory flag is checked first. Red seen for each. |

Group 2 run-level, 2026-10-30:

- `cited_by`: searched as literal text in `docs/help`, spec 1144, P14, `docs/design.md`, `README.md`, `src/mame_curator`, `tests/docs`: `roving`, `tabIndex`, `useGameGridFocus`, `focused`, `focus ring`, `walkthrough-toggle`, `ring-ring`, `header h1`, `isGuideSeen`, `subscribeTextSize`, `arrow keys`. Hits are in `swept`.
- `swept`, asking of each fix whether it contradicts, breaks or makes stale:
  - P14 §§ on focus and INV-6: agree, and are now true: arrows move a focus ring, walkthrough moves focus, Esc returns to the card. Its code sketches are frozen.
  - Spec 1144 §4.3 "one `<h1>`": now true. INV-10: green. Its `walkthrough-toggle` test id is kept.
  - `src/mame_curator/filter/review_state_spec.md` INV-6: agrees.
  - `docs/design.md`: agrees.
  - `docs/help/01-getting-started.md` Keyboard shortcuts: not false, but lists no grid keys. See `surfaced`.
  - The comment above the games area in `LibraryPage.tsx`: agrees.
  - `.claude/code-pairs.json`: absent.
- `collateral`: `e2e/library-flow.spec.ts` read `header h1`, now `header` plus the app name's text.
- `surfaced`:
  - The command palette drops focus to the page on close: run. Radix returns focus only to a trigger, so other dialogs with none should match: read, not run.
  - Removing the focused card from the list, by R under a review filter with walkthrough off, should drop focus too: reasoned, not run.
  - The drawer's highlight and its focus are two cursors: arrows move one, Tab the other, and Enter acts on focus only.
  - Help lists no grid keys.
  - Copy reports that e2e leaves under `frontend/e2e/fixtures/data/` are ignored by git but not by Prettier, so `prettier --check` fails after an e2e run until they are removed.
- `out_of_scope`:
  - `GameCard`'s `focused` prop is dead. It was dead before this run, so it stays, per the project's rule.
  - `LibraryPage.tsx` was already past the 350-line cap, and this adds to it.
- `falsified`: none.

## Group 3: guide steps

| Finding | Sev | Verified | Disposition | Was → now |
|---|---|---|---|---|
| `WhatThatFindsStep.tsx:41`: stale fetch after Back | HIGH | yes, red run: the guide jumped to Where after Back and a new choice | fixed | Fetch ran on after Back → leaving the step aborts it, `fetchGameNames` takes the signal and returns nothing once aborted. Red seen in `GuidePage_results.test.tsx`; each part mutated. |
| `CheckStep.tsx:30`: BIOS claim not always true | MEDIUM | yes, read: `preflight` checks winners only, and `runner.py` skips a missing BIOS as `SKIPPED_MISSING_SOURCE`, so the job ends `OK` | fixed | Whole set promised → dry run adds `counts.bios_missing_source`, `job_finished` adds `bios_missing`. Check promises only the rest and states the missing; the outcome says so in a `role="alert"`. Spec §4.4, §4.5 and `api/spec.md` updated. Red seen in pytest and vitest. |
| `GuideStep.tsx:33`: heading changes not announced | MEDIUM | yes, still open after d0172a7: red in Chromium, no focus event on "This finds" or "Ready to copy?" | fixed | One `h1` throughout → `key={heading}`, a new element and a real focus event per text. The Check report and the Where folder are now `role="status"` regions, because focus reads only the heading. Red seen in vitest and Playwright. A real screen reader was not run. |
| `WhereStep.tsx:43`: error points at field errors not shown | MEDIUM | yes, red run; a search found no reader of `ApiError.fields` anywhere | fixed | "see field errors below" → `apiErrorMessage` gives one plain sentence per refused path, else the API's message, and `toastApiError` uses the same words, as its comment promised. The friendly string no longer says "below". Fix is in `apiErrorToast.ts`, not the cited line. Spec §4.4 updated. Red seen. |
| `strings_internal.ts:112`: empty-state hint names a sidebar simple view lacks | MEDIUM | yes, read; `docs/help/02-choosing-games.md` said the same | fixed | Names a sidebar → "Try a different search, or clear your filters…"; help page matches. Red seen. |
| LOW, lane 1: `WhatThatFindsStep.tsx:54`, `CheckStep.tsx:66`, `:31`, `:91`, `fetchGameNames.ts:46`, `strings.ts:7` | LOW | yes, each read; `:91` also measured | fixed, all six | `:54` a failed count → `loadFailed` heading. `:66` heading follows the report: ready, nothing new, cannot start or failed. `:31` playlist line only with Start; spec table amended. `:91` a new `busy` state on `GuideAction` shows it is starting and ignores a second press. Plain `disabled` dropped focus in Chromium on a failed start, so it was not used. Back and the exit hide meanwhile, so a failed start is not lost; INV-3 amended. `:46` duplicates dropped, and a moved total or an early empty page fails with plain words. `:7` comment corrected, no red run: nothing observable changes. Red seen for the rest. |
| LOW, lane 3: `docs/help/01-getting-started.md:43`, `:44` | LOW | yes, each read against `CmdKPalette.tsx` and `App.tsx` | fixed, both | `:43` "search games, settings and actions" → "jump to a page or a help topic". `:44` adds "on the Library page". The grid keys are added, as the orchestrator asked. No red run: documents. |
| Orchestrator: `strings.copy.biosWarning` says "listxml" | LOW | yes, read | fixed | "machine list (listxml)" → "MAME's records". Red seen. |

Group 3 run-level, 2026-10-30:

- `cited_by`: old words searched as literal text in `docs`, `README.md`, `src`, `frontend/src` and `tests`: `see field errors`, `sidebar`, `Ctrl-K`, `listxml)`, `bios_included`, `BIOS`. Hits are in `swept` or `out_of_scope`.
- `swept`, asking of each fix whether it contradicts, breaks or makes stale:
  - Spec 1144 §4.3, §4.4, §4.5, §6, INV-2, INV-3, INV-5, INV-7: fixed. INV-8 and INV-13: agree.
  - `api/spec.md` Copy job lifecycle: fixed, gains the BIOS counts.
  - `docs/specs/P04-http-api.md` event table: frozen, under its superseded note.
  - `src/mame_curator/copy/spec.md` on a missing BIOS: agrees.
  - `docs/help/01-getting-started.md`, `02-choosing-games.md`: fixed. `03-copying-games.md` "Any BIOS": fixed.
  - The `useDryRun.ts` comment listing the counts: fixed.
  - `.claude/code-pairs.json`: absent.
- `collateral`:
  - `fetchGameNames.test.ts` "stops on an empty page" expected the short list this run removes, so it now expects the failure.
  - The new `CopyingStep` tests moved the timing of `keeps focus on the button…`, which then lost a race with the step's own focus. It now waits for that focus first.
- `surfaced`: none.
- `out_of_scope`:
  - `DryRunModal.tsx` reads `counts.bios_included`, which the dry-run route does not send, so the Library should always say 0 BIOS included: read, not run.
  - On a clean finish under `on_success` or `always`, `useLibraryController` closes `CopyModal`, so the Library never shows the BIOS alert or the warnings.
  - The outcome reads "Your games are copied." when selected games were skipped as missing. Check says so first, but the outcome does not.
  - "Copy these" uses plain `disabled`, so a failed name fetch should drop focus as Start did: read, not run.
  - `useConfigPatch` toasts as well, so a refused folder shows the same words twice in the guide.
  - `strings.nav.commandPalette`, `strings.cmdK.placeholder` and `docs/design.md`'s palette lines still promise a search of games and settings.
- `falsified`: none.

## Group 4: silent failures elsewhere

| Finding | Sev | Verified | Disposition | Was → now |
|---|---|---|---|---|
| `App.tsx:384`: failed config load shows Loading forever | MEDIUM | | | |
| `App.tsx:308`: failed help topic shows an empty pane | MEDIUM | | | |
| `App.tsx:176`: session failures invisible | MEDIUM | | | |
| LOW, lane 3: `App.tsx:89` | LOW | | | |

## Closed without a fix pass

| Finding | Sev | Disposition |
|---|---|---|
| `AlternativesDrawer.tsx:150`: override sent with the wrong parent | HIGH | queued: `mame-curator-1149`, same defect |
| `CheckStep.tsx:38`: Start hidden for games not in the playlist | MEDIUM | queued: `mame-curator-1154`, user ruling, spec amendment first, no gate because the spec is at its loop cap |
| `LibraryGrid.tsx:26`: `groupKey` never read | MEDIUM | queued: `mame-curator-1155`, needs a decision |
| Lane 2 and lane 3 open questions | n/a | queued: `mame-curator-1156`, each needs a decision |
| Commit dc8bb1c's body: `LibraryPage.tsx` grew by 3 lines | LOW | dismissed: a commit message is a frozen record; the true figures are in the review's return |

## Run-level

- `cited_by`:
- `swept`:
- `collateral`:
- `surfaced`:
- `out_of_scope`:
- `falsified`:

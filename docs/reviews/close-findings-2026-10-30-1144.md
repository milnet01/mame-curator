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
| `GameCard.tsx` `handleKeyDown`: Enter on Add opens the drawer | HIGH | | | |
| `LibraryGrid.tsx:278`: active card invisible, arrows never move focus | HIGH | | | |
| `LibraryGrid.tsx:163`: Enter opens the wrong game | HIGH | | | |
| `LibraryGrid.tsx:170`: modifier keys not checked | HIGH → MEDIUM | | | |
| `AlternativesDrawer.tsx:209`: drawer cannot scroll | HIGH | | | |
| `LibraryPage.tsx:99`: open cart at 200% may hide the games (measure first) | MEDIUM | | | |
| `LibraryGrid.tsx:94`: columns do not follow text size | MEDIUM | settled | dismissed: user ruling 2026-10-30, no layout changes | |
| LOW, lane 2: `FiltersSidebar.tsx:102`, `LibraryFullHeader.tsx:76`, `useLibraryController.ts:312`, `libraryView.ts:23`, `SimpleLibraryBar.tsx:38` | LOW | | | |
| LOW, lane 3: `AppShell.tsx:81`, `textSize.ts:46`, `guideState.ts:11` | LOW | | | |

## Group 3: guide steps

| Finding | Sev | Verified | Disposition | Was → now |
|---|---|---|---|---|
| `WhatThatFindsStep.tsx:41`: stale fetch after Back | HIGH | | | |
| `CheckStep.tsx:30`: BIOS claim not always true | MEDIUM | | | |
| `GuideStep.tsx:33`: heading changes not announced | MEDIUM | | | |
| `WhereStep.tsx:43`: error points at field errors not shown | MEDIUM | | | |
| `strings_internal.ts:112`: empty-state hint names a sidebar simple view lacks | MEDIUM | | | |
| LOW, lane 1: `WhatThatFindsStep.tsx:54`, `CheckStep.tsx:66`, `:31`, `:91`, `fetchGameNames.ts:46`, `strings.ts:7` | LOW | | | |
| LOW, lane 3: `docs/help/01-getting-started.md:43`, `:44` | LOW | | | |

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
| `CheckStep.tsx:38`: Start hidden for games not in the playlist | MEDIUM | queued: `mame-curator-1154`, user ruling, spec amendment needs review-contract |
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

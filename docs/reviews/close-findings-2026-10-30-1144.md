# close-findings: review-code on mame-curator-1144

Dated record, 2026-10-30. Source: `docs/reviews/review-code-2026-10-30-1144/`. Each finding's text is in its lane file. Locations are as the review cited them at dc8bb1c. An empty disposition means not yet closed.

User rulings, 2026-10-30:

- The large text is good; no layout changes wanted.
- Hide the exit while a copy is paused.
- Offer Start for games on disk but not in the playlist.

## Group 1: copy honesty

| Finding | Sev | Verified | Disposition | Was → now |
|---|---|---|---|---|
| `useCopySession.ts:153` and CopyingStep: `reason` dropped, a crash reads as Stop | MEDIUM | | | |
| `useCopySession.ts:172`: lost stream stays running | MEDIUM | | | |
| `useCopySession.ts:178`, `:208`: pause, resume, abort failures silent | MEDIUM | | | |
| `jobs.py:143`, `useCopySession.ts:128`: Pause before a tick leaves no Resume | MEDIUM | | | |
| `CopyingStep.tsx:50`: exit live while paused (user ruling: hide it) | MEDIUM | | | |
| `CopyingStep.tsx:67`: warnings not shown | MEDIUM | | | |
| `CopyingStep.tsx:79`: focus lost on Pause/Resume | MEDIUM | | | |
| `CopyingStep.tsx:110`: dialog stays open after the job ends | MEDIUM | | | |
| `useLibraryController.ts:291`: cart cleared on partial failure | HIGH | | | |
| `LibraryPage.tsx:325`: dismissing the modal during a copy loses control | HIGH | | | |
| `CopyModal.tsx:95`: conflict banner can never show | HIGH → LOW | | | |
| `CopyModal.tsx:129`: Done and status | MEDIUM | | | |
| `CopyModal.tsx:134`: `terminating` never set | MEDIUM | | | |
| LOW, lane 1: `CopyingStep.tsx:92`, `:70`, `:95`; `AbortCopyDialog.tsx:33`, `:38`; `useCopySession.ts:51` | LOW | | | |
| LOW, lane 2: `useCopySession.ts:67`, `:97`, `:136`; `CopyModal.tsx:77`; `AbortCopyDialog.tsx:33`; `LibraryPage.tsx:364` | LOW | | | |

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

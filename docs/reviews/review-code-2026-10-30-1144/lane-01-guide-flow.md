## Line counts and what I started with

**Line counts (read in full with `Read`):**

| File | Lines |
|---|---|
| `frontend/src/pages/GuidePage.tsx` | 180 |
| `frontend/src/components/guide/GuideAction.tsx` | 48 |
| `frontend/src/components/guide/GuideStep.tsx` | 63 |
| `frontend/src/components/guide/steps/CheckStep.tsx` | 106 |
| `frontend/src/components/guide/steps/ChooseGroupStep.tsx` | 67 |
| `frontend/src/components/guide/steps/CopyingStep.tsx` | 117 |
| `frontend/src/components/guide/steps/SetupNeededStep.tsx` | 17 |
| `frontend/src/components/guide/steps/WhatThatFindsStep.tsx` | 103 |
| `frontend/src/components/guide/steps/WhereStep.tsx` | 88 |
| `frontend/src/components/guide/steps/WhichGamesStep.tsx` | 29 |
| `frontend/src/lib/guideState.ts` | 23 |
| `frontend/src/lib/fetchGameNames.ts` | 48 |
| `frontend/src/lib/apiErrorToast.ts` | 84 |
| `frontend/src/hooks/useCopySession.ts` | 213 |
| `frontend/src/hooks/useGames.ts` | 59 |
| `frontend/src/components/library/AbortCopyDialog.tsx` | 67 |
| `frontend/src/strings_guide.ts` | 103 |
| `frontend/src/strings.ts` | 18 |

**Disagreement resolved:**
- The brief asks for context first; the lane file fixes line counts as the opening, and a brief cannot change that. So line counts come first.
- The brief also says both "end with the files you opened" and "end at 3 items". I put the 3 items last in the findings and the file list after them.

**Already in my context on arrival:**
- The global `CLAUDE.md`, including its paragraphs on review skills.
- The user's email address.
- The lane prompt and a session hook note about the Ants verbs.
- No git snapshot, memory index or project `CLAUDE.md`.
- After STEP 1, the shared context, which holds the allowlist and false-positive ledger.

**Tempted to open and did not:**
- Any test, including `GuidePage_steps.test.tsx`, because of the ban.
- `runner.py` lines 176–195 and 300–360.
- The rest of `FsBrowser.tsx`, `SettingsPage`'s tab list and `AppShell`.
- The `strings.errors.byCode` entry for config errors.

## Critical (0)

Nothing found.

## High (1)

- [dim 2] `frontend/src/components/guide/steps/WhatThatFindsStep.tsx:41` — `await fetchGameNames(query, (done, total) =>` — The name fetch is never cancelled, and Back stays live while it runs (only "Copy these" is disabled, line 88).
  - **Failure:** press "Copy these" on "every game", press Back, then choose a group. When the old fetch resolves, `GuidePage.tsx:127` (`setNames(found);`) stores the old list and jumps to Where. Check and Start then use names the user backed out of. Check shows counts, not names, so nothing reveals it.
  - **Contract:** breaks INV-5.
  - **Also:** a user who pressed Back and stayed put is pulled forward unasked.
  - **Fix:** ignore the result after unmount, using a ref or `AbortController`, and thread the signal into `fetchGameNames`.

## Medium (11)

- [dim 16] `frontend/src/hooks/useCopySession.ts:153` — `return { ...prev, state: "aborted" };` — The hook drops `job_aborted`'s `reason`, so a crash reads exactly like the user's own Stop.
  - **How it happens:** `jobs.py:417` emits `job_aborted` when the worker crashes. `runner.py` calls `write_lpl` with no guard, and it raises `PlaylistError` (`playlist.py:56`).
  - **What the user sees:** "The copy has stopped." with no `role="alert"`, no reason and no Activity link (`CopyingStep.tsx:39-41`), even though every file may have copied and only the playlist failed.
  - **Contract:** breaks spec §4.3, "A failure is announced with `role="alert"` and worded text".
  - **Fix:** keep `reason`; any value other than `CANCELLED` shows the alert and the Activity link.

- [dim 16] `frontend/src/hooks/useCopySession.ts:172` — `if (es.readyState === EventSource.CLOSED) closeStream();` — A lost stream leaves the state at `running` for good.
  - **How it happens:** after a server restart, the reconnect gets a 404 from `/api/copy/status`, and the browser's `EventSource` closes.
  - **What the user sees:** "Copying your games" and "The copy will carry on" stay on screen with a frozen count.
  - **Contract:** breaks coding-standards §13, "No silent spinners that never resolve".
  - **Fix:** on CLOSED, move to a failure state that says the connection was lost and links to Activity.

- [dim 7] `frontend/src/hooks/useCopySession.ts:178` — `const pauseMutation = useMutation({` — Pause, resume and abort have no `onError`, and `queryClient.ts` confirms there is no global mutation handler. `GuidePage.tsx:84-86` passes none either.
  - **What the user sees:** a failed Stop or Pause (network down, 404) changes nothing and says nothing.
  - **Contract:** breaks §4.3.
  - **Fix:** take an `onError` as `start` does, and show a `role="alert"` on the Copying step.

- [dim 2] `src/mame_curator/api/jobs.py:143` — `is_paused = self._controller.state == CopyControlState.PAUSED` — `paused` is only emitted from a progress tick, and the hook ignores the state in the pause response.
  - **How it happens:** press Pause after the job starts but before the first file. The worker blocks at `runner.py` `ctl.wait_if_paused()` with no tick, so no event ever arrives.
  - **What the user sees:** Pause and "You can close this page. The copy will carry on." with no Resume, while the copy is actually stopped. Only Cancel gets out of it.
  - **Likelihood:** the window grows with list size, because run_copy works through the plan before the first boundary. I reasoned this from the code and did not run it.
  - **Fix:** apply the `JobStatus.state` that pause and resume return, or emit `paused` from `JobManager.pause`.

- [dim 16] `frontend/src/components/guide/steps/CopyingStep.tsx:50` — `exitLabel={strings.guide.exit}` — The exit stays live while paused, and the hint warns only about closing the page.
  - **Dead end:** `useCopySession` is the only caller of the pause, resume and abort routes, and it gets state only from its own `start` (callers are `GuidePage` and `useLibraryController`). So a paused job left behind cannot be resumed or cancelled from any UI I searched.
  - **What the user sees:** every later Start returns `job_already_running`, "Wait or cancel it first", which they cannot do until the server restarts.
  - **Fix:** hide the exit while paused, or resume or attach on mount. Which is right is partly a spec question (see Open questions).

- [dim 9] `frontend/src/components/guide/steps/CheckStep.tsx:38` — `canStart: !notWritable && gap >= 0 && newGames > 0,` — "Nothing new on disk" does not mean "in the playlist".
  - **How it happens:** `runner.py` skips `write_lpl` on a cancel (`# Write playlist (skip when dry-run or cancelled-mid-flight).`). Stop with "Keep files" therefore leaves files that are in no playlist. The same applies if the playlist was deleted or moved.
  - **What the user sees:** a later guide run over those games says "All of these are already copied." and hides Start, so the guide can never list them.
  - **Which side is wrong:** the code matches §4.4 and INV-8, so the document is wrong. A real start would write the entries, because `_build_playlist_entries` includes `SKIPPED_IDEMPOTENT`.
  - **Fix:** have the dry run report games absent from the playlist, and allow Start for them.

- [dim 2] `frontend/src/components/guide/steps/CheckStep.tsx:30` — `(counts.bios ?? 0) > 0 && strings.guide.check.bios(counts.bios),` — "N BIOS files these games need will be included" is not always true.
  - **How it happens:** `counts.bios` is the whole resolved set. `preflight` checks only winners for a missing source (`for short in plan.winners`). A missing BIOS zip goes to `skipped`, not `failed`, so the status is `OK`.
  - **What the user sees:** "Your games are copied." for games that may not run.
  - **Fix:** report the BIOS missing-source count in the dry run, then state it on Check and on the outcome.

- [dim 7] `frontend/src/components/guide/steps/CopyingStep.tsx:67` — `{finished && !complete && (` — `state.warnings` is never shown here, but `CopyModal` shows it. So BIOS warnings such as "its BIOS can't be worked out" vanish, and the guide reports complete.
  - **Fix:** render the warnings in the Copying step at `text-xl`.

- [dim 12] `frontend/src/components/guide/GuideStep.tsx:33` — `const id = requestAnimationFrame(() => headingRef.current?.focus());` — The `h1` stays the same element when the heading changes within a step.
  - **Why it fails:** `focus()` on an already focused element fires nothing, and the `h1` is not a live region. After the step's first focus, these changes have no announcement I can find:
    - "Counting the games…" → "This finds N games"
    - "Checking your folders…" → "Ready to copy?"
    - "Copying your games" → "Your games are copied."
  - **Effect on the Goal:** a screen-reader user is never told the result, or that the copy finished. Only the partial case has an alert.
  - **Uncertainty:** I worked this out from DOM behaviour and did not test it on a real screen reader. A simulated page would pass it.
  - **Fix:** add `key={heading}` to the `h1`, or add a `role="status"` region.

- [dim 12] `frontend/src/components/guide/steps/CopyingStep.tsx:79` — `<GuideAction onClick={onPause}>{strings.copy.pause}</GuideAction>` — Pause and Resume sit in separate conditional branches, so the focused button is removed when the state flips.
  - **What the user sees:** the heading text does not change, so the focus effect does not run and focus falls to `body`. A keyboard or magnifier user loses their place at the moment they need Resume. The paused hint is also not announced.
  - **Fix:** use one button whose label and handler switch, or move focus to Resume.

- [dim 7] `frontend/src/components/guide/steps/CopyingStep.tsx:110` — `open={abortOpen}` — The dialog stays open if the job ends behind it.
  - **What the user sees:** pressing "Move to recycle bin" after that sends a POST that returns 404, and the failure is silent. The dialog closes and the files stay, while the user believes they were removed.
  - **Fix:** use `open={abortOpen && (state.state === "running" || state.state === "paused")}`.

## Low / Info

- [dim 2] `frontend/src/components/guide/steps/CopyingStep.tsx:92` — `{strings.copy.abort}` — The label is "Cancel", but §4.4 says "Stop". The dialog is titled "Cancel" and its Cancel button (`AbortCopyDialog.tsx:43`) means *keep copying*. Fix: use guide-specific Stop and "Keep copying" labels.
- [dim 2] `frontend/src/components/library/AbortCopyDialog.tsx:33` — `<Dialog open={open} onOpenChange={onOpenChange}>` — Coding-standards §4 requires an `AlertDialog` for destructive actions. Fix: swap the primitive.
- [dim 2] `frontend/src/components/library/AbortCopyDialog.tsx:38` — `{strings.copy.abortConfirm(filesDone > 0)}` — With 0 files done the text says files "will be kept", yet "Move to recycle bin" still shows. Fix: hide that button at 0.
- [dim 2] `frontend/src/components/guide/steps/CopyingStep.tsx:70` — `<Link to="/activity" className="underline">` — §4.3 says every action is a `GuideAction` at least 3rem tall. Fix: use `GuideAction to`.
- [dim 16] `frontend/src/components/guide/steps/CopyingStep.tsx:95` — `{state.state === "terminating" && (` — Nothing sets this state: the hook ignores the abort response. After Stop the screen shows running with live Pause and Stop until a file boundary. Fix: set `terminating` when abort succeeds.
- [dim 7] `frontend/src/components/guide/steps/WhatThatFindsStep.tsx:54` — `? strings.guide.finds.loadingHeading` — When the count fails, the heading stays "Counting the games…" beside the alert. Fix: use `loadFailed` as the heading.
- [dim 7] `frontend/src/components/guide/steps/CheckStep.tsx:66` — `: strings.guide.check.heading` — "Ready to copy?" shows even when the dry run failed or Start is hidden. Fix: choose the heading from the report.
- [dim 2] `frontend/src/components/guide/steps/CheckStep.tsx:31` — `Boolean(summary.existing_playlist) && strings.guide.check.existingPlaylist,` — "These will be added" also shows beside "All of these are already copied." with no Start. The spec table allows it, so this is both sides. Fix: show it only with `canStart`.
- [dim 7] `frontend/src/components/guide/steps/CheckStep.tsx:91` — `onClick={() => {` — Start has no pending state or disable, and coding-standards §13 asks for loading states. `start_copy` stats every source file before it answers, so a big list gives no feedback. A second press gets the 409. Fix: expose `isPending`.
- [dim 9] `frontend/src/lib/fetchGameNames.ts:46` — `if (data.items.length === 0 || names.length >= data.total) return names;` — If the library rebuilds mid-paging (say a Settings change in another tab), pages shift. The list can hold duplicates or gaps, and a shrink returns short without an error. Fix: drop duplicates, and fail if `total` changes between pages.
- [dim 2] `frontend/src/hooks/useCopySession.ts:51` — `cancelledRef.current = true;` — It is never reset, and `main.tsx` uses `StrictMode`. In a dev build only, the simulated unmount leaves it true, so `onSuccess` bails and the copy runs with no UI. The comment at lines 64-66 also says `reset()` sets it; `reset` does not. Fix: set it false in the effect body.
- [dim 2] `frontend/src/strings.ts:7` — ` * `strings_internal.ts` below the project's 500-line hard cap and` — This is stale, and the document is wrong, not the code: `strings_internal.ts` has entries past line 780, and `strings_guide.ts` says it is past its cap. Lines 10-11 also ignore the new guide module. Fix: reword.
- [dim 3] Nothing found. Errors and paths render as React text, the genre is URL-encoded by `URLSearchParams`, and the folder save goes through `PATCH /api/config`. I read the path validation. I read only part of `FsBrowser`, and did not check its grant flow.
- [dim 2b] No zombie found among what I read: `/start` is routed (`App.tsx`) and every step file is imported by `GuidePage`. The "Start here" entries in `AppShell` and the palette were not checked. I did not use the test-count carve-out.
- [dim 4] Nothing beyond the `CopyModal`/`CopyingStep` warnings gap above.
- [dim 5] Nothing found. I searched `src/mame_curator` for a request body cap on the long name list and found none.
- [dim 8] Nothing found. `closeStream()` inside a `setState` updater is idempotent.
- [dim 10] N/A: no observability contract named.
- [dim 11] Nothing found in the lane files. The UI only displays server paths as text.
- [dim 13] Nothing found. Lane files take all user text from the strings module. `CopyModal` has literals but is a cross-reference, not a subject.
- [dim 15] Nothing found. These files make only same-origin API requests.
- [dim 17] Nothing found. The `v1` key matches §13.
- INFO: the `frontend/e2e` flow, real screen readers, real layout and packaged bundles were not run. All behaviour above comes from reading the code.

## Covered by spec and looks correct

I opened and checked these:

- **Step numbers:** 5 or 6, with "Step 1" alone on the first step (§4.3).
- **Back and exit:** present or absent as INV-3 requires.
- **First-load redirect:** runs once per load and only at `/` (`App.tsx`, §4.2), with the seen flag set only when `setup_required` is false.
- **Setup mode:** only its one step is reachable, including when localStorage is unavailable.
- **Paging:** 500 per page, matching the server maximum, with only the selection's filters and no default year (INV-5).
- **Requests:** `APPEND` on both dry run and start, with `append_decisions: {}` (INV-6).
- **Report mapping:** `readReport` follows §4.4, and Start is hidden in all three INV-8 cases.
- **Copy outcome:** `PARTIAL_FAILURE` shows an alert and an Activity link; only `OK` shows complete.
- **Folder save:** uses `useConfigPatch`, then invalidates both queries, and shows failures on the step.
- **Look through them first:** the selection is applied once and the route state cleared (`useLibraryController`).
- **Recycling on Stop:** only this run's `succeeded` files are recycled, so "already there" files survive a repeat copy's Stop.
- **Route protection:** `/start` sits inside the `ErrorBoundary`.
- **Cart:** the lane's files never touch it (INV-4).

## Open questions

- **Should the guide offer Start when games are on disk but not in the playlist?** §4.4 and INV-8 say hide it; I think the document is wrong there.
- **Is §6's "This guide cannot come back to a paused copy" meant to accept the permanent 409?** The hint covers closing the page but not the exit link. I cannot tell how much of this the spec intended.
- **§4.4 says a save failure "shows the API's message", but `apiErrorMessage` prefers a friendly `byCode` string.** I did not check whether a config error has one, which would hide the field detail.
- **Does `/settings?tab=paths` select a real tab?** `SettingsPage` reads `tab`, but I did not open its list.
- **Is a game's `review_state` meant to be ignored?** The guide copies games with any review state, as the API default does. §9 tracks only Add all's gap, so I filed nothing.

## 3 items to fix first

1. **The stale name fetch (High).** It is the one defect that copies games the user did not choose, and nothing on screen reveals it.
2. **A crash or lost stream reading as "stopped" or "copying" (the `job_aborted` and `es.onerror` findings).** The guide's core promise is a truthful outcome, and both cases mislead at the end of a long job.
3. **Completion not announced, and focus lost on Pause.** The spec's purpose is this user, and no gate can catch these two: simulated pages pass them, and only real assistive technology shows them.

## Files opened

**Subject files:** the 18 listed above.

**Contract and context:**
- `shared-context.md` (scratch directory)
- `docs/specs/mame-curator-1144-guided-library.md` (311 lines)
- `docs/help/01-getting-started.md`, `docs/help/02-choosing-games.md`
- Sections only: `docs/standards/coding-standards.md` (§§4, 13); `src/mame_curator/copy/spec.md` (Preflight, Playlist conflict resolution, CopyReport); `src/mame_curator/api/spec.md` (Copy job lifecycle)

**Server, read in full:**
- `src/mame_curator/api/routes/copy.py`, `routes/games.py`, `routes/config.py`
- `src/mame_curator/api/schemas_copy.py`, `api/jobs.py`
- `src/mame_curator/copy/preflight.py`

**Server, slices only:**
- `src/mame_curator/copy/runner.py` (60–175, 196–300, 360–432, 440–510)
- `src/mame_curator/copy/controller.py` (48–80)

**Frontend, slices only:**
- `frontend/src/hooks/useDryRun.ts`, `useConfig.ts`, `useFacets.ts`, `useSetupCheck.ts`
- `frontend/src/components/library/CopyModal.tsx` (1–175)
- `frontend/src/lib/queryClient.ts`
- `frontend/src/App.tsx` (462–495, 555–585)
- `frontend/src/pages/libraryPageHelpers.ts` (24–75)
- `frontend/src/strings_internal.ts` (670–705)
- `frontend/src/components/settings/FsBrowser.tsx` (66–92)

**Search rows only:** `frontend/src/main.tsx`, `frontend/src/pages/useLibraryController.ts`, `frontend/src/pages/SettingsPage.tsx`, `src/mame_curator/copy/playlist.py`, the rest of `strings_internal.ts`.

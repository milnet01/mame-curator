# close-findings: review-code on mame-curator-1145

Dated record, 2026-11-02. Source: `review-code --since 63690e3`, run to a084596. Each finding's text is in its lane file, kept on this machine at `~/.local/share/claude-scratch/reviews/MAME_Curator/review-code-2026-11-02/`, because the repository is public. Locations are as the review cited them at a084596. An empty disposition means not yet closed.

Decisions taken by this run on the review's questions, 2026-11-02. None changes a user ruling:

- Restore and import in setup mode retry the DAT as a save does; the spec says so.
- The PATCH reply gains a field saying setup mode ended, and the refresh uses it.
- `setup`, `refresh-inis` and `refresh-snaps` without `--config` use the config `serve` uses.
- The wizard's same-folder check and focus return also apply to WhereStep.
- `simple` hides folders only, as its spec and prop doc say.
- Downgrade to an older `run.sh` is not documented.
- The help sentence on the playlist folder stays; it sits under First-time setup.

Waiting on the user: the wording of the grant prompt, with mame-curator-1170.

## Group 1: a save that ends setup

| Finding | Sev | Verified | Disposition | Was → now |
|---|---|---|---|---|
| `SetupWizard.tsx:88-92`: good save may raise the failure alert | MEDIUM | yes, measured: alert recorder, seen in 3 of 9 whole runs at 6x CPU slowdown, never at full speed | fixed in 8c403ce | Alert entered the page on a good save → shown only if the check still says setup is on |
| `useConfig.ts:51-52`: refresh depends on the cached check (lanes 3, 5) | MEDIUM | yes, read | fixed in 8c403ce | Cached check → the reply's new `setup_ended` |
| `routes/config.py:207`, `api/spec.md:338-339`: `restart_required` means two things | LOW | yes, read | fixed in 8c403ce | One flag, wrong spec sentence → `setup_ended` carries the other fact; spec amended |
| `useConfig.ts:37`: restart prompt lost on refetch | MEDIUM | yes, read: GET always said false | fixed in 8c403ce | GET false → GET reports it |
| `strings_internal.ts:598-599`: restart banner names the wrong cause | MEDIUM | yes, read | fixed in 8c403ce | Always blamed the server → two plain messages |
| `useConfig.ts:78-81`, `:109-112`: restore and import refresh too little; no retry in setup mode | MEDIUM | yes, read | fixed in 8c403ce | No retry, snapshots refreshed only → retry in setup mode, same reply fields, all queries refreshed; INV-15 |
| `state.py:253`: bad UTF-8 file raises out of the retry | MEDIUM | yes, test showed `UnicodeDecodeError` | fixed in 8c403ce | 500 with the swap skipped → typed error, notes read as none, swap before retry |
| `routes/config.py:88`: NUL path can stop the app starting | LOW (calibrated) | yes, narrowed: only a NUL in a folder part stops the start | fixed in 8c403ce | → refused on save; a config already holding one still starts |
| `routes/config.py:240-244`: failed restore leaves the old world | LOW | yes, test | fixed in 8c403ce | Restored files beside the old world → files put back, error raised; INV-16 |
| `routes/stubs.py:50`: narrow catch on the setup check | LOW | yes, read | fixed in 8c403ce | `OSError` gave a 500 → `dat_parses` false. Red through a mocked `parse_dat` |
| `updates_ini.py` `_Staged.ctx`: staged preview survives the swap | LOW | yes, read | fixed in 8c403ce | Old preview survived → cleared when a retry ends setup. Red through a stand-in object |
| `state.py:252`: unknown-key wording in `api/spec.md` | LOW | yes, read `api/spec.md` | fixed in 8c403ce | Wording corrected. No red run: wording only |
| `SetupWizard.tsx:111`: first chosen path may not be heard | LOW | yes, read and test; no real screen reader | fixed in 8c403ce | Status element added at choice time → on the page first |
| `SetupWizard.tsx:63`: same-folder check is by string only; WhereStep has none | LOW | yes, read | fixed in 8c403ce | Text compare, wizard only → server check on resolved paths when a save changes either; page check in WhereStep |
| `SetupWizard.tsx:68-96`: leaving during the read loses the outcome | LOW | yes, read | fixed in 8c403ce | Unnamed → spec §6 names it. No red run: wording only |
| `useConfig.ts:53`: refetches the startup update check; no time limit on the wait | LOW | yes, read | fixed in 8c403ce | Refetched, no limit → excluded; a 30 second limit, the helper's number, untested on a full DAT |
| `useConfig.ts:37`: no `cancelQueries` | LOW | yes, test | fixed in 8c403ce | Older GET overwrote the reply → cancelled first |
| `useConfig.ts:43`: "saved" toast beside a failure alert | LOW | yes, read | fixed in 8c403ce | Toast beside the alert → the wizard's save has no toasts |
| `routes/config.py:167`: `exclude_none` drops nested None | MEDIUM | refuted: orchestrator probe kept the None | dismissed | Probe in the project's venv: `exclude_none` keeps nested None, output `{'paths': {'listxml': None, 'a': 1}}`. Never a defect |

## Group 2: the folder picker

| Finding | Sev | Verified | Disposition | Was → now |
|---|---|---|---|---|
| `PathRow.tsx:62`: Browse on a file row dead-ends | HIGH | yes, e2e before the fix | fixed in 5601d16 | Listing or grant aimed at the file → opens the file's folder (client helper `folderOf`) |
| `useFs.ts:58`: jargon toast with every grant prompt | HIGH | yes, test with the app's query client | fixed in 5601d16 | Toast with each prompt → silent listing query |
| `FsBrowser.tsx:260-262`: a folder of zips reads "Empty." | HIGH | yes, test | fixed in 5601d16 | "Empty." → says the folder holds only files, or "No folders here." |
| `ConfirmationDialog.tsx:75,79,94` with `FsBrowser.tsx:179`: long path overflows (lanes 4, 5) | MEDIUM | yes, measured at three widths, two text sizes, two path lengths | fixed in 5601d16 | 195–4806 px past the sides → 0 px in all 24 combinations. Cause also lay in vendored `ui/alert-dialog.tsx`, where classes never merged; that file is now changed locally |
| `FsBrowser.tsx:100`: Windows and macOS hidden folders; dot-files in file mode | MEDIUM | yes, real Windows attributes over `ssh wintest` | fixed in 5601d16 | Dot prefix only → server `FsEntry.hidden`, folders only. `fs_list` itself not run on Windows; macOS not run |
| `FsBrowser.tsx:186`: drive that is also a config root vanishes | MEDIUM | yes, test | fixed in 5601d16 | Drive vanished from both lists → stays |
| `FsBrowser.tsx:282`: "Use this folder" live on a failed listing | MEDIUM | yes, test | fixed in 5601d16 | Live on a failed or loading listing → needs an opened listing |
| `FsBrowser.tsx:237`: no row cap | MEDIUM | yes, measured with 40,000 real files | fixed in 5601d16 | 40,000 rows, 1.7 s → 38 drawn, 0.6 s; windowed above 300 rows |
| `FsBrowser.tsx:122`: grant wide, lasting, no revoke | MEDIUM | settled by 1170 for reaching drives; search found no caller for the server's DELETE | queued as mame-curator-1175 | Revoke control not built; prompt wording waits on the user |
| `routes/fs.py:50-57`: one odd file stops the listing | MEDIUM | yes, real non-UTF-8 name | fixed in 5601d16 | 500 → name left out, the rest listed. The 500 comes at JSON output, not at the model |
| `FsBrowser.tsx:235`, `:206-210`, `:123-130`, `:145`, `:214` | LOW | yes, test each | fixed in 5601d16, all five | Each as its lane says. `:214` had no clean red: the dialog grew rather than cut the path |
| `useFs.ts:58` staleTime | LOW | yes, test | fixed in 5601d16 | 30 seconds → 0 |
| `strings_internal.ts:654`: "ships in Phase 8" | LOW | yes, read | fixed in 5601d16 | Sentence, caller and test removed |
| `PathRow.tsx:58`, `FolderField.tsx:64`: refused path stays in the field | LOW | yes, test | fixed in 5601d16 | Refused path stayed → field shows what is saved. A refused typed path now must be retyped |
| WhereStep: focus drops when the picker closes (lanes 3, 4) | open question | yes, e2e before the fix | fixed in 5601d16 | Focus dropped → heading focused after Cancel, Esc and a pick |

## Group 3: launchers and command line

| Finding | Sev | Verified | Disposition | Was → now |
|---|---|---|---|---|
| `cli/__init__.py:150`, `refresh_inis.py:110`: refresh-inis silently skips the config update | HIGH | yes, read and ran | fixed in ccbdfbd | Green ticks and no update → updates the file `serve` reads, says so when nothing was updated; `refresh-snaps` too |
| `run.bat:15`, `:24-27`: Windows Store stub gives a false error | HIGH | yes, ran on real Windows with the Store stub | fixed in ccbdfbd | "Python  is too old" → "python not found" with install words |
| `README.md:95`, `:98`, `04-command-line.md:6-7`, `setup.py:81`: documents assume `./config.yaml` | MEDIUM | yes, read and ran | fixed in ccbdfbd | `setup` writes where `serve` reads; documents say where settings live. Narrowly breaking by versioning-overrides items 1 and 3; `--out config.yaml` restores the old target |
| `run.bat:56`: failed sync carries on | MEDIUM | yes, ran on Windows | fixed in ccbdfbd | Went on to Starting → stops with an `error:` line and the sync's exit code |
| `serve.py:213-222`: uvicorn's exit passes through (with 1139) | MEDIUM | yes, ran real uvicorn: exit 3 and a traceback; taken port gave exit 1 with no `error:` line | fixed in ccbdfbd | Exit 1 and one `error:` line; closes 1139 |
| `serve.py:158`: browser opens whatever holds the port | MEDIUM | yes, opened on a foreign server | fixed in ccbdfbd | Opens only when this run's random header comes back |
| `run.bat:21`, `:28`, `:44`: window closes on error | MEDIUM | yes, ran on Windows; ShellExecute stood in for a double-click | fixed in ccbdfbd | Pauses on failure after a double-click only |
| `run.sh:51`, `run.bat:37`: uv installer unverified; comment cites a missing ADR | MEDIUM | yes, read; no matching ADR in `docs/decisions` | part fixed in ccbdfbd, rest queued as mame-curator-1179 | False comment gone; TLS 1.2 floor and failed-fetch report in `run.bat`. No pin or checksum |
| `run.bat:37-42`, `:9-11`; `run.sh:22-24`, `:34` | LOW | yes, ran on Windows and with stubs | fixed in ccbdfbd | Failed install says so; failed `cd` stops; `!` survives; `run.sh` accepts python3.12 to 3.14 |
| `setup.py:35` and others: paths not escaped | LOW | yes, ran | fixed in ccbdfbd | Fixed in setup, serve and both refresh commands; rest queued as mame-curator-1180 |
| `serve.py:164`, `:153`, `:50-53`; `setup.py:81` atomic write | LOW | yes, ran; `:50-53` read | fixed in ccbdfbd | Logs False; IPv6 URL bracketed; comment corrected; atomic write |
| `cli/spec.md` exit-1 list; `README.md:24` | LOW | yes, read | fixed in ccbdfbd | Prose. Exit list completed; README points at first-time setup |

## Group 4: copy and snapshot safety

| Finding | Sev | Verified | Disposition | Was → now |
|---|---|---|---|---|
| `jobs.py:470`: replay past the queue size hangs | HIGH | yes, ran: timed out past the queue size | fixed in a5417fa | Hung on finished and live jobs → yields stored events, then drains the queue |
| `routes/copy.py:38`: unchecked names reach paths outside the sandbox | HIGH → MEDIUM | yes, ran on a temp tree: `replaces` moved an outside file to the recycle bin | fixed in a5417fa | → 422 `copy_names_unknown`, no job starts; `copy/paths.py` guards the build point |
| `routes/copy.py:35-38`: copy can run in setup mode and empty the playlist | MEDIUM | yes, ran | fixed in a5417fa | OVERWRITE emptied the playlist → 409 `copy_setup_required`, playlist bytes unchanged |
| `routes/config.py:237-238`: restoring the oldest snapshot can destroy it (with 1132) | MEDIUM | yes, ran | fixed in a5417fa | 404 and snapshot gone → 200, snapshot survives; closes 1132's prune half |
| `routes/config.py:225`, `routes/copy.py:158`: id not format-checked (with 1132) | LOW | yes, ran; history `..` read `data/report.json` | fixed in a5417fa | → 404 at both |
| `jobs.py:267`: pause reply claims a state (1159) | LOW | yes, ran | fixed in a5417fa | Said `paused` after a cancel → the controller's real state; closes 1159 |
| `jobs.py:344`: `bytes_done` is per file | LOW | yes, read: nothing displays it | fixed in a5417fa | Largest file's bytes → finished files plus current |
| `routes/config.py:366-367`: import marker has no reader | LOW | yes, read: no reader | fixed in a5417fa | Marker and its promise removed; a failed import puts back what it wrote |
| `_atomic.py`: replace cuts a symlinked config | LOW | yes, ran | fixed in a5417fa | Link replaced by a file → link survives; mode stays 0o644, a pinned trade-off |
| `routes/config.py:283`: import does not fold `picker:` | LOW | yes, ran | fixed in a5417fa | 422 → folded |
| `api/fs.py:30`: module-level set | LOW | yes, read: two callers | fixed in a5417fa | Module set gone |

## Group 5: Library and leftovers

| Finding | Sev | Verified | Disposition | Was → now |
|---|---|---|---|---|
| `useLibraryController.ts:205-219`: Add all ignores the review filter | HIGH | yes, ran; duplicate of 1151 | fixed in 1aba9f5 | Hand-built query without `review_state` → `toQueryString(pageQuery)` |
| `strings_internal.ts:515`: a switch no code reads | HIGH | yes, ran; search found no code reading it | fixed in 1aba9f5 | Switch and string gone; the config key stays so existing files load |
| `App.tsx:418,477`: restore and import show no progress or success | LOW | yes, ran under vitest only | fixed in 1aba9f5 | No progress or success words → plain words on the page; a second press ignored |
| `App.tsx:266,302`: Activity and Stats have no Try again | LOW | yes, ran; duplicate of 1167 | fixed in 1aba9f5 | Bare error text → `RouteLoadError` with Try again |

## Run-level

- **cited_by:** searched the tree outside history for `import.in_progress`, `fetch_videos`, `backupWizardForwardLink`, `SetupNeededStep`, `data/e2e`, `Fetch video` and `Phase 8`.
- **swept:** `fetch_videos` docs agree (the key is kept, unread). `import.in_progress` remains only in a test asserting its absence. `SetupNeededStep` in spec 1145 is frozen: it describes what the wizard replaced. `Phase 8` in `design.md` and plans is frozen phase history; `design.md` § 6.6 is 1173. `data/e2e` now names the fixture folder. The project has no `.claude/code-pairs.json`, so no pair list was walked. Asked of every fix: contradict, break, stale.
- **collateral:** none found by this sweep.
- **surfaced:** whether `setup` landing in the per-user config counts as MAJOR under versioning-overrides, for the user; the grant prompt's wording, with 1170.
- **out_of_scope:** 1175 to 1187 filed as they surfaced, 1174 before them; 1179 names a hazard. 1177 and 1186 were fixed in this run.
- **falsified:** none.

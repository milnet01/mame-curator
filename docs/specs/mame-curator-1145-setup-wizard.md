<!-- ants-spec-format: 1 -->
# mame-curator-1145 — Set up MAME Curator in the browser, one question per screen

**Status:** spec draft (2026-10-30).
**Kind:** accessibility.
**Source:** ROADMAP mame-curator-1145 (user, 2026-10-30: "That wizard is basically all I wanted right from the beginning.").

**Blocked by:** mame-curator-1144.

**Layman:** A new user answers three questions in large text, in the browser: where their games are, where their game list is, and where to copy to. The Library then works straight away, with no terminal and no restart.

## 1. Goal

A user with no configuration opens MAME Curator and, without a terminal, Settings or a restart, reaches the guide's first question with their games loaded.

## 2. Problem

1. **The guide stops at setup.** `SetupNeededStep` offers only "Open Settings", which is the page the user could not use.
2. **A save does not load the games.** `patch_config` calls `replace_world`, which passes `machines` through, so `setup_required` stays true until the server restarts. A person who started the app by double-clicking has no plain way to restart it.
3. **A same-path save does nothing.** `patch_config` returns early when `new_config == world.config`, so a DAT dropped at the path the config already names is never read.
4. **The launchers ask first.** `run.sh` and `run.bat` run `mame-curator setup` in a terminal when `config.yaml` is absent, so a user who clones the project never reaches a browser wizard. Bundles already reach it: `ensure_starter_config` writes a starter config whose DAT is absent.
5. **The picker speaks jargon.** `strings.settings.fsBrowser*` and `fsGrant*` say "allowlist", "directory" and "dir", and `FsBrowser` lists folders in `text-sm`.

## 3. Scope decisions (agreed with the user)

From the user, 2026-10-30: one question per screen, large text, plain words, nothing extra, and the smallest wizard that reaches a working Library.

Author's calls, open to the cold review and the user:

- **Three questions, four keys.** The roadmap's Layman names three answers and its body names four keys. The fourth, `paths.retroarch_playlist`, becomes `mame.lpl` inside the chosen destination, the example `mame-curator setup` prompts with. Settings can change it.
- **Ending setup mode needs no restart.** §4.1 re-reads the DAT on a save. §8 says why a "please restart" screen lost.
- **The launchers stop asking.** With no `config.yaml`, `run.sh` and `run.bat` go straight to `serve`, which writes the per-user starter config. `mame-curator setup` stays as a command for scripts and for people who want it.
- **No welcome or finished screen.** The wizard's last answer leads straight to "Which games would you like?".
- **Nothing is pre-filled.** The starter config's folders are empty ones the app made, so offering them would invite a user to accept a folder with no games.

## 4. Design

### 4.1 Backend: a save in setup mode retries the DAT

In `api/state.py`:

```python
def retry_setup(world: WorldState) -> WorldState:
    """Re-read everything from disk; return `world` unless the DAT now loads."""
```

It calls `build_world(world.config_path)` and returns the result when `setup_required` is false. It returns `world` when the DAT is still unreadable, or when `build_world` raises `ParserError`, `FilterError`, `ConfigError` or `OSError`, logging a WARNING for the raise. `build_world` is used rather than a DAT-only parse because the listxml's driver status and clone data are not held on the world.

In `patch_config`, under the existing `world_lock`:

- The no-op return gains `and not world.setup_required`, so a same-path save still retries (§2.3).
- After `write_yaml_atomic` and `replace_world`, when `world.setup_required` holds: `new_world = await asyncio.to_thread(retry_setup, new_world)`.
- `restart_required` becomes `server_changed or new_world.setup_required`.

Every save in setup mode retries, not only one that changes `source_dat`, for the reason mame-curator-1095 §4.2b gives. This replaces that section's condition. `_validate_paths` is unchanged, so 1095 INV-9 holds.

### 4.2 The wizard

```
frontend/src/components/guide/steps/SetupWizard.tsx   replaces SetupNeededStep.tsx
frontend/src/lib/playlistPath.ts                      playlistIn(dest)
```

`GuidePage` renders `SetupWizard` when `setup_required` is true. Each step renders through `GuideStep`, with `stepNumber` and `stepCount={3}`, and uses `GuideAction`. Text lives in `strings.guide.setup`.

| Step | Heading before a choice | Line below it | Heading after a choice | Actions after a choice |
|---|---|---|---|---|
| 1 | "Where are your MAME games?" | "Choose the folder that holds your game files. They are usually .zip files." | "Use this folder for your games?" | "Yes, use this folder", "Choose another folder" |
| 2 | "Where is your game list?" | "This is the file that lists every MAME game. It ends in .xml or .zip, and is often called a DAT file." | "Use this game list?" | "Yes, use this file", "Choose another file" |
| 3 | "Where should copied games go?" | "Choose the folder your chosen games will be copied to. Your original games are not changed." | "Copy games to this folder?" | "Yes, finish setup", "Choose another folder" |

- Before a choice the one action is "Choose a folder" or "Choose a file", which opens `FsBrowser` (`mode="file"` on step 2).
- After a choice the path shows as large text in a `role="status"` element, and focus moves to the heading. `GuideStep` gains `focusKey?: number`, added to its focus effect's dependencies. The wizard passes a count of choices made, so a second choice moves focus although the heading stays the same.
- Every step has the exit "Look around on my own". Steps 2 and 3 have Back, which keeps the answers given.
- `FsBrowser` opens at the current answer on steps 1 and 3 and at the home folder if there is none. Step 2 opens at the home folder too, because step 1's folder can hold tens of thousands of game files and `mode="file"` draws a row for each.

### 4.3 The save

"Yes, finish setup" sends one `PATCH /api/config` through `useConfigPatch`.

```ts
{ paths: { ...config.paths, source_roms, source_dat, dest_roms, retroarch_playlist } }
```

`retroarch_playlist` is `config.paths.retroarch_playlist` when `dest_roms` equals `config.paths.dest_roms`, so a user repairing a working setup keeps a playlist they placed themselves. Otherwise it is `playlistIn(dest_roms)`, which joins with the separator `dest_roms` uses and adds none after a trailing one.

While the save runs, Back and the exit are hidden, the action shows busy, and a `role="status"` element says "Reading your game list. This can take a minute."

| The save's answer | What the wizard does |
|---|---|
| Success, `restart_required` false | `useConfigPatch` has already refetched everything (below). `GuidePage` then sees `setup_required` false and shows the guide's first step, and marks the guide seen |
| Success, `restart_required` true | Returns to step 2 with `role="alert"`: "That file could not be read as a game list. Please choose another." |
| Refused or failed | Stays on step 3 with `apiErrorMessage` in a `role="alert"` element. Actions and Back return |

Choosing the games folder as the destination is stopped on step 3 before any save, with `role="alert"`: "Please choose a different folder from the one holding your games."

`useConfigPatch`'s `onSuccess` returns `qc.invalidateQueries()` for everything when the cached `["setup", "check"]` answer says `setup_required` is true. The mutation therefore stays pending, and the action busy, until the refetch settles. A Settings save that ends setup mode refreshes too, and no prompt is needed.

### 4.4 The picker

`FsBrowser` gains `large?: boolean`. When set, all its text is `text-xl`, messages and buttons included, and its rows and buttons are at least `3rem` tall. `ConfirmationDialog`, which draws the grant prompt, gains the same prop. `SetupWizard` sets it. Its title follows `mode`: "Choose a folder" or "Choose a file".

After "Allow", the picker stays open on the allowed folder, for every caller. Today `ConfirmationDialog`'s confirm also calls its `onOpenChange(false)`, which closes the picker. Cancel still closes it.

Its strings change for every caller, to plain words:

| Key | Text |
|---|---|
| `fsBrowserDescription` | "Open folders until you reach the one you want, then choose Use this folder." |
| `fsBrowserDescriptionFile` (new) | "Open folders until you find the file, then press it." |
| `fsBrowserUseDirectory` | "Use this folder" |
| `fsBrowserDirTag` | "folder" |
| `fsBrowserListError` | "This folder could not be opened." |
| `fsBrowserUpAtTop` | "Already at the top." |
| `fsBrowserHomeError` | "Your home folder could not be found. Choose a drive to carry on." |
| `fsGrantTitle` | "Allow MAME Curator to look here?" |
| `fsGrantConfirm(path)` | "MAME Curator is not yet allowed to look in {path}. Allow it?" |
| `fsGrantActionLabel(path)` | "Allow {path}" |

### 4.5 The launchers

`run.sh` and `run.bat` lose their "config.yaml — interactive setup if missing" block, and their closing `serve` line is unchanged. `serve` with no `--config` already resolves `./config.yaml`, then creates the per-user starter (`resolve_config_path`, `ensure_starter_config`). A user with a `./config.yaml` sees no change.

## 5. Invariants

- **INV-1** — In setup mode, a save naming a readable DAT loads its games and ends setup mode, with `restart_required` false and no restart.
  *Test:* `tests/api/test_setup_mode.py::test_setup_save_with_readable_dat_ends_setup_mode`, asserting the PATCH reply, then `/api/setup/check` and a non-empty `/api/games`.
  *Breaks when:* `patch_config` keeps only `replace_world`, which passes the empty `machines` through.

- **INV-2** — In setup mode, a save naming an unreadable DAT is kept, setup mode stays on, and `restart_required` is true. This amends mame-curator-1095 INV-10.
  *Test:* `tests/api/test_setup_mode.py::test_dat_change_requests_restart`, re-pointed at a malformed DAT, and asserting `setup_required` stays true.
  *Breaks when:* `restart_required` is computed from the old world, or from `server_changed` alone.

- **INV-3** — In setup mode, a save that changes nothing still retries the DAT.
  *Test:* `tests/api/test_setup_mode.py::test_setup_save_same_path_rereads_dat`: start with the DAT absent, write it at the configured path, PATCH the current paths, assert setup mode ended.
  *Breaks when:* the no-op return fires in setup mode.

- **INV-4** — A failure elsewhere in the retry leaves the save kept and the app in setup mode, not a 500.
  *Test:* `tests/api/test_setup_mode.py::test_setup_save_survives_other_unreadable_input`, with one PATCH naming a readable DAT and a malformed `paths.listxml`.
  *Breaks when:* `retry_setup` lets a `ParserError` from the listxml escape.

- **INV-5** — The retry does not run on the event loop, so other requests are answered during a long read.
  *Test:* `tests/api/test_setup_mode.py::test_setup_retry_runs_off_the_event_loop`, patching `build_world` with a recorder that compares its thread with the loop's.
  *Breaks when:* `retry_setup` is called directly from the coroutine.

- **INV-6** — In setup mode `/start` shows the three steps of §4.2 in order, nothing else of the guide is reachable, and `GUIDE_SEEN_KEY` stays unset. This amends mame-curator-1144 INV-14.
  *Test:* `frontend/src/pages/__tests__/GuidePage_setup.test.tsx`, and `GuidePage_entry.test.tsx`.
  *Breaks when:* `GuidePage` renders `GuideSteps`, or `SetupNeededStep`, in setup mode.

- **INV-7** — The answers are saved by exactly one PATCH, sent by the last step, holding all four keys. Leaving early sends none. The playlist follows §4.3's rule.
  *Test:* `GuidePage_setup.test.tsx`, counting PATCH bodies through a full walk, an exit from step 3, a changed destination and an unchanged one.
  *Breaks when:* a step saves its own answer, which `_validate_paths` could refuse because of another path not yet answered; or the playlist is always overwritten.

- **INV-8** — After a successful save the guide's first step shows without a page load, and every query is refetched. A Settings save that ends setup mode refetches every query too.
  *Test:* `GuidePage_setup.test.tsx`, whose setup-check handler flips after the PATCH, `frontend/e2e/setup-wizard.spec.ts`, and `frontend/src/hooks/__tests__/useConfig.test.tsx` for the hook.
  *Breaks when:* only the setup check is invalidated, which leaves the empty games list cached for its `staleTime`; or the invalidation lives in the wizard alone.

- **INV-9** — A DAT that cannot be read returns the user to step 2 with §4.3's sentence, their other answers kept. A refused save stays on step 3 and says why in a `role="alert"` element, and Back works again.
  *Test:* `GuidePage_setup.test.tsx`, with a reply of `restart_required: true`, a 422 naming `paths.source_roms`, and a 500.
  *Breaks when:* a kept-but-unreadable save is treated as success, or a refused save leaves the step busy.

- **INV-10** — Every step has the exit, steps 2 and 3 have Back, and neither shows during the save. Focus moves to the heading on each step change and on each choice, including after the picker closes.
  *Test:* `GuidePage_setup.test.tsx` for the actions, and `frontend/e2e/setup-wizard.spec.ts` for focus, walking a second choice too, because jsdom does not run the dialog's focus return against the frame `GuideStep` waits for.
  *Breaks when:* the dialog's returning focus lands after the heading's, or a second choice does not change `focusKey`.

- **INV-11** — Choosing the games folder as the destination is refused before any save.
  *Test:* `GuidePage_setup.test.tsx`, asserting the alert and no PATCH.
  *Breaks when:* the check is removed, which leaves "All of these are already copied." as the user's only clue.

- **INV-12** — The wizard's picker asks before looking outside the existing allowed folders, stays open on a folder the user allows, and step 2 picks a file. `large` changes only size.
  *Test:* `GuidePage_setup.test.tsx` for a `fs_sandboxed` listing, and `frontend/src/components/settings/__tests__/FsBrowser.test.tsx` for the title by mode, `large` and the open picker after a grant.
  *Breaks when:* the wizard adds its own listing, skips `FsBrowser`'s grant, or a confirmed grant closes the picker.

- **INV-13** — With no `config.yaml`, neither launcher runs `mame-curator setup`, and both reach `serve`.
  *Test:* `tests/tools/test_run_sh_port.py::test_no_config_goes_straight_to_serve`, running a copy with no config against the stub `uv`, and `tests/tools/test_run_sh_port.py::test_run_bat_never_runs_setup`, reading the script. It lives there because `test_run_bat_port.py` skips itself off Windows.
  *Breaks when:* the block stays in either file.

- **INV-14** — In a real browser against a real server started in setup mode, a new user can walk the three steps with the real picker and reach a Library with games.
  *Test:* `frontend/e2e/setup-wizard.spec.ts` starts its own `mame-curator serve` from a temporary starter config on its own port, with its own origin, so the browser holds no guide key. It uses the fixture DAT `tests/parser/fixtures/mini.dat.xml`.
  *Breaks when:* any link in the journey is missing, which is what the unit tests' fake handlers cannot show.

## 6. Failure modes

- **The chosen file is not a game list:** INV-9. The user picks again without losing the other answers.
- **The user chooses a wrong games folder:** nothing checks it here. The guide's Check step says "N could not be found in your ROM folder".
- **A folder the user wants does not exist yet:** `FsBrowser` cannot make one, and `_validate_paths` refuses a missing destination. The user makes it elsewhere first. §9 keeps this out of scope.
- **The folder or file vanishes between choice and save:** the save is refused, INV-9.
- **The user closes the page during the read:** the server finishes the save. On the next load, setup mode is already over.
- **The setup check fails after a good save:** the query keeps its old answer, so the wizard stays. It then shows `strings.guide.loadFailed` on step 3, and pressing the action again is safe (INV-3).
- **Another input fails during the retry:** a listxml, INI or overrides file that went bad after the server started, or a malformed `paths.listxml` saved through Settings. INV-4 keeps the save and §4.1 asks for a restart. The wizard shows §4.3's sentence, which then blames the wrong file, and the next start fails, as it already does after any save of a malformed listxml. A new user cannot reach this, because neither the starter config nor the wizard names those files. §9 keeps the repair out of scope.
- **A second tab is open:** its own queries catch up when they next refetch. Nothing else depends on it.
- **A copy is running:** setup mode has no games, so no copy can be.

## 7. Tests

| Invariant | Test |
|---|---|
| INV-1, INV-2, INV-3, INV-4, INV-5 | `tests/api/test_setup_mode.py` |
| INV-6 | `frontend/src/pages/__tests__/GuidePage_setup.test.tsx`, `GuidePage_entry.test.tsx` |
| INV-7, INV-9, INV-11 | `GuidePage_setup.test.tsx` |
| INV-8 | `GuidePage_setup.test.tsx`, `frontend/e2e/setup-wizard.spec.ts`, `frontend/src/hooks/__tests__/useConfig.test.tsx` |
| INV-10 | `GuidePage_setup.test.tsx`, `frontend/e2e/setup-wizard.spec.ts` |
| INV-12 | `GuidePage_setup.test.tsx`, `frontend/src/components/settings/__tests__/FsBrowser.test.tsx` |
| INV-13 | `tests/tools/test_run_sh_port.py` |
| INV-14 | `frontend/e2e/setup-wizard.spec.ts` |

**Existing tests that change:** `test_dat_change_requests_restart` (INV-2), `GuidePage_entry.test.tsx`'s setup case (INV-6), and `FsBrowser.test.tsx`'s literals for the changed strings.

Each new test must be seen to fail before its code exists. `frontend/e2e` runs by hand: `cd frontend && npm run build && npm run e2e`.

## 8. Alternatives considered (and rejected)

- **End on "Please close the app and open it again."** No backend change, and 1095 §4.2b's prompt already exists. It lost because the user may not know how to close a server started by double-click, the browser tab then dies, and the goal is a working Library at the end of the wizard.
- **A restart endpoint.** The server restarting itself differs by bundle, launcher and platform, and the page must then survive the outage. Re-reading in place is one guarded call.
- **Ask a fourth question for the playlist.** "Playlist" needs explaining, most new users have no answer, and Settings can change it.
- **Save each answer as it is given.** `_validate_paths` checks all paths on every save, so one answer can be refused for another's fault, and leaving early would change the config.
- **Pre-fill the starter folders.** See §3.

## 9. Out of scope

- Making a new folder from the picker — deferred; not yet queued.
- Asking for the optional reference files or `paths.listxml` — deferred; not yet queued. The Library's existing `ListxmlBanner` says what they add.
- Changing the DAT outside setup mode, which still needs a restart (1095 §4.2b) — deferred; not yet queued.
- Giving the guide's Where step the `large` picker — deferred; not yet queued.
- Refusing a save whose `paths.listxml` or other reference file will not parse, or starting in setup mode when one is bad — deferred; not yet queued.
- Removing `mame-curator setup`, which `cli/spec.md` says the browser wizard replaces — it stays for scripts.

## 10. What checks this

| Rule | What catches a breach |
|------|----------------------|
| INV-1, INV-2, INV-3, INV-4, INV-5 | `tests/api/test_setup_mode.py` |
| INV-6, INV-7, INV-9, INV-11 | `GuidePage_setup.test.tsx` |
| INV-8 | `GuidePage_setup.test.tsx` and `useConfig.test.tsx`, for the refetch; the real journey only by hand |
| INV-10 | Partial: `GuidePage_setup.test.tsx` for the actions; focus is `setup-wizard.spec.ts`, which no gate runs |
| INV-12 | `GuidePage_setup.test.tsx`, `FsBrowser.test.tsx` |
| INV-13 | `test_run_sh_port.py` |
| INV-14 | **nothing automatic** — `setup-wizard.spec.ts` runs by hand, because no gate runs `frontend/e2e` |
| The words and the large text suit this user | **nothing** — only the user can judge this, on the running app |

## 11. Cross-doc impact

- `CHANGELOG.md`: a user-facing entry.
- `docs/help/01-getting-started.md` and `04-command-line.md`, `README.md`: first run happens in the browser.
- `docs/specs/mame-curator-1144-guided-library.md` §4.8 and INV-14, `docs/specs/mame-curator-1095-desktop-bundles.md` §4.2b and INV-10: a pointer to this spec.
- `src/mame_curator/api/spec.md`: `patch_config`'s setup-mode behaviour and `build_world`'s callers. `src/mame_curator/cli/spec.md`: `setup` stays beside the browser wizard.

## 12. Cold-eyes loop log

Rows live in `../reviews/mame-curator-1145-setup-wizard-loop-log.md`.

## 13. Migration / compatibility

No config or file format changes. `restart_required` keeps its type and its meaning for the Settings banner, and is now false when a setup-mode save ends setup mode. A user with a `./config.yaml` is unaffected by §4.5. A user who runs `./run.sh` with none now gets the per-user config rather than one in the project folder.

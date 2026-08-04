# mame-curator-1095 — Ship self-contained desktop bundles for Linux, Windows and macOS

**Status:** spec draft (2026-08-04).
**Kind:** package.
**Source:** ROADMAP mame-curator-1095 (user request, 2026-08-04).

**Pairs with:** mame-curator-1089 (`run.bat` port forwarding — the bundles
bypass both bootstrap scripts, so 1089 stays scoped to the scripts).

**Layman:** download one file, double-click it, and MAME Curator opens in
your browser — no Python, no terminal, no install.

## 1. Goal

Each `v*.*.*` tag produces three downloadable artefacts — a Linux
`.AppImage`, a Windows `.exe`, and an unsigned macOS `.app` inside a
`.dmg` — that run on a machine with no Python, no `uv` and no network.
Each is built by a job in `.github/workflows/release.yml` with a local
mirror script that runs the same steps, so a packaging break is found on
a developer machine rather than in a tagged release. A first run with no
configuration starts successfully and is configured from the existing
Settings page.

## 2. Problem

Today the only published artefacts are an sdist and a wheel
(`release.yml`'s `build` job runs `uv build`). Both require a Python
3.12+ interpreter and a package installer. The clone-and-run path
(`run.sh`) additionally requires `python3`, installs `uv` over the
network, and runs `uv sync`. There is no artefact a person without a
Python toolchain can use.

Four defects block a naive "just run PyInstaller over it" answer. All four
were verified against current source, not recalled:

1. **The frontend would not be served.** `api/app.py` computes
   `_FRONTEND_DIST` from `Path(__file__).resolve().parents[3] / "frontend"
   / "dist"` — a path relative to the *source tree*. Inside a frozen
   bundle `__file__` lives under PyInstaller's extraction root, so
   `parents[3]` resolves outside the bundle, the `frontend/dist` check in
   `create_app` fails, and the SPA mount is skipped. The bundle would
   serve a JSON API with no user interface.

2. **`frontend/dist` is not packaged at all.** `[tool.hatch.build.targets.wheel]`
   declares `packages = ["src/mame_curator"]` and nothing else; `grep -n
   frontend pyproject.toml` returns no match. The built SPA reaches the
   bundle only if the packaging step adds it explicitly.

3. **A first run cannot produce a config.** `cli/commands/serve.py`
   exits 1 when the config file is absent, directing the user to
   `mame-curator setup`, which is an interactive terminal wizard —
   `cli/commands/setup.py::_cmd_setup` collects four paths through
   `rich.prompt.Prompt.ask`. A double-clicked bundle has no terminal to
   answer it in.

4. **Writing a starter config is not sufficient on its own.**
   `api/schemas.py::AppConfig` declares `paths: PathsConfig` with no
   default, and `PathsConfig` requires `source_roms`, `source_dat`,
   `dest_roms` and `retroarch_playlist` — four `Path` fields, none
   defaulted. `api/state.py::build_world` then calls
   `parse_dat(paths.source_dat)` unconditionally, so a config carrying
   placeholder paths raises `DATError` inside the lifespan and the server
   never binds. A zero-machine stub DAT does not rescue it either:

   ```
   $ uv run python -c "
   from pathlib import Path
   from mame_curator.parser import parse_dat
   try:
       parse_dat(Path('stub.xml'))
   except Exception as e:
       print(type(e).__name__, e)
   "
   DATError DAT contained no <machine> elements; check that this file is
   actually a MAME DAT (path=PosixPath('stub.xml'))
   ```

   (The `try/except` is the command as run — calling `parse_dat` bare
   prints a traceback rather than the single line above.)

   Defect 4 is why this spec touches `api/` at all. Packaging alone
   yields three bundles that start and immediately die.

The same failure already reaches existing users: if a configured DAT is
moved or deleted, the whole application refuses to start rather than
letting its owner correct the path in Settings.

## 3. Scope decisions (agreed with the user)

Preference calls, all made by the user on 2026-08-04 in response to a
four-question brief:

1. **First run writes a starter config** into the per-user config
   directory, rather than showing an error dialog or requiring the CLI
   wizard. Chosen over "package only, no first-run change".
2. **macOS ships unsigned**, with documented Gatekeeper steps. No Apple
   Developer account is being bought, so notarisation is out.
3. **The pipeline is wired but no release is tagged this round.** The
   AppImage is built locally for inspection; publishing stays a
   deliberate later act.
4. **Windows is a single one-file `.exe`**, not an installer.

Two decisions follow from §2 rather than preference, and are recorded
here because they widen the work beyond packaging:

5. **`build_world` degrades instead of failing** when the DAT cannot be
   read (§4.2). This is the mechanism decision 1 depends on; without it
   the starter config produces a server that cannot start.
6. **`serve`'s `--config` argparse default changes from
   `Path("config.yaml")` to `None`**, because "the user named a config"
   and "the user named nothing" are otherwise indistinguishable and must
   resolve differently. **Scoped to `sub_serve` alone.**
   `cli/__init__.py` registers `--config` with that default on three
   parsers (`grep -n '"--config"' src/mame_curator/cli/__init__.py` →
   lines 147, 182, 207); `refresh-inis` (147) and `refresh-snaps` (182)
   **keep `Path("config.yaml")` and keep today's resolution**. They are
   batch commands run from a shell in a project directory, never from a
   double-clicked bundle, so the first-run problem does not apply to
   them; extending the per-user layer to them is a separate decision
   nobody has asked for.

## 4. Design

### 4.1 Config location

New module `src/mame_curator/config_location.py`:

```python
STARTER_HEADER: str                 # comment banner written above a starter config
def user_config_path() -> Path      # <user_config_dir>/config.yaml
def user_data_path() -> Path        # <user_data_dir>/ — the four starter paths live here
def resolve_config_path(explicit: Path | None) -> Path
def ensure_starter_config(path: Path) -> bool   # True if it created the file
```

Both accessors pass **`appauthor=False`**:
`platformdirs.user_config_dir("mame-curator", appauthor=False)`. Without
it, `_append_parts` in `platformdirs/windows.py` appends the author
before the app name and defaults the author *to the app name*
(`author = self.appauthor or self.appname`), so Windows would get
`%LOCALAPPDATA%\mame-curator\mame-curator` — double-nested. Linux and
macOS are unaffected either way; this is a Windows-only correctness
detail that is invisible on the development machine.

`resolve_config_path` precedence, first hit wins:

| # | Source | Missing-file behaviour |
|---|---|---|
| 1 | `explicit` (`--config <path>`) | returned as given; `_cmd_serve` reports exit 1 exactly as today |
| 2 | `./config.yaml` in the working directory | skipped when absent |
| 3 | `platformdirs.user_config_dir("mame-curator", appauthor=False)/config.yaml` | **created** from the starter template |

Layer 2 keeps every current workflow working unchanged — `run.sh`,
`scripts/dev.sh`, and a developer sitting in the repo root all continue to
read the repo's own `config.yaml` without knowing this feature exists.

`platformdirs` (>=4.11.0, current release; already present in `uv.lock`
at 4.10.0 as a transitive dependency) becomes a direct dependency. With
`appauthor=False` it resolves `~/.config/mame-curator`,
`%LOCALAPPDATA%\mame-curator` and
`~/Library/Application Support/mame-curator` without three hand-written
branches.

**Where resolution happens in `_cmd_serve` is pinned by a sibling
contract.** `cli/spec.md` § "`serve` host, port and browser resolution"
splits the command into a stage 1 that validates `$PORT` **before any
config I/O** and a stage 2 that reads the file, and
`tests/cli/test_serve_port_env.py::test_invalid_port_checked_before_config`
pins the ordering. `resolve_config_path` and `ensure_starter_config`
both touch the filesystem, so they belong in **stage 2**, after the
`$PORT` raise and in place of the current `args.config.exists()` check.
Resolving the config at the top of `_cmd_serve` reds that test.

**`ensure_starter_config` creates the data directories too**, because
three of the four required paths are checked for existence by the API
before a config can be saved (§4.2): `source-roms/` and `dest-roms/` are
created, as is the parent of `mame.lpl`. `source_dat` is deliberately
**not** fabricated — a file that must be the user's own.

**Failure to write is fatal and reported.** An unwritable or
uncreatable config directory (a read-only home, a sandbox, a
`$XDG_CONFIG_HOME` pointing somewhere unavailable) raises `OSError`;
`_cmd_serve` catches it and exits 1 naming the path and the cause, in
the same escaped form as its other messages. It does not silently fall
back to the working directory — writing a config somewhere the user did
not ask for is how two configs come to exist.

**Layer-2 edge cases**, so the implementer does not have to choose: a
`./config.yaml` that exists but is a directory or is unreadable is
layer 2 **hit**, not skipped — the resolver tests existence, not
readability, and the resulting error is reported by the existing
`_load_server_config` path rather than silently falling through to a
different config. A per-user config that exists but is corrupt is
likewise never overwritten: `ensure_starter_config` creates only when
the file is **absent**.

**`overrides.yaml`, `sessions.yaml` and `data/` follow the config file,
and that is intended.** `api/state.py::build_world` derives all three
from `config_path.parent`, so with a per-user config they land beside it
in the config directory rather than in `user_data_dir`. Splitting them
would mean changing `build_world`'s contract for every existing
installation; keeping the whole per-installation state in one directory
is also what makes a bundle's state trivially removable.

The starter config is `config.example.yaml`'s four required `paths:`
values pointed at per-user directories the bundle creates, so the file
validates as an `AppConfig`:

```yaml
paths:
  source_roms: <user_data_dir>/source-roms
  source_dat: <user_data_dir>/source-dat.xml   # does not exist yet — see §4.2
  dest_roms: <user_data_dir>/dest-roms
  retroarch_playlist: <user_data_dir>/mame.lpl
server:
  host: 127.0.0.1
  port: 8080
  open_browser_on_start: true
```

### 4.2 Degraded start when the DAT is unreadable

`api/state.py::build_world` currently calls `parse_dat(paths.source_dat)`
unconditionally. It gains one guarded call:

```python
try:
    machines = parse_dat(paths.source_dat)
    setup_required = False
except (ParserError, OSError) as exc:
    logger.warning("DAT unreadable (%s) — starting in setup mode: %s", paths.source_dat, exc)
    machines = {}
    setup_required = True
```

`WorldState` gains `setup_required: bool = False` (the model is
`extra="forbid"`, so the field must be declared). It is surfaced on the
existing `GET /api/setup/check` response so the SPA can tell a genuinely
empty library from an unconfigured one.

The catch is deliberately narrow: `ParserError` and `OSError` are what a
missing, truncated or non-DAT file produce. A `RuntimeError` from our own
parser still propagates, per `cli/spec.md` § "Errors the CLI catches".

**This changes existing behaviour**: an application whose configured DAT
disappears now starts with an empty library and a warning, where it
previously refused to start. That is the better outcome — the Settings
page is the only place the path can be corrected, and it is unreachable
when the lifespan aborts.

Starting is necessary but not sufficient. Two further changes in `api/`
are what make the Settings page able to *finish* the job, and both were
missing from the first draft of this design:

**(a) `_validate_paths` must not reject the save that fixes the paths.**
`api/routes/config.py::_validate_paths` appends a `path_not_found`
`FieldError` for each of `source_roms`, `source_dat`, `dest_roms` and
`retroarch_playlist.parent` that does not exist, and `patch_config`
raises `ConfigError` when the list is non-empty. The starter config
points `source_dat` at a file that by construction does not exist, so
**every** `PATCH /api/config` is rejected until it is corrected —
including a PATCH that changes something unrelated. §4.1's directory
creation clears three of the four; the fourth is closed here: while
`world.setup_required` is true, a `path_not_found` on **`source_dat`
alone** is downgraded to a non-fatal field warning, so the config
persists and the user can save partial progress. Every other path error
stays fatal, and once `setup_required` is false the rule reverts.

**(b) `restart_required` must fire when the DAT path changes.** It is
currently `server_changed = new_config.server != world.config.server` —
`server:` only. A user who corrects `paths.source_dat` therefore gets
`restart_required: false` and no prompt, while `machines` stays empty
because `replace_world` does not re-parse the DAT. The condition
becomes `server_changed or (world.setup_required and
new_config.paths.source_dat != world.config.paths.source_dat)`, so the
one edit that ends setup mode is also the one that asks for the restart
that applies it.

**The SPA side is not free, and an earlier draft of this spec wrongly
said it was.** `setup_required` on `SetupCheck` (`api/routes/stubs.py`)
is mirrored in `frontend/src/api/schemas.ts` (`SetupCheckSchema`) and
`frontend/src/api/types.ts`, and `tools/check_api_types_sync.py` walks
`api/schemas_setup.py` — so adding the Python field alone turns the
`API type sync (Python ↔ TS)` step red in both `ci.yml` and
`release.yml`. The zod schema and the TS interface change in the same
commit.

### 4.3 Resource paths inside a frozen bundle

New module `src/mame_curator/_resources.py`:

```python
def bundle_root() -> Path:
    """Extraction root when frozen, else the repository root."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)        # PyInstaller onefile + onedir both set it
    return Path(__file__).resolve().parents[2]

def frontend_dist() -> Path:
    return bundle_root() / "frontend" / "dist"
```

`api/app.py`'s module-level `_FRONTEND_DIST` is replaced by a call to
`frontend_dist()` inside `create_app`, so the path is resolved at app
construction rather than at import.

### 4.4 One PyInstaller spec, three platforms

`packaging/mame-curator.spec` is shared; each platform's script invokes it
with a different `--distpath` and post-processing step. PyInstaller
6.21.0 (current release) is added as a `packaging` optional-dependency
group, not a runtime dependency.

The spec must carry, because PyInstaller's static analysis cannot see
them:

- `hiddenimports` for uvicorn's dynamically imported machinery — the
  `.auto` selectors (`uvicorn.logging`, `uvicorn.loops.auto`,
  `uvicorn.protocols.http.auto`, `uvicorn.protocols.websockets.auto`,
  `uvicorn.lifespan.on`) **and the implementations they select at
  runtime**, which is the half a `.auto`-only list misses: the project
  depends on `uvicorn[standard]`, so `uvloop`, `httptools` and
  `websockets` are what those selectors resolve to. `sse-starlette` is
  imported by the copy-progress route and is likewise invisible to
  static analysis. This list is a starting point, not an inventory —
  INV-13 is the authority, because only launching the artefact and
  fetching a page proves the set is complete.
- `datas` entries for `frontend/dist` (defect 2), `config.example.yaml`,
  and `packaging/` (the icon renditions, referenced by INV-14's
  allowlist).

Windows uses `--onefile`; Linux and macOS use one-dir, because the
AppImage and the `.app` are themselves the single-file wrapper. This also
confines a known upstream defect to Windows: PyInstaller `--onefile`
breaks uvicorn's Ctrl-C handling — signal delivery during lifespan
shutdown raises `CancelledError` instead of exiting cleanly, confirmed
across PyInstaller 5.x and 6.x with no upstream fix, and absent in
one-dir mode. Source: https://github.com/pyinstaller/pyinstaller/issues/8817

### 4.5 Linux — AppImage

`local-appimage.sh` and the `build-appimage` CI job run: build the
frontend, run PyInstaller one-dir, assemble an `AppDir` (`AppRun`,
`mame-curator.desktop`, `mame-curator.png`), then run `appimagetool`.

`appimagetool` publishes only a rolling `continuous` tag (verified:
`gh api repos/AppImage/appimagetool/releases/latest` → `tag_name:
continuous`, published 2025-12-04, asset
`appimagetool-x86_64.AppImage`). A rolling tag is not a version pin, so
the script pins the **sha256 of the downloaded binary** and fails loudly
when it changes — an unreviewed upstream binary is a supply-chain
decision, not a build detail.

### 4.6 Windows — single `.exe`

`local-exe.sh` and the `build-exe` CI job run the same frontend build and
PyInstaller with `--onefile --console`. The job declares
**`shell: bash`**: `windows-latest` defaults to `pwsh`, which cannot run
the script at all, and Git Bash ships on the GitHub runner image. Naming
the shell is what makes "the CI job runs the same steps" true rather
than aspirational. The console window is kept
deliberately: it is where uvicorn prints the URL, and `--windowed` gives
a server process nowhere to write stdout.

### 4.7 macOS — unsigned `.app` in a `.dmg`

`local-macos.sh` and the `build-macos` CI job produce `MAME Curator.app`
via PyInstaller's `BUNDLE`, then `hdiutil create` a `.dmg`. No signing,
no notarisation (§3 decision 2). The release notes and README gain the
first-launch instruction: right-click (or Control-click) the `.app`,
choose **Open**, then **Open** again in the dialog — needed once.
`xattr -dr com.apple.quarantine <path>` is documented as the fallback.
Source: https://chrplr.github.io/note-about-macos-unsigned-apps/

### 4.8 Local mirror scripts and their honest limit

The three scripts sit beside `local-CI.sh` and hold the same relationship
to `release.yml` that it holds to `ci.yml`. Only one of them can actually
run here:

| Script | Runs on this machine? | What local execution proves |
|---|---|---|
| `local-appimage.sh` | yes | the whole path, end to end — the AppImage is produced and launched |
| `local-exe.sh` | **no** — Linux host | `shellcheck` only; PyInstaller cannot cross-build a Windows binary |
| `local-macos.sh` | **no** — Linux host | `shellcheck` only; `hdiutil` and `BUNDLE` are macOS-only |

Both Windows and macOS scripts therefore have their first real execution
in CI. The spec states this rather than implying local coverage, because
a script that has never run reads exactly like one that has.

### 4.9 Icon

No application icon exists (`find . -iname '*.ico' -o -iname '*.icns'`
returns nothing; the only PNGs are `docs/screenshots/` and the media
cache). `packaging/icon.svg` is added as the single source, rendered to
`.png` (AppImage), `.ico` (Windows) and `.icns` (macOS) at build time.
It is a placeholder by intent — a wordmark tile, not a commissioned
design.

### 4.10 Where a GUI-launched failure goes

§2 defect 3 establishes that a double-clicked bundle has no terminal;
the corollary is that **every existing exit-1 path is currently
invisible to exactly the users this feature is for** — an unwritable
config directory, a port already bound, a corrupt config, a `--config`
typo in a shortcut. All of them print to stderr and vanish with the
process.

Two mechanisms, neither of which is a dialog framework:

1. **The Windows `.exe` keeps its console** (§4.6), so the message is on
   screen for the one platform where a GUI launch has no terminal at
   all.
2. **All three bundles tee stderr to a log file** at
   `platformdirs.user_log_dir("mame-curator", appauthor=False)/mame-curator.log`,
   truncated per run. The README's troubleshooting section names the
   path per platform. A user who reports "it just closes" can be asked
   for one file.

A native error dialog is out of scope (§9): it needs a GUI toolkit in
the bundle for a path that should be rare.

### 4.11 Artefact naming

One convention, because INV-12's mirror test compares the names CI and
the local scripts produce:

| Platform | Artefact |
|---|---|
| Linux | `MAME_Curator-<version>-x86_64.AppImage` |
| Windows | `MAME_Curator-<version>-x86_64.exe` |
| macOS | `MAME_Curator-<version>-<arch>.dmg` |

`<version>` is `pyproject.toml`'s `version` (1.2.0 today), read by the
scripts rather than hardcoded.

## 5. Invariants

- **INV-1** — With no `--config` and no `./config.yaml`,
  `resolve_config_path` returns the per-user path and
  `ensure_starter_config` creates it, along with the `source-roms/`,
  `dest-roms/` and playlist-parent directories.
  *Test:* `tests/cli/test_config_location.py::test_starter_config_and_dirs_are_created`.
  *Breaks when:* `resolve_config_path` returns the CWD path when it does
  not exist, or the directories are not created — which leaves
  `_validate_paths` rejecting the user's first save (§4.2a).

- **INV-2** — `serve` then reaches `uvicorn.run` rather than exiting 1.
  *Test:* `tests/cli/test_config_location.py::test_serve_starts_with_generated_config`
  — asserts against a mocked `uvicorn.run`, the pattern
  `tests/cli/test_serve_config_layer.py` already uses. Stated separately
  from INV-1 because "and starts" is the half a creation-only assertion
  cannot see, and INV-13's manual recipe is the only place a real bind is
  exercised.
  *Breaks when:* the config is created but the exit-1 branch still fires
  on the now-resolved path.

- **INV-3** — The starter config is created in **stage 2** of
  `_cmd_serve`, after `$PORT` validation.
  *Test:* `tests/cli/test_serve_port_env.py::test_invalid_port_checked_before_config`
  — the existing test, which must stay green with no edit.
  *Breaks when:* resolution is hoisted to the top of `_cmd_serve`, which
  reads naturally and reverses the exit-1 ordering `cli/spec.md` pins.

- **INV-4** — An explicit `--config` naming a missing file still exits 1
  and never creates anything.
  *Test:* `tests/cli/test_config_location.py::test_explicit_missing_config_still_exits_1`.
  *Breaks when:* the starter-config path is applied to layer 1, silently
  manufacturing a config the user did not ask for and masking a typo.

- **INV-5** — `./config.yaml` beats the per-user config.
  *Test:* `tests/cli/test_config_location.py::test_cwd_config_beats_user_config`.
  *Breaks when:* the per-user layer is checked first, which would move
  every existing `run.sh` and `scripts/dev.sh` user onto a different
  config without telling them.

- **INV-6** — The generated starter config validates as an `AppConfig`.
  *Test:* `tests/cli/test_config_location.py::test_starter_config_is_valid_appconfig`.
  *Breaks when:* a required `PathsConfig` field is added and the template
  is not updated — `AppConfig` then rejects the generated file on
  required-field validation, which is what four no-default fields make
  easy.

- **INV-7** — `build_world` returns a world with `setup_required=True`
  and no machines when `source_dat` is unreadable, rather than raising.
  *Test:* `tests/api/test_setup_mode.py::test_missing_dat_starts_in_setup_mode`.
  *Breaks when:* `parse_dat` raises something outside `(ParserError,
  OSError)` — the reason the catch names classes rather than `Exception`.

- **INV-8** — A DAT that exists but is malformed also degrades rather
  than aborting the lifespan.
  *Test:* `tests/api/test_setup_mode.py::test_malformed_dat_starts_in_setup_mode`.
  *Breaks when:* the catch is narrowed to `FileNotFoundError`. Stated
  separately from INV-7 because a missing file and a corrupt file take
  different paths through `parse_dat`, and a fixture that only deletes
  the file passes against a narrowed catch.

- **INV-9** — While `setup_required` is true, a `PATCH /api/config`
  whose only remaining path error is a missing `source_dat` is
  **persisted**, not rejected.
  *Test:* `tests/api/test_setup_mode.py::test_patch_persists_while_only_dat_missing`.
  *Breaks when:* `_validate_paths` keeps treating `source_dat` as fatal —
  which blocks every save the recovery journey depends on, including
  saves that have nothing to do with paths.

- **INV-10** — Correcting `paths.source_dat` while in setup mode returns
  `restart_required: true`.
  *Test:* `tests/api/test_setup_mode.py::test_dat_change_requests_restart`.
  *Breaks when:* the condition stays `server_changed` alone — the user
  fixes the path, sees no prompt, and the library stays empty because
  `replace_world` does not re-parse the DAT.

- **INV-11** — `frontend_dist()` resolves inside the extraction root when
  frozen, and to the repository tree otherwise.
  *Test:* `tests/test_resources.py::test_frontend_dist_follows_meipass`
  (monkeypatches `sys.frozen` / `sys._MEIPASS`; `tests/test_*.py` at the
  top level is where this project tests package-root modules — see
  `tests/test_atomic.py`, `tests/test_downloads.py`).
  *Breaks when:* the path is captured at import time again, which is what
  makes the current module-level `_FRONTEND_DIST` wrong in a bundle.
  **Third case, stated because the invariant names only two:** in a
  pip-installed wheel neither branch is right — `parents[2]` lands above
  `site-packages` and no `frontend/dist` exists there. That is unchanged
  from today's behaviour (the wheel has never shipped the SPA, §2 defect
  2) and stays out of scope; the branch returns the wrong path and the
  existing `is_dir()` guard in `create_app` skips the mount, exactly as
  it does now.

- **INV-12** — Every step in each local script appears in its CI job and
  vice versa.
  *Test:* `tests/tools/test_release_scripts.py::test_local_scripts_mirror_release_yml`.
  *Breaks when:* a step is added to `release.yml` only — the drift that
  makes a local mirror worse than no mirror, because it reports success
  for a pipeline it no longer represents.

- **INV-13** — The built AppImage runs on a machine with no project
  Python environment and serves the SPA.
  *Test:* manual recipe — no arrow; it cannot run in `pytest` because it
  binds a port and needs a built AppImage:

  ```bash
  ./local-appimage.sh
  HOME="$(mktemp -d)" ./dist/MAME_Curator-*.AppImage &   # background: it does not return
  until curl -sf http://127.0.0.1:8080/ >/dev/null; do sleep 1; done
  curl -sf http://127.0.0.1:8080/ | grep -q 'id="root"' && echo PASS
  kill %1
  ```

  A fresh `HOME` rather than `env -i`: the run must exercise §4.1's
  per-user path, and `platformdirs` resolves it from `HOME`/`XDG_*`,
  which `env -i` strips — the recipe would then test a code path the
  bundle never takes.
  *Breaks when:* a dynamically imported dependency is missing from
  `hiddenimports`, or the AppDir is assembled without `frontend/dist` —
  both produce a bundle that launches and passes a "did the process
  start" check while serving nothing, which is why the recipe fetches a
  page rather than testing liveness.

- **INV-14** — `packaging/mame-curator.spec` declares no `datas` entry
  outside an allowlist (`frontend/dist`, `config.example.yaml`,
  `packaging/`), so `config.yaml`, `data/` and the media cache cannot be
  swept into a bundle by a widened glob.
  *Test:* `tests/tools/test_release_scripts.py::test_spec_datas_are_allowlisted`.
  *Breaks when:* a `datas` glob widens to a parent directory — the
  mechanism by which a real DAT path, a media cache or a config with
  local paths would ship to every user.
  **Scoped deliberately to the declaration, not the artefact**: the test
  reads the PyInstaller spec, so it cannot see a file PyInstaller pulls
  in by dependency analysis. Auditing a built bundle's contents is the
  stronger check and needs all three artefacts; it is INV-13's manual
  recipe's neighbour, and is not claimed here.

## 6. Failure modes

| Assumption | When it breaks | Result |
|---|---|---|
| PyInstaller finds every import | a dependency imports dynamically and is not in `hiddenimports` | the bundle starts and fails on the first request that touches it; caught only by INV-13's launch, which is why the recipe fetches a page rather than checking the process is alive |
| `sys._MEIPASS` exists when frozen | a future PyInstaller changes the attribute | `bundle_root()` falls back to the source tree and the SPA 404s; INV-11 pins the current contract |
| `appimagetool` continuous asset is stable | upstream rebuilds it | the pinned sha256 mismatches and the build stops rather than silently using a new binary (§4.5) |
| one-file uvicorn shutdown is merely untidy | it turns out to hang rather than exit | Windows users cannot close the app cleanly; the fallback is the one-dir-plus-zip alternative in §8 |
| the user leaves setup mode | they correct `source_dat` in Settings and restart | `setup_required` returns to false and the library populates — via the two `api/` changes in §4.2, not via the pre-existing `restart_required` flow, which fires on `server:` changes only |
| the user never opens Settings | the bundle is launched, glanced at and closed | the library stays empty with only a `DEBUG`-level warning in the console; nothing in this design nags them, and `setup_required` on `/api/setup/check` is the only signal the SPA has to work with |
| the config directory is writable | a read-only home, a sandbox, an unavailable `$XDG_CONFIG_HOME` | `ensure_starter_config` raises `OSError`; `_cmd_serve` exits 1 naming the path (§4.1). A GUI launch surfaces it per §4.10 |
| macOS Gatekeeper behaviour holds | Apple tightens unsigned-app policy | the documented right-click flow stops working and signing becomes mandatory; nothing in this design detects that, it surfaces as user reports |

## 7. Tests

New files:

- `tests/cli/test_config_location.py` — INV-1, INV-2, INV-4 to INV-6
  (INV-3 is the existing `test_serve_port_env.py` case, unedited).
- `tests/api/test_setup_mode.py` — INV-7, INV-8, INV-9, INV-10.
- `tests/test_resources.py` — INV-11.
- `tests/tools/test_release_scripts.py` — INV-12, INV-14.

Each must be seen failing against pre-change code first. INV-1's test
fails today with the exit-1 "config file not found" path; INV-7's fails
with an uncaught `DATError`; INV-9's fails with a `ConfigError` from
`_validate_paths`; INV-10's fails because `restart_required` is
`server_changed` alone; INV-11's fails because `_FRONTEND_DIST` is a
module constant with no `sys.frozen` branch to exercise.

`tests/tools/test_release_scripts.py` follows the existing
`tests/tools/test_run_sh_port.py` pattern — parse the shell and the YAML,
compare step sets — and must be marked `skipif(sys.platform == "win32")`
per the guard in `tests/docs/test_posix_only_tests_skip_on_win32.py`.
**That marking means INV-12 is never checked on the platform `local-exe.sh`
targets**; it is a Linux-leg check of a Windows-facing script, which is
the same asymmetry §4.8 records.

The frontend gains no new test: the zod schema and TS interface changes
(§4.2) are covered by the existing `API type sync (Python ↔ TS)` gate,
which fails when they are absent.

The DS05 declaration-count pin in
`tests/docs/test_ds05_test_count_stable.py` moves by the number of tests
added, in the same commit.

## 8. Alternatives considered (and rejected)

- **Stub DAT with one placeholder machine**, so `build_world` succeeds
  without any `api/` change. Cheapest option and it was measured
  (§2 defect 4): rejected because a zero-machine DAT is refused outright,
  so the stub needs a fabricated machine that then appears in the user's
  library as a phantom entry. Degrading in `build_world` costs a few more
  lines and also fixes the pre-existing "moved DAT bricks the app" case.
- **A dedicated setup-mode API returning 503 from world-dependent
  routes**, with a frontend redirect. Correct, and considerably more
  work across two languages; the empty-world degrade reaches the same
  Settings page **with a much smaller frontend change** — a zod field
  and a TS interface field (§4.2), not a routing mode. Reconsider if the
  empty library proves confusing in use. (An earlier draft of this spec
  claimed "no frontend change"; that was wrong — `SetupCheck` is
  mirrored in TS and gated by `check_api_types_sync.py`.)

- **Windows one-dir plus a `.zip` instead of one-file.** Sidesteps the
  uvicorn Ctrl-C defect (§4.4) and starts faster, at the cost of not
  being the single file the user asked for (§3 decision 4). Held as the
  named fallback if the one-file shutdown proves to hang rather than
  merely print noise.
- **`.zip` instead of `.dmg` for macOS.** A zip avoids the "eject the
  disk image" step and is what one of the sources recommends. Rejected
  because the user's brief named a `.dmg` and it is the more conventional
  macOS delivery; the decision is cheap to reverse.
- **Windows installer (Inno Setup / NSIS)** — rejected by the user
  (§3 decision 4); a single file was the explicit ask.
- **`briefcase` / `pyapp` / `nuitka` instead of PyInstaller.** PyInstaller
  is the only one of the four that covers all three targets with one spec
  file and has documented FastAPI/uvicorn precedent. Revisit only if the
  one-file uvicorn defect proves fatal.
- **Hand-rolled per-OS config paths instead of `platformdirs`.** Twenty
  lines and three branches to re-derive a solved problem, against a
  dependency already in the lockfile (rule 3).

## 9. Out of scope

- Signing and notarising the macOS bundle — needs a paid Apple account
  (§3 decision 2).
- Windows code-signing certificates; the `.exe` will show a SmartScreen
  warning.
- Publishing a release. The pipeline is wired and idle until a tag is
  pushed (§3 decision 3).
- **`aarch64` AppImage** and an **Intel / `universal2` macOS build**.
  `macos-latest` is Apple Silicon, so the `.dmg` this pipeline produces
  is arm64-only and Intel Macs are not served; Linux ships x86_64 only.
  Both are separate items, and §4.11 puts the architecture in the
  filename so the gap is visible rather than implied.
- `run.bat`'s unconditional `--port` — mame-curator-1089.
- Auto-update for installed bundles.

## 10. Resource cost

**One** new runtime dependency: `platformdirs>=4.11.0`, already in the
lockfile transitively at 4.10.0. `pyinstaller>=6.21.0` is a
build-time-only optional-dependency group, absent from the wheel's
runtime requirements — `>=`, matching every other pin in
`pyproject.toml` and the project's latest-versions posture, not the
`==` an earlier draft of this section wrote.

Three new CI jobs, each on a different runner OS. Their runtime is not
estimated here — the first tagged release measures it, and a guess in a
spec is indistinguishable from a measurement. The repository is public,
so all three runners are free of minute quota; on a private repo the
macOS job would bill at 10× the Linux rate.

Artefact sizes and cold-start times are not yet measured. The first
`local-appimage.sh` run in `docs/plans/mame-curator-1095-desktop-bundles.md`
produces the first real figures, and no claim is made until it does —
but **declining to guess is not declining to budget**: that step also
writes the measured figures into this section as a ceiling, with a
build-failing check in each local script at 1.5× the recorded size. A
one-file `.exe` whose extraction cost is its main user-visible risk
otherwise has no regression guard at all.

## 11. What checks this

| Rule | What catches a breach |
|------|----------------------|
| INV-1 | `tests/cli/test_config_location.py::test_starter_config_and_dirs_are_created` |
| INV-2 | `tests/cli/test_config_location.py::test_serve_starts_with_generated_config` |
| INV-3 | `tests/cli/test_serve_port_env.py::test_invalid_port_checked_before_config` (existing) |
| INV-4 | `tests/cli/test_config_location.py::test_explicit_missing_config_still_exits_1` |
| INV-5 | `tests/cli/test_config_location.py::test_cwd_config_beats_user_config` |
| INV-6 | `tests/cli/test_config_location.py::test_starter_config_is_valid_appconfig` |
| INV-7 | `tests/api/test_setup_mode.py::test_missing_dat_starts_in_setup_mode` |
| INV-8 | `tests/api/test_setup_mode.py::test_malformed_dat_starts_in_setup_mode` |
| INV-9 | `tests/api/test_setup_mode.py::test_patch_persists_while_only_dat_missing` |
| INV-10 | `tests/api/test_setup_mode.py::test_dat_change_requests_restart` |
| INV-11 | `tests/test_resources.py::test_frontend_dist_follows_meipass` |
| INV-12 | `tests/tools/test_release_scripts.py::test_local_scripts_mirror_release_yml` — Linux leg only |
| INV-13 | **nothing** automated — needs a built AppImage and a bound port; the manual recipe in §5 is run before each release, and CI's own build job proves only that the file is produced, not that it runs |
| INV-14 | `tests/tools/test_release_scripts.py::test_spec_datas_are_allowlisted` |
| §4.2 SPA field | `tools/check_api_types_sync.py` via the `API type sync` step in `ci.yml` and `release.yml` |
| Windows `.exe` actually works | **nothing** local — no Windows host (§4.8); the CI job's first run is the first execution |
| macOS `.app` actually works | **nothing** local — no macOS host (§4.8); same |
| one-file uvicorn shutdown | **nothing** — upstream defect with no test surface on a Linux dev box; surfaces as a user report |
| §4.10 log file is written | **nothing** — no automated launch of any bundle exists to assert against; INV-13's recipe is where a human would notice its absence |

**Five** `nothing` rows. **Two** share one limit — this machine cannot
execute the Windows or the macOS target — and that pair is the honest
cost of cross-platform packaging from a single-OS developer machine. The
other three are distinct: INV-13 needs a built artefact and a free port,
so it is a manual recipe rather than an absent one; the one-file uvicorn
defect is upstream, with no test surface on any host we control; and
§4.10's log file has no automated launch to assert against, which is the
same gap as INV-13 one level down.

## 12. Cross-doc impact

- `pyproject.toml` — the `platformdirs` runtime dependency, the
  `packaging` optional-dependency group, and whatever `frontend/dist`
  packaging the build target needs (§2 defect 2).
- `docs/plans/mame-curator-1095-desktop-bundles.md` — the build order,
  written with this spec (`/write-spec --plan`) and cited by §10.
- `src/mame_curator/api/routes/config.py` — `_validate_paths`'
  setup-mode relaxation and the `restart_required` condition (§4.2).
- `src/mame_curator/api/routes/stubs.py` — `setup_required` on
  `SetupCheck`.
- `frontend/src/api/schemas.ts` + `frontend/src/api/types.ts` — the
  mirrored field, without which `check_api_types_sync.py` fails.
- `README.md` — download-and-run instructions for all three platforms,
  including the macOS right-click step and §4.10's log-file paths.
- `CHANGELOG.md` — user-facing entry under a dated topic subsection.
- `.github/workflows/release.yml` — three new jobs.
- `docs/standards/coding-standards.md` §8 version-break registry — only
  if a dependency has to be pinned back.
- `CLAUDE.md` § Common commands — the three new local scripts.
- `tests/docs/test_ds05_test_count_stable.py` — the declaration-count
  pin, bumped in the same commit as the new tests.
- `src/mame_curator/api/spec.md` — the `build_world` degrade and
  `WorldState.setup_required` change that module's contract.
- `src/mame_curator/cli/spec.md` — the `--config` default change and the
  new resolution order belong in its `serve` section.

## 13. Cold-eyes loop log

| Loop | Date | Lanes | CRIT | HIGH | MED | LOW | Outcome |
|------|------|-------|------|------|-----|-----|---------|
| 1 | 2026-08-04 | 3 × general-purpose | 3 | 5 | 12 | 16 | 36 verified / 0 unverified. **35 fixed, 1 dismissed** (no TOC — the governing `spec-skeleton.md` mandates none). Dimension tally: dim 2×8, dim 5×8, dim 4×5, dim 10×4, dim 7×3, dim 13×2, dim 6×2, dim 15×2, dim 9×1, dim 1×1, dim 11×1. All three CRITICALs were the same defect class — the first-run recovery journey asserted against code that does not support it: `restart_required` fires only on `server:` changes (`api/routes/config.py`), `_validate_paths` **rejects** every PATCH while the starter `source_dat` is absent (so the user can never save the fix), and the `--config` default change was written as one edit when three registrations carry it. §4.2 gained the two `api/` changes that make the journey real; §3 decision 6 is now scoped to `sub_serve`. Also fixed: §4.2/§8 contradicted each other on whether the frontend changes (it does — `SetupCheck` is mirrored in TS and gated by `check_api_types_sync.py`); INV-13's recipe could not pass as written (`env -i` strips the `HOME` `platformdirs` needs, and the AppImage never returns to the `&&`); `platformdirs` needs `appauthor=False` or Windows double-nests. **Collateral caught by 4c, not by a lane:** the four letter-suffixed ids this loop added (`INV-1b`…`INV-6c`) parsed as 10 invariants instead of 14 — silently absorbed into the preceding body — so all 14 were renumbered sequentially. Doc grew 493 → 758 lines. |

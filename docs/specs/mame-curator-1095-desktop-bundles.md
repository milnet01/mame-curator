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
   $ uv run python -c "from pathlib import Path; from mame_curator.parser import parse_dat; parse_dat(Path('stub.xml'))"
   DATError DAT contained no <machine> elements; check that this file is
   actually a MAME DAT (path=...stub.xml)
   ```

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
6. **The `--config` argparse default changes from `Path("config.yaml")`
   to `None`**, because "the user named a config" and "the user named
   nothing" are otherwise indistinguishable and must resolve differently.

## 4. Design

### 4.1 Config location

New module `src/mame_curator/config_location.py`:

```python
STARTER_HEADER: str          # comment banner written above a starter config
def user_config_path() -> Path:      # <user_config_dir>/mame-curator/config.yaml
def resolve_config_path(explicit: Path | None) -> Path
def ensure_starter_config(path: Path) -> bool   # True if it created the file
```

`resolve_config_path` precedence, first hit wins:

| # | Source | Missing-file behaviour |
|---|---|---|
| 1 | `explicit` (`--config <path>`) | returned as given; `_cmd_serve` reports exit 1 exactly as today |
| 2 | `./config.yaml` in the working directory | skipped when absent |
| 3 | `platformdirs.user_config_dir("mame-curator")/config.yaml` | **created** from the starter template |

Layer 2 keeps every current workflow working unchanged — `run.sh`,
`scripts/dev.sh`, and a developer sitting in the repo root all continue to
read the repo's own `config.yaml` without knowing this feature exists.

`platformdirs` (>=4.11.0, current release; already present in `uv.lock`
at 4.10.0 as a transitive dependency) becomes a direct dependency. It
resolves `~/.config/mame-curator`, `%LOCALAPPDATA%\mame-curator` and
`~/Library/Application Support/mame-curator` without three hand-written
branches.

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

- `hiddenimports` for uvicorn's dynamically imported machinery —
  `uvicorn.logging`, `uvicorn.loops.auto`, `uvicorn.protocols.http.auto`,
  `uvicorn.protocols.websockets.auto`, `uvicorn.lifespan.on`.
- `datas` entries for `frontend/dist` (defect 2) and
  `config.example.yaml`.

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
PyInstaller with `--onefile --console`. The console window is kept
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

## 5. Invariants

- **INV-1** — With no `--config` and no `./config.yaml`, `serve` creates
  the per-user config and starts, instead of exiting 1.
  *Test:* `tests/cli/test_config_location.py::test_serve_creates_starter_config`.
  *Breaks when:* `resolve_config_path` returns the CWD path when it does
  not exist, or `ensure_starter_config` writes a file `AppConfig` rejects.

- **INV-2** — An explicit `--config` naming a missing file still exits 1
  and never creates anything.
  *Test:* `tests/cli/test_config_location.py::test_explicit_missing_config_still_exits_1`.
  *Breaks when:* the starter-config path is applied to layer 1, silently
  manufacturing a config the user did not ask for and masking a typo.

- **INV-3** — `./config.yaml` beats the per-user config.
  *Test:* `tests/cli/test_config_location.py::test_cwd_config_beats_user_config`.
  *Breaks when:* the per-user layer is checked first, which would move
  every existing `run.sh` and `scripts/dev.sh` user onto a different
  config without telling them.

- **INV-4** — The generated starter config validates as an `AppConfig`.
  *Test:* `tests/cli/test_config_location.py::test_starter_config_is_valid_appconfig`.
  *Breaks when:* a required `PathsConfig` field is added and the template
  is not updated — the failure mode `extra="forbid"` plus four
  no-default fields makes easy.

- **INV-5** — `build_world` returns a world with `setup_required=True`
  and no machines when `source_dat` is unreadable, rather than raising.
  *Test:* `tests/api/test_setup_mode.py::test_missing_dat_starts_in_setup_mode`.
  *Breaks when:* `parse_dat` raises something outside `(ParserError,
  OSError)` — the reason the catch names classes rather than `Exception`.

- **INV-6** — A DAT that exists but is malformed also degrades rather
  than aborting the lifespan.
  *Test:* `tests/api/test_setup_mode.py::test_malformed_dat_starts_in_setup_mode`.
  *Breaks when:* the catch is narrowed to `FileNotFoundError`. Stated
  separately from INV-5 because a missing file and a corrupt file take
  different paths through `parse_dat`, and a fixture that only deletes
  the file passes against a narrowed catch.

- **INV-7** — `frontend_dist()` resolves inside the extraction root when
  frozen, and to the repository tree otherwise.
  *Test:* `tests/api/test_resources.py::test_frontend_dist_follows_meipass`
  (monkeypatches `sys.frozen` / `sys._MEIPASS`).
  *Breaks when:* the path is captured at import time again, which is what
  makes the current module-level `_FRONTEND_DIST` wrong in a bundle.

- **INV-8** — Every step in each local script appears in its CI job and
  vice versa.
  *Test:* `tests/tools/test_release_scripts_mirror_ci.py::test_local_scripts_mirror_release_yml`.
  *Breaks when:* a step is added to `release.yml` only — the drift that
  makes a local mirror worse than no mirror, because it reports success
  for a pipeline it no longer represents.

- **INV-9** — The built AppImage runs on a machine with no project
  Python environment and serves the SPA.
  *Test:* manual recipe — `./local-appimage.sh && env -i
  ./dist/MAME_Curator-*.AppImage` then `curl -sf http://127.0.0.1:8080/ |
  grep -q '<div id="root">'`. No arrow: this cannot run in `pytest`
  because it binds a port and needs a built AppImage.
  *Breaks when:* a dynamically imported dependency is missing from
  `hiddenimports`, or the AppDir is assembled without `frontend/dist` —
  both produce a bundle that launches and passes a "did the process
  start" check while serving nothing, which is why the recipe fetches a
  page rather than testing liveness.

- **INV-10** — `packaging/mame-curator.spec` declares no `datas` entry
  outside an allowlist (`frontend/dist`, `config.example.yaml`,
  `packaging/`), so `config.yaml`, `data/` and the media cache cannot be
  swept into a bundle by a widened glob.
  *Test:* `tests/tools/test_release_scripts_mirror_ci.py::test_spec_datas_are_allowlisted`.
  *Breaks when:* a `datas` glob widens to a parent directory — the
  mechanism by which a real DAT path, a media cache or a config with
  local paths would ship to every user.
  **Scoped deliberately to the declaration, not the artefact**: the test
  reads the PyInstaller spec, so it cannot see a file PyInstaller pulls
  in by dependency analysis. Auditing a built bundle's contents is the
  stronger check and needs all three artefacts; it is INV-9's manual
  recipe's neighbour, and is not claimed here.

## 6. Failure modes

| Assumption | When it breaks | Result |
|---|---|---|
| PyInstaller finds every import | a dependency imports dynamically and is not in `hiddenimports` | the bundle starts and fails on the first request that touches it; caught only by INV-9's launch, which is why the recipe fetches a page rather than checking the process is alive |
| `sys._MEIPASS` exists when frozen | a future PyInstaller changes the attribute | `bundle_root()` falls back to the source tree and the SPA 404s; INV-7 pins the current contract |
| `appimagetool` continuous asset is stable | upstream rebuilds it | the pinned sha256 mismatches and the build stops rather than silently using a new binary (§4.5) |
| one-file uvicorn shutdown is merely untidy | it turns out to hang rather than exit | Windows users cannot close the app cleanly; the fallback is one-dir plus a zip, recorded in §8 |
| the starter config's paths stay absent | the user points Settings at a real DAT | `setup_required` returns to false on the next restart — the existing `restart_required` flow already covers this |
| macOS Gatekeeper behaviour holds | Apple tightens unsigned-app policy | the documented right-click flow stops working and signing becomes mandatory; nothing in this design detects that, it surfaces as user reports |

## 7. Tests

New files:

- `tests/cli/test_config_location.py` — INV-1 to INV-4.
- `tests/api/test_setup_mode.py` — INV-5, INV-6.
- `tests/api/test_resources.py` — INV-7.
- `tests/tools/test_release_scripts_mirror_ci.py` — INV-8, INV-10.

Each must be seen failing against pre-change code first. INV-1's test
fails today with the exit-1 "config file not found" path; INV-5's fails
with an uncaught `DATError`; INV-7's fails because `_FRONTEND_DIST` is a
module constant with no `sys.frozen` branch to exercise.

`tests/tools/test_release_scripts_mirror_ci.py` follows the existing
`tests/tools/test_run_sh_port.py` pattern — parse the shell and the YAML,
compare step sets — and must be marked `skipif(sys.platform == "win32")`
per the guard in `tests/docs/test_posix_only_tests_skip_on_win32.py`.

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
  Settings page with no frontend change. Reconsider if the empty library
  proves confusing in use.
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
- ARM builds (`aarch64` AppImage, Apple Silicon-native `.app`). The macOS
  runner's architecture decides what ships; a universal2 build is a
  separate item.
- `run.bat`'s unconditional `--port` — mame-curator-1089.
- Auto-update for installed bundles.

## 10. Resource cost

Two new runtime dependencies: `platformdirs>=4.11.0` (already in the
lockfile transitively) and nothing else. `pyinstaller==6.21.0` is a
build-time-only optional-dependency group, absent from the wheel's
runtime requirements.

Three new CI jobs, each on a different runner OS. Their runtime is not
estimated here — the first tagged release measures it, and a guess in a
spec is indistinguishable from a measurement. The repository is public,
so all three runners are free of minute quota; on a private repo the
macOS job would bill at 10× the Linux rate.

Artefact sizes are not yet measured — the AppImage build in step 1 of the
plan produces the first real figure, and no size claim is made until it
does.

## 11. What checks this

| Rule | What catches a breach |
|------|----------------------|
| INV-1 | `tests/cli/test_config_location.py::test_serve_creates_starter_config` |
| INV-2 | `tests/cli/test_config_location.py::test_explicit_missing_config_still_exits_1` |
| INV-3 | `tests/cli/test_config_location.py::test_cwd_config_beats_user_config` |
| INV-4 | `tests/cli/test_config_location.py::test_starter_config_is_valid_appconfig` |
| INV-5 | `tests/api/test_setup_mode.py::test_missing_dat_starts_in_setup_mode` |
| INV-6 | `tests/api/test_setup_mode.py::test_malformed_dat_starts_in_setup_mode` |
| INV-7 | `tests/api/test_resources.py::test_frontend_dist_follows_meipass` |
| INV-8 | `tests/tools/test_release_scripts_mirror_ci.py::test_local_scripts_mirror_release_yml` |
| INV-9 | **nothing** automated — needs a built AppImage and a bound port; the manual recipe in §5 is run before each release, and CI's own build job proves only that the file is produced, not that it runs |
| INV-10 | `tests/tools/test_release_scripts_mirror_ci.py::test_spec_datas_are_allowlisted` |
| Windows `.exe` actually works | **nothing** local — no Windows host (§4.8); the CI job's first run is the first execution |
| macOS `.app` actually works | **nothing** local — no macOS host (§4.8); same |
| one-file uvicorn shutdown | **nothing** — upstream defect with no test surface on a Linux dev box; surfaces as a user report |

Four `nothing` rows. **Two** share one limit — this machine cannot
execute the Windows or the macOS target — and that pair is the honest
cost of cross-platform packaging from a single-OS developer machine. The
other two are distinct: INV-9 needs a built artefact and a free port, so
it is a manual recipe rather than an absent one; and the one-file uvicorn
defect is upstream, with no test surface on any host we control.

## 12. Cross-doc impact

- `README.md` — download-and-run instructions for all three platforms,
  including the macOS right-click step.
- `CHANGELOG.md` — user-facing entry under a dated topic subsection.
- `.github/workflows/release.yml` — three new jobs.
- `docs/standards/coding-standards.md` §8 version-break registry — only
  if a dependency has to be pinned back.
- `CLAUDE.md` § Common commands — the three new local scripts.
- `src/mame_curator/api/spec.md` — the `build_world` degrade and
  `WorldState.setup_required` change that module's contract.
- `src/mame_curator/cli/spec.md` — the `--config` default change and the
  new resolution order belong in its `serve` section.

## 13. Cold-eyes loop log

| Loop | Date | Lanes | CRIT | HIGH | MED | LOW | Outcome |
|------|------|-------|------|------|-----|-----|---------|

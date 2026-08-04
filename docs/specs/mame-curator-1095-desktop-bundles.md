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
class ConfigSource(StrEnum):        # which layer won
    EXPLICIT = "explicit"           # --config <path>
    CWD = "cwd"                     # ./config.yaml
    USER = "user"                   # the per-user path

STARTER_HEADER: str                 # comment banner — see the note below
def user_config_path() -> Path      # <user_config_dir>/config.yaml
def user_data_path() -> Path        # <user_data_dir>/ — the four starter paths live here
def user_log_path() -> Path         # <user_log_dir>/mame-curator.log — see §4.11
def resolve_config_path(explicit: Path | None) -> tuple[Path, ConfigSource]
def ensure_starter_config(path: Path) -> bool   # True if it created the file
```

**`resolve_config_path` returns which layer won, and that is
load-bearing rather than decorative.** A bare `-> Path` discards the
one fact the caller needs: `ensure_starter_config` must run for layer 3
and must **not** run for layers 1 and 2. An implementer wiring
`ensure_starter_config(resolve_config_path(args.config))` against a
`Path`-only signature satisfies the types and breaks INV-4 by
manufacturing a config for a mistyped `--config`. This is the same
provenance-loss trap `cli/spec.md` spends four paragraphs on for
`_resolve_port`, and it is avoided the same way — by carrying the
provenance instead of re-deriving it from the value.

`STARTER_HEADER` **supersedes** `cli/commands/setup.py::_SETUP_HEADER`
rather than duplicating it: the wizard's banner moves to this module and
`_cmd_setup` imports it, so one generated-config banner exists and both
writers use it.

`_cmd_serve` calls `ensure_starter_config` **only when the source is
`ConfigSource.USER`**, and the resolved path — not `args.config`, which
is now `None` by default — is what reaches `_load_server_config` and
`create_app`.

All three accessors pass **`appauthor=False`**:
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

Layer 2 keeps the current workflows working unchanged: `run.sh` `cd`s to
its own directory before exec'ing, and a developer sitting in the repo
root gets the repo's `config.yaml` without knowing this feature exists.
`scripts/dev.sh` is unaffected for a different reason — it passes
`--config "${CONFIG}"` explicitly, so it resolves through **layer 1**
and never reaches either of the layers below.

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
`extra="forbid"`, so the field must be declared).

**The rest of `build_world` runs unchanged on the empty dict** and must
produce a complete `WorldState`, not a partial one: `run_filter`,
`compose_allowlist` and the `bytes_by_machine` mapping all execute with
`machines={}`. INV-7's test asserts the world is *usable* — every field
populated, `bytes_by_machine` empty rather than absent — not merely that
it has no machines. A degrade that returns a half-built world moves the
crash from the lifespan to the first request. It is surfaced on the
existing `GET /api/setup/check` response so the SPA can tell a genuinely
empty library from an unconfigured one.

The catch is deliberately narrow: `ParserError` and `OSError` are what a
missing, truncated or non-DAT file produce — `parser/dat.py` already
wraps `zipfile.BadZipFile`, `OSError` and `etree.XMLSyntaxError` into
`DATError`, so a corrupt `.zip` DAT is covered. A `RuntimeError` from
our own parser still propagates: this runs in the API lifespan, so
`api/spec.md` owns the rule, and it is the same typed-catches-only
discipline `cli/spec.md` § "Errors the CLI catches" states for the CLI
boundary.

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
creation clears three of the four; the fourth is closed here.

`_validate_paths` today is `_validate_paths(config: AppConfig) ->
tuple[FieldError, ...]` and cannot see the world, so it gains a
keyword-only parameter:

```python
def _validate_paths(config: AppConfig, *, setup_required: bool = False) -> tuple[FieldError, ...]:
```

When `setup_required` is true, the `source_dat` `path_not_found` error
**is not appended at all** — the field is skipped, not collected and
filtered, so no new warnings channel is needed and
`AppConfigResponse` is unchanged (which matters: adding a field to it
would pull a second `check_api_types_sync.py` surface into scope). The
missing DAT is already reported to the SPA through `setup_required` on
`SetupCheck` and to the console through §4.2's `logger.warning`.

Every **other** path error stays fatal even in setup mode, and once
`setup_required` is false the `source_dat` check applies again. The
call site passes it explicitly:
`_validate_paths(new_config, setup_required=world.setup_required)`.

**(b) `restart_required` must fire when the DAT path changes.** It is
currently `server_changed = new_config.server != world.config.server` —
`server:` only. A user who corrects `paths.source_dat` therefore gets
`restart_required: false` and no prompt, while `machines` stays empty
because `replace_world` does not re-parse the DAT. The condition becomes:

```python
restart_required = server_changed or world.setup_required
```

**Deliberately not `… and new_config.paths.source_dat !=
world.config.paths.source_dat`.** The likeliest recovery is that the
user drops their DAT at exactly the path the starter config already
names, in which case the path string is unchanged and a
difference-based condition returns false — leaving the library empty
with no prompt, which is the precise failure INV-10 exists to prevent.
While `setup_required` is true, *any* successful save asks for the
restart; it is one extra prompt during setup and it cannot miss.

**A DAT swap outside setup mode still returns `restart_required: false`
and a stale library.** That is pre-existing behaviour, unchanged here
and knowingly left alone: it is a `replace_world` question, not a
first-run one, and widening it would pull the world-rebuild contract
into a packaging item.

**The SPA side is not free, and an earlier draft of this spec wrongly
said it was.** The field is declared on `SetupCheck` in
**`api/schemas_setup.py`** (`routes/stubs.py` only imports it and
populates it in `setup_check`), and is mirrored in `frontend/src/api/schemas.ts` (`SetupCheckSchema`) and
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
6.21.0 (current release) is added as a **`bundle`** optional-dependency
group, not a runtime dependency — `bundle` rather than `packaging`,
which would collide with both the `packaging/` directory this spec adds
and the widely-installed PyPI distribution of that name.

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
  allowlist). **The destination path matters as much as the source**:
  `frontend/dist` must land at `frontend/dist` inside the bundle,
  because §4.3's `frontend_dist()` looks for `bundle_root() /
  "frontend" / "dist"`. A `datas=[("frontend/dist", ".")]` builds green
  and 404s every page.

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

The `build-exe` CI job runs on `windows-latest`; `local-exe.sh` runs the
same steps **on this Linux machine under Wine**. Both invoke the same
frontend build and PyInstaller with `--onefile --console`.

**Wine is the supported route, not a hack.** PyInstaller's FAQ states
that cross-compilation is unsupported and directs Windows-from-Linux
builds at Wine explicitly — "please use Wine for this, as PyInstaller
runs fine in Wine". `local-exe.sh` therefore provisions a project-local
`WINEPREFIX` at `.wine-build/` (gitignored), installs the Windows
CPython that matches `pyproject.toml`'s `requires-python`, and runs
`wine python -m PyInstaller` against the shared spec file.
Source: https://github.com/pyinstaller/pyinstaller/wiki/FAQ

**What that does and does not prove.** It builds a real PE binary with
the real Windows CPython, so it catches the packaging failures that
actually bite — a missing `hiddenimport`, a `datas` entry that did not
land, a spec-file syntax error — before a tag is pushed. It is **not**
a substitute for the CI job: the binary is produced under Wine rather
than on Windows, and Wine's own behaviour differs from Windows at the
edges. CI on `windows-latest` remains the authority; `local-exe.sh` is
the pre-flight that stops most red CI runs happening at all. The job declares
**`shell: bash`**: `windows-latest` defaults to `pwsh`, which cannot run
the script at all, and Git Bash ships on the GitHub runner image. Naming
the shell is what makes "the CI job runs the same steps" true rather
than aspirational. The console window is kept
deliberately: it is where uvicorn prints the URL, and `--windowed` gives
a server process nowhere to write stdout.

### 4.7 macOS — unsigned `.app` in a `.dmg`

`local-macos.sh` and the `build-macos` CI job produce `MAME Curator.app`
via PyInstaller's `BUNDLE`, then `hdiutil create` a `.dmg`.

**There is no Linux equivalent of the Wine route here, and this is
settled rather than unexplored.** PyInstaller's FAQ: "Packaging macOS
binaries while running under Linux is currently not possible at all."
`osxcross` is a C/C++ cross-toolchain — it can compile Darwin objects,
but PyInstaller must *run* a macOS CPython to freeze it, and nothing on
Linux hosts one. So `local-macos.sh` is the only one of the three
scripts that genuinely cannot run here.
Source: https://github.com/pyinstaller/pyinstaller/wiki/FAQ No signing,
no notarisation (§3 decision 2). The release notes and README gain the
first-launch instruction: right-click (or Control-click) the `.app`,
choose **Open**, then **Open** again in the dialog — needed once.
`xattr -dr com.apple.quarantine <path>` is documented as the fallback.
Source: https://chrplr.github.io/note-about-macos-unsigned-apps/

### 4.8 Local mirror scripts and their honest limit

The three scripts sit beside `local-CI.sh` and hold the same relationship
to `release.yml` that it holds to `ci.yml`. **Two of the three run here**:

| Script | Runs on this machine? | What local execution proves |
|---|---|---|
| `local-appimage.sh` | yes, natively | the whole path, end to end — the AppImage is produced and launched (INV-13) |
| `local-exe.sh` | yes, **under Wine** (§4.6) | a real PE binary is produced and starts; catches missing hidden imports and absent `datas`. Not binary-identical to the CI build |
| `local-macos.sh` | **no** — impossible, not merely unavailable (§4.7) | `shellcheck` only |

**Only `local-macos.sh` has its first real execution in CI.** An earlier
draft of this spec said the same of `local-exe.sh`; that was wrong, and
it mattered — it wrote off the platform whose bundle carries the most
packaging risk (one-file mode, §4.4) as unverifiable, when the tool's own
FAQ documents the route. The spec states which scripts have been run
rather than implying coverage, because a script that has never run reads
exactly like one that has.

### 4.9 Icon

No application icon exists (`find . -iname '*.ico' -o -iname '*.icns'`
returns nothing; the only PNGs are `docs/screenshots/` and the media
cache). `packaging/icon.svg` is added as the single source, rendered to
`.png` (AppImage), `.ico` (Windows) and `.icns` (macOS) at build time.
It is a placeholder by intent — a wordmark tile, not a commissioned
design.

### 4.10 Attaching the bundles to the Release

**Three build jobs are not enough on their own, and this is the step that
makes §1 true.** `release.yml`'s `publish` job declares `needs: build`
and downloads a *single* artifact named `dist` before handing
`files: dist/*` to `softprops/action-gh-release`. Three new build jobs
satisfy "three new jobs in `release.yml`" while their outputs are
discarded when the run ends, and `fail_on_unmatched_files: true` does not
notice, because `dist/*` still matches the sdist and the wheel.

So the wiring is part of the contract:

- each build job uploads under its own artifact name — `bundle-linux`,
  `bundle-windows`, `bundle-macos`;
- `publish` gains `needs: [build, build-appimage, build-exe, build-macos]`;
- `publish` gains one `download-artifact` step per bundle, all into
  `dist/`, so the existing `files: dist/*` picks them up unchanged.

`needs` is also what enforces §3 decision 3's ordering: a bundle job that
fails stops the Release rather than publishing a partial set.

### 4.11 Where a GUI-launched failure goes

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
2. **All three bundles tee stderr to a log file** at `user_log_path()`
   (§4.1), truncated per run.
   **Owner: `main.py::main()`**, which installs the tee as its first
   action and **only when `getattr(sys, "frozen", False)`** — a
   source-tree or `pip install` run keeps today's plain stderr, so no
   developer workflow changes and no test has to account for a redirect.
   `main()` is the one entry point all three bundles share, which is
   what avoids three per-platform wrappers doing it three ways. The
   README's troubleshooting section names the resolved path per
   platform.

A native error dialog is out of scope (§9): it needs a GUI toolkit in
the bundle for a path that should be rare.

### 4.12 Artefact naming

One convention. It is **not** what INV-12 checks — that invariant
compares *step sets*, not filenames — but the local scripts and the CI
jobs must agree on it or the `download-artifact` steps in §4.10 match
nothing:

| Platform | Artefact | `<arch>` today |
|---|---|---|
| Linux | `MAME_Curator-<version>-<arch>.AppImage` | `x86_64` |
| Windows | `MAME_Curator-<version>-<arch>.exe` | `x86_64` |
| macOS | `MAME_Curator-<version>-<arch>.dmg` | `arm64` (`macos-latest` is Apple Silicon) |

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
  # Background: the bundle runs a server and never returns. A fresh HOME
  # forces the per-user config path; --no-open-browser stops the poller
  # spawning a tab on every run of the recipe.
  HOME="$(mktemp -d)" ./dist/MAME_Curator-*-x86_64.AppImage --no-open-browser &
  for _ in $(seq 60); do
      curl -sf http://127.0.0.1:8080/ >/dev/null && break
      sleep 1
  done
  curl -sf http://127.0.0.1:8080/ | grep -q 'id="root"' && echo PASS || echo FAIL
  kill %1
  ```

  **The loop is bounded on purpose.** An unbounded `until` hangs forever
  on exactly the failure this invariant exists to catch — a missing
  `hiddenimport` makes the bundle exit at once, so the port never opens
  and a waiting recipe never reports.

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

- **INV-15** — Each local build script fails when its artefact exceeds
  the size ceiling recorded in §10.
  *Test:* `tests/tools/test_release_scripts.py::test_scripts_carry_a_size_ceiling`
  — asserts each script contains a numeric ceiling and a non-zero exit
  on breach. It cannot assert the *artefact* is under it (that needs a
  build), only that the guard exists and is wired.
  *Breaks when:* the ceiling is written into §10 as prose and never into
  the scripts — which is what "we will measure it later" degrades into
  when nothing checks.

- **INV-16** — `local-exe.sh` produces a PE executable that starts under
  Wine and serves the SPA.
  *Test:* manual recipe — no arrow; it needs a built `.exe` and a bound
  port, exactly as INV-13 does:

  ```bash
  ./local-exe.sh
  WINEPREFIX="$PWD/.wine-build" wine dist/MAME_Curator-*-x86_64.exe --no-open-browser &
  for _ in $(seq 60); do
      curl -sf http://127.0.0.1:8080/ >/dev/null && break
      sleep 1
  done
  curl -sf http://127.0.0.1:8080/ | grep -q 'id="root"' && echo PASS || echo FAIL
  kill %1
  ```

  *Breaks when:* the same two causes as INV-13 — a missing
  `hiddenimport` or an absent `datas` entry. A Wine PASS does **not**
  promise the binary works on real Windows; it promises the bundle was
  assembled correctly, which is the failure class that would otherwise
  reach a tagged release.

## 6. Failure modes

| Assumption | When it breaks | Result |
|---|---|---|
| PyInstaller finds every import | a dependency imports dynamically and is not in `hiddenimports` | the bundle starts and fails on the first request that touches it; caught only by INV-13's launch, which is why the recipe fetches a page rather than checking the process is alive |
| `sys._MEIPASS` exists when frozen | a future PyInstaller changes the attribute | `bundle_root()` falls back to the source tree and the SPA 404s; INV-11 pins the current contract |
| `appimagetool` continuous asset is stable | upstream rebuilds it | the pinned sha256 mismatches and the build stops rather than silently using a new binary (§4.5) |
| one-file uvicorn shutdown is merely untidy | it turns out to hang rather than exit | Windows users cannot close the app cleanly; the fallback is the one-dir-plus-zip alternative in §8 |
| the user leaves setup mode | they correct `source_dat` in Settings and restart | `setup_required` returns to false and the library populates — via the two `api/` changes in §4.2, not via the pre-existing `restart_required` flow, which fires on `server:` changes only |
| the user never opens Settings | the bundle is launched, glanced at and closed | the library stays empty; §4.2's `logger.warning` line **is** visible on a default run (`cli/spec.md` § "Logging configuration" pins the default level to `INFO`), and `setup_required` on `/api/setup/check` is the signal the SPA has to work with. Nothing in this design nags the user beyond that |
| the config directory is writable | a read-only home, a sandbox, an unavailable `$XDG_CONFIG_HOME` | `ensure_starter_config` raises `OSError`; `_cmd_serve` exits 1 naming the path (§4.1). A GUI launch surfaces it per §4.11 |
| macOS Gatekeeper behaviour holds | Apple tightens unsigned-app policy | the documented right-click flow stops working and signing becomes mandatory; nothing in this design detects that, it surfaces as user reports |

## 7. Tests

New files:

- `tests/cli/test_config_location.py` — INV-1, INV-2, INV-4 to INV-6
  (INV-3 is the existing `test_serve_port_env.py` case, unedited).
- `tests/api/test_setup_mode.py` — INV-7, INV-8, INV-9, INV-10.
- `tests/test_resources.py` — INV-11.
- `tests/tools/test_release_scripts.py` — INV-12, INV-14.

Each must be seen failing against pre-change code first. INV-1's and
INV-2's tests fail at import today — `config_location.py` does not
exist; INV-4's is the one that fails on the exit-1 "config file not
found" path, which is the behaviour it pins as unchanged. INV-7's fails
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
- **Cross-building the macOS bundle on Linux** — `osxcross`,
  `darling`, or a packaged macOS SDK. Rejected on the tool's own
  authority rather than on effort: PyInstaller must execute a macOS
  CPython to freeze one, and `osxcross` is a C/C++ compiler toolchain,
  not a Darwin userland. Apple's licence also confines macOS to Apple
  hardware. This is closed, not deferred — §4.7 carries the citation so
  the question is not reopened every release.

- **A macOS VM on this machine** — same licence constraint, and it would
  make the local script depend on a VM nobody else building this project
  would have. GitHub's `macos-latest` runner is the supported answer and
  costs nothing on a public repo.

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
  Both are separate items, and §4.12 puts the architecture in the
  filename so the gap is visible rather than implied.
- `run.bat`'s unconditional `--port` — mame-curator-1089.
- Auto-update for installed bundles.
- Any local macOS build path (§4.7, §8) — closed on PyInstaller's own
  documentation, not deferred to a later item.

## 10. Resource cost

**One** new runtime dependency: `platformdirs>=4.11.0`, already in the
lockfile transitively at 4.10.0. `pyinstaller>=6.21.0` is in the build-time-only `bundle`
optional-dependency group, absent from the wheel's
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
build-failing check in each local script at 1.5× the recorded size (see
INV-15). A one-file `.exe` whose extraction cost is its main
user-visible risk otherwise has no regression guard at all.

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
| macOS `.app` actually works | **nothing** local — building a macOS bundle on Linux is impossible, not merely unavailable (§4.7); the CI job's first run is the first execution |
| one-file uvicorn shutdown | **nothing** — upstream defect with no test surface on a Linux dev box; surfaces as a user report |
| §4.1 unwritable config dir exits 1 | **nothing** — no test drives an unwritable `$XDG_CONFIG_HOME`; the §6 row is the contract and a `chmod 500` reproduction is the manual check |
| INV-15 | `tests/tools/test_release_scripts.py::test_scripts_carry_a_size_ceiling` |
| INV-16 | manual recipe in §5 — a Wine build-and-launch; the `build-exe` CI job on `windows-latest` is the authority for real-Windows behaviour |
| §4.11 log file is written | **nothing** — no automated launch of any bundle exists to assert against; INV-13's recipe is where a human would notice its absence |

**Five** `nothing` rows, down from six: the Windows row became INV-16
once the Wine route was verified, leaving macOS as the only target this
machine cannot reach at all. The remaining five: macOS is the honest
cost of cross-platform packaging from a single-OS developer machine, and
the other four are distinct — INV-13 needs a built artefact and a free
port,
so it is a manual recipe rather than an absent one; the one-file uvicorn
defect is upstream, with no test surface on any host we control;
§4.11's log file has no automated launch to assert against, which is the
same gap as INV-13 one level down; and §4.1's unwritable-directory exit
has no fixture that can create one portably.

## 12. Cross-doc impact

- `pyproject.toml` — the `platformdirs` runtime dependency and the
  `bundle` optional-dependency group. **The wheel build target is
  unchanged**: defect 2 is solved by the PyInstaller `datas` entry
  (§4.4), not by teaching the wheel to ship the SPA, which INV-11
  explicitly leaves out of scope.
- `uv.lock` — regenerated for the `platformdirs` promotion (it is there
  transitively at 4.10.0; the pin is `>=4.11.0`).
- `docs/plans/mame-curator-1095-desktop-bundles.md` — the build order,
  written with this spec (`/write-spec --plan`) and cited by §10.
- `src/mame_curator/api/routes/config.py` — `_validate_paths`'
  setup-mode relaxation and the `restart_required` condition (§4.2).
- `src/mame_curator/api/routes/stubs.py` — `setup_required` on
  `SetupCheck`.
- `frontend/src/api/schemas.ts` + `frontend/src/api/types.ts` — the
  mirrored field, without which `check_api_types_sync.py` fails.
- `README.md` — download-and-run instructions for all three platforms,
  including the macOS right-click step and §4.11's log-file paths.
- `CHANGELOG.md` — user-facing entry under a dated topic subsection.
- `.github/workflows/release.yml` — three new jobs.
- `docs/standards/coding-standards.md` §8 version-break registry — only
  if a dependency has to be pinned back.
- `CLAUDE.md` § Common commands — the three new local scripts.
- `.gitignore` — `.wine-build/` (the Wine prefix `local-exe.sh`
  provisions) and `dist/`.
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
| 2 | 2026-08-04 | 3 × general-purpose | 3 | 4 | 9 | 11 | **27 verified / 1 dismissed (no TOC — the skeleton mandates none). All 27 fixed. Stopped here, not at the cap: origin split was 7 draft defects vs 16 fix collateral** — a decisive margin on the first split, which `/cold-eyes` Phase 5 answers by sweeping harder rather than dispatching a loop 3 that would generate the next batch. Dimension tally: dim 5×7, dim 2×6, dim 10×6, dim 7×4, dim 4×2, dim 15×1, dim 13×1, dim 6×1, dim 1×1, dim 11×1. Draft defects (the ones a third loop would have been for): the `publish` job takes `needs: build` and one `download-artifact` named `dist`, so three new *build* jobs would have satisfied §12 while their outputs were discarded — §4.10 now specifies the wiring; `resolve_config_path -> Path` discarded which layer won, so a conforming implementation could satisfy the signature and break INV-4 by manufacturing a config for a mistyped `--config` (now returns `tuple[Path, ConfigSource]`, the same provenance-loss trap `cli/spec.md` fixed for `_resolve_port`); `scripts/dev.sh` passes `--config` and so resolves through layer 1, not layer 2 as claimed. Collateral from loop 1's own fixes: `SetupCheck` attributed to `routes/stubs.py` when it is declared in `schemas_setup.py` (all three lanes); the `restart_required` condition tested path *inequality*, which fails on the likeliest recovery of all — the user dropping their DAT at exactly the path the starter config already names; `_validate_paths` was given a `setup_required` rule without the parameter it would need to see it. **Caught by the 4b sweep rather than a lane:** INV-15, added this loop to close a "promise with no gate" finding, itself shipped with no §11 row — the same defect one level down. Doc grew 758 → 890 lines. |
| impl | 2026-08-04 | **none — no reviewer dispatched** | — | — | — | — | **Implementation fold-back, not a review loop.** The user asked how others cross-build Windows and macOS from Linux; the answer falsified a clause this document had carried through both gate loops. §4.8 claimed `local-exe.sh` "cannot execute on this Linux box" and could get `shellcheck` only. PyInstaller's own FAQ says the opposite for Windows — cross-compilation is unsupported *and* "please use Wine for this, as PyInstaller runs fine in Wine" — and Wine 11.14 is already installed here (`wine cmd /c echo` returns, prefix reports AMD64). For macOS the same FAQ closes it outright: "Packaging macOS binaries while running under Linux is currently not possible at all", and `osxcross` does not help because PyInstaller must *run* a macOS CPython, not merely compile Darwin objects. Changed: §4.6 gained the Wine build route, §4.7 and §8 record why macOS is closed rather than deferred, §4.8's table now says two of three scripts run locally, and the `Windows .exe actually works` row stopped being **nothing** — it became INV-16, dropping the un-caught count from six to five. **This row exists because no cold reader produced it**; the amendment has had the deterministic checks but not an independent read. |

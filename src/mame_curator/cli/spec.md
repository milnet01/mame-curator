# cli/ spec

## Contract

A thin argparse-based command dispatcher that wires user-facing subcommands to the underlying library code (`parser/` for Phase 1; `filter/` for Phase 2; `copy/` for Phase 3; `api/` server-launch for Phase 4+). The CLI is an API surface in its own right: this spec pins the contract that shell scripts, CI tooling, and end users can depend on.

## Subcommand inventory

The set of subcommands grows phase-by-phase. Each subcommand's behavioral contract lives in **its host module's `spec.md`**, not here — this spec covers wiring discipline only.

| Phase | Subcommand | Status | Host module spec |
|---|---|---|---|
| 1 | `parse <DAT>` | shipped | `parser/spec.md` |
| 2 | `filter ...` | shipped | `filter/spec.md` |
| 3 | `copy ...` | shipped | `copy/spec.md` |
| 4 | `serve` (or invoked via `uvicorn`) | shipped | `api/spec.md` |
| — | `setup` | shipped | (no host module — wizard wraps `AppConfig` schema directly) |
| 7 | `refresh-inis ...` | shipped | `updates/spec.md` |
| 10 | `refresh-snaps ...` | shipped | `updates/spec.md` |

The `setup` subcommand is a small CLI-only bootstrap shipped ahead of the
P08 browser-based first-run wizard. Scope is deliberately minimal:
prompts for the four required `paths.*` fields (or accepts them via flags
for non-interactive use), validates that `source_roms` and `source_dat`
exist, then writes a starter `config.yaml` that omits the rest of the
sections so they fall back to `AppConfig` defaults. Anything richer
(filter chip lists, region priority, theme, …) is tweaked through the
in-app Settings page or by hand-editing — `setup`'s job is "get me to a
running app", not "configure every knob". The full P08 wizard (browser
flow, FS picker, INI auto-detection) replaces `setup` when it lands.

The CLI MUST refuse to run with no subcommand (argparse `required=True` on the subparsers group). Adding a subcommand is a change to `build_parser()` alone — register the subparser and attach its handler with `set_defaults(func=...)`; `run()` is never edited. See § "Dispatch pattern" for the mandatory form. Handlers live one-per-module in `cli/commands/<name>.py` (dashes in the subcommand name become underscores in the module name: `refresh-inis` → `cli/commands/refresh_inis.py`) and are re-exported from `cli/__init__.py` as `_cmd_<name>` so tests can import them from their historical location.

## Top-level flags

| Flag | Action |
|---|---|
| `-v` / `--verbose` | Toggles `logging.basicConfig` level from `INFO` (default) to `DEBUG`. |
| `--version` | Prints `mame-curator <version>` and exits 0 (uses `mame_curator.__version__`; wired in FP27). |

Subcommand-specific flags live on their respective subparsers, not here.

## Exit codes

| Code | Meaning | Source |
|---|---|---|
| `0` | Success. | Library calls returned without raising. **Not reachable from `serve`** — see the 130 row. |
| `1` | Runtime / data error — DAT corrupt, listxml unreadable, override target missing, copy `PARTIAL_FAILURE` / `FAILED`, server failed to start, etc. | A `ParserError` / `FilterError` / `CopyError` / `ConfigError` was caught at the CLI boundary, or `_cmd_copy`'s report status was non-OK and not a cancel-family, or `_cmd_serve` hit one of its five startup failures (below). |
| `2` | Usage error — unknown subcommand, missing required argument, malformed flag, etc. | argparse exits with this BEFORE `run()` is ever called. The CLI MUST NOT use `2` for runtime errors (collides with argparse's reserved meaning; breaks shell-scripting around the tool). |
| `3` | User-prompt cancel — `mame-curator copy` was cancelled via the playlist-conflict prompt (`CopyReportStatus.CANCELLED_PLAYLIST_CONFLICT`). Distinct from SIGINT-driven cancel so shell scripts that special-case 130 don't mis-attribute prompt-cancels (FP05 B10). | `_cmd_copy` |
| `130` | SIGINT-family cancel — `mame-curator copy` was cancelled by Ctrl-C / signal-driven stop (`CopyReportStatus.CANCELLED`). Conventional POSIX exit code (128 + signal 2 = 130). Also **every non-error return from `serve`** (FP28 D1). | `_cmd_copy`, `_cmd_serve` |

`serve` returns `130` on **every** path where the server actually ran,
not just an observed `KeyboardInterrupt`. The current uvicorn catches
Ctrl-C internally and returns normally, so a healthy server that the user
stopped reaches the end of `_cmd_serve` indistinguishably from a clean
shutdown — and the only way a long-running server ends today is a signal.
Reporting `0` there would claim a graceful exit the CLI cannot observe.
This deliberately supersedes `docs/specs/P04.md` § serve, which specified
`0` on clean lifespan shutdown before FP28 D1 measured the behaviour.

`_cmd_serve`'s exit-`1` paths, in the order they are checked:

1. `$PORT` set and invalid (see § "`serve` host, port and browser resolution").
2. `--config` names a file that does not exist.
3. The API extras are not installed (`ImportError` on `uvicorn` / `mame_curator.api`).
4. `config.yaml` is unreadable, is not a YAML mapping, or its `server:`
   section fails validation (`ConfigError`).
5. `create_app` raised `ConfigError` / `ParserError` / `FilterError`, or
   the bind failed (`OSError` — address in use, permission denied for a
   privileged port; `OverflowError` — a `--port` outside 0-65535).

## `serve` host, port and browser resolution

`_cmd_serve` resolves three settings, each by the same precedence rule —
**command-line flag → environment → `config.yaml` → built-in default**,
first one present wins. The `config.yaml` layer is the `server:` section,
typed by `api.schemas.ServerConfig` (`host`, `port`,
`open_browser_on_start`).

Only the `server:` block is read here, not the whole `AppConfig`: full
config validation belongs to the API lifespan, and `serve` must still be
able to start a server whose *other* sections are mid-edit. A `config.yaml`
that is unreadable, is not a YAML mapping, or whose `server:` block fails
`ServerConfig` validation exits **1** naming the file and the cause.

### Port

1. **`--port <n>`** — explicit beats implicit. Passed through as given (including `--port 0`, which uvicorn reads as "any free port"); only argparse's `type=int` constrains it. **The 1024-65535 check does NOT apply to the flag** — a caller who names a port explicitly is taken at their word (a privileged port under `sudo` is the motivating case). `$PORT` is not read at all when the flag is present, so a malformed `$PORT` alongside `--port 9000` is ignored, not an error.
2. **`$PORT`** — read only when `--port` is absent. MUST match `[0-9]+` in full and fall inside **1024-65535, inclusive**. Leading zeros are accepted (`08080` → 8080); a leading `+`, surrounding whitespace, underscores, and non-ASCII digits are NOT — `int()` and `str.isdigit()` both accept some of those, so neither is a conforming implementation on its own.
3. **`server.port`** — read when neither of the above is set. Constrained only by `ServerConfig`'s `int` type, on the same "taken at their word" grounds as (1): a hand-edited config naming port 80 is as deliberate as a typed flag.
4. **`8080`** — `ServerConfig.port`'s own default, reached when `config.yaml` has no `server:` block. `serve.DEFAULT_PORT` mirrors it as the fallback for `_resolve_port`'s unit-level callers; a test pins the two equal so they cannot drift.

A `$PORT` that is present and does not satisfy (2) MUST exit **1** with `error: PORT='<value>' is not a valid port — expected an integer in 1024-65535.` on stderr, where `<value>` is the environment value **verbatim** per § "Error messages" — rich markup in it (`[abc]`) MUST be escaped, not interpreted. It MUST NOT fall back to 8080 or to `server.port`, and MUST NOT be allowed to reach argparse (whose `invalid int value:` message omits the range) or the bind call (whose `permission denied` names neither). The check runs **before** the config-existence check, so a bad `$PORT` reports as itself rather than as a missing config.

A port that passes resolution but lies outside the OS socket range (`--port 99999`, `--port -1`) raises `OverflowError` from `socket.bind`, which is **not** an `OSError` subclass. `_cmd_serve` MUST catch it alongside `OSError` and report exit 1; letting it escape is the traceback § "Errors the CLI catches" forbids.

### Host

1. **`--host <addr>`**, else 2. **`server.host`**, else 3. **`127.0.0.1`** (`ServerConfig.host`'s default). There is deliberately no `$HOST` layer: `$PORT` has an environment layer because process supervisors and PaaS runtimes set it by convention, and nothing sets `$HOST` the same way.

### Browser

The browser opens on start iff `server.open_browser_on_start` is true AND `--no-open-browser` was not passed — the flag is a one-shot override of the config default, so `scripts/dev.sh` can suppress it without editing anyone's config.

It is opened from a **daemon thread that polls the resolved address until it accepts a TCP connection**, then calls `webbrowser.open`. A fixed delay is not a conforming implementation: uvicorn runs the application lifespan — which parses a ~48 MB DAT, tens of seconds on a cold cache — *before* it creates the listening socket, so any constant is simultaneously too short on a cold start (the browser shows "unable to connect") and too long on a warm one. Polling makes the open coincide with the port actually accepting.

The poll is **best-effort and MUST NOT be able to fail the server**: it gives up silently after 300 s, and the thread is a daemon so a failed open can never hold the process open at shutdown. When the bind host is a wildcard (`0.0.0.0`, `::`, or empty) the browser URL uses `127.0.0.1` instead — a wildcard is an address to listen on, not one every platform can connect to.

### Entry points

`run.sh` forwards `--port "${PORT}"` **only when `$PORT` is non-empty**; with `$PORT` unset it execs `mame-curator serve` with no port flag, so `server.port` is honoured. Forwarding an unconditional `--port 8080` would make rule (1) fire on every bootstrap and the config layer unreachable through the project's primary entry point.

`run.sh` still performs its own `$PORT` check before the exec. The two checks are deliberate duplicates across a language boundary: `run.sh` must reject the value before it `exec`s, and it cannot import Python to do so. Its regex carries a `{1,5}` digit bound the Python side does not need — a wider digit string makes `test -lt` error out instead of comparing, which would read as "in range". The messages are byte-identical for every value either check accepts as *reaching* the message; they can differ in quoting for values containing a quote or a newline (bash prints `PORT='<raw>'`, Python uses `repr`).

`run.sh` does **not** open the browser — `_cmd_serve` does, per § Browser above. The shell script cannot see when the socket starts accepting without polling it in bash, and duplicating the poll across the language boundary buys nothing here (unlike the `$PORT` check, which must happen before the exec).

**Coverage is `run.sh` and the direct `mame-curator serve` invocation, not every entry point.** `run.bat` (the Windows bootstrap) defaults `$PORT` the same way but forwards it as `--port`, which by rule (1) skips validation entirely — so on Windows a bad `PORT` still reaches argparse or the bind. Tracked as **mame-curator-1089**. `scripts/dev.sh` passes `--port 8080` and `--no-open-browser` explicitly, for the same reason Vite's proxy target is hardcoded.

## Output routing (per coding standards §9)

- **Success / summary output → stdout.** One `rich.console.Console()` (default `file=sys.stdout`) for the user-facing summary lines (`machines: 43579`, `winners: 2847`, `report: report.json`).
- **Errors → stderr.** A separate `rich.console.Console(stderr=True)` for any user-facing error message. Shell scripts using `2>err.log` rely on this; collapsing errors to stdout breaks the pattern.
- **Library code MUST NOT print.** Anything going to the user's terminal goes through one of the two Consoles above (or through `logging`, which the CLI configures in `main()`). `print()` outside `cli/` is a coding-standards violation.

## Error messages

Error messages must be actionable per coding standards §9. At minimum every CLI-surfaced error MUST include:

1. The category prefix (`error:` styled red via rich markup).
2. The offending input identifier — the path the user gave, the URL, the override key, the line number — verbatim, so the user can grep/replace/inspect it without reading any other text.
3. The cause sentence from the underlying typed exception (`DATError.__str__`, `FilterError.__str__`, etc., which already includes the `path=` attribute when the parser sets one).
4. (Where useful) the next user action to take. If the next action depends on configuration the user can change, name the config key.

Example (good): `error: failed to parse /mnt/Games/MAME/foo.zip — DAT zip contains zero .xml files (path=/mnt/Games/MAME/foo.zip). Re-download from <link> or set paths.source_dat in config.yaml.`

Example (bad — bare exception, no path prefix at CLI layer): `error: invalid XML`.

**Every interpolated user-supplied value MUST pass through
`rich.markup.escape`.** `rich` reads `[...]` as a style tag, so an
unescaped f-string prints `PORT='[abc]'` as `PORT=''` — silently deleting
the offending value, which is precisely the part requirement (2) exists to
guarantee. This binds the whole class, not one message: any path, port,
URL, override key or exception string reaching a `Console.print` in `cli/`
is user input for this purpose. Style markup the CLI itself writes
(`[red]error:[/red]`) is not, and is the only markup that should survive.

## Logging configuration

`logging.basicConfig(...)` is called **inside `main()`** — never at module import. Importing `mame_curator.cli` from tests, the FastAPI application factory, or a Python REPL must not mutate the global root logger. The level is set from `args.verbose`: `DEBUG` if set, else `INFO`. The format string is `"%(asctime)s %(levelname)s %(name)s: %(message)s"`.

## Dispatch pattern

Each subparser registers its handler via `set_defaults(func=_cmd_<name>)` at
the time it is added in `build_parser()`. `run()` then dispatches with a
single `return int(args.func(args))`. Adding a new subcommand is a two-line
registration in `build_parser()` (the `add_parser()` + the `set_defaults()`)
plus the new `_cmd_<name>` function — no edit to `run()` required.

This pattern is mandatory; the prior `if args.command == "parse"` chain was
acceptable for one subcommand but does not scale and was migrated in
indie-review pass 3 (Tier 1 C1). New subcommands MUST follow the
`set_defaults(func=...)` form.

**Missing-`func` discipline.** `run()` is only reached after argparse has
accepted a known subcommand (`required=True` rejects anything else with
exit code 2 *before* `run()` is called). A code path where `args.func` is
absent therefore means a subparser was added without the matching
`set_defaults(func=...)` call — a developer bug, not a user error. `run()`
MUST raise `AssertionError(...)` in that case rather than returning a
runtime-error exit code; the assertion surfaces the bug loudly in tests
and CI instead of masking it as a silent runtime failure.

## Errors the CLI catches, and the ones it deliberately does not

The CLI is the outermost user-facing layer. It catches the **typed** library
errors (`ParserError`, `FilterError`, `CopyError`, `ConfigError` and their
subclasses) plus the specific stdlib errors a bad user input can reach
(`OSError` / `OverflowError` at the bind), and converts each into a
`(stderr message, exit code 1)` pair. Every `_cmd_<name>` function wraps its
library call in a `try` that catches the exception classes its phase's
module actually raises.

It does **not** catch bare `Exception`, and a traceback from a *programmer*
error — `RuntimeError`, `AttributeError`, `TypeError` — is an intended
outcome, not a CLI bug (FP28 D2). The distinction is who can act on it:

- **User-caused failure** (bad path, bad port, corrupt DAT, missing config)
  → typed catch, one actionable line, exit 1. A traceback here is a defect:
  it buries the one sentence the user needed under a stack they cannot use.
- **Bug in our own code** → propagate. The stack *is* the actionable
  content, and it is what a bug report needs. Flattening it to
  `error: internal error` discards the only evidence of where it happened.

The practical test when adding a catch: name the exception classes the call
can raise on valid inputs. If the list is "anything", the catch is too wide.

## Out of scope

- Argument parsing for subcommand flags — that's the host module's responsibility (it adds the flags to the subparser).
- Business logic of any subcommand — the CLI dispatches to a one-line library call and prints results; logic lives in the library module.
- Web-server *lifecycle* for `serve` — `_cmd_serve` calls `uvicorn.run` itself and owns only what surrounds it: resolving host/port/browser, and mapping startup failure to an exit code. Everything from the socket inwards — application lifespan, startup/shutdown ordering, request handling — belongs to `api/` and `api/spec.md`.
- Per-phase contract details (how `parse` counts BIOSes, how `filter` orders tiebreakers, etc.) — see the host module's `spec.md`.

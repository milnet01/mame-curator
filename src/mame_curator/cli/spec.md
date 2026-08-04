# cli/ spec

- [Contract](#contract)
- [Subcommand inventory](#subcommand-inventory)
- [Top-level flags](#top-level-flags)
- [Exit codes](#exit-codes)
- [`serve` host, port and browser resolution](#serve-host-port-and-browser-resolution)
- [Output routing (per coding standards §9)](#output-routing-per-coding-standards-9)
- [Error messages](#error-messages)
- [Logging configuration](#logging-configuration)
- [Dispatch pattern](#dispatch-pattern)
- [Errors the CLI catches, and the ones it deliberately does not](#errors-the-cli-catches-and-the-ones-it-deliberately-does-not)
- [Out of scope](#out-of-scope)
- [Cold-eyes loop log](#cold-eyes-loop-log)

## Contract

A thin argparse-based command dispatcher that wires user-facing subcommands to the underlying library code (`parser/` for Phase 1; `filter/` for Phase 2; `copy/` for Phase 3; `api/` server-launch for Phase 4+). The CLI is an API surface in its own right: this spec pins the contract that shell scripts, CI tooling, and end users can depend on.

## Subcommand inventory

The set of subcommands grows phase-by-phase. Each subcommand's behavioral contract lives in **its host module's `spec.md`**, not here — this spec covers wiring discipline only.

| Phase | Subcommand | Status | Host module spec |
|---|---|---|---|
| 1 | `parse <DAT>` | shipped | `parser/spec.md` |
| 2 | `filter ...` | shipped | `filter/spec.md` |
| 3 | `copy ...` | shipped | `copy/spec.md` |
| 4 | `serve` (or invoked via `uvicorn`) | shipped; host/port/browser resolution partly **pending** — see § "`serve` host, port and browser resolution" | this spec (launch wiring) + `api/spec.md` (everything from the socket inwards) |
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
| `1` | Runtime / data error — DAT corrupt, listxml unreadable, override target missing, copy `PARTIAL_FAILURE` / `FAILED`, server failed to start, etc. | A `ParserError` / `FilterError` / `CopyError` / `ConfigError` was caught at the CLI boundary, or `_cmd_copy`'s report status was non-OK and not a cancel-family, or `_cmd_serve` hit one of its startup failures (below). |
| `2` | Usage error — unknown subcommand, missing required argument, malformed flag, etc. | argparse exits with this BEFORE `run()` is ever called. The CLI MUST NOT use `2` for runtime errors (collides with argparse's reserved meaning; breaks shell-scripting around the tool). |
| `3` | User-prompt cancel — `mame-curator copy` was cancelled via the playlist-conflict prompt (`CopyReportStatus.CANCELLED_PLAYLIST_CONFLICT`). Distinct from SIGINT-driven cancel so shell scripts that special-case 130 don't mis-attribute prompt-cancels (FP05 B10). | `_cmd_copy` |
| `130` | SIGINT-family cancel — `mame-curator copy` was cancelled by Ctrl-C / signal-driven stop (`CopyReportStatus.CANCELLED`). Conventional POSIX exit code (128 + signal 2 = 130). Also **every non-error return from `serve`** (FP28 D1). | `_cmd_copy`, `_cmd_serve` |

`serve` returns `130` on **every** path where the server actually ran,
not just an observed `KeyboardInterrupt`. The current uvicorn catches
Ctrl-C internally and returns normally, so a healthy server that the user
stopped reaches the end of `_cmd_serve` indistinguishably from a clean
shutdown — and the only way a long-running server ends today is a signal.
Reporting `0` there would claim a graceful exit the CLI cannot observe.
This deliberately supersedes `docs/specs/P04.md` § "CLI integration"
(`P04.md:854-859`), which specified `0` on clean lifespan shutdown before
FP28 D1 measured the behaviour.

**The supersession is not yet reciprocal, and this doc alone cannot make
it so.** `P04.md:856` still states `0`; `P04.md:859` still instructs that
`cli/spec.md` § "Exit codes" be updated at P04 close; and the matching
acceptance checkbox (`P04.md:885`) is still unticked. Until those three
are corrected, two contract docs assert opposite exit codes for the same
path. **This spec is canonical for `serve`'s exit code** — P04 owns the
HTTP contract, not the process's exit status — and the reciprocal P04
edit is required before either doc can be trusted on the point.

`_cmd_serve`'s exit-`1` paths, in the order they are checked:

1. `$PORT` set and invalid (see § "`serve` host, port and browser resolution").
2. `--config` names a file that does not exist.
3. The API extras are not installed (`ImportError` on `uvicorn` / `mame_curator.api`).
4. `config.yaml` is unreadable, is not a YAML mapping, or its `server:`
   section fails validation (`ConfigError`). `cli/` deliberately re-uses
   `api.errors.ConfigError` here rather than defining a `CliError` of its
   own: the failure *is* an API-config failure, the same class the API
   lifespan raises for the same file, and coding-standards §9's
   "typed exceptions per module" is about never raising bare `Exception`,
   not about forbidding a caller from catching its callee's typed error.
5. `create_app` raised `ConfigError` / `ParserError` / `FilterError`.
6. The bind failed — `OSError` (address in use, permission denied for a
   privileged port) or `OverflowError` (a **resolved** port outside
   0-65535, which can come from `--port` or from `server.port`; neither
   is range-checked, see § Port rules (1) and (3)).

## `serve` host, port and browser resolution

> **Status — this section is a forward contract, not a description.**
> Shipped today: the `--port` flag, the `$PORT` layer and the `8080`
> default (`_resolve_port`), plus the `$PORT` error message and its
> ordering. **Everything marked `PENDING` below is specified but not yet
> built** — the `config.yaml` layer, the `--no-open-browser` flag doing
> anything, the browser poll thread, the `OverflowError` catch, and
> `run.sh`'s conditional forwarding. Tracked as **mame-curator-1090**
> (the wiring) and **mame-curator-1091** (nine defects a–i). Every other
> section of this spec describes shipped behaviour; treat an unmarked
> clause anywhere else as current.

`_cmd_serve` resolves three settings. They do **not** share one precedence
rule — each is stated in full in its own subsection below, and the
differences are deliberate:

| Setting | Resolution |
|---|---|
| **Port** | `--port` → `$PORT` → `server.port` → `8080`; first present wins. |
| **Host** | `--host` → `server.host` → `127.0.0.1`. **No environment layer** — see § Host. |
| **Browser** | Not a chain at all: a config default with a one-way suppress flag. `--no-open-browser` can only turn the open *off*, never on. See § Browser. |

The `config.yaml` layer is the `server:` section, typed by
`api.schemas.ServerConfig` (`host`, `port`, `open_browser_on_start`).

**Only the `server:` block is read here, not the whole `AppConfig`** (`PENDING`):
full config validation belongs to the API lifespan, and `serve` must still
be able to start a server whose *other* sections are mid-edit.

**The block is read once, unconditionally, and before host/port/browser
are resolved** — not lazily when a layer below the flags turns out to be
needed. So a malformed `server:` block fails the command even when
`--host`, `--port` and `--no-open-browser` are all supplied and nothing
from the file would have been consumed. This is the stricter of the two
conforming readings and it is chosen on purpose: a config the user cannot
see is broken is worse than a command that refuses to start, and the lazy
alternative makes `scripts/dev.sh` (which supplies exactly those flags)
the one invocation that never notices the breakage. A `config.yaml` that
is unreadable, is not a YAML mapping, or whose `server:` block fails
`ServerConfig` validation exits **1** naming the file and the cause.

**Resolution is two-staged, and the stages straddle the exit-`1` ordering
above.** `$PORT` is validated in stage 1, before any config I/O, so a bad
`$PORT` reports as itself rather than as a missing or malformed config
(exit-`1` path 1 precedes paths 2 and 4). The `server:` layer is read in
stage 2, only after the config file is known to exist and the API extras
import has succeeded (exit-`1` paths 2 and 3).

**Ownership of the resolution is `_cmd_serve`, not `_resolve_port`.**
`_resolve_port(explicit: int | None) -> int` keeps its current signature
and its current meaning — flag → `$PORT` → `DEFAULT_PORT` — so the eleven
existing tests in `tests/cli/test_serve_port_env.py` that call
`_resolve_port(None)` and expect `8080` continue to pass unchanged.
`_cmd_serve` reads the `server:` block and applies layer (3) around it;
the config value is **not** threaded into `_resolve_port` as a second
parameter. An implementer who instead widens `_resolve_port`'s signature
will red those eleven tests, which is the signal that this clause was
skipped rather than a licence to update them.

### Port

1. **`--port <n>`** — explicit beats implicit. Passed through as given (including `--port 0`, which uvicorn reads as "any free port" — see § Browser for why that value suppresses the browser open); only argparse's `type=int` constrains it. **The 1024-65535 check does NOT apply to the flag** — a caller who names a port explicitly is taken at their word (a privileged port under `sudo` is the motivating case). `$PORT` is not read at all when the flag is present, so a malformed `$PORT` alongside `--port 9000` is ignored, not an error.
2. **`$PORT`** — read only when `--port` is absent. MUST match `[0-9]+` in full and fall inside **1024-65535, inclusive**. Leading zeros are accepted (`08080` → 8080); a leading `+`, surrounding whitespace, underscores, and non-ASCII digits are NOT — `int()` and `str.isdigit()` both accept some of those, so neither is a conforming implementation on its own.
3. **`server.port`** (`PENDING`) — read when neither of the above is set. Constrained only by `ServerConfig`'s `int` type, on the same "taken at their word" grounds as (1): a hand-edited config naming port 80 is as deliberate as a typed flag. Because it is unconstrained, it can reach the bind out of range — see exit-`1` path 6.
4. **`8080`** — `ServerConfig.port`'s own default, reached when `config.yaml` has no `server:` block **or has one that omits `port`** (every `ServerConfig` field carries its own default, so a partial block is valid). `serve.DEFAULT_PORT` mirrors it as the fallback for `_resolve_port`'s unit-level callers. **A test MUST pin `serve.DEFAULT_PORT == ServerConfig.model_fields["port"].default` so the two cannot drift** — no such test exists today, and writing it is part of mame-curator-1090.

A `$PORT` that is present and does not satisfy (2) MUST exit **1** with `error: PORT='<value>' is not a valid port — expected an integer in 1024-65535.` on stderr, where `<value>` is the environment value **verbatim** per § "Error messages" — rich markup in it (`[abc]`) MUST be escaped, not interpreted. It MUST NOT fall back to 8080 or to `server.port`, and MUST NOT be allowed to reach argparse (whose `invalid int value:` message omits the range) or the bind call (whose `permission denied` names neither). The check runs **before** the config-existence check, so a bad `$PORT` reports as itself rather than as a missing config.

A port that passes resolution but lies outside the OS socket range (`--port 99999`, `--port -1`, or a `server.port` of either) raises `OverflowError` from `socket.bind`, which is **not** an `OSError` subclass. `_cmd_serve` MUST catch it alongside `OSError` and report exit 1 (`PENDING` — the current code catches `OSError` only); letting it escape is the traceback § "Errors the CLI catches" forbids.

### Host

1. **`--host <addr>`**, else 2. **`server.host`** (`PENDING`), else 3. **`127.0.0.1`** (`ServerConfig.host`'s default). There is deliberately no `$HOST` layer: `$PORT` has an environment layer because process supervisors and PaaS runtimes set it by convention, and nothing sets `$HOST` the same way.

### Browser

**Whole subsection `PENDING`** — nothing below is implemented; `--no-open-browser` is registered on the subparser but never read, and `_cmd_serve` contains no browser code.

The browser opens on start iff `server.open_browser_on_start` is true AND `--no-open-browser` was not passed. **The flag is a one-way suppression, not a two-way override**: it can turn an open off, and there is deliberately no flag that forces one on against a config saying false. That asymmetry is what lets `scripts/dev.sh` suppress the open without editing anyone's config.

It is opened from a **daemon thread that polls the resolved address until it accepts a TCP connection**, then calls `webbrowser.open`. A fixed delay is not a conforming implementation: uvicorn runs the application lifespan — which parses a ~48 MB DAT, tens of seconds on a cold cache — *before* it creates the listening socket, so any constant is simultaneously too short on a cold start (the browser shows "unable to connect") and too long on a warm one. Polling makes the open coincide with the port actually accepting.

**Poll budget** — all three constants are module-level in `cli/commands/serve.py` so a test can monkeypatch them:

| Constant | Value | Why |
|---|---|---|
| `_BROWSER_POLL_INTERVAL_S` | `0.1` | Sleep between connect attempts. Without it "polls until it accepts" permits a tight `connect()` loop for the whole giveup window. |
| `_BROWSER_CONNECT_TIMEOUT_S` | `0.25` | Per-attempt socket timeout. Bounds one attempt against a host that blackholes rather than refusing. |
| `_BROWSER_POLL_TIMEOUT_S` | `300.0` | Total giveup. Sized for a cold-cache DAT parse with headroom. |

The poll is **best-effort and MUST NOT be able to fail the server**: on giveup it logs one `logger.debug` line naming the URL and the elapsed budget and returns — never raises, never touches the exit code — and the thread is a daemon so a failed open can never hold the process open at shutdown. The debug line exists so the giveup is observable; a genuinely silent giveup is untestable at the 300 s value.

**The browser open is skipped entirely when the resolved port is `0`.** `--port 0` means "any free port", so the port uvicorn actually binds is not knowable to the resolver — the address the poller would be given is unconnectable by construction, and it would burn the full 300 s budget before giving up. Skip, and log the same `logger.debug` line.

When the bind host is a wildcard the browser URL uses `127.0.0.1` instead — a wildcard is an address to listen on, not one every platform can connect to. Treat as wildcard: the empty string, `0.0.0.0`, and any unspecified IPv6 form (`::`, `[::]`, `::0`). The robust test is `ipaddress.ip_address(host).is_unspecified` after stripping any surrounding brackets, not a literal string list.

**Test surface** (none of these exist yet; they are mame-curator-1090's "tests to write first"): the open is skipped when `open_browser_on_start` is false; skipped when `--no-open-browser` is passed with config true; skipped when the resolved port is `0`; fires once the poll target starts accepting; gives up and logs after `_BROWSER_POLL_TIMEOUT_S` (monkeypatched small); rewrites each wildcard form to `127.0.0.1`; and a `webbrowser.open` that raises does not change the exit code.

### Entry points

`run.sh` MUST forward `--port "${PORT}"` **only when `$PORT` is non-empty**; with `$PORT` unset it must exec `mame-curator serve` with no port flag, so `server.port` is honoured. Forwarding an unconditional `--port 8080` makes rule (1) fire on every bootstrap and the config layer unreachable through the project's primary entry point.

**`PENDING` — `run.sh` does not do this today.** It currently sets `PORT=${PORT:-8080}` and then execs `--port "${PORT}"` unconditionally, so the default is baked in at the shell layer. Two changes land together: drop the `:-8080` default so an unset `$PORT` stays empty, and make the flag conditional. Two cases in `tests/tools/test_run_sh_port.py` assert `"run mame-curator serve --port 8080"` for absent and empty `$PORT`; under this contract both become `"run mame-curator serve"`, and changing them is part of the same commit.

`run.sh` still performs its own `$PORT` check before the exec. The two checks are deliberate duplicates across a language boundary: `run.sh` must reject the value before it `exec`s, and it cannot import Python to do so. Its regex carries a `{1,5}` digit bound the Python side does not need — a wider digit string makes `test -lt` error out instead of comparing, which would read as "in range". The **plain-text** messages are identical for every value either check accepts as *reaching* the message. Two axes on which the emitted bytes still differ, neither of which is a defect: the Python side prints through `rich` with `[red]error:[/red]`, so on a tty it carries ANSI styling the bash `echo` does not; and quoting differs for values containing a quote or a newline (bash prints `PORT='<raw>'`, Python uses `repr`). Assert on the text, never on the byte stream.

`run.sh` MUST NOT open the browser — `_cmd_serve` does, per § Browser above. The shell script cannot see when the socket starts accepting without polling it in bash, and duplicating the poll across the language boundary buys nothing here (unlike the `$PORT` check, which must happen before the exec).

**`PENDING` — `run.sh` does open it today**, from a backgrounded subshell that sleeps 2 s and then calls `xdg-open` / `open`. That block is **deleted** as part of mame-curator-1090, in the same commit that adds the Python poller. Adding the poller without deleting the block gives every bootstrap two browser opens, and the blind 2 s sleep is the "Unable to connect" first-load wart the poller exists to fix. `run.sh` keeps its `echo "Starting MAME Curator on ${URL}"` announce line — that is the manual fallback when no opener is available, and it is unaffected.

**Coverage is `run.sh` and the direct `mame-curator serve` invocation, not every entry point.** `run.bat` (the Windows bootstrap) defaults `$PORT` the same way but forwards it as `--port`, which by rule (1) skips validation entirely — so on Windows a bad `PORT` still reaches argparse or the bind. Tracked as **mame-curator-1089**. `scripts/dev.sh` passes `--port 8080` and `--no-open-browser` explicitly, for two different reasons: `--port 8080` because Vite proxies `/api` and `/media` to a hardcoded `http://127.0.0.1:8080`, so a developer with `PORT` exported would otherwise move the backend out from under the proxy; `--no-open-browser` because dev.sh already opens the Vite dev server at `:5173`, and a second tab on the backend port is noise.

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

## Cold-eyes loop log

| Loop | Date | Lanes | Severity (verified) | Dimensions | Outcome |
|---|---|---|---|---|---|
| 1 | 2026-08-04 | 3 × general-purpose | C 3 · H 5 · M 7 · L 8 · I 0 (23 verified / 1 unverified) | dim 2×6, dim 5×4, dim 6×5, dim 7×2, dim 15×2, dim 4×1, dim 9×1, dim 10×1, dim 11×1 | 23 fixed. Dominant defect: the whole § "`serve` host, port and browser resolution" was written in present-tense indicative while unimplemented, with no shipped-vs-pending marker — fixed with a status banner plus inline `PENDING` tags. Also fixed: the "same precedence rule" generalisation (false for host and browser), a drift test asserted to exist that does not, the unstated owner of the config layer, and the unstated read discipline for the `server:` block. 1 dismissed (`refresh-snaps` "shipped" is correct — P10 closed 2026-07-02). Surfaced, not fixed: the reciprocal `docs/specs/P04.md` exit-code edit; two test-module docstrings citing this spec's former section name. |

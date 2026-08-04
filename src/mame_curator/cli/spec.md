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

The set of subcommands grows phase-by-phase. Each subcommand's behavioral contract lives in **its host module's `spec.md`**, not here — this spec covers wiring discipline only. **Two deliberate exceptions, for two different reasons.** `setup` has no host module at all — it wraps the `AppConfig` schema directly, and its **scope** is stated below (the full flag/exit-code contract is not yet written; see the deferred list in mame-curator-1090's review notes). `serve` does have a host module, but `api/spec.md` owns everything from the socket inwards and explicitly disclaims the entrypoint, so the launch wiring lives here in § "`serve` host, port and browser resolution".

| Phase | Subcommand | Status | Host module spec |
|---|---|---|---|
| 1 | `parse <DAT>` | shipped | `parser/spec.md` |
| 2 | `filter ...` | shipped | `filter/spec.md` |
| 3 | `copy ...` | shipped | `copy/spec.md` |
| 4 | `serve` | shipped; host/port/browser resolution partly `PENDING` — see § "`serve` host, port and browser resolution" | this spec (launch wiring) + `api/spec.md` (everything from the socket inwards) |
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
4. (`PENDING`) `config.yaml` is unreadable, is not a YAML mapping, or its
   `server:` section fails validation (`ConfigError`). Because `load_app_config`
   is deliberately not used here, `cli/` opens and parses the file itself,
   which means it **raises** this error rather than merely catching one.
   The reader is `cli/commands/serve.py:_load_server_config(path: Path) ->
   ServerConfig`; it wraps `OSError` and YAML parse errors, and re-raises
   `pydantic.ValidationError`, as `api.errors.ConfigError` naming the file
   and the cause. `cli/` re-uses `api.errors.ConfigError` rather than
   defining a `CliError` of its own: the failure *is* an API-config
   failure, the same class the API lifespan raises for the same file, and
   coding-standards §9's "typed exceptions per module" bars raising bare
   `Exception` — not reusing a sibling module's typed error for the exact
   condition it names.
5. `create_app` raised `ConfigError` / `ParserError` / `FilterError`.
6. The bind failed — `OSError` (address in use, permission denied for a
   privileged port), or `OverflowError` (`PENDING`; a **resolved** port
   outside 0-65535, which can come from `--port` or from `server.port` —
   neither is range-checked, see § Port rules (1) and (3)). The `OSError`
   half ships today; the `OverflowError` half does not.

## `serve` host, port and browser resolution

> **Status — this section is a forward contract, not a description.**
> Shipped today: the `--port` flag, the `$PORT` layer and the `8080`
> default (`_resolve_port`), plus the `$PORT` error message and its
> ordering. **Everything marked `PENDING` below is specified but not yet
> built** — the `config.yaml` layer, the `--no-open-browser` flag doing
> anything, the browser poll thread, the `OverflowError` catch, and
> `run.sh`'s conditional forwarding. Tracked as **mame-curator-1090**
> (the wiring) and **mame-curator-1091** (nine defects a–i).
>
> **Pending clauses also appear outside this section**, so an unmarked
> clause is *not* a reliable shipped signal on its own. Every one of them
> carries an inline `PENDING` marker; grep for it. They currently live in
> § "Subcommand inventory" (the `serve` row), § "Exit codes" (exit-`1`
> paths 4 and 6), § "Error messages" (the class-wide escape rule) and
> § "Out of scope" (the browser half of `serve`'s wiring), as well as
> throughout this section. **`PENDING` is the signal; section boundaries
> are not.**

`_cmd_serve` resolves three settings. They do **not** share one precedence
rule — each is stated in full in its own subsection below, and the
differences are deliberate:

| Setting | Resolution |
|---|---|
| **Port** | `--port` → `$PORT` → `server.port` → `8080`; first present wins. Layers 3 and 4 are one read, not two — `ServerConfig.port` always carries a value once the block parses, so `8080` is reached as *that field's own default*, never as a separate lookup. |
| **Host** | `--host` → `server.host` → `127.0.0.1`. **No environment layer** — see § Host. |
| **Browser** | Not a chain at all: a config default with a one-way suppress flag. `--no-open-browser` can only turn the open *off*, never on. See § Browser. |

The `config.yaml` layer is the `server:` section, typed by
`api.schemas.ServerConfig` (`host`, `port`, `open_browser_on_start`).

**Only the `server:` block is read here, not the whole `AppConfig`** (`PENDING`):
full config validation belongs to the API lifespan, and `serve` must still
be able to start a server whose *other* sections are mid-edit.

**The block is read once, and unconditionally** — not lazily when a layer
below the flags turns out to be needed. So a malformed `server:` block
fails the command even when `--host`, `--port` and `--no-open-browser`
are all supplied and nothing from the file would have been consumed. This
is the stricter of the two conforming readings and it is chosen on
purpose: a config the user cannot see is broken is worse than a command
that refuses to start. Under the lazy alternative, the invocations that
supply every relevant flag are exactly the ones that never discover their
config is malformed — and those are the long-lived scripted callers
(`scripts/dev.sh` supplies `--port` and `--no-open-browser`; a supervisor
unit typically supplies all three), i.e. the callers whose config rots
longest before anyone looks at it. A `config.yaml` that is unreadable, is not a YAML
mapping, or whose `server:` block fails `ServerConfig` validation exits
**1** naming the file and the cause.

**"Unconditionally" is about the flags, not about ordering** — the read
still happens after the two checks that precede it. Resolution is
two-staged, and the stages straddle the exit-`1` ordering above:

- **Stage 1** — `$PORT` is validated before any config I/O (exit-`1` path
  1 precedes paths 2 and 4; § Port states the rationale).
- **Stage 2** — the `server:` block is read, only after the config file is
  known to exist and the API extras import has succeeded (exit-`1` paths
  2 and 3), and regardless of which flags were supplied.

**Ownership of the resolution is `_cmd_serve`, not `_resolve_port`.**
`_resolve_port(explicit: int | None) -> int` keeps its current signature
and its current meaning — flag → `$PORT` → `DEFAULT_PORT`. The config
value is **not** threaded into it as a second parameter.

`_cmd_serve` therefore **cannot infer layer (3) from `_resolve_port`'s
return value**: that function returns `8080` identically for "nothing was
set" and for an explicit `--port 8080` or `PORT=8080`, so a
`if port == DEFAULT_PORT: port = server.port` implementation would let
`server.port: 9000` silently beat an explicit `--port 8080` — a
precedence inversion no existing test catches. `_cmd_serve` MUST
re-derive presence directly instead:

**The two stages are two separate statements, and collapsing them into one
`if/else` breaks the stage-1 ordering.** The selection needs `server`, which
only exists after the stage-2 read; but the `$PORT` *raise* must happen before
any config I/O. So the presence test and the validation both run in stage 1,
and stage 2 only picks:

```python
# --- Stage 1: before any config I/O -------------------------------
# Validates $PORT and raises on an invalid one, exactly as today. The
# value is computed here; whether it WINS is decided in stage 2.
port_from_flag_or_env = _resolve_port(args.port)
use_config_port = args.port is None and not os.environ.get("PORT", "")

# ... exit-1 paths 2 and 3, then the server: block read ...

# --- Stage 2: after `server` exists -------------------------------
port = server.port if use_config_port else port_from_flag_or_env
```

`_resolve_port` is called **once**. Note that `port_from_flag_or_env` is
discarded when `use_config_port` is true — that is intentional, and it is what
lets the invalid-`$PORT` error fire before the config-existence check while
still allowing layer (3) to win when nothing was set.

Two existing tests in `tests/cli/test_serve_port_env.py` call
`_resolve_port(None)` and expect `8080` (the `$PORT`-unset and `PORT=""`
cases); they must keep passing unchanged, as must every other
`_resolve_port` caller in that module. An implementer who widens
`_resolve_port`'s signature reds all of them, which is the signal that
this clause was skipped rather than a licence to update them.

**Test surface for the config layer** (none exist yet; part of
mame-curator-1090's tests-to-write-first): a valid `server: {port: 9000}`
with no flag and no `$PORT` binds 9000; the same config with `--port 9500`
binds 9500; the same config with `PORT=9600` binds 9600.

**Two of these cases are the precedence-inversion regression and MUST NOT
be omitted: `--port 8080` against `server: {port: 9000}` binds 8080, and
`PORT=8080` against the same config binds 8080.** Only a flag or env value
*equal to `DEFAULT_PORT`* distinguishes the correct algorithm from the
`if port == DEFAULT_PORT: port = server.port` form — verified by running
both against all six cases: the 9500 and 9600 cases pass under the broken
form too, so a test surface without an 8080-vs-9000 pair ships the
inversion green.

Continuing: `server: {host: 0.0.0.0}` with no
`--host` binds the wildcard; a `server:` block omitting `port` falls to
8080; an unreadable `config.yaml`, a non-mapping `config.yaml`, and a
`server:` block failing `ServerConfig` validation each exit 1 naming the
file and the cause **even when `--host`, `--port` and
`--no-open-browser` are all supplied**; and a config whose *other*
sections are invalid still starts (only `server:` is parsed here).

### Port

1. **`--port <n>`** — explicit beats implicit. Passed through as given (including `--port 0`, which uvicorn reads as "any free port" — see § Browser for why that value suppresses the browser open); only argparse's `type=int` constrains it. **The 1024-65535 check does NOT apply to the flag** — a caller who names a port explicitly is taken at their word (a privileged port under `sudo` is the motivating case). `$PORT` is not read at all when the flag is present, so a malformed `$PORT` alongside `--port 9000` is ignored, not an error.
2. **`$PORT`** — read only when `--port` is absent. **An unset `$PORT` and a set-but-empty `PORT=""` both count as absent** and fall through to (3); this matches bash's `${PORT:-…}` and is what the two existing `_resolve_port(None) == 8080` tests pin. Otherwise it MUST match `[0-9]+` in full and fall inside **1024-65535, inclusive**. Leading zeros are accepted (`08080` → 8080); a leading `+`, surrounding whitespace, underscores, and non-ASCII digits are NOT — `int()` and `str.isdigit()` both accept some of those, so neither is a conforming implementation on its own.
3. **`server.port`** (`PENDING`) — read when neither of the above is set. Constrained only by `ServerConfig`'s `int` type, on the same "taken at their word" grounds as (1): a hand-edited config naming port 80 is as deliberate as a typed flag. Because it is unconstrained, it can reach the bind out of range — see exit-`1` path 6.
4. **`8080`** — `ServerConfig.port`'s own default, reached when `config.yaml` has no `server:` block **or has one that omits `port`** (every `ServerConfig` field carries its own default, so a partial block is valid). `serve.DEFAULT_PORT` mirrors it as the fallback for `_resolve_port`'s unit-level callers. **A test MUST pin `serve.DEFAULT_PORT == ServerConfig.model_fields["port"].default` so the two cannot drift** — no such test exists today, and writing it is part of mame-curator-1090.

A `$PORT` that is non-empty and does not satisfy (2) MUST exit **1** with `error: PORT='<value>' is not a valid port — expected an integer in 1024-65535.` on stderr, where `<value>` is the environment value **verbatim** per § "Error messages" — rich markup in it (`[abc]`) MUST be escaped, not interpreted. It MUST NOT fall back to 8080 or to `server.port`, and MUST NOT be allowed to reach argparse (whose `invalid int value:` message omits the range) or the bind call (whose `permission denied` names neither). The check runs **before** the config-existence check, so a bad `$PORT` reports as itself rather than as a missing config.

A port that passes resolution but lies outside the OS socket range (`--port 99999`, `--port -1`, or a `server.port` of either) raises `OverflowError` from `socket.bind`, which is **not** an `OSError` subclass. `_cmd_serve` MUST catch it alongside `OSError` and report exit 1 (`PENDING` — the current code catches `OSError` only); letting it escape is the traceback § "Errors the CLI catches" forbids.

### Host

1. **`--host <addr>`**, else 2. **`server.host`** (`PENDING`), else 3. **`127.0.0.1`** (`ServerConfig.host`'s default). **`--host` counts as present only when non-empty** — `--host ""` is treated as absent and falls through to (2), matching the current `args.host or "127.0.0.1"`. An empty bind host therefore reaches uvicorn only from `server.host: ""`, which is the one route by which § Browser's empty-string wildcard case arises. There is deliberately no `$HOST` layer: `$PORT` has an environment layer because process supervisors and PaaS runtimes set it by convention, and nothing sets `$HOST` the same way.

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

The poll is **best-effort and MUST NOT be able to fail the server**: it returns rather than raising on every failure path, never touches the exit code, and the thread is a daemon so a failed open can never hold the process open at shutdown.

**Each non-open outcome logs its own distinguishable line**, so a test can tell them apart and `-v` shows the user which happened. All are `logger.debug` — a browser that did not open is not a malfunction, and § "Logging configuration" pins the default level to `INFO`, so **these lines are observable under `-v` and in caplog, not on a default run**. That is the intended visibility: the URL is already on stdout for the user to click.

| Outcome | Line |
|---|---|
| Poll exhausted `_BROWSER_POLL_TIMEOUT_S` | `browser open gave up: <url> not accepting after <n>s` |
| Resolved port is `0` | `browser open skipped: port 0 (bound port not knowable before listen)` |
| `open_browser_on_start` false, or `--no-open-browser` | `browser open skipped: disabled by <config|flag>` |
| `webbrowser.open` raised | `browser open failed: <exc>` |

**The browser open is skipped entirely when the resolved port is `0`.** `--port 0` means "any free port", so the port uvicorn actually binds is not knowable to the resolver — the address the poller would be given is unconnectable by construction, and it would burn the full 300 s budget before giving up.

When the bind host is a wildcard the browser URL uses `127.0.0.1` instead — a wildcard is an address to listen on, not one every platform can connect to. Wildcards are the empty string, `0.0.0.0`, and every unspecified IPv6 form (`::`, `[::]`, `::0`).

**A bare `ipaddress.ip_address(host).is_unspecified` is NOT a conforming test** — it raises `ValueError` on the empty string, which is itself one of the wildcard forms, and on any hostname (`--host localhost`, `--host myhost.local`), for which the spec's answer is "not a wildcard". The predicate is:

```python
def _is_wildcard(host: str) -> bool:
    if not host:                       # empty string IS a wildcard
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_unspecified
    except ValueError:                 # a hostname, not a literal address
        return False                   # use it as given
```

**Test surface** (none of these exist yet; they are mame-curator-1090's "tests to write first"): the open is skipped when `open_browser_on_start` is false; skipped when `--no-open-browser` is passed with config true; skipped when the resolved port is `0`; fires once the poll target starts accepting; gives up after `_BROWSER_POLL_TIMEOUT_S` (monkeypatched small); each of the four outcomes above emits its own distinct line; `_is_wildcard` returns true for `""`, `0.0.0.0`, `::`, `[::]`, `::0` and false for `127.0.0.1`, `192.168.1.5` and `localhost`; and a `webbrowser.open` that raises does not change the exit code.

**One existing-test change lands with this**: `_serve_args` in `tests/cli/test_serve_port_env.py` builds `argparse.Namespace(config=…, host=…, port=…)` with **no `no_open_browser` attribute**, so the first `args.no_open_browser` read raises `AttributeError` across all four `_cmd_serve` end-to-end tests. Give the helper a `no_open_browser: bool = False` default in the same commit; do not paper over it with `getattr(args, …, False)` in production code, which would hide a genuinely missing argparse registration.

### Entry points

`run.sh` MUST forward `--port "${PORT}"` **only when `$PORT` is non-empty**; with `$PORT` unset it must exec `mame-curator serve` with no port flag, so `server.port` is honoured. Forwarding an unconditional `--port 8080` makes rule (1) fire on every bootstrap and the config layer unreachable through the project's primary entry point.

**`PENDING` — `run.sh` does not do this today.** It currently sets `PORT=${PORT:-8080}` and then execs `--port "${PORT}"` unconditionally, so the default is baked in at the shell layer. **Three changes land together, and omitting the third breaks the default bootstrap:**

1. Drop the `:-8080` default, so an unset `$PORT` stays empty.
2. **Guard the `$PORT` validation block on `[ -n "${PORT}" ]`.** The existing check is `if ! [[ "${PORT}" =~ ^[0-9]{1,5}$ ]] || …`. Today it never sees an empty string, because `PORT=${PORT:-8080}` runs first — but **once change (1) drops that default, an empty `$PORT` reaches the regex and fails it** (verified in bash: the block then exits 1 with `error: PORT='' is not a valid port`). Left unguarded, change (1) alone makes *every* no-`$PORT` launch abort. An empty `$PORT` must skip validation entirely, exactly as it now falls through to layer (3) on the Python side.
3. Make the `--port` flag conditional on the same non-empty test.

Two cases in `tests/tools/test_run_sh_port.py` assert `"run mame-curator serve --port 8080"` for absent and empty `$PORT`; under this contract both become `"run mame-curator serve"` **with a zero exit code**, and changing them is part of the same commit. Assert the exit code as well as the argv — a `--port`-less serve line and an aborted script are otherwise indistinguishable in the `serve_argv` helper, which returns `None` for both.

`run.sh` still performs its own `$PORT` check before the exec. The two checks are deliberate duplicates across a language boundary: `run.sh` must reject the value before it `exec`s, and it cannot import Python to do so. Its regex carries a `{1,5}` digit bound the Python side does not need — a wider digit string makes `test -lt` error out instead of comparing, which would read as "in range". The **plain-text** messages are identical for every value either check accepts as *reaching* the message. Two axes on which the emitted bytes still differ, neither of which is a defect: the Python side prints through `rich` with `[red]error:[/red]`, so on a tty it carries ANSI styling the bash `echo` does not; and quoting differs for values containing a quote or a newline (bash prints `PORT='<raw>'`, Python uses `repr`). Assert on the text, never on the byte stream.

`run.sh` MUST NOT open the browser — `_cmd_serve` does, per § Browser above. The shell script cannot see when the socket starts accepting without polling it in bash, and duplicating the poll across the language boundary buys nothing here (unlike the `$PORT` check, which must happen before the exec).

**`PENDING` — `run.sh` does open it today**, from a backgrounded subshell that sleeps 2 s and then calls `xdg-open` / `open`. That block is **deleted** as part of mame-curator-1090, in the same commit that adds the Python poller. Adding the poller without deleting the block gives every bootstrap two browser opens, and the blind 2 s sleep is the "Unable to connect" first-load wart the poller exists to fix. `run.sh` keeps an announce line — it is the manual fallback when no opener is available — but **the line does change, because `URL` is built from `$PORT`.** With the `:-8080` default dropped and `$PORT` unset, `URL="http://127.0.0.1:${PORT}/"` renders as `http://127.0.0.1:/`, and the real port is not knowable to the shell at all once it can come from `server.port`. So:

- **`$PORT` non-empty** — announce as today, `http://127.0.0.1:${PORT}/`. The shell knows the port because it is the one being forwarded.
- **`$PORT` empty** — announce without a URL (`Starting MAME Curator — the address will be printed once the server binds`). `serve` owns the address in this case, and uvicorn already logs `Uvicorn running on http://<host>:<port>` on bind.

Pin both cases in `tests/tools/test_run_sh_port.py`; the existing `PORT=5999` case already asserts `http://127.0.0.1:5999/` is announced, and the empty case must assert that no `http://127.0.0.1:/` appears.

**Coverage is `run.sh` and the direct `mame-curator serve` invocation, not every entry point.** `run.bat` (the Windows bootstrap) defaults `$PORT` the same way but forwards it as `--port`, which by rule (1) skips validation entirely — so on Windows a bad `PORT` still reaches argparse or the bind. Tracked as **mame-curator-1089**. **That item has a second half once mame-curator-1090 lands:** unconditional `--port` forwarding also makes layer (3) unreachable, so `server.port` would be honoured on Linux/macOS and silently ignored on Windows. `run.bat` needs the same three changes `run.sh` gets, or the two bootstraps diverge on which config keys work. `scripts/dev.sh` passes `--port 8080` and `--no-open-browser` explicitly, for two different reasons: `--port 8080` because Vite proxies `/api` and `/media` to a hardcoded `http://127.0.0.1:8080`, so a developer with `PORT` exported would otherwise move the backend out from under the proxy; `--no-open-browser` because dev.sh already opens the Vite dev server at `:5173`, and a second tab on the backend port is noise.

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

**`PENDING` — the class-wide rule is not yet enforced class-wide.** Today
only `_cmd_serve`'s `$PORT` message escapes. Four other `Console.print`
sites in the same function interpolate unescaped: the config-not-found
message (`{args.config!r}` — a user-supplied path, the likeliest of the
four to contain brackets), the missing-extras message (`{exc}`), the
`create_app` failure (`{exc}`), and the bind failure
(`{host}:{port}: {exc}`). Bringing them into line is part of
mame-curator-1091. The rule above is the contract; this note records that
the code has not caught up, so a reader does not mistake the gap for a
deliberate exemption.

## Logging configuration

`logging.basicConfig(...)` is called **inside `main()`** — never at module import. Importing `mame_curator.cli` from tests, the FastAPI application factory, or a Python REPL must not mutate the global root logger. The level is set from `args.verbose`: `DEBUG` if set, else `INFO`. The format string is `"%(asctime)s %(levelname)s %(name)s: %(message)s"`.

## Dispatch pattern

Each subparser registers its handler via `set_defaults(func=_cmd_<name>)` at
the time it is added in `build_parser()`. `run()` then dispatches with a
single `return int(args.func(args))`, after the missing-`func` guard below.
Adding a new subcommand is a two-line
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
subclasses) plus the specific stdlib errors a bad user input or a missing
install can reach: `ValueError` from `_resolve_port` (an invalid `$PORT`),
`ImportError` (the API extras are absent), and `OSError` — plus
`OverflowError` (`PENDING`) — at the bind. Each converts into a
`(stderr message, exit code 1)` pair. `KeyboardInterrupt` is also caught
at `_cmd_serve`, but maps to 130 rather than 1 and so is not part of this
class. Every `_cmd_<name>` function wraps its
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
- Web-server *lifecycle* for `serve` — `_cmd_serve` calls `uvicorn.run` itself and owns only what surrounds it: resolving host/port/browser (the browser half `PENDING`), and mapping startup failure to an exit code. Everything from the socket inwards — application lifespan, startup/shutdown ordering, request handling — belongs to `api/` and `api/spec.md`.
- Per-phase contract details (how `parse` counts BIOSes, how `filter` orders tiebreakers, etc.) — see the host module's `spec.md`.

## Cold-eyes loop log

| Loop | Date | Lanes | Severity (verified) | Dimensions | Outcome |
|---|---|---|---|---|---|
| 1 | 2026-08-04 | 3 × general-purpose | C 3 · H 5 · M 7 · L 8 · I 0 (23 verified / 1 unverified) | dim 2×6, dim 5×4, dim 6×5, dim 7×2, dim 15×2, dim 4×1, dim 9×1, dim 10×1, dim 11×1 | 23 fixed. Dominant defect: the whole § "`serve` host, port and browser resolution" was written in present-tense indicative while unimplemented, with no shipped-vs-pending marker — fixed with a status banner plus inline `PENDING` tags. Also fixed: the "same precedence rule" generalisation (false for host and browser), a drift test asserted to exist that does not, the unstated owner of the config layer, and the unstated read discipline for the `server:` block. 1 dismissed (`refresh-snaps` "shipped" is correct — P10 closed 2026-07-02). Surfaced, not fixed: the reciprocal `docs/specs/P04.md` exit-code edit; two test-module docstrings citing this spec's former section name. |
| 3 | 2026-08-04 | 3 × general-purpose | C 3 · H 4 · M 8 · L 9 · I 0 (24 verified / 0 unverified) | dim 7×6, dim 5×5, dim 4×5, dim 2×4, dim 15×2, dim 6×1, dim 10×1, dim 11×1, dim 1×1 | **Converged-by-cap. 11 fixed, 13 filed as mame-curator-1094.** Origin split: 12 fix collateral vs 8 draft defects — with loop 2's 14-vs-4 that is the "collateral outnumbers draft defects two loops running" trigger, so this run stops rather than looping a fourth time. Fixed (all build-changing): loop 2's normative snippet validated `$PORT` *after* the config read and would have redded the pinned ordering test — restructured into two statements and **verified by executing both forms across all six precedence cases**; the same run proved loop 2's test surface could not catch the precedence inversion it named (the naive `port == DEFAULT_PORT` form passes the 9500 and 9600 cases, and only an 8080-vs-9000 pair reds it). Also fixed: the "one other section carries pending clauses" rule was false — replaced with "grep for `PENDING`"; the `server:` reader was never named though the design requires `cli/` to *raise* `ConfigError`, not just catch it; the class-wide escape rule is violated by four shipped call sites; the dev.sh rationale rested on a flag it does not pass. Remaining tail is MEDIUM/LOW and filed, not lost. |
| 2 | 2026-08-04 | 3 × general-purpose | C 5 · H 3 · M 7 · L 3 · I 0 (18 verified / 0 unverified) | dim 5×5, dim 2×4, dim 6×4, dim 7×3, dim 15×3, dim 10×2, dim 4×2, dim 1×1 | 18 fixed, 1 dismissed. **14 of 18 were loop-1 fix collateral, 4 draft defects** — loop 1 answered prose defects with substantive new contract text, and the new text carried its own. Four were verified by execution rather than reading: `ipaddress.ip_address("")` and `("localhost")` both raise, so the prescribed wildcard predicate crashed on two inputs the same sentence mandated handling; bash rejects an empty `$PORT`, so loop 1's two-step `run.sh` change list would have broken the default bootstrap; only 2 tests (not the stated eleven) call `_resolve_port(None)` expecting 8080; bash and Python agree on leading zeros, confirming the message-parity claim. Both prescribed code blocks now parse, and `_is_wildcard` was run against its own stated test surface. Draft defects fixed: the `setup`/`serve` carve-out to the host-module rule (missed in loop 1), `run.bat`'s second-half divergence under 1090, `PORT=""` presence, the `run()` guard. Dismissed: moving the exit-`1` list out of § "Exit codes" — a structural tidy that would strand § Port's "path 6" cross-references. |

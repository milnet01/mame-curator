# cli/ spec

## Contract

A thin argparse-based command dispatcher that wires user-facing subcommands to the underlying library code (`parser/` for Phase 1; `filter/` for Phase 2; `copy/` for Phase 3; `api/` server-launch for Phase 4+). The CLI is an API surface in its own right: this spec pins the contract that shell scripts, CI tooling, and end users can depend on.

## Subcommand inventory

The set of subcommands grows phase-by-phase. Each subcommand's behavioral contract lives in **its host module's `spec.md`**, not here — this spec covers wiring discipline only.

| Phase | Subcommand | Status | Host module spec |
|---|---|---|---|
| 1 | `parse <DAT>` | shipped | `parser/spec.md` |
| 2 | `filter ...` | shipped | `filter/spec.md` |
| 3 | `copy ...` | planned | `copy/spec.md` |
| 4 | `serve` (or invoked via `uvicorn`) | planned | `api/spec.md` |

The CLI MUST refuse to run with no subcommand (argparse `required=True` on the subparsers group). Adding a subcommand requires both registering it in `build_parser()` AND adding a dispatch branch in `run()` — the dispatch branch calls a handler defined in `cli/_cmd_<name>.py` (or, for tiny phase-1 handlers, inline in `__init__.py`).

## Top-level flags

| Flag | Action |
|---|---|
| `-v` / `--verbose` | Toggles `logging.basicConfig` level from `INFO` (default) to `DEBUG`. |
| `--version` | (Future, not yet implemented.) Prints `mame_curator.__version__` and exits 0. |

Subcommand-specific flags live on their respective subparsers, not here.

## Exit codes

| Code | Meaning | Source |
|---|---|---|
| `0` | Success. | Library calls returned without raising. |
| `1` | Runtime / data error — DAT corrupt, listxml unreadable, override target missing, etc. | A `ParserError` / `FilterError` / `CopyError` was caught at the CLI boundary. |
| `2` | Usage error — unknown subcommand, missing required argument, malformed flag, etc. | argparse exits with this BEFORE `run()` is ever called. The CLI MUST NOT use `2` for runtime errors (collides with argparse's reserved meaning; breaks shell-scripting around the tool). |

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

## Errors the CLI catches but never raises

The CLI is the outermost user-facing layer. It catches typed library errors (`ParserError` and its subclasses; future `FilterError`, `CopyError`) and converts them into `(stderr message, exit code 1)` tuples. It **never** lets a Python traceback reach the user — a traceback in the user's terminal is a CLI bug, not an acceptable failure mode.

What this means in practice: every `_cmd_<name>` function wraps its library call in a `try` block that catches the exception classes from that phase's module, and the bare-`Exception` catch at the top of `run()` (when added) converts unexpected errors to `error: internal error: <type>: <msg>` plus a "report this at <issue tracker>" pointer. A traceback only appears with `--debug` (Phase 7+ enhancement, not yet implemented).

## Out of scope

- Argument parsing for subcommand flags — that's the host module's responsibility (it adds the flags to the subparser).
- Business logic of any subcommand — the CLI dispatches to a one-line library call and prints results; logic lives in the library module.
- Web-server lifecycle for Phase 4 `serve` — `setup/wizard.py` and `main.py` orchestrate uvicorn lifespan; the CLI just kicks it off.
- Per-phase contract details (how `parse` counts BIOSes, how `filter` orders tiebreakers, etc.) — see the host module's `spec.md`.

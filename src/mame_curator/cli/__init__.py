"""mame-curator command-line interface.

Subcommands (added incrementally as phases land):
    parse <dat-path>   — parse the DAT and print summary stats (Phase 1)
    filter <args>      — run the filter pipeline and write a report (Phase 2)
    copy <args>        — copy winners + BIOS deps and write mame.lpl (Phase 3)
    serve <args>       — run the HTTP API server (Phase 4)
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from rich.console import Console

from mame_curator._atomic import atomic_write_text
from mame_curator.copy import (
    ConflictStrategy,
    CopyError,
    CopyPlan,
    CopyReportStatus,
    purge_recycle,
    run_copy,
)
from mame_curator.filter import (
    FilterConfig,
    FilterContext,
    FilterError,
    Overrides,
    Sessions,
    load_overrides,
    load_sessions,
    run_filter,
)
from mame_curator.parser import (
    ParserError,
    parse_bestgames,
    parse_catver,
    parse_dat,
    parse_languages,
    parse_mature,
)
from mame_curator.parser.listxml import (
    parse_listxml_bios_chain,
    parse_listxml_cloneof,
    parse_listxml_disks,
)

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level argument parser with all subcommands.

    Each subparser registers its handler via `set_defaults(func=...)` per
    cli/spec.md §"Dispatch pattern" — `run()` then dispatches with
    `args.func(args)` instead of an if/elif chain.
    """
    parser = argparse.ArgumentParser(prog="mame-curator", description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true", help="enable DEBUG-level logging")
    sub = parser.add_subparsers(dest="command", required=True)

    parse_cmd = sub.add_parser("parse", help="Parse a DAT and print summary stats")
    parse_cmd.add_argument("dat", type=Path, help="Path to DAT XML or .zip")
    parse_cmd.set_defaults(func=_cmd_parse)

    filt = sub.add_parser("filter", help="Run the filter pipeline and write a JSON report")
    filt.add_argument("--dat", type=Path, required=True, help="Path to DAT XML or .zip")
    filt.add_argument("--listxml", type=Path, required=True, help="Official MAME -listxml output")
    filt.add_argument("--catver", type=Path, required=True, help="progettoSnaps catver.ini")
    filt.add_argument("--languages", type=Path, required=True, help="progettoSnaps languages.ini")
    filt.add_argument("--bestgames", type=Path, required=True, help="progettoSnaps bestgames.ini")
    filt.add_argument("--mature", type=Path, default=None, help="progettoSnaps mature.ini")
    filt.add_argument(
        "--overrides", type=Path, default=None, help="overrides.yaml (parent → winner pinning)"
    )
    filt.add_argument(
        "--sessions", type=Path, default=None, help="sessions.yaml (continuation-mode focus)"
    )
    filt.add_argument("--out", type=Path, required=True, help="Path to write report JSON")
    filt.set_defaults(func=_cmd_filter)

    cp = sub.add_parser("copy", help="Copy winners + BIOS deps and write mame.lpl")
    cp_mode = cp.add_mutually_exclusive_group(required=True)
    cp_mode.add_argument("--dry-run", action="store_true", help="Preview without writing")
    cp_mode.add_argument("--apply", action="store_true", help="Execute the copy")
    cp.add_argument("--dat", type=Path, required=True, help="Path to DAT XML or .zip")
    cp.add_argument("--listxml", type=Path, required=True, help="Official MAME -listxml output")
    cp.add_argument(
        "--filter-report", type=Path, required=True, help="Path to a Phase-2 filter JSON report"
    )
    cp.add_argument("--source", type=Path, required=True, help="Source ROM directory")
    cp.add_argument("--dest", type=Path, required=True, help="Destination ROM directory")
    cp.add_argument(
        "--conflict",
        choices=("append", "overwrite", "cancel"),
        default="cancel",
        help="Strategy when mame.lpl already exists",
    )
    cp.add_argument(
        "--delete-existing-zips",
        action="store_true",
        help="With --conflict overwrite, recycle existing dest zips",
    )
    cp.add_argument(
        "--purge-recycle",
        action="store_true",
        help="One-shot: delete recycle entries older than 30 days; exits without copying",
    )
    cp.set_defaults(func=_cmd_copy)

    sub_serve = sub.add_parser("serve", help="Run the HTTP API server.")
    sub_serve.add_argument("--host", default=None, help="Bind address (overrides config).")
    sub_serve.add_argument("--port", type=int, default=None, help="Bind port (overrides config).")
    sub_serve.add_argument(
        "--config", type=Path, default=Path("config.yaml"), help="Config file path."
    )
    sub_serve.add_argument(
        "--no-open-browser", action="store_true", help="Skip auto-opening the browser."
    )
    sub_serve.set_defaults(func=_cmd_serve)

    return parser


def run(args: argparse.Namespace) -> int:
    """Dispatch to the chosen subcommand. Returns process exit code.

    Per cli/spec.md §"Dispatch pattern": argparse's `set_defaults(func=...)`
    on each subparser populates `args.func` with the handler; this `run()`
    is a one-line dispatcher. A missing `func` means the developer added a
    subparser without the `set_defaults` call.
    """
    if not hasattr(args, "func"):
        raise AssertionError(
            f"subcommand {args.command!r} did not register a func via set_defaults(); "
            f"check build_parser()"
        )
    return int(args.func(args))


def _cmd_parse(args: argparse.Namespace) -> int:
    console = Console()
    err_console = Console(stderr=True, soft_wrap=True)
    try:
        machines = parse_dat(args.dat)
    except ParserError as exc:
        # FP07 A1: quote args.dat via repr() so a control byte in a
        # user-controlled path can't break the single-line error contract.
        err_console.print(f"[red]error:[/red] failed to parse {args.dat!r}: {exc}")
        return 1

    parents = sum(1 for m in machines.values() if m.cloneof is None)
    clones = sum(1 for m in machines.values() if m.cloneof is not None)
    bios = sum(1 for m in machines.values() if m.is_bios)
    devices = sum(1 for m in machines.values() if m.is_device)
    mechanical = sum(1 for m in machines.values() if m.is_mechanical)

    console.print(f"DAT: {args.dat}")
    console.print(f"  machines: {len(machines)}")
    console.print(f"  parents: {parents}")
    console.print(f"  clones: {clones}")
    console.print(f"  bios: {bios}")
    console.print(f"  devices: {devices}")
    console.print(f"  mechanical: {mechanical}")
    return 0


def _cmd_filter(args: argparse.Namespace) -> int:
    console = Console()
    err_console = Console(stderr=True, soft_wrap=True)
    try:
        machines = parse_dat(args.dat)
        mature = frozenset(parse_mature(args.mature)) if args.mature else frozenset()
        ctx = FilterContext(
            category=parse_catver(args.catver),
            languages={k: tuple(v) for k, v in parse_languages(args.languages).items()},
            bestgames_tier=parse_bestgames(args.bestgames),
            cloneof_map=parse_listxml_cloneof(args.listxml),
            chd_required=frozenset(parse_listxml_disks(args.listxml)),
            mature=mature,
        )
        # Unset --overrides / --sessions → empty in-memory model. The pre-DS01
        # sentinel-path antipattern (`Path("/nonexistent/overrides.yaml")`)
        # was brittle (someone could `mkdir /nonexistent`) and failed the
        # six-month test. Direct construction is the contract (DS01 C8).
        overrides = load_overrides(args.overrides) if args.overrides else Overrides()
        sessions = load_sessions(args.sessions) if args.sessions else Sessions()
    except (ParserError, FilterError) as exc:
        err_console.print(f"[red]error:[/red] failed to load inputs: {exc}")
        return 1
    except OSError as exc:
        # FP05 B8: defense-in-depth. The loaders above already wrap OSError
        # into typed errors (ParserError / FilterError); the residual surface
        # for raw OSError reaching this scope is narrow (TOCTOU between
        # `path.exists()` and read). Spec § "Errors the CLI catches but
        # never raises" requires exit-1 with a labelled error line.
        err_console.print(f"[red]error:[/red] cannot read input: {exc}")
        return 1

    result = run_filter(machines, ctx, FilterConfig(), overrides, sessions)
    # FP05 C2: atomic write via shared `atomic_write_text` helper (was an
    # inline tmp + os.replace block; the helper handles `try/finally`,
    # unique tmp-name via `tempfile.NamedTemporaryFile`, and OSError
    # propagation including EXDEV). FP05 closing-review R5: catch the
    # OSError surface so a cross-FS rename / perm-denied / disk-full
    # doesn't leak a traceback to the user.
    try:
        atomic_write_text(args.out, result.model_dump_json(indent=2) + "\n")
    except OSError as exc:
        # FP07 A2: quote args.out via repr() — same threat model as A1.
        err_console.print(f"[red]error:[/red] failed to write {args.out!r}: {exc}")
        return 1

    console.print(f"  winners: {len(result.winners)}")
    console.print(f"  dropped: {len(result.dropped)}")
    console.print(f"  contested groups: {len(result.contested_groups)}")
    console.print(f"  warnings: {len(result.warnings)}")
    console.print(f"  report: {args.out}")
    return 0


def _cmd_copy(args: argparse.Namespace) -> int:
    console = Console()
    err_console = Console(stderr=True, soft_wrap=True)

    if args.purge_recycle:
        # FP06 A1: the --purge-recycle short-circuit returns before B9's try
        # block runs, so OSError from purge_recycle (perm-denied recycle root,
        # broken symlink, NFS hiccup) was reaching the user as a traceback.
        # Flat outer try mirrors B9's pattern; B9's try is reserved for
        # parser-input loading and binds variables consumed downstream.
        try:
            dirs, freed = purge_recycle()
        except OSError as exc:
            err_console.print(f"[red]error:[/red] failed to purge recycle: {exc}")
            return 1
        console.print(f"  recycle purged: {dirs} directories, {freed} bytes freed")
        return 0

    try:
        machines = parse_dat(args.dat)
        bios_chain = parse_listxml_bios_chain(args.listxml)
        chd_required = frozenset(parse_listxml_disks(args.listxml))
    except ParserError as exc:
        err_console.print(f"[red]error:[/red] failed to load inputs: {exc}")
        return 1
    except OSError as exc:
        # FP05 B9: mirror DS01 C6 / FP05 B8 into _cmd_copy. Defense-in-depth
        # against bare OSError surfacing from `--dat` / `--listxml` paths
        # that point at directories or unreadable files. The parsers wrap
        # most OSError cases, but the TOCTOU between `.exists()` and read
        # can still surface a bare exception.
        err_console.print(f"[red]error:[/red] cannot read input: {exc}")
        return 1

    try:
        report_data = json.loads(args.filter_report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        # FP07 A3: quote args.filter_report via repr() — same threat model.
        err_console.print(
            f"[red]error:[/red] failed to read filter report {args.filter_report!r}: {exc}"
        )
        return 1

    winners = tuple(report_data.get("winners", ()))
    plan = CopyPlan(
        winners=winners,
        machines={short: machines[short] for short in winners if short in machines},
        bios_chain=bios_chain,
        chd_required=chd_required,
        source_dir=args.source,
        dest_dir=args.dest,
        conflict_strategy=ConflictStrategy(args.conflict.upper()),
        delete_existing_zips=args.delete_existing_zips,
        dry_run=args.dry_run,
    )

    try:
        report = run_copy(plan)
    except CopyError as exc:
        err_console.print(f"[red]error:[/red] copy failed: {exc}")
        return 1

    console.print(f"  status: {report.status.value}")
    console.print(f"  winners: {report.plan_summary.winners_count}")
    console.print(f"  bios deps: {len(report.bios_included)}")
    console.print(f"  succeeded: {len(report.succeeded)}")
    console.print(f"  skipped: {len(report.skipped)}")
    console.print(f"  failed: {len(report.failed)}")
    console.print(f"  recycled: {len(report.recycled)}")
    console.print(f"  bytes copied: {report.bytes_copied}")
    if args.dry_run:
        console.print("  [yellow](dry-run — no files written)[/yellow]")

    # FP05 B10: distinct exit codes per CopyReportStatus.
    # OK: 0 (clean run).
    # CANCELLED (SIGINT family — user-initiated stop): 130 = 128 + signal 2.
    # CANCELLED_PLAYLIST_CONFLICT (deliberate user-prompt-cancel — distinct
    #   from signal-driven, so shell scripts that special-case 130 don't
    #   mis-attribute prompt-cancels): 3.
    # PARTIAL_FAILURE / FAILED: 1 (generic runtime error, per cli/spec.md).
    if report.status is CopyReportStatus.OK:
        return 0
    if report.status is CopyReportStatus.CANCELLED:
        return 130
    if report.status is CopyReportStatus.CANCELLED_PLAYLIST_CONFLICT:
        return 3
    return 1


def _cmd_serve(args: argparse.Namespace) -> int:
    err_console = Console(stderr=True, soft_wrap=True)
    if not args.config.exists():
        err_console.print(
            f"[red]error:[/red] config file not found: {args.config!r} — "
            "run `mame-curator setup` first"
        )
        return 1

    try:
        import uvicorn

        from mame_curator.api import create_app
    except ImportError as exc:
        err_console.print(
            f"[red]error:[/red] API extras not installed ({exc}); "
            "install with `pip install mame-curator[api]`"
        )
        return 1

    try:
        app = create_app(args.config)
    except Exception as exc:
        err_console.print(f"[red]error:[/red] failed to create app: {exc}")
        return 1

    host = args.host or "127.0.0.1"
    port = args.port or 8080
    try:
        uvicorn.run(app, host=host, port=port, log_level="info")
    except OSError as exc:
        err_console.print(f"[red]error:[/red] failed to bind {host}:{port}: {exc}")
        return 1
    return 0

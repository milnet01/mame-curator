"""mame-curator command-line interface.

Subcommands (added incrementally as phases land):
    parse <dat-path>   — parse the DAT and print summary stats (Phase 1)
    filter <args>      — run the filter pipeline and write a report (Phase 2)
    copy <args>        — copy winners + BIOS deps and write mame.lpl (Phase 3)
"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import os
from pathlib import Path

from rich.console import Console

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
        err_console.print(f"[red]error:[/red] failed to parse {args.dat}: {exc}")
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
        # CLI input paths can point at directories, dangling symlinks, EIO,
        # perm-denied — all OSError. cli/spec.md § "Errors the CLI catches but
        # never raises" requires exit-1 with a labelled error line, not a raw
        # traceback (DS01 C6).
        err_console.print(f"[red]error:[/red] cannot read input: {exc}")
        return 1

    result = run_filter(machines, ctx, FilterConfig(), overrides, sessions)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # Atomic write: prevents half-written report.json on Ctrl-C / OOM
    # mid-write (DS01 C7). Mirrors copy/executor.py:60-72's `.tmp` + `os.replace`
    # pattern, including the try/finally cleanup so a failed `write_text`
    # doesn't leave a stale `.tmp` for the next run to overwrite or carry
    # forward (DS01 closing-review fix).
    tmp = args.out.with_suffix(args.out.suffix + ".tmp")
    completed = False
    try:
        tmp.write_text(result.model_dump_json(indent=2) + "\n")
        os.replace(tmp, args.out)
        completed = True
    finally:
        if not completed:
            with contextlib.suppress(OSError):
                tmp.unlink(missing_ok=True)

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
        dirs, freed = purge_recycle()
        console.print(f"  recycle purged: {dirs} directories, {freed} bytes freed")
        return 0

    try:
        machines = parse_dat(args.dat)
        bios_chain = parse_listxml_bios_chain(args.listxml)
        chd_required = frozenset(parse_listxml_disks(args.listxml))
    except ParserError as exc:
        err_console.print(f"[red]error:[/red] failed to load inputs: {exc}")
        return 1

    try:
        report_data = json.loads(args.filter_report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        err_console.print(
            f"[red]error:[/red] failed to read filter report {args.filter_report}: {exc}"
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

    if report.status in (CopyReportStatus.OK,):
        return 0
    return 1

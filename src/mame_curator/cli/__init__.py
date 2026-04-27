"""mame-curator command-line interface.

Subcommands (added incrementally as phases land):
    parse <dat-path>   — parse the DAT and print summary stats (Phase 1)
    filter <args>      — run the filter pipeline and write a report (Phase 2)
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from rich.console import Console

from mame_curator.filter import (
    FilterConfig,
    FilterContext,
    FilterError,
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
from mame_curator.parser.listxml import parse_listxml_cloneof, parse_listxml_disks

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
        # load_overrides / load_sessions return empty objects for missing files,
        # so an unset --overrides / --sessions resolves to the same neutral state.
        overrides = (
            load_overrides(args.overrides)
            if args.overrides
            else load_overrides(Path("/nonexistent/overrides.yaml"))
        )
        sessions = (
            load_sessions(args.sessions)
            if args.sessions
            else load_sessions(Path("/nonexistent/sessions.yaml"))
        )
    except (ParserError, FilterError) as exc:
        err_console.print(f"[red]error:[/red] failed to load inputs: {exc}")
        return 1

    result = run_filter(machines, ctx, FilterConfig(), overrides, sessions)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(result.model_dump_json(indent=2) + "\n")

    console.print(f"  winners: {len(result.winners)}")
    console.print(f"  dropped: {len(result.dropped)}")
    console.print(f"  contested groups: {len(result.contested_groups)}")
    console.print(f"  warnings: {len(result.warnings)}")
    console.print(f"  report: {args.out}")
    return 0

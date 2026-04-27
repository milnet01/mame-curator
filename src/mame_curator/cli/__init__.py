"""mame-curator command-line interface.

Subcommands (added incrementally as phases land):
    parse <dat-path>   — parse the DAT and print summary stats (Phase 1)
    filter <config>    — Phase 2
    copy ...           — Phase 3
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from rich.console import Console

from mame_curator.parser import ParserError, parse_dat

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level argument parser with all subcommands."""
    parser = argparse.ArgumentParser(prog="mame-curator", description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true", help="enable DEBUG-level logging")
    sub = parser.add_subparsers(dest="command", required=True)

    parse_cmd = sub.add_parser("parse", help="Parse a DAT and print summary stats")
    parse_cmd.add_argument("dat", type=Path, help="Path to DAT XML or .zip")

    return parser


def run(args: argparse.Namespace) -> int:
    """Dispatch to the chosen subcommand. Returns process exit code."""
    if args.command == "parse":
        return _cmd_parse(args)
    # Per cli/spec.md "Dispatch pattern": argparse `required=True` makes
    # this branch unreachable from any real argv. Reaching it means the
    # dispatch table here is out of sync with build_parser() — a developer
    # bug. Surface it loudly instead of returning a silent runtime-error
    # exit code that masks the missing handler.
    raise AssertionError(f"unhandled subcommand in run(): {args.command!r}")


def _cmd_parse(args: argparse.Namespace) -> int:
    console = Console()
    err_console = Console(
        stderr=True, soft_wrap=True
    )  # §9: errors → stderr; soft_wrap keeps paths intact
    try:
        machines = parse_dat(args.dat)
    except ParserError as exc:
        # standards §9: errors at trust boundaries MUST include the offending input
        err_console.print(f"[red]error:[/red] failed to parse {args.dat}: {exc}")
        return 1  # POSIX runtime error; argparse reserves 2 for usage errors

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

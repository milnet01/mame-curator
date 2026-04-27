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
    sub = parser.add_subparsers(dest="command", required=True)

    parse_cmd = sub.add_parser("parse", help="Parse a DAT and print summary stats")
    parse_cmd.add_argument("dat", type=Path, help="Path to DAT XML or .zip")

    return parser


def run(args: argparse.Namespace) -> int:
    """Dispatch to the chosen subcommand. Returns process exit code."""
    if args.command == "parse":
        return _cmd_parse(args)
    return 1  # unreachable: argparse `required=True` enforces a subcommand


def _cmd_parse(args: argparse.Namespace) -> int:
    console = Console()
    try:
        machines = parse_dat(args.dat)
    except ParserError as exc:
        console.print(f"[red]error:[/red] {exc}")
        return 2

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

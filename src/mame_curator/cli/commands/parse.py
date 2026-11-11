"""`mame-curator parse` subcommand handler."""

from __future__ import annotations

import argparse

from rich.console import Console
from rich.markup import escape

from mame_curator.cli.commands._text import shown_path
from mame_curator.parser import ParserError, parse_dat


def _cmd_parse(args: argparse.Namespace) -> int:
    console = Console(soft_wrap=True)
    err_console = Console(stderr=True, soft_wrap=True)
    try:
        machines = parse_dat(args.dat)
    except ParserError as exc:
        err_console.print(
            f"[red]error:[/red] failed to parse {shown_path(args.dat)}: {escape(str(exc))}"
        )
        return 1

    parents = sum(1 for m in machines.values() if m.cloneof is None)
    clones = sum(1 for m in machines.values() if m.cloneof is not None)
    bios = sum(1 for m in machines.values() if m.is_bios)
    devices = sum(1 for m in machines.values() if m.is_device)
    mechanical = sum(1 for m in machines.values() if m.is_mechanical)

    console.print(f"DAT: {shown_path(args.dat)}")
    console.print(f"  machines: {len(machines)}")
    console.print(f"  parents: {parents}")
    console.print(f"  clones: {clones}")
    console.print(f"  bios: {bios}")
    console.print(f"  devices: {devices}")
    console.print(f"  mechanical: {mechanical}")
    return 0

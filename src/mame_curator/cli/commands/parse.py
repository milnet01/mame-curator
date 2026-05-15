"""`mame-curator parse` subcommand handler."""

from __future__ import annotations

import argparse

from rich.console import Console

from mame_curator.parser import ParserError, parse_dat


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

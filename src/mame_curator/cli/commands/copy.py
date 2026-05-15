"""`mame-curator copy` subcommand handler."""

from __future__ import annotations

import argparse
import json

from rich.console import Console

from mame_curator.copy import (
    ConflictStrategy,
    CopyError,
    CopyPlan,
    CopyReportStatus,
    purge_recycle,
    run_copy,
)
from mame_curator.parser import ParserError, parse_dat
from mame_curator.parser.listxml import parse_listxml_bios_chain, parse_listxml_disks


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

"""`mame-curator filter` subcommand handler."""

from __future__ import annotations

import argparse

from rich.console import Console

from mame_curator._atomic import atomic_write_text
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
from mame_curator.parser.listxml import parse_listxml_cloneof, parse_listxml_disks


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

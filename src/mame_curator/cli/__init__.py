"""mame-curator command-line interface.

Subcommands (added incrementally as phases land):
    parse <dat-path>   — parse the DAT and print summary stats (Phase 1)
    filter <args>      — run the filter pipeline and write a report (Phase 2)
    copy <args>        — copy winners + BIOS deps and write mame.lpl (Phase 3)
    serve <args>       — run the HTTP API server (Phase 4)
    setup <args>       — interactive bootstrap wizard for config.yaml
    refresh-inis <args>  — download progettoSnaps reference INIs (P07)
    refresh-snaps <args> — download + extract progettoSnaps snap pack (P10 3a)
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from mame_curator import __version__

# PEP 484 explicit re-export: `import X as X` flags the underscore-prefixed
# command handlers as public re-exports, so tests can import them via
# `mame_curator.cli` (the historical location pre-DS02 A2 split) without
# mypy attr-defined warnings. The handlers live in cli/commands/<name>.py
# now, but this module is still the import surface for build_parser() /
# run() consumers and the FP28 tests that exercise _cmd_serve and
# _cmd_refresh_inis directly.
from mame_curator.cli.commands.copy import _cmd_copy as _cmd_copy
from mame_curator.cli.commands.filter import _cmd_filter as _cmd_filter
from mame_curator.cli.commands.parse import _cmd_parse as _cmd_parse
from mame_curator.cli.commands.refresh_inis import _cmd_refresh_inis as _cmd_refresh_inis
from mame_curator.cli.commands.refresh_snaps import _cmd_refresh_snaps as _cmd_refresh_snaps
from mame_curator.cli.commands.serve import _cmd_serve as _cmd_serve
from mame_curator.cli.commands.setup import _cmd_setup as _cmd_setup

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level argument parser with all subcommands.

    Each subparser registers its handler via `set_defaults(func=...)` per
    cli/spec.md §"Dispatch pattern" — `run()` then dispatches with
    `args.func(args)` instead of an if/elif chain.
    """
    parser = argparse.ArgumentParser(prog="mame-curator", description=__doc__)
    parser.add_argument(
        "--version",
        action="version",
        version=f"mame-curator {__version__}",
        help="show version and exit",
    )
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

    sub_setup = sub.add_parser(
        "setup", help="Interactive wizard that writes a starter config.yaml."
    )
    sub_setup.add_argument(
        "--out",
        type=Path,
        default=Path("config.yaml"),
        help="Where to write the config (default: ./config.yaml).",
    )
    sub_setup.add_argument(
        "--force", action="store_true", help="Overwrite an existing config file."
    )
    sub_setup.add_argument(
        "--source-roms", type=Path, default=None, help="Path to the non-merged ROM directory."
    )
    sub_setup.add_argument(
        "--source-dat", type=Path, default=None, help="Path to the MAME DAT (.xml or .zip)."
    )
    sub_setup.add_argument(
        "--dest-roms", type=Path, default=None, help="Where curated ROMs will be copied."
    )
    sub_setup.add_argument(
        "--retroarch-playlist",
        type=Path,
        default=None,
        help="Where to write the RetroArch mame.lpl playlist.",
    )
    sub_setup.set_defaults(func=_cmd_setup)

    refresh = sub.add_parser(
        "refresh-inis",
        help=(
            "Download progettoSnaps reference INIs (catver, languages, bestgames, series, mature)."
        ),
    )
    refresh.add_argument(
        "--dest",
        type=Path,
        required=True,
        help="Directory to write the INI files into (created if missing).",
    )
    refresh.add_argument(
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help=(
            "Path to config.yaml — fields under paths.{catver,languages,bestgames,"
            "series,mature} that are currently unset will be patched to point at the "
            "downloaded INIs (existing values are preserved). Pass --no-config to skip."
        ),
    )
    refresh.add_argument(
        "--no-config",
        action="store_true",
        help="Don't auto-patch config.yaml.",
    )
    refresh.set_defaults(func=_cmd_refresh_inis)

    refresh_snaps = sub.add_parser(
        "refresh-snaps",
        help=(
            "Download the progettoSnaps snap pack and extract PNGs into "
            "<dest>/snap/ (snap kind only — progettoSnaps no longer "
            "publishes flyers / titles upstream)."
        ),
    )
    refresh_snaps.add_argument(
        "--dest",
        type=Path,
        default=Path("./data/snaps"),
        help="Destination root (the pack lands under <dest>/snap/). Default: ./data/snaps",
    )
    refresh_snaps.add_argument(
        "--url",
        type=str,
        default=None,
        help=(
            "Override the discovered pack URL. Use this if upstream restructures "
            "or you want to pin an older MAME version."
        ),
    )
    refresh_snaps.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing PNG files in <dest>/snap/ (default: skip).",
    )
    refresh_snaps.set_defaults(func=_cmd_refresh_snaps)

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

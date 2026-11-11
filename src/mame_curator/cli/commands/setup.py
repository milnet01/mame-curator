"""`mame-curator setup` subcommand handler."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml
from rich.console import Console
from rich.markup import escape
from rich.prompt import Prompt

from mame_curator._atomic import atomic_write_text
from mame_curator.cli.commands._text import shown_path
from mame_curator.config_location import STARTER_HEADER, resolve_config_path


def _prompt_path(label: str, supplied: Path | None) -> Path:
    """Return a Path either from the supplied flag value or via prompt.

    Empty / whitespace-only input re-prompts. Tilde expansion is applied so
    users can type ``~/Games/MAME`` without surprise.
    """
    if supplied is not None:
        return supplied
    while True:
        raw = Prompt.ask(label).strip()
        if raw:
            return Path(raw).expanduser()


def _cmd_setup(args: argparse.Namespace) -> int:
    # soft_wrap: a path must stay whole, to be copied or read back.
    console = Console(soft_wrap=True)
    err_console = Console(stderr=True, soft_wrap=True)

    # Without --out, write the file `serve` will read. A new ./config.yaml beside
    # a per-user config would silently take over from it.
    out, _ = resolve_config_path(args.out)
    shown_out = shown_path(out)

    if out.exists() and not args.force:
        err_console.print(
            f"[red]error:[/red] {shown_out} already exists — pass --force to overwrite."
        )
        return 1

    console.print(f"[bold]MAME Curator setup[/bold] — writes a starter config to {shown_out}.")
    console.print("Press Enter after each path. Tilde (~) is expanded.\n")

    try:
        source_roms = _prompt_path("Source ROM directory (non-merged)", args.source_roms)
        source_dat = _prompt_path("Source DAT file (.xml or .zip)", args.source_dat)
        dest_roms = _prompt_path("Destination ROM directory", args.dest_roms)
        retroarch_playlist = _prompt_path(
            "RetroArch playlist target (e.g. <dest>/mame.lpl)", args.retroarch_playlist
        )
    except EOFError:
        # A closed stdin (piped from /dev/null, a CI job) is a user-caused
        # failure: one line naming the non-interactive route, exit 1.
        err_console.print(
            "[red]error:[/red] no input to answer the prompts — pass --source-roms, "
            "--source-dat, --dest-roms and --retroarch-playlist instead."
        )
        return 1

    if not source_roms.is_dir():
        err_console.print(
            f"[red]error:[/red] source_roms {shown_path(source_roms)} "
            "does not exist or is not a directory."
        )
        return 1
    if not source_dat.is_file():
        err_console.print(
            f"[red]error:[/red] source_dat {shown_path(source_dat)} "
            "does not exist or is not a file."
        )
        return 1

    paths_block = {
        "paths": {
            "source_roms": str(source_roms),
            "source_dat": str(source_dat),
            "dest_roms": str(dest_roms),
            "retroarch_playlist": str(retroarch_playlist),
        }
    }
    body = STARTER_HEADER + yaml.safe_dump(paths_block, sort_keys=False)

    try:
        atomic_write_text(out, body)
    except OSError as exc:
        err_console.print(f"[red]error:[/red] failed to write {shown_out}: {escape(str(exc))}")
        return 1

    console.print(f"\n[green]✓[/green] wrote {shown_out}")
    serve_command = "mame-curator serve"
    if args.out is not None:
        serve_command += f" --config {shown_out}"
    console.print(f"Run [bold]{serve_command}[/bold] to start the app.")
    return 0

"""``mame-curator refresh-snaps`` subcommand handler.

Downloads the progettoSnaps snap pack and extracts ``<name>.png`` files
into ``--dest/snap/``. Snap is the only kind progettoSnaps maintains
upstream — see ``docs/specs/P10.md`` § "1. progettoSnaps — local pack
model" for the architectural decision.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console


def _resolve_dest(args: argparse.Namespace, err_console: Console) -> Path | None:
    """Resolve the pack destination root, or ``None`` if config is unreadable.

    mame-curator-1081: an explicit ``--dest`` always wins. Otherwise bind the
    download folder to ``media.snaps_dir`` from ``--config`` so it can't diverge
    from the folder the progettoSnaps media source reads. An absent config file
    falls back to the ``MediaConfig`` default; a present-but-invalid config is a
    hard error (the user can pass ``--dest`` to bypass it).
    """
    # argparse Namespace attributes are ``Any``; pin the type so the returns
    # below satisfy the ``Path | None`` signature (no-any-return).
    dest: Path | None = args.dest
    if dest is not None:
        return dest

    from mame_curator.api.schemas import MediaConfig

    if not args.config.exists():
        return MediaConfig().snaps_dir

    from mame_curator.api.errors import ConfigError
    from mame_curator.api.state import load_app_config

    try:
        return load_app_config(args.config).media.snaps_dir
    except (ConfigError, OSError) as exc:
        err_console.print(
            f"[red]error:[/red] could not read media.snaps_dir from {args.config!s} "
            f"({exc}); fix the config or pass --dest explicitly"
        )
        return None


def _cmd_refresh_snaps(args: argparse.Namespace) -> int:
    """Discover (or honour ``--url``), download, and extract the snap pack."""
    console = Console()
    err_console = Console(stderr=True, soft_wrap=True)

    dest = _resolve_dest(args, err_console)
    if dest is None:
        return 1

    # Defence-in-depth import guard matching ``_cmd_refresh_inis`` / ``_cmd_serve``
    # (FP28 D3 pattern). Reachable only in exotic install states.
    try:
        import asyncio

        import httpx

        from mame_curator.updates import refresh_snaps
    except ImportError as exc:
        err_console.print(
            f"[red]error:[/red] failed to import dependencies ({exc}); "
            "reinstall the project (uv sync, or pip install -e .)"
        )
        return 1

    async def _run() -> int:
        # Generous timeout: the snap pack is ~500 MB and the download primitive
        # streams chunks; httpx's request-level timeout covers the connect /
        # initial-response window, not total transfer time.
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            report = await refresh_snaps(
                dest_dir=dest,
                client=client,
                url=args.url,
                force=args.force,
            )

        if report.error:
            err_console.print(f"[red]✗[/red] {report.error}")
            return 1
        if report.downloaded:
            console.print(
                f"[green]✓[/green] downloaded {report.pack_url} "
                f"→ {report.files_extracted} PNG(s) extracted, "
                f"{report.files_skipped} skipped (existed; use --force to overwrite)"
            )
        else:
            console.print(f"[yellow]·[/yellow] no download performed ({report.pack_url})")
        return 0

    return asyncio.run(_run())

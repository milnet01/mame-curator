"""``mame-curator refresh-snaps`` subcommand handler.

Downloads the progettoSnaps snap pack and extracts ``<name>.png`` files
into ``--dest/snap/``. Snap is the only kind progettoSnaps maintains
upstream — see ``docs/specs/P10.md`` § "1. progettoSnaps — local pack
model" for the architectural decision.
"""

from __future__ import annotations

import argparse

from rich.console import Console


def _cmd_refresh_snaps(args: argparse.Namespace) -> int:
    """Discover (or honour ``--url``), download, and extract the snap pack."""
    console = Console()
    err_console = Console(stderr=True, soft_wrap=True)

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
                dest_dir=args.dest,
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

"""`mame-curator refresh-inis` subcommand handler."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml
from rich.console import Console
from rich.markup import escape

from mame_curator._atomic import atomic_write_text
from mame_curator.config_location import ConfigSource, resolve_config_path
from mame_curator.updates.ini import INI_CONFIG_FIELDS


def _warn_config_not_updated(console: Console, config_path: Path, reason: str) -> None:
    console.print(
        f"[yellow]⚠[/yellow] {escape(str(config_path))} {reason} "
        "The app will not use these files until that is put right."
    )


def _patch_config_with_ini_paths(
    *,
    config_path: Path,
    ini_dir: Path,
    downloaded: list[str],
    console: Console,
) -> None:
    """FP18 § A: point unset ``paths.<ini-field>`` at the downloaded files.

    Existing user-supplied paths are preserved (never clobbered). Atomic
    write via ``atomic_write_text``. Prints which fields were updated and
    a restart-the-server hint.
    """
    try:
        body = config_path.read_text(encoding="utf-8")
        data = yaml.safe_load(body)
    except (OSError, yaml.YAMLError) as exc:
        console.print(
            f"[yellow]⚠[/yellow] could not read {escape(str(config_path))} to patch INI paths: "
            f"{escape(str(exc))}"
        )
        return
    if not isinstance(data, dict):
        _warn_config_not_updated(console, config_path, "is not a YAML mapping, so was not updated.")
        return
    paths = data.setdefault("paths", {})
    if not isinstance(paths, dict):
        _warn_config_not_updated(console, config_path, "has a `paths:` that is not a mapping.")
        return

    updated_fields: list[str] = []
    for filename in downloaded:
        field = INI_CONFIG_FIELDS.get(filename)
        if field is None:
            continue
        if paths.get(field):
            continue
        paths[field] = str(ini_dir / filename)
        updated_fields.append(field)

    if not updated_fields:
        console.print(
            f"Nothing to update in {escape(str(config_path))}: these paths are already set, "
            "and are left as they are."
        )
        return

    new_body = yaml.safe_dump(data, sort_keys=False)
    try:
        atomic_write_text(config_path, new_body)
    except OSError as exc:
        console.print(
            f"[yellow]⚠[/yellow] could not write {escape(str(config_path))}: {escape(str(exc))}"
        )
        return

    console.print(
        f"\n[green]✓[/green] {escape(str(config_path))} updated with {len(updated_fields)} "
        f"INI path(s): {', '.join(updated_fields)}"
    )
    console.print(
        "[yellow]Restart `mame-curator serve` (or re-run ./run.sh) for the new "
        "paths to take effect.[/yellow]"
    )


def _cmd_refresh_inis(args: argparse.Namespace) -> int:
    """Download the progettoSnaps reference INIs to ``--dest``.

    FP18: auto-patch ``config.yaml``'s ``paths.*`` for any field that's
    still unset, so the next ``serve`` actually consumes the downloaded
    files. Without ``--config`` that is the file ``serve`` reads. With no
    file there, it warns rather than creating one. Surfaces a per-file outcome
    line: green ✓ for success, red ✗ for failure with the manual-fallback URL
    the user can grab themselves.
    """
    # soft_wrap: a path must stay whole, to be copied or read back.
    console = Console(soft_wrap=True)
    err_console = Console(stderr=True, soft_wrap=True)

    # FP28 D3: defence-in-depth import guard mirroring _cmd_serve's shape.
    # httpx is a top-level dep, so the ImportError path is only reachable
    # in exotic install states (pip install --no-deps, broken wheel,
    # partial editable install) — but the consistency with _cmd_serve's
    # guard avoids a raw traceback in those rare cases.
    try:
        import asyncio

        import httpx

        from mame_curator.updates import refresh_inis
    except ImportError as exc:
        err_console.print(
            f"[red]error:[/red] failed to import dependencies ({escape(str(exc))}); "
            "reinstall the project (uv sync, or pip install -e .)"
        )
        return 1

    async def _run() -> int:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            report = await refresh_inis(dest_dir=args.dest, client=client)

        for name in report.updated:
            console.print(f"[green]✓[/green] {escape(name)}")
        for name, url in report.failed:
            err_console.print(f"[red]✗[/red] {escape(name)} — manual download: {escape(url)}")

        if report.updated and not args.no_config:
            config_path, source = resolve_config_path(args.config)
            if config_path.exists():
                _patch_config_with_ini_paths(
                    config_path=config_path,
                    # The per-user config is read from any folder, so a relative
                    # path in it would point somewhere else on the next start.
                    ini_dir=args.dest.absolute() if source is ConfigSource.USER else args.dest,
                    downloaded=report.updated,
                    console=console,
                )
            else:
                _warn_config_not_updated(
                    console,
                    config_path,
                    "does not exist yet, so was not updated. Start the app once, then run "
                    "this command again.",
                )

        return 0 if report.all_succeeded else 1

    return asyncio.run(_run())

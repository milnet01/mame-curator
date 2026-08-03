"""`mame-curator serve` subcommand handler."""

from __future__ import annotations

import argparse
import os
import re

from rich.console import Console
from rich.markup import escape

from mame_curator.filter import FilterError
from mame_curator.parser import ParserError

DEFAULT_PORT = 8080
MIN_PORT = 1024
MAX_PORT = 65535
_DIGITS = re.compile(r"[0-9]+")


def _resolve_port(explicit: int | None) -> int:
    """Resolve the bind port: ``--port`` flag → ``$PORT`` → 8080.

    `run.sh` converts `$PORT` into an explicit `--port`, so this only
    fires for callers that invoke `mame-curator serve` directly — but the
    range and the message match `run.sh`'s own check so the error reads
    the same whichever way the user came in.

    Raises:
        ValueError: `$PORT` is set to something other than an integer in
            1024-65535. Never falls back to the default silently.
    """
    if explicit is not None:
        return explicit
    raw = os.environ.get("PORT", "")
    if not raw:
        return DEFAULT_PORT
    if not _DIGITS.fullmatch(raw) or not MIN_PORT <= int(raw) <= MAX_PORT:
        raise ValueError(
            f"PORT={raw!r} is not a valid port — expected an integer in {MIN_PORT}-{MAX_PORT}."
        )
    return int(raw)


def _cmd_serve(args: argparse.Namespace) -> int:
    err_console = Console(stderr=True, soft_wrap=True)
    try:
        port = _resolve_port(args.port)
    except ValueError as exc:
        # `escape` because the offending value is user input and rich would
        # otherwise eat any `[...]` in it as a style tag — `PORT='[abc]'`
        # printed as `PORT=''`, dropping the one thing spec.md § "Error
        # messages" requires the message to carry verbatim.
        err_console.print(f"[red]error:[/red] {escape(str(exc))}")
        return 1

    if not args.config.exists():
        err_console.print(
            f"[red]error:[/red] config file not found: {args.config!r} — "
            "run `mame-curator setup` first"
        )
        return 1

    try:
        import uvicorn

        from mame_curator.api import create_app
        from mame_curator.api.errors import ConfigError
    except ImportError as exc:
        err_console.print(
            f"[red]error:[/red] API extras not installed ({exc}); "
            "install with `pip install mame-curator[api]`"
        )
        return 1

    # FP28 D2: narrowed from bare `except Exception` to the typed errors
    # create_app actually raises on bad inputs. Programmer errors
    # (RuntimeError, AttributeError, ...) propagate as tracebacks per
    # coding-standards.md § 9 — the trace is the actionable signal.
    # NOTE: create_app is currently a pure FastAPI factory; config
    # validation happens inside the async lifespan and surfaces during
    # uvicorn.run, not here. This catch is defence-in-depth in case a
    # future refactor moves validation up into the factory body.
    try:
        app = create_app(args.config)
    except (ConfigError, ParserError, FilterError) as exc:
        err_console.print(f"[red]error:[/red] failed to create app: {exc}")
        return 1

    host = args.host or "127.0.0.1"
    try:
        uvicorn.run(app, host=host, port=port, log_level="info")
    except OSError as exc:
        err_console.print(f"[red]error:[/red] failed to bind {host}:{port}: {exc}")
        return 1
    except KeyboardInterrupt:
        # FP28 D1: uvicorn catches Ctrl-C internally and returns normally
        # in the current version; this except is defence-in-depth for a
        # future re-raise. POSIX convention for SIGINT is exit 130.
        return 130
    # FP28 D1: fall-through is also 130, not 0 — uvicorn's internal
    # KeyboardInterrupt catch means the function reaches here when the
    # user Ctrl-C'd a healthy server. The visible exit code must reflect
    # the signal, not a clean shutdown.
    return 130

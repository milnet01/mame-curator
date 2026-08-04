"""`mame-curator serve` subcommand handler."""

from __future__ import annotations

import argparse
import ipaddress
import logging
import os
import re
import socket
import threading
import time
import webbrowser
from typing import TYPE_CHECKING

from rich.console import Console
from rich.markup import escape

from mame_curator.config_location import (
    ConfigSource,
    ensure_starter_config,
    resolve_config_path,
)
from mame_curator.filter import FilterError
from mame_curator.parser import ParserError

if TYPE_CHECKING:
    from pathlib import Path

    from fastapi import FastAPI

    from mame_curator.api.schemas import ServerConfig

logger = logging.getLogger(__name__)

DEFAULT_PORT = 8080
MIN_PORT = 1024
MAX_PORT = 65535
_DIGITS = re.compile(r"[0-9]+")

# Browser poll budget. Module-level so a test can monkeypatch them.
_BROWSER_POLL_INTERVAL_S = 0.1
_BROWSER_CONNECT_TIMEOUT_S = 0.25
_BROWSER_POLL_TIMEOUT_S = 300.0


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


def _load_server_config(path: Path) -> ServerConfig:
    """Read `config.yaml`'s `server:` block — and only that block.

    Full `AppConfig` validation belongs to the API lifespan; `serve` must
    still be able to start a server whose *other* sections are mid-edit.
    The block is read once and unconditionally, so a malformed one fails
    the command even when every relevant flag was supplied.

    Raises:
        ConfigError: `path` is unreadable, is not a YAML mapping, or its
            `server:` block fails `ServerConfig` validation.
    """
    # Imported here, not at module scope: `api.errors` pulls in FastAPI,
    # which `_cmd_serve` treats as an optional extra and reports on
    # separately (exit-1 path 3). This function only runs after that
    # import has already succeeded.
    import yaml
    from pydantic import ValidationError

    from mame_curator.api.errors import ConfigError
    from mame_curator.api.schemas import ServerConfig

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"failed to read {str(path)!r}: {exc!r}") from exc
    except yaml.YAMLError as exc:
        # repr-quote `exc`: YAML and Pydantic error strings are multi-line,
        # and ConfigError's `detail` is single-line by API contract (FP09 A1).
        raise ConfigError(f"failed to parse {str(path)!r}: {exc!r}") from exc

    if not isinstance(raw, dict):
        raise ConfigError(f"{str(path)!r} must be a YAML mapping")

    try:
        # `or {}` so an explicit `server:` with no value reads as "absent",
        # matching a file with no `server:` key at all.
        return ServerConfig.model_validate(raw.get("server") or {})
    except ValidationError as exc:
        raise ConfigError(f"{str(path)!r} has an invalid `server:` block: {exc!r}") from exc


def _is_wildcard(host: str) -> bool:
    """Is `host` an address to listen on rather than one to connect to?

    A bare `ip_address(host).is_unspecified` is not a conforming test: it
    raises on the empty string, which is itself a wildcard, and on any
    hostname, for which the answer is "no".
    """
    if not host:  # empty string IS a wildcard
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_unspecified
    except ValueError:  # a hostname, not a literal address
        return False  # use it as given


def _open_browser_when_ready(host: str, port: int) -> None:
    """Poll `host:port` until it accepts a connection, then open a browser.

    A fixed delay is not a conforming implementation: uvicorn runs the
    application lifespan — which parses a ~48 MB DAT, tens of seconds on a
    cold cache — *before* it creates the listening socket, so any constant
    is simultaneously too short on a cold start and too long on a warm one.

    Best-effort by contract: every failure path returns rather than
    raising, and each non-open outcome logs its own distinguishable line.
    """
    connect_host = "127.0.0.1" if _is_wildcard(host) else host
    url = f"http://{connect_host}:{port}/"
    deadline = time.monotonic() + _BROWSER_POLL_TIMEOUT_S

    while time.monotonic() < deadline:
        try:
            with socket.create_connection((connect_host, port), timeout=_BROWSER_CONNECT_TIMEOUT_S):
                pass
        except OSError:
            time.sleep(_BROWSER_POLL_INTERVAL_S)
            continue
        try:
            webbrowser.open(url)
        except Exception as exc:
            # Deliberately broad, and the one place in `cli/` where that is
            # right: this runs in a daemon thread, `webbrowser` backends
            # raise whatever their platform opener raises, and cli/spec.md
            # § Browser requires that a failed open can never reach the
            # server or the exit code. An escaping exception here would
            # print a traceback the user can do nothing about.
            logger.debug("browser open failed: %s", exc)
        return

    logger.debug("browser open gave up: %s not accepting after %ss", url, _BROWSER_POLL_TIMEOUT_S)


def _maybe_open_browser(host: str, port: int, *, enabled: bool, suppressed: bool) -> None:
    """Start the browser poller, or log the reason it was skipped.

    `suppressed` is `--no-open-browser` and `enabled` is
    `server.open_browser_on_start`. The flag is a one-way suppression:
    it can turn an open off, and there is deliberately no flag that
    forces one on against a config saying false.
    """
    if suppressed:
        logger.debug("browser open skipped: disabled by flag")
    elif not enabled:
        logger.debug("browser open skipped: disabled by config")
    elif port == 0:
        # `--port 0` is "any free port"; the port uvicorn actually binds is
        # not knowable here, so the poll target would be unconnectable by
        # construction and would burn the whole budget before giving up.
        logger.debug("browser open skipped: port 0 (bound port not knowable before listen)")
    else:
        threading.Thread(target=_open_browser_when_ready, args=(host, port), daemon=True).start()


def _run_server(app: FastAPI, host: str, port: int, err_console: Console) -> int:
    """Run uvicorn, and translate how it ended into an exit code.

    Everything from the socket inwards belongs to `api/`; this owns only
    the startup failures and the exit code (`cli/spec.md` § Out of scope).
    """
    import uvicorn

    try:
        uvicorn.run(app, host=host, port=port, log_level="info")
    except (OSError, OverflowError) as exc:
        # OverflowError, not an OSError subclass, is what `socket.bind`
        # raises for a resolved port outside 0-65535 — reachable from both
        # `--port` and `server.port`, neither of which is range-checked.
        err_console.print(
            f"[red]error:[/red] failed to bind {escape(host)}:{port}: {escape(str(exc))}"
        )
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


def _cmd_serve(args: argparse.Namespace) -> int:
    err_console = Console(stderr=True, soft_wrap=True)

    # --- Stage 1: before any config I/O -------------------------------
    # Validates $PORT and raises on an invalid one. The value is computed
    # here; whether it WINS is decided in stage 2, once `server` exists.
    # Collapsing the two into one if/else would push the $PORT error after
    # the config-existence check, which reverses the exit-1 path ordering.
    try:
        port_from_flag_or_env = _resolve_port(args.port)
    except ValueError as exc:
        # `escape` because the offending value is user input and rich would
        # otherwise eat any `[...]` in it as a style tag — `PORT='[abc]'`
        # printed as `PORT=''`, dropping the one thing spec.md § "Error
        # messages" requires the message to carry verbatim.
        err_console.print(f"[red]error:[/red] {escape(str(exc))}")
        return 1

    # `server.port` is reachable only when neither of the layers above was
    # supplied. Re-derived from the inputs rather than inferred from
    # `_resolve_port`'s return value: that returns 8080 identically for
    # "nothing was set" and for an explicit `--port 8080`, so inferring it
    # would let `server.port` beat an explicit flag.
    use_config_port = args.port is None and not os.environ.get("PORT", "")

    # Resolution and starter-config creation replace the old
    # `args.config.exists()` check, and sit HERE rather than at the top of
    # the function: `cli/spec.md` pins the $PORT raise before any config
    # I/O, and `test_invalid_port_checked_before_config` fails if this is
    # hoisted above it.
    config_path, config_source = resolve_config_path(args.config)
    if config_source is ConfigSource.USER:
        try:
            ensure_starter_config(config_path)
        except OSError as exc:
            err_console.print(
                f"[red]error:[/red] cannot create config at "
                f"{escape(str(config_path))}: {escape(str(exc))}"
            )
            return 1
    if not config_path.exists():
        # Only reachable for an explicit --config: layer 2 is skipped when
        # absent and layer 3 was just created.
        err_console.print(
            f"[red]error:[/red] config file not found: {escape(repr(config_path))} — "
            "run `mame-curator setup` first"
        )
        return 1

    try:
        # `uvicorn` is imported for the probe, not for use here — `_run_server`
        # imports it again where it is actually called. Its absence must be
        # reported as the one actionable line below (exit-1 path 3) rather
        # than as an ImportError traceback from deeper in the command.
        import uvicorn  # noqa: F401

        from mame_curator.api import create_app
        from mame_curator.api.errors import ConfigError
    except ImportError as exc:
        err_console.print(
            f"[red]error:[/red] API extras not installed ({escape(str(exc))}); "
            "install with `pip install mame-curator\\[api]`"
        )
        return 1

    # --- Stage 2: after the config file exists and the extras imported --
    try:
        server = _load_server_config(config_path)
    except ConfigError as exc:
        err_console.print(f"[red]error:[/red] {escape(str(exc))}")
        return 1

    port = server.port if use_config_port else port_from_flag_or_env
    host = args.host or server.host

    # FP28 D2: narrowed from bare `except Exception` to the typed errors
    # create_app actually raises on bad inputs. Programmer errors
    # (RuntimeError, AttributeError, ...) propagate as tracebacks per
    # coding-standards.md § 9 — the trace is the actionable signal.
    # NOTE: create_app is currently a pure FastAPI factory; config
    # validation happens inside the async lifespan and surfaces during
    # uvicorn.run, not here. This catch is defence-in-depth in case a
    # future refactor moves validation up into the factory body.
    try:
        app = create_app(config_path)
    except (ConfigError, ParserError, FilterError) as exc:
        err_console.print(f"[red]error:[/red] failed to create app: {escape(str(exc))}")
        return 1

    _maybe_open_browser(
        host, port, enabled=server.open_browser_on_start, suppressed=args.no_open_browser
    )

    return _run_server(app, host, port, err_console)

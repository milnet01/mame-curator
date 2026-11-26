"""`mame-curator serve` subcommand handler."""

from __future__ import annotations

import argparse
import http.client
import ipaddress
import logging
import os
import re
import secrets
import threading
import time
import webbrowser
from typing import TYPE_CHECKING

from rich.console import Console
from rich.markup import escape

from mame_curator.cli.commands._single_instance import InstanceLock, running_url
from mame_curator.cli.commands._text import shown_path
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

# Mirrors `ServerConfig.port`'s default; it does not set the app's port.
# `_resolve_port` returns it with no flag and no $PORT, and `_cmd_serve` then
# takes `server.port` instead, so only direct callers of `_resolve_port` see it.
DEFAULT_PORT = 8080
MIN_PORT = 1024
MAX_PORT = 65535
_DIGITS = re.compile(r"[0-9]+")

# Browser poll budget. Module-level so a test can monkeypatch them.
_BROWSER_POLL_INTERVAL_S = 0.1
_BROWSER_CONNECT_TIMEOUT_S = 0.25
_BROWSER_POLL_TIMEOUT_S = 300.0

# uvicorn puts this on every reply, with a value made fresh for each `serve`
# run, so the browser poller can tell this server from whatever else holds the
# port, including another copy of this app. It proves identity to ourselves on
# loopback and guards nothing, so it is not a secret.
_INSTANCE_HEADER = "x-mame-curator-instance"


def _resolve_port(explicit: int | None) -> int:
    """Resolve the bind port: ``--port`` flag → ``$PORT`` → 8080.

    `run.sh` checks `$PORT` itself and passes it as `--port`, so `$PORT` is
    read here for `run.bat`, which leaves it to this check, and for callers
    that invoke `mame-curator serve` directly. The range and the message match
    `run.sh`'s check, so the error reads the same whichever way the user came in.

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
    from pydantic import ValidationError

    from mame_curator.api.errors import ConfigError
    from mame_curator.api.schemas import ServerConfig
    from mame_curator.api.state import ignore_unknown_keys, read_yaml_mapping

    raw = read_yaml_mapping(path)
    # `or {}` so an explicit `server:` with no value reads as "absent",
    # matching a file with no `server:` key at all.
    block = raw.get("server") or {}
    if isinstance(block, dict):
        # A non-mapping block is left for validation to refuse.
        ignore_unknown_keys(ServerConfig, block, where=str(path), prefix="server.")
    try:
        return ServerConfig.model_validate(block)
    except ValidationError as exc:
        # repr-quote `exc`: a Pydantic error message spans several lines, and
        # ConfigError's `detail` is single-line by API contract (FP09 A1).
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


def _answers_as_this_server(host: str, port: int, instance: str) -> bool:
    """Does the server at `host:port` carry this run's identity header?

    Any status counts: uvicorn adds the header to every reply, and only
    identity is being asked. A port that refuses, stays silent or speaks
    something other than HTTP is simply not this server, yet.
    """
    connection = http.client.HTTPConnection(host, port, timeout=_BROWSER_CONNECT_TIMEOUT_S)
    try:
        connection.request("HEAD", "/")
        return connection.getresponse().getheader(_INSTANCE_HEADER) == instance
    except (OSError, http.client.HTTPException):
        return False
    finally:
        connection.close()


def _open_browser_when_ready(host: str, port: int, instance: str) -> None:
    """Poll `host:port` until this server answers there, then open a browser.

    A fixed delay is not a conforming implementation: uvicorn runs the
    application lifespan — which parses a ~48 MB DAT, tens of seconds on a
    cold cache — *before* it creates the listening socket, so any constant
    is simultaneously too short on a cold start and too long on a warm one.
    A port that merely accepts is not enough either: another program, or
    another copy of this app, may hold it, and this copy is about to fail to
    bind.

    Best-effort by contract: every failure path returns rather than
    raising, and each non-open outcome logs its own distinguishable line.
    """
    connect_host, url = _browser_address(host, port)
    deadline = time.monotonic() + _BROWSER_POLL_TIMEOUT_S

    while time.monotonic() < deadline:
        if not _answers_as_this_server(connect_host, port, instance):
            time.sleep(_BROWSER_POLL_INTERVAL_S)
            continue
        _open_url(url)
        return

    logger.debug("browser open gave up: %s not accepting after %ss", url, _BROWSER_POLL_TIMEOUT_S)


def _browser_address(host: str, port: int) -> tuple[str, str]:
    """`(host to connect to, URL to open)` for a server bound to `host:port`."""
    connect_host = "127.0.0.1" if _is_wildcard(host) else host.strip("[]")
    # An IPv6 literal needs brackets in a URL, and none on a socket.
    url_host = f"[{connect_host}]" if ":" in connect_host else connect_host
    return connect_host, f"http://{url_host}:{port}/"


def _open_url(url: str) -> None:
    """Open `url` in the browser; best-effort, so every failure only logs."""
    try:
        if not webbrowser.open(url):
            logger.debug("browser open failed: no browser could be started")
    except Exception as exc:
        # Deliberately broad, and the one place in `cli/` where that is
        # right: it may run in a daemon thread, `webbrowser` backends
        # raise whatever their platform opener raises, and cli/spec.md
        # § Browser requires that a failed open can never reach the
        # server or the exit code. An escaping exception here would
        # print a traceback the user can do nothing about.
        logger.debug("browser open failed: %s", exc)


def _browser_skip_reason(*, enabled: bool, suppressed: bool, managed: bool) -> str | None:
    """Why the browser must not open, or None when it may.

    `suppressed` is `--no-open-browser`, `enabled` is
    `server.open_browser_on_start`, and `managed` is `LWSM_MANAGED=1`:
    LocalWebServerManager has its own Open button, and the user picks the
    browser there. The flag is a one-way suppression: it can turn an open
    off, and there is deliberately no flag that forces one on against a
    config saying false.
    """
    if suppressed:
        return "disabled by flag"
    if managed:
        return "started by LocalWebServerManager"
    if not enabled:
        return "disabled by config"
    return None


def _maybe_open_browser(
    host: str, port: int, instance: str, *, enabled: bool, suppressed: bool, managed: bool
) -> None:
    """Start the browser poller, or log the reason it was skipped."""
    reason = _browser_skip_reason(enabled=enabled, suppressed=suppressed, managed=managed)
    if reason is not None:
        logger.debug("browser open skipped: %s", reason)
    elif port == 0:
        # `--port 0` is "any free port"; the port uvicorn actually binds is
        # not knowable here, so the poll target would be unconnectable by
        # construction and would burn the whole budget before giving up.
        logger.debug("browser open skipped: port 0 (bound port not knowable before listen)")
    else:
        threading.Thread(
            target=_open_browser_when_ready, args=(host, port, instance), daemon=True
        ).start()


class _HideKnownStartupFailure(logging.Filter):
    """Drop uvicorn's traceback once the lifespan has recorded a typed failure.

    A failure the user caused gets one line from `_run_server`, not a stack
    (`cli/spec.md` § "Errors the CLI catches"). Any other failure records
    nothing here, so a bug in our own code still shows its traceback.
    """

    def __init__(self, app: FastAPI) -> None:
        super().__init__()
        self._app = app

    def filter(self, record: logging.LogRecord) -> bool:
        return getattr(self._app.state, "startup_error", None) is None


def _run_server(
    app: FastAPI, host: str, port: int, instance: str, config_path: Path, err_console: Console
) -> int:
    """Run uvicorn, and translate how it ended into an exit code.

    Everything from the socket inwards belongs to `api/`; this owns only
    the startup failures and the exit code (`cli/spec.md` § Out of scope).
    """
    import uvicorn

    uvicorn_logger = logging.getLogger("uvicorn.error")
    hide_known_failure = _HideKnownStartupFailure(app)
    uvicorn_logger.addFilter(hide_known_failure)
    try:
        uvicorn.run(
            app, host=host, port=port, log_level="info", headers=[(_INSTANCE_HEADER, instance)]
        )
    except (OSError, OverflowError) as exc:
        # OverflowError, not an OSError subclass, is what `socket.bind`
        # raises for a resolved port outside 0-65535 — reachable from both
        # `--port` and `server.port`, neither of which is range-checked.
        err_console.print(
            f"[red]error:[/red] failed to bind {escape(host)}:{port}: {escape(str(exc))}"
        )
        return 1
    except SystemExit:
        # mame-curator-1139: uvicorn reports a startup failure by calling
        # `sys.exit` itself, with 1 for a failed bind and 3 for a failed
        # lifespan. The code is its own; ours for "failed to start" is 1, and 3
        # means a cancelled copy (`cli/spec.md` § Exit codes).
        cause = getattr(app.state, "startup_error", None)
        if cause is not None:
            reason = " ".join(str(cause).split())
            err_console.print(
                f"[red]error:[/red] could not start with {shown_path(config_path)}: "
                f"{escape(reason)}"
            )
        else:
            err_console.print(
                f"[red]error:[/red] the server could not start on {escape(host)}:{port}. "
                "The lines above say why. If the port is in use, MAME Curator may "
                "already be running."
            )
        return 1
    except KeyboardInterrupt:
        # FP28 D1: uvicorn catches Ctrl-C internally and returns normally
        # in the current version; this except is defence-in-depth for a
        # future re-raise. POSIX convention for SIGINT is exit 130.
        return 130
    finally:
        uvicorn_logger.removeFilter(hide_known_failure)
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
                f"{shown_path(config_path)}: {escape(str(exc))}"
            )
            return 1
    if not config_path.exists():
        # Only reachable for an explicit --config: layer 2 is skipped when
        # absent and layer 3 was just created.
        err_console.print(
            f"[red]error:[/red] config file not found: {shown_path(config_path)} — "
            "check the path, or run `mame-curator setup --out` with it first"
        )
        return 1

    try:
        # `uvicorn` is imported for the probe, not for use here — `_run_server`
        # imports it again where it is actually called. Its absence must be
        # reported as the one actionable line below (exit-1 path 3) rather
        # than as an ImportError traceback from deeper in the command.
        import uvicorn  # noqa: F401

        from mame_curator.api.errors import ConfigError
        from mame_curator.api.state import data_dir_for
    except ImportError as exc:
        err_console.print(
            f"[red]error:[/red] the web-server packages could not be loaded "
            f"({escape(str(exc))}); reinstall MAME Curator"
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
    skip_reason = _browser_skip_reason(
        enabled=server.open_browser_on_start,
        suppressed=args.no_open_browser,
        managed=os.environ.get("LWSM_MANAGED") == "1",
    )

    data_dir = data_dir_for(config_path)
    lock = InstanceLock(data_dir)
    if not lock.claim("" if port == 0 else _browser_address(host, port)[1]):
        return _hand_over(data_dir, config_path, skip_reason, err_console)
    try:
        return _start(args, config_path, host, port, server, err_console)
    finally:
        lock.release()


def _hand_over(
    data_dir: Path, config_path: Path, skip_reason: str | None, err_console: Console
) -> int:
    """Another copy holds this data folder: point the user at it, start nothing."""
    url = running_url(data_dir)
    if url is None:
        err_console.print(
            f"[red]error:[/red] MAME Curator is already running with {shown_path(config_path)}. "
            "Use the copy that is open, or close it first."
        )
        return 1
    Console(soft_wrap=True).print(f"MAME Curator is already running at {escape(url)}")
    if skip_reason is not None:
        logger.debug("browser open skipped: %s", skip_reason)
    else:
        _open_url(url)
    return 0


def _start(
    args: argparse.Namespace,
    config_path: Path,
    host: str,
    port: int,
    server: ServerConfig,
    err_console: Console,
) -> int:
    """Build the app and run it: stage 3, with this copy's claim held."""
    from mame_curator.api import create_app
    from mame_curator.api.errors import ConfigError

    # A safety net: create_app validates nothing today, and a config error
    # surfaces later as `_run_server`'s SystemExit. Only the typed errors are
    # caught; a programmer error keeps its traceback (coding-standards § 9).
    try:
        app = create_app(config_path, bind_host=host)
    except (ConfigError, ParserError, FilterError) as exc:
        err_console.print(f"[red]error:[/red] failed to create app: {escape(str(exc))}")
        return 1

    instance = secrets.token_hex(16)
    _maybe_open_browser(
        host,
        port,
        instance,
        enabled=server.open_browser_on_start,
        suppressed=args.no_open_browser,
        managed=os.environ.get("LWSM_MANAGED") == "1",
    )

    return _run_server(app, host, port, instance, config_path, err_console)

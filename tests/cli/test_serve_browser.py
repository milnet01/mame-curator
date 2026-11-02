"""Browser auto-open for `mame-curator serve`.

The open is not a chain: `server.open_browser_on_start` decides, and
`--no-open-browser` can only suppress. It fires from a daemon thread that
**polls the resolved address until this server answers there** — uvicorn runs
the application lifespan (a ~48 MB DAT parse) before it creates the
listening socket, so any fixed delay is simultaneously too short on a cold
start and too long on a warm one. A port that merely accepts is not enough:
another program, or another copy of this app, may hold it.

The poll is best-effort by contract: it can never raise into the server,
never touches the exit code, and each non-open outcome logs its own
distinguishable `DEBUG` line so a test can tell them apart.

See `src/mame_curator/cli/spec.md` § Browser.
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import socket
import stat
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import closing, contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from mame_curator.cli.commands import serve as serve_mod
from mame_curator.cli.commands.serve import _cmd_serve, _is_wildcard, _open_browser_when_ready

LOGGER_NAME = "mame_curator.cli.commands.serve"
_THIS_RUN = "this-server"


def _serve_args(
    config: Path, *, port: int | None = None, no_open_browser: bool = False
) -> argparse.Namespace:
    return argparse.Namespace(config=config, host=None, port=port, no_open_browser=no_open_browser)


def _config(tmp_path: Path, body: str = "paths: {}\n") -> Path:
    config = tmp_path / "config.yaml"
    config.write_text(body)
    return config


def _free_port() -> int:
    """An ephemeral port that nothing is listening on by the time we return."""
    with closing(socket.socket()) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _serve_capturing_thread(
    args: argparse.Namespace,
) -> tuple[int, list[dict[str, Any]]]:
    """Run `_cmd_serve`; return (rc, the kwargs of each Thread constructed).

    The thread is captured rather than run: whether the poller is *started*
    is this layer's contract, and `_open_browser_when_ready` is tested
    directly below. The whole `threading` name is replaced rather than
    `threading.Thread` patched in place — the latter mutates the stdlib
    module for every thread in the process, not just this call.
    """
    with (
        patch("mame_curator.api.create_app"),
        patch("uvicorn.run"),
        patch.object(serve_mod, "threading") as threading_mock,
    ):
        rc = _cmd_serve(args)
    return rc, [call.kwargs for call in threading_mock.Thread.call_args_list]


class _Answering(ThreadingHTTPServer):
    """An HTTP server whose replies carry `header_value`, if it is set."""

    header_value: str | None = None


class _Handler(BaseHTTPRequestHandler):
    server: _Answering

    def do_HEAD(self) -> None:
        self.send_response(200)
        if self.server.header_value is not None:
            self.send_header(serve_mod._INSTANCE_HEADER, self.server.header_value)
        self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        pass


class _Answering6(_Answering):
    address_family = socket.AF_INET6


@contextmanager
def _http_server(
    header_value: str | None = None, *, cls: type[_Answering] = _Answering, host: str = "127.0.0.1"
) -> Iterator[_Answering]:
    server = cls((host, 0), _Handler)
    server.header_value = header_value
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _serve_with_real_poller(
    monkeypatch: pytest.MonkeyPatch,
    args: argparse.Namespace,
    *,
    answer_for: _Answering | None = None,
    wait_s: float = 1.0,
) -> Any:
    """Run `_cmd_serve` with a real poller thread and a stand-in for uvicorn.

    The stand-in "runs" for `wait_s`, or until the browser opens. Given
    `answer_for`, it makes that server answer with the identity `serve` handed
    to uvicorn, which is what a real uvicorn does on every reply.
    Returns the `webbrowser` mock.
    """
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.delenv("LWSM_MANAGED", raising=False)
    monkeypatch.setattr(serve_mod, "_BROWSER_POLL_TIMEOUT_S", 30.0)
    monkeypatch.setattr(serve_mod, "_BROWSER_POLL_INTERVAL_S", 0.01)
    monkeypatch.setattr(serve_mod, "_BROWSER_CONNECT_TIMEOUT_S", 0.2)
    opened = threading.Event()

    def _open(_url: str) -> bool:
        opened.set()
        return True

    def _fake_uvicorn_run(_app: Any, **kwargs: Any) -> None:
        if answer_for is not None:
            answer_for.header_value = dict(kwargs["headers"])[serve_mod._INSTANCE_HEADER]
        opened.wait(timeout=wait_s)

    with (
        patch("mame_curator.api.create_app"),
        patch("uvicorn.run", _fake_uvicorn_run),
        patch.object(serve_mod, "webbrowser") as webbrowser_mock,
    ):
        webbrowser_mock.open.side_effect = _open
        assert _cmd_serve(args) == 130
    return webbrowser_mock


# ---- _is_wildcard ----------------------------------------------------


# S104: wildcard literals under test as *values*; no socket is bound to them.
@pytest.mark.parametrize("host", ["", "0.0.0.0", "::", "[::]", "::0"])  # noqa: S104
def test_wildcard_hosts_are_detected(host: str) -> None:
    """A wildcard is an address to listen on, not one to connect to."""
    assert _is_wildcard(host) is True


@pytest.mark.parametrize("host", ["127.0.0.1", "192.168.1.5", "localhost", "myhost.local", "::1"])
def test_non_wildcard_hosts_are_used_as_given(host: str) -> None:
    """A bare `ip_address(host).is_unspecified` raises on the hostnames here."""
    assert _is_wildcard(host) is False


# ---- The decision: config default, one-way suppression ---------------


def test_browser_opens_by_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """`ServerConfig.open_browser_on_start` defaults true."""
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.delenv("LWSM_MANAGED", raising=False)
    rc, started = _serve_capturing_thread(_serve_args(_config(tmp_path)))

    assert rc == 130
    assert len(started) == 1
    assert started[0]["target"] is serve_mod._open_browser_when_ready
    assert started[0]["daemon"] is True, "a failed open must never hold the process open"


def test_browser_skipped_when_config_disables_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.delenv("PORT", raising=False)
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)

    _, started = _serve_capturing_thread(
        _serve_args(_config(tmp_path, "server: {open_browser_on_start: false}\n"))
    )

    assert not started
    assert "browser open skipped: disabled by config" in caplog.text


def test_browser_skipped_by_flag_against_config_true(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """The flag suppresses; there is deliberately no flag that forces an open on."""
    monkeypatch.delenv("PORT", raising=False)
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)

    _, started = _serve_capturing_thread(
        _serve_args(
            _config(tmp_path, "server: {open_browser_on_start: true}\n"), no_open_browser=True
        )
    )

    assert not started
    assert "browser open skipped: disabled by flag" in caplog.text


def test_browser_skipped_when_started_by_lwsm(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """LocalWebServerManager has its own Open button, so a second page is unwanted."""
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.setenv("LWSM_MANAGED", "1")
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)

    _, started = _serve_capturing_thread(
        _serve_args(_config(tmp_path, "server: {open_browser_on_start: true}\n"))
    )

    assert not started
    assert "browser open skipped: started by LocalWebServerManager" in caplog.text


@pytest.mark.parametrize("value", ["", "0", "true"])
def test_browser_opens_when_lwsm_marker_is_not_one(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, value: str
) -> None:
    """Only the exact value `1` means managed; anything else is the unchanged path."""
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.setenv("LWSM_MANAGED", value)

    _, started = _serve_capturing_thread(_serve_args(_config(tmp_path)))

    assert len(started) == 1


def test_browser_skipped_when_port_is_zero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """`--port 0` means "any free port" — the bound port is not knowable here."""
    monkeypatch.delenv("PORT", raising=False)
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)

    _, started = _serve_capturing_thread(_serve_args(_config(tmp_path), port=0))

    assert not started
    assert "browser open skipped: port 0" in caplog.text


def test_skip_lines_are_debug_not_info(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A browser that did not open is not a malfunction — `-v` shows it, a default run does not."""
    monkeypatch.delenv("PORT", raising=False)
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    _serve_capturing_thread(_serve_args(_config(tmp_path), port=0))

    assert "browser open skipped" not in caplog.text


# ---- The poller ------------------------------------------------------


@pytest.mark.parametrize(
    ("bind_host", "expected_host"),
    [("127.0.0.1", "127.0.0.1"), ("0.0.0.0", "127.0.0.1")],  # noqa: S104
    ids=["loopback", "wildcard-connects-to-loopback"],
)
def test_poller_opens_once_this_server_answers(bind_host: str, expected_host: str) -> None:
    """The open coincides with this server answering, not with a timer.

    The wildcard case is the one a fixed delay cannot fix either way: a
    wildcard is an address to listen on, not one to connect to.
    """
    with (
        _http_server(_THIS_RUN) as server,
        patch.object(serve_mod, "webbrowser") as webbrowser_mock,
    ):
        port = server.server_address[1]
        _open_browser_when_ready(bind_host, port, _THIS_RUN)

    webbrowser_mock.open.assert_called_once_with(f"http://{expected_host}:{port}/")


def test_poller_gives_up_after_the_budget(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Nothing is listening — the poll exhausts its budget and says so."""
    monkeypatch.setattr(serve_mod, "_BROWSER_POLL_TIMEOUT_S", 0.2)
    monkeypatch.setattr(serve_mod, "_BROWSER_POLL_INTERVAL_S", 0.01)
    monkeypatch.setattr(serve_mod, "_BROWSER_CONNECT_TIMEOUT_S", 0.05)
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
    port = _free_port()

    with patch.object(serve_mod, "webbrowser") as webbrowser_mock:
        _open_browser_when_ready("127.0.0.1", port, _THIS_RUN)

    webbrowser_mock.open.assert_not_called()
    assert "browser open gave up" in caplog.text
    assert str(port) in caplog.text


def test_poller_survives_a_raising_webbrowser(caplog: pytest.LogCaptureFixture) -> None:
    """`webbrowser.open` raising must not escape the thread."""
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
    with (
        _http_server(_THIS_RUN) as server,
        patch.object(serve_mod, "webbrowser") as webbrowser_mock,
    ):
        webbrowser_mock.open.side_effect = OSError("no opener")
        _open_browser_when_ready("127.0.0.1", server.server_address[1], _THIS_RUN)

    assert "browser open failed: no opener" in caplog.text


def test_raising_webbrowser_does_not_change_the_exit_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """End to end, through a real daemon thread: the poll cannot fail the server."""
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.delenv("LWSM_MANAGED", raising=False)
    monkeypatch.setattr(serve_mod, "_BROWSER_POLL_TIMEOUT_S", 5.0)
    monkeypatch.setattr(serve_mod, "_BROWSER_POLL_INTERVAL_S", 0.01)
    monkeypatch.setattr(serve_mod, "_BROWSER_CONNECT_TIMEOUT_S", 0.05)
    attempted = threading.Event()

    def _fail(url: str) -> bool:
        attempted.set()
        raise OSError("no opener")

    def _fake_uvicorn_run(_app: Any, **kwargs: Any) -> None:
        server.header_value = dict(kwargs["headers"])[serve_mod._INSTANCE_HEADER]

    with (
        _http_server() as server,
        patch("mame_curator.api.create_app"),
        patch("uvicorn.run", _fake_uvicorn_run),
        patch.object(serve_mod, "webbrowser") as webbrowser_mock,
    ):
        webbrowser_mock.open.side_effect = _fail
        rc = _cmd_serve(_serve_args(_config(tmp_path), port=server.server_address[1]))
        assert attempted.wait(timeout=10), "the poller never reached webbrowser.open"

    assert rc == 130


# ---- The open is for this server, not for whatever holds the port -----


@pytest.mark.parametrize("foreign_header", [None, "another-copy"], ids=["other-app", "other-copy"])
def test_browser_does_not_open_another_programs_page(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, foreign_header: str | None
) -> None:
    """Another app, or another copy of this one, holds the port: no browser."""
    with _http_server(foreign_header) as foreign:
        args = _serve_args(_config(tmp_path), port=foreign.server_address[1])
        webbrowser_mock = _serve_with_real_poller(monkeypatch, args)

    webbrowser_mock.open.assert_not_called()


def test_browser_does_not_open_on_a_port_that_never_answers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A service that accepts and stays silent is not this server either."""
    with closing(socket.socket()) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        args = _serve_args(_config(tmp_path), port=int(listener.getsockname()[1]))
        webbrowser_mock = _serve_with_real_poller(monkeypatch, args)

    webbrowser_mock.open.assert_not_called()


def test_browser_opens_when_this_server_answers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The identity `serve` hands to uvicorn is the one the poller looks for."""
    with _http_server() as server:
        port = server.server_address[1]
        args = _serve_args(_config(tmp_path), port=port)
        webbrowser_mock = _serve_with_real_poller(monkeypatch, args, answer_for=server, wait_s=10.0)

    webbrowser_mock.open.assert_called_once_with(f"http://127.0.0.1:{port}/")


def test_browser_url_brackets_an_ipv6_address(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`http://::1:8080/` is not a working address."""
    try:
        context = _http_server(cls=_Answering6, host="::1")
        server = context.__enter__()
    except OSError:
        pytest.skip("no IPv6 loopback here")
    try:
        port = server.server_address[1]
        args = argparse.Namespace(
            config=_config(tmp_path), host="::1", port=port, no_open_browser=False
        )
        webbrowser_mock = _serve_with_real_poller(monkeypatch, args, answer_for=server, wait_s=10.0)
    finally:
        context.__exit__(None, None, None)

    webbrowser_mock.open.assert_called_once_with(f"http://[::1]:{port}/")


def test_browser_that_cannot_start_logs_its_own_line(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`webbrowser.open` returning False is a non-open outcome, so it has a line."""
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.delenv("LWSM_MANAGED", raising=False)
    monkeypatch.setattr(serve_mod, "_BROWSER_POLL_INTERVAL_S", 0.01)
    attempted = threading.Event()

    def _no_browser(_url: str) -> bool:
        attempted.set()
        return False

    def _fake_uvicorn_run(_app: Any, **kwargs: Any) -> None:
        server.header_value = dict(kwargs["headers"])[serve_mod._INSTANCE_HEADER]
        attempted.wait(timeout=10)
        time.sleep(0.05)

    with (
        _http_server() as server,
        patch("mame_curator.api.create_app"),
        patch("uvicorn.run", _fake_uvicorn_run),
        patch.object(serve_mod, "webbrowser") as webbrowser_mock,
    ):
        webbrowser_mock.open.side_effect = _no_browser
        _cmd_serve(_serve_args(_config(tmp_path), port=server.server_address[1]))

    assert "browser open failed: no browser could be started" in caplog.text


# ---- Against a real uvicorn -------------------------------------------


def _browser_recorder(tmp_path: Path) -> tuple[dict[str, str], Path]:
    """An environment whose `webbrowser.open` writes the URL to a file."""
    record = tmp_path / "opened.txt"
    script = tmp_path / "fake-browser"
    script.write_text(f'#!/bin/sh\nprintf \'%s\\n\' "$1" >> "{record}"\n')
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    env = {k: v for k, v in os.environ.items() if k != "PORT"}
    env["BROWSER"] = f"{script} %s"
    return env, record


def _real_serve(env: dict[str, str], config: Path, port: int) -> subprocess.Popen[str]:
    # S603: the interpreter running this suite and the project's own entry point.
    return subprocess.Popen(  # noqa: S603
        [
            sys.executable,
            "-c",
            "from mame_curator.main import main; raise SystemExit(main())",
            "serve",
            "--config",
            str(config),
            "--port",
            str(port),
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


_STARTS = """\
paths:
  source_roms: /nonexistent/roms
  source_dat: /nonexistent/dat.xml
  dest_roms: /nonexistent/dest
  retroarch_playlist: /nonexistent/dest/mame.lpl
"""

_POSIX_ONLY = pytest.mark.skipif(
    sys.platform == "win32", reason="uses a shell-script browser and SIGINT"
)


@pytest.mark.slow
@_POSIX_ONLY
def test_real_server_opens_the_browser_at_itself(tmp_path: Path) -> None:
    """The header really reaches the wire, so the check passes for the real server."""
    env, record = _browser_recorder(tmp_path)
    port = _free_port()
    proc = _real_serve(env, _config(tmp_path, _STARTS), port)
    try:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline and not record.exists() and proc.poll() is None:
            time.sleep(0.1)
    finally:
        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=30)

    assert record.read_text().splitlines() == [f"http://127.0.0.1:{port}/"]


@pytest.mark.slow
@_POSIX_ONLY
def test_real_second_copy_opens_nothing_and_exits_1(tmp_path: Path) -> None:
    """The finding's own case: something else already holds the port."""
    env, record = _browser_recorder(tmp_path)
    with _http_server() as holder:
        proc = _real_serve(env, _config(tmp_path, _STARTS), holder.server_address[1])
        rc = proc.wait(timeout=60)

    assert rc == 1
    assert not record.exists()

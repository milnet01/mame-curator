"""Browser auto-open for `mame-curator serve`.

The open is not a chain: `server.open_browser_on_start` decides, and
`--no-open-browser` can only suppress. It fires from a daemon thread that
**polls the resolved address until it accepts a connection** — uvicorn runs
the application lifespan (a ~48 MB DAT parse) before it creates the
listening socket, so any fixed delay is simultaneously too short on a cold
start and too long on a warm one.

The poll is best-effort by contract: it can never raise into the server,
never touches the exit code, and each non-open outcome logs its own
distinguishable `DEBUG` line so a test can tell them apart.

See `src/mame_curator/cli/spec.md` § Browser.
"""

from __future__ import annotations

import argparse
import logging
import socket
import threading
from contextlib import closing
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from mame_curator.cli.commands import serve as serve_mod
from mame_curator.cli.commands.serve import _cmd_serve, _is_wildcard, _open_browser_when_ready

LOGGER_NAME = "mame_curator.cli.commands.serve"


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
def test_poller_opens_once_the_port_accepts(bind_host: str, expected_host: str) -> None:
    """The open coincides with the port actually accepting, not with a timer.

    The wildcard case is the one a fixed delay cannot fix either way: a
    wildcard is an address to listen on, not one to connect to.
    """
    with closing(socket.socket()) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = int(listener.getsockname()[1])

        with patch.object(serve_mod, "webbrowser") as webbrowser_mock:
            _open_browser_when_ready(bind_host, port)

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
        _open_browser_when_ready("127.0.0.1", port)

    webbrowser_mock.open.assert_not_called()
    assert "browser open gave up" in caplog.text
    assert str(port) in caplog.text


def test_poller_survives_a_raising_webbrowser(caplog: pytest.LogCaptureFixture) -> None:
    """`webbrowser.open` raising must not escape the thread."""
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
    with closing(socket.socket()) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = int(listener.getsockname()[1])

        with patch.object(serve_mod, "webbrowser") as webbrowser_mock:
            webbrowser_mock.open.side_effect = OSError("no opener")
            _open_browser_when_ready("127.0.0.1", port)

    assert "browser open failed: no opener" in caplog.text


def test_raising_webbrowser_does_not_change_the_exit_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """End to end, through a real daemon thread: the poll cannot fail the server."""
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.setattr(serve_mod, "_BROWSER_POLL_TIMEOUT_S", 5.0)
    monkeypatch.setattr(serve_mod, "_BROWSER_POLL_INTERVAL_S", 0.01)
    monkeypatch.setattr(serve_mod, "_BROWSER_CONNECT_TIMEOUT_S", 0.05)
    attempted = threading.Event()

    def _fail(url: str) -> bool:
        attempted.set()
        raise OSError("no opener")

    with (
        closing(socket.socket()) as listener,
        patch("mame_curator.api.create_app"),
        patch("uvicorn.run"),
        patch.object(serve_mod, "webbrowser") as webbrowser_mock,
    ):
        webbrowser_mock.open.side_effect = _fail
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        rc = _cmd_serve(_serve_args(_config(tmp_path), port=int(listener.getsockname()[1])))
        assert attempted.wait(timeout=10), "the poller never reached webbrowser.open"

    assert rc == 130

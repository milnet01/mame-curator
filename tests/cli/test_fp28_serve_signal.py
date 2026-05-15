"""FP28 D1 + D2 — `_cmd_serve` exit codes and exception narrowing.

D1: ``cli/__init__.py:492`` wraps ``uvicorn.run(app, ...)``; uvicorn catches
``KeyboardInterrupt`` internally and returns normally, after which the
function falls through to ``return 0`` at L496. POSIX convention for Ctrl-C
is exit 130. D1 wraps ``uvicorn.run`` in ``try / except KeyboardInterrupt:
return 130`` and changes the trailing return to ``return 130`` as a defensive
fall-through.

D2: ``cli/__init__.py:485`` catches ``except Exception as exc:`` for the
``create_app`` call and squashes any uncaught exception into a one-line
"failed to create app: ..." stderr message. D2 narrows the catch to
``(ConfigError, ParserError, FilterError)`` so unexpected exceptions
propagate as tracebacks — the actionable signal for programmer errors.

Pre-fix: D2 — ``RuntimeError`` from ``create_app`` returns 1 with a one-line
stderr message; ``pytest.raises(RuntimeError)`` doesn't fire → test fails.
Post-fix: D2 — ``RuntimeError`` propagates; ``pytest.raises`` catches it.

D1 test is slow (subprocess + port + signal); marked ``@pytest.mark.slow``.

See ``docs/specs/FP28.md`` §§ D1, D2.
"""

from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port: int = s.getsockname()[1]
        return port


def _build_minimal_config(tmp_path: Path) -> Path:
    """Write a config.yaml that boots end-to-end against the mini-DAT fixture.

    Pytest's conftest discovery doesn't surface ``tests/api/conftest.py``'s
    ``config_file`` fixture under ``tests/cli/``; this helper reproduces a
    subset of its shape — enough for ``build_world`` to succeed and uvicorn
    to bind so the SIGINT path is reachable.
    """
    fixtures = Path(__file__).resolve().parents[1]
    parser_fixtures = fixtures / "parser" / "fixtures"
    src = tmp_path / "src"
    src.mkdir()
    dest = tmp_path / "dest"
    dest.mkdir()
    config = tmp_path / "config.yaml"
    config.write_text(
        f"paths:\n"
        f"  source_roms: {src}\n"
        f"  source_dat: {parser_fixtures / 'mini.dat.xml'}\n"
        f"  dest_roms: {dest}\n"
        f"  retroarch_playlist: {dest}/mame.lpl\n"
    )
    return config


@pytest.mark.slow
@pytest.mark.skipif(
    sys.platform == "win32",
    reason="uvicorn signal handling differs on Windows; POSIX is the load-bearing case",
)
def test_serve_returns_130_on_keyboard_interrupt(tmp_path: Path) -> None:
    """Spawn ``mame-curator serve``, send SIGINT, assert returncode == 130."""
    import signal

    config_file = _build_minimal_config(tmp_path)
    port = _find_free_port()

    # Spawning the project's own console_scripts entry point — there is no
    # untrusted input here and the partial path is the canonical install
    # invocation. Threat-model: this test runs inside the project's own
    # test suite against the same `mame-curator` the developer just built.
    proc = subprocess.Popen(  # noqa: S603
        [  # noqa: S607
            "mame-curator",
            "serve",
            "--config",
            str(config_file),
            "--port",
            str(port),
            "--host",
            "127.0.0.1",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for port to bind (max ~10 s — server has to parse DAT + INIs).
    deadline = time.monotonic() + 10.0
    bound = False
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            _stdout, stderr = proc.communicate()
            pytest.fail(
                f"server exited before binding "
                f"(rc={proc.returncode}); stderr={stderr.decode(errors='replace')!r}"
            )
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                bound = True
                break
        except OSError:
            time.sleep(0.1)

    if not bound:
        proc.kill()
        proc.wait()
        pytest.fail("server did not bind to port within deadline")

    proc.send_signal(signal.SIGINT)
    try:
        proc.wait(timeout=5.0)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        pytest.fail("server did not exit within deadline after SIGINT")

    assert proc.returncode == 130, (
        f"FP28 D1 — expected exit 130 (POSIX Ctrl-C convention), got {proc.returncode}"
    )


def test_serve_does_not_swallow_unknown_exception(tmp_path: Path) -> None:
    """Monkeypatch ``create_app`` to raise ``RuntimeError``; assert it propagates."""
    from mame_curator.cli import _cmd_serve

    # The patched create_app never touches the file — but `_cmd_serve`'s
    # config-existence pre-check at L465 runs first and bails out with
    # exit 1 if the path doesn't exist. A zero-byte file is enough.
    config = tmp_path / "config.yaml"
    config.write_text("paths: {}\n")

    args = argparse.Namespace(
        config=config,
        host="127.0.0.1",
        port=8080,
    )

    with (
        patch("mame_curator.api.create_app", side_effect=RuntimeError("boom")),
        pytest.raises(RuntimeError, match="boom"),
    ):
        _cmd_serve(args)

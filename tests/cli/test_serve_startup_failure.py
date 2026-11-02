"""A server that fails to start exits 1 with one `error:` line (mame-curator-1139).

uvicorn does not raise on a startup failure. It logs, then calls `sys.exit`:
1 when the bind fails, 3 when the application lifespan fails. Exit 3 belongs to
`copy`'s playlist-conflict cancel (`cli/spec.md` § Exit codes), so `serve` must
not let either code through. A failure the user caused, such as a bad value in
`config.yaml`, must not bury its one line under a traceback; a bug in our own
code still shows one (§ "Errors the CLI catches").
"""

from __future__ import annotations

import argparse
import socket
import subprocess
import sys
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import pytest

from mame_curator.cli.commands.serve import _cmd_serve

_BAD_SECTION = """\
paths:
  source_roms: /nonexistent/roms
  source_dat: /nonexistent/dat.xml
  dest_roms: /nonexistent/dest
  retroarch_playlist: /nonexistent/dest/mame.lpl
filters:
  region_priority: 5
"""


def _free_port() -> int:
    with closing(socket.socket()) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _args(config: Path, port: int) -> argparse.Namespace:
    return argparse.Namespace(config=config, host=None, port=port, no_open_browser=True)


def _serve_subprocess(config: Path, port: int) -> subprocess.CompletedProcess[str]:
    """Run the real command, because only a real uvicorn exits the way uvicorn does."""
    # S603: the interpreter running this suite and the project's own entry point.
    return subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-c",
            "from mame_curator.main import main; raise SystemExit(main())",
            "serve",
            "--config",
            str(config),
            "--port",
            str(port),
            "--no-open-browser",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def _error_lines(output: str) -> list[str]:
    return [line for line in output.splitlines() if line.startswith("error:")]


@pytest.mark.parametrize("code", [1, 3, None, "text"], ids=["bind", "lifespan", "none", "text"])
def test_any_uvicorn_exit_becomes_exit_1_with_one_error_line(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    code: int | str | None,
) -> None:
    """Whatever uvicorn exits with, `serve` says so once and returns 1."""
    monkeypatch.delenv("PORT", raising=False)
    config = tmp_path / "config.yaml"
    config.write_text("paths: {}\n")

    with patch("mame_curator.api.create_app"), patch("uvicorn.run", side_effect=SystemExit(code)):
        try:
            rc = _cmd_serve(_args(config, 18000))
        except SystemExit as exc:
            pytest.fail(f"uvicorn's SystemExit({exc.code!r}) escaped _cmd_serve")

    assert rc == 1
    assert len(_error_lines(capsys.readouterr().err)) == 1


@pytest.mark.slow
def test_bad_value_in_another_section_is_one_line_naming_the_file(tmp_path: Path) -> None:
    """The real path of 1139: the lifespan refuses the config."""
    config = tmp_path / "config.yaml"
    config.write_text(_BAD_SECTION)

    result = _serve_subprocess(config, _free_port())

    assert result.returncode == 1, result.stderr
    errors = _error_lines(result.stderr)
    assert len(errors) == 1, result.stderr
    assert str(config) in errors[0]
    assert "region_priority" in errors[0], "the line must carry the cause"
    assert "Traceback" not in result.stderr


@pytest.mark.slow
def test_taken_port_is_exit_1_with_one_error_line(tmp_path: Path) -> None:
    """A bind failure: uvicorn logs the reason, and `serve` adds what it means."""
    config = tmp_path / "config.yaml"
    config.write_text(_BAD_SECTION.replace("filters:\n  region_priority: 5\n", ""))

    with closing(socket.socket()) as holder:
        holder.bind(("127.0.0.1", 0))
        holder.listen(1)
        result = _serve_subprocess(config, int(holder.getsockname()[1]))

    assert result.returncode == 1, result.stderr
    assert len(_error_lines(result.stderr)) == 1, result.stderr
    assert "Traceback" not in result.stderr


def test_a_bug_in_the_lifespan_still_shows_its_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    """A programmer error is not flattened: the stack is what a bug report needs."""
    monkeypatch.delenv("PORT", raising=False)
    config = tmp_path / "config.yaml"
    config.write_text(_BAD_SECTION)

    with patch("mame_curator.api.app.build_world", side_effect=RuntimeError("our bug")):
        rc = _cmd_serve(_args(config, _free_port()))

    captured = capfd.readouterr()
    assert rc == 1
    assert "Traceback" in captured.err
    assert "our bug" in captured.err

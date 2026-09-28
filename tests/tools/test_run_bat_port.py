"""`$PORT` contract for `run.bat` — the Windows bootstrap entry point.

`run.bat` must hand `%PORT%` to `serve` untouched and never forward it as
`--port`. An explicit `--port` skips `_resolve_port`'s validation and hides
`server.port` in config.yaml (mame-curator-1089): `PORT=abc` then reached
argparse and exited 2 instead of the named exit-1 error.

The script is run for real against a stub `uv.cmd` on `PATH` that records
its argv and the `PORT` it inherited, so the assertion is on the command
line `run.bat` builds. `tests/cli/test_serve_port_env.py` pins the Python
half — the validation itself.

The absent-`PORT` case also proves the script gets past its first two
sections at all. Before 1089 it could not on any Windows machine: a `^`
inside the quoted `python -c` version check reached Python as a syntax
error ("Python 3.13 is too old"), and a `)` inside an echo in the uv
`if (...)` block closed the block early ("... was unexpected at this
time"). Both were found running this script on a Windows host.

Windows-only: `cmd.exe` exists nowhere else. CI's `windows-latest` leg
runs it. See `src/mame_curator/cli/spec.md` § "`serve` host, port and
browser resolution".
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="run.bat is the Windows bootstrap; it needs cmd.exe",
)

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_BAT = REPO_ROOT / "run.bat"

# Delayed expansion so a PORT holding cmd metacharacters is logged, not
# parsed. `%*` is safe: run.bat's own arguments never carry them.
_STUB_UV = """@echo off
setlocal enabledelayedexpansion
>>"%UV_LOG%" echo %*
if "%1"=="run" >>"%UV_LOG%" echo PORT=[!PORT!]
exit /b 0
"""


class _Result:
    def __init__(self, returncode: int, output: str, uv_log: list[str]):
        self.returncode = returncode
        self.output = output
        self.uv_log = uv_log

    @property
    def serve_argv(self) -> str | None:
        """The `uv run mame-curator serve ...` line, if it was reached."""
        return next((line for line in self.uv_log if "serve" in line), None)

    @property
    def serve_port_env(self) -> str | None:
        """The `PORT` value the stubbed `uv run` inherited."""
        return next((line for line in self.uv_log if line.startswith("PORT=")), None)


RunBat = Callable[[str | None], _Result]


@pytest.fixture
def run_bat(tmp_path: Path) -> RunBat:
    """Return a callable that runs a copy of `run.bat` in a sandbox.

    The sandbox has a stub `uv.cmd` first on `PATH` and a `config.yaml`, so
    the setup branch is skipped. `python` is the real one — the version
    gate at the top of the script is part of what's being run.
    """
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    shutil.copy(RUN_BAT, sandbox / "run.bat")
    (sandbox / "config.yaml").write_text("paths: {}\n")

    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    (stub_bin / "uv.cmd").write_text(_STUB_UV)

    uv_log = tmp_path / "uv.log"
    uv_log.touch()

    def _run(port: str | None) -> _Result:
        env = {k: v for k, v in os.environ.items() if k.upper() != "PORT"}
        env["PATH"] = f"{stub_bin}{os.pathsep}{os.environ['PATH']}"
        env["UV_LOG"] = str(uv_log)
        if port is not None:
            env["PORT"] = port
        # S603 noqa rationale: cmd.exe plus a path to the project's own
        # script, inside a tmp_path sandbox, with no untrusted input.
        proc = subprocess.run(  # noqa: S603
            ["cmd.exe", "/c", str(sandbox / "run.bat")],  # noqa: S607
            capture_output=True,
            text=True,
            env=env,
            cwd=str(sandbox),
            check=False,
            timeout=120,
        )
        return _Result(
            proc.returncode,
            proc.stdout + proc.stderr,
            uv_log.read_text().splitlines(),
        )

    return _run


def test_port_absent_serves_without_a_port_flag(run_bat: RunBat) -> None:
    """No `PORT`: the script runs end to end and `server.port` stays reachable."""
    result = run_bat(None)
    assert result.returncode == 0, result.output
    # mame-curator-1106: --no-dev keeps the dev dependency group off end-user installs.
    assert "sync --inexact --no-dev --quiet" in result.uv_log, result.output
    assert result.serve_argv == "run mame-curator serve"
    assert result.serve_port_env == "PORT=[]"
    assert "http://127.0.0.1:/" not in result.output
    assert "Starting MAME Curator" in result.output


@pytest.mark.parametrize("raw", ["5999", "abc", "80"])
def test_port_set_is_left_to_serve(run_bat: RunBat, raw: str) -> None:
    """A set `PORT`, valid or not, reaches `serve` by environment only.

    `serve` validates it; a `--port` flag here would skip that check.
    """
    result = run_bat(raw)
    assert result.returncode == 0, result.output
    assert result.serve_argv == "run mame-curator serve"
    assert result.serve_port_env == f"PORT=[{raw}]"
    assert f"http://127.0.0.1:{raw}/" in result.output


@pytest.mark.parametrize("raw", ["a)b", '"8080"'])
def test_port_with_cmd_metacharacters_does_not_break_the_parse(run_bat: RunBat, raw: str) -> None:
    """A `)` or quote in `PORT` must not end the announce block early."""
    result = run_bat(raw)
    assert "was unexpected at this time" not in result.output
    assert result.returncode == 0, result.output
    assert result.serve_argv == "run mame-curator serve"

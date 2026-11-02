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
if "%1"=="run" >>"%UV_LOG%" echo CD=[!CD!]
if "%1"=="sync" if defined UV_SYNC_RC exit /b %UV_SYNC_RC%
if "%1"=="run" if defined UV_RUN_RC exit /b %UV_RUN_RC%
exit /b 0
"""

# What the Microsoft Store shortcut named `python` does (measured on Windows 10,
# 2026-11-02): `where` finds it, it prints only to stderr, and it exits 9009.
_STUB_STORE_PYTHON = """@echo off
>&2 echo Python was not found; run without arguments to install from the Microsoft Store.
exit /b 9009
"""

_STUB_OLD_PYTHON = """@echo off
echo %* | find "sys.version_info >=" >nul && (echo 1 & exit /b 0)
echo 3.9
exit /b 0
"""

_PAUSE_LINE = "Press any key to close this window"
_INSTALL_WORDS = "Install Python 3.12 or newer"


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
    assert result.serve_argv == "run --no-dev mame-curator serve"
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
    assert result.serve_argv == "run --no-dev mame-curator serve"
    assert result.serve_port_env == f"PORT=[{raw}]"
    assert f"http://127.0.0.1:{raw}/" in result.output


@pytest.mark.parametrize("raw", ["a)b", '"8080"'])
def test_port_with_cmd_metacharacters_does_not_break_the_parse(run_bat: RunBat, raw: str) -> None:
    """A `)` or quote in `PORT` must not end the announce block early."""
    result = run_bat(raw)
    assert "was unexpected at this time" not in result.output
    assert result.returncode == 0, result.output
    assert result.serve_argv == "run --no-dev mame-curator serve"


# ---- Failing well (review-code 2026-11-02, lane 02) -------------------


def _system32() -> str:
    return str(Path(os.environ["SYSTEMROOT"]) / "System32")


class _Sandbox:
    """A copy of `run.bat`, stubs, and the ways a user can start it."""

    def __init__(self, tmp_path: Path, folder: str = "sandbox") -> None:
        self.folder = tmp_path / folder
        self.folder.mkdir()
        self.script = self.folder / "run.bat"
        shutil.copy(RUN_BAT, self.script)
        self.stubs = tmp_path / "bin"
        self.stubs.mkdir()
        self.uv_log = tmp_path / "uv.log"
        self.uv_log.touch()

    def stub(self, name: str, body: str) -> None:
        (self.stubs / name).write_text(body)

    def _env(self, path: str, **extra: str) -> dict[str, str]:
        env = {k: v for k, v in os.environ.items() if k.upper() not in {"PORT", "PATH"}}
        env.update(PATH=path, UV_LOG=str(self.uv_log), **extra)
        return env

    def run(
        self,
        command: str | list[str],
        *,
        path: str | None = None,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> _Result:
        """Run `command` raw, so a test controls the exact command line cmd.exe sees."""
        # S603: cmd.exe and the project's own script, in a tmp_path sandbox. stdin
        # is empty, so a `pause` returns at once instead of hanging the suite.
        proc = subprocess.run(  # noqa: S603
            command,
            capture_output=True,
            text=True,
            env=self._env(path or f"{self.stubs}{os.pathsep}{os.environ['PATH']}", **(env or {})),
            cwd=str(cwd or self.folder),
            check=False,
            stdin=subprocess.DEVNULL,
            timeout=120,
        )
        return _Result(
            proc.returncode, proc.stdout + proc.stderr, self.uv_log.read_text().splitlines()
        )

    def double_click(self, *, cwd: Path | None = None, **extra: str) -> _Result:
        """The command line Windows builds for a double-click (measured)."""
        return self.run(f'cmd.exe /c ""{self.script}" "', cwd=cwd, env=extra)

    def from_powershell(self, **extra: str) -> _Result:
        """The command line PowerShell builds for `.\\run.bat` (measured)."""
        return self.run(f'cmd.exe /c ""{self.script}""', env=extra)

    def from_program(self, **extra: str) -> _Result:
        return self.run(["cmd.exe", "/c", str(self.script)], env=extra)

    def typed_at_a_prompt(self, before: str = "", **extra: str) -> _Result:
        """Type the command into an open prompt: cmd.exe has no `/c` at all."""
        typed = f'{before}"{self.script}"\r\nexit\r\n'
        env = self._env(f"{self.stubs}{os.pathsep}{os.environ['PATH']}", **extra)
        # S603: as `run`.
        proc = subprocess.run(
            ["cmd.exe"],  # noqa: S607
            input=typed,
            capture_output=True,
            text=True,
            env=env,
            cwd=str(self.folder),
            check=False,
            timeout=120,
        )
        return _Result(
            proc.returncode, proc.stdout + proc.stderr, self.uv_log.read_text().splitlines()
        )


@pytest.fixture
def sandbox(tmp_path: Path) -> _Sandbox:
    box = _Sandbox(tmp_path)
    box.stub("uv.cmd", _STUB_UV)
    return box


def test_store_shortcut_counts_as_no_python(sandbox: _Sandbox) -> None:
    """The HIGH finding: "Python  is too old" to someone who has no Python."""
    sandbox.stub("python.cmd", _STUB_STORE_PYTHON)
    result = sandbox.from_program()
    assert result.returncode == 1, result.output
    assert "too old" not in result.output, result.output
    assert _INSTALL_WORDS in result.output, result.output
    assert result.serve_argv is None


def test_store_shortcut_message_is_not_shown(sandbox: _Sandbox) -> None:
    """One instruction, ours: its Store advice would contradict the python.org words."""
    sandbox.stub("python.cmd", _STUB_STORE_PYTHON)
    assert "Microsoft Store" not in sandbox.from_program().output


def test_a_stale_py_ok_in_the_environment_is_ignored(sandbox: _Sandbox) -> None:
    sandbox.stub("python.cmd", _STUB_STORE_PYTHON)
    result = sandbox.from_program(PY_OK="0")
    assert result.returncode == 1, result.output
    assert _INSTALL_WORDS in result.output, result.output


def test_no_python_on_path_gets_the_install_words(sandbox: _Sandbox) -> None:
    result = sandbox.run(
        ["cmd.exe", "/c", str(sandbox.script)], path=f"{sandbox.stubs}{os.pathsep}{_system32()}"
    )
    assert result.returncode == 1, result.output
    assert "python not found" in result.output
    assert _INSTALL_WORDS in result.output


def test_too_old_python_gets_the_version_and_the_install_words(sandbox: _Sandbox) -> None:
    sandbox.stub("python.cmd", _STUB_OLD_PYTHON)
    result = sandbox.from_program()
    assert result.returncode == 1, result.output
    assert "Python 3.9 is too old" in result.output, result.output
    assert _INSTALL_WORDS in result.output, result.output


def test_failed_sync_stops_before_starting(sandbox: _Sandbox) -> None:
    result = sandbox.from_program(UV_SYNC_RC="7")
    assert result.returncode == 7, result.output
    assert "Starting MAME Curator" not in result.output, result.output
    assert result.serve_argv is None


def _real_python_dir() -> str:
    return str(Path(sys.executable).parent)


def test_failed_uv_install_says_so(tmp_path: Path) -> None:
    """A failed install must not claim it completed and send the user to a new window."""
    box = _Sandbox(tmp_path)
    box.stub("powershell.cmd", "@echo off\nexit /b 1\n")
    result = box.run(
        ["cmd.exe", "/c", str(box.script)],
        path=os.pathsep.join([str(box.stubs), _real_python_dir(), _system32()]),
    )
    assert result.returncode == 1, result.output
    assert "could not install uv" in result.output, result.output
    assert "completed" not in result.output, result.output


def test_uv_installed_but_not_on_path_says_open_a_new_window(tmp_path: Path) -> None:
    box = _Sandbox(tmp_path)
    box.stub("powershell.cmd", "@echo off\nexit /b 0\n")
    result = box.run(
        ["cmd.exe", "/c", str(box.script)],
        path=os.pathsep.join([str(box.stubs), _real_python_dir(), _system32()]),
    )
    assert result.returncode == 1, result.output
    assert "new Command Prompt" in result.output, result.output


@pytest.mark.parametrize("folder", ["a!b", "a (b)", "a & b"])
def test_awkward_folder_names_reach_serve(tmp_path: Path, folder: str) -> None:
    """A `!` was eaten by delayed expansion, so `uv` ran in the wrong folder."""
    box = _Sandbox(tmp_path, folder)
    box.stub("uv.cmd", _STUB_UV)
    result = box.double_click(cwd=tmp_path)
    assert result.returncode == 0, result.output
    assert result.serve_argv == "run --no-dev mame-curator serve"
    assert f"CD=[{box.folder}]" in result.uv_log, result.uv_log


def test_double_click_pauses_on_failure(sandbox: _Sandbox) -> None:
    """Without the pause the window closes and takes the error with it."""
    result = sandbox.double_click(UV_RUN_RC="1")
    assert _PAUSE_LINE in result.output, result.output
    assert result.returncode == 1


def test_double_click_pauses_on_an_early_failure_too(sandbox: _Sandbox) -> None:
    sandbox.stub("python.cmd", _STUB_STORE_PYTHON)
    result = sandbox.double_click()
    assert _INSTALL_WORDS in result.output, result.output
    assert _PAUSE_LINE in result.output, result.output


def test_double_click_does_not_pause_on_success(sandbox: _Sandbox) -> None:
    result = sandbox.double_click()
    assert result.returncode == 0, result.output
    assert _PAUSE_LINE not in result.output, result.output


def test_double_click_does_not_pause_after_ctrl_c(sandbox: _Sandbox) -> None:
    """`serve` exits 130 when stopped; that is not a failure to read about."""
    result = sandbox.double_click(UV_RUN_RC="130")
    assert _PAUSE_LINE not in result.output, result.output
    assert result.returncode == 130


@pytest.mark.parametrize("start", ["typed_at_a_prompt", "from_powershell", "from_program"])
def test_no_pause_when_started_from_a_prompt(sandbox: _Sandbox, start: str) -> None:
    """An open prompt keeps the message on screen, and a program must not hang."""
    result = getattr(sandbox, start)(UV_RUN_RC="1")
    assert result.serve_argv == "run --no-dev mame-curator serve", result.output
    assert _PAUSE_LINE not in result.output, result.output


def test_an_earlier_failure_at_the_prompt_is_not_mistaken_for_ours(sandbox: _Sandbox) -> None:
    """The errorlevel left by the last command at the prompt must not stop the script."""
    result = sandbox.typed_at_a_prompt(before="cmd /c exit 1\r\n")
    assert result.serve_argv == "run --no-dev mame-curator serve", result.output

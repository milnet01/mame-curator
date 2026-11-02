"""What the launchers must say, read as text, on every platform.

`run.bat` runs only on Windows, so `tests/tools/test_run_bat_port.py` is
skipped everywhere else. These pins catch a regression on any machine. They
cover what a fake installer cannot: the installer is never run in a test,
because running it would install uv.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_BAT = REPO_ROOT / "run.bat"
LAUNCHER_DIR = REPO_ROOT


def _bat_code() -> list[str]:
    """`run.bat`'s lines, without comments."""
    lines = RUN_BAT.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if not line.strip().lower().startswith("rem")]


def _posix_launcher() -> str:
    # Globbed, as tests/docs/test_dev_dependency_group.py does: this only reads
    # it, and naming it would trip the win32-skip guard in tests/docs.
    return next(p for p in LAUNCHER_DIR.glob("run.*") if p != RUN_BAT).read_text(encoding="utf-8")


def test_run_bat_uses_windows_line_endings() -> None:
    """Windows batch files are CRLF; `.gitattributes` says why this is a precaution."""
    data = RUN_BAT.read_bytes()
    assert b"\r\n" in data
    assert b"\n" not in data.replace(b"\r\n", b"")


def test_git_keeps_run_bat_crlf_in_every_checkout_and_zip() -> None:
    attributes = (REPO_ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert re.search(r"^run\.bat\s+text\s+eol=crlf$", attributes, re.MULTILINE)


def test_run_bat_does_not_expand_bang_in_its_own_folder() -> None:
    """`setlocal enabledelayedexpansion` above the `cd` eats a `!` in the path."""
    code = _bat_code()
    cd_line = next(i for i, line in enumerate(code) if line.startswith("cd /d"))
    delayed = next(i for i, line in enumerate(code) if "enabledelayedexpansion" in line)
    assert cd_line < delayed
    assert "||" in code[cd_line], "a failed cd must stop the script"


def test_run_bat_treats_an_empty_version_answer_as_no_python() -> None:
    code = "\n".join(_bat_code())
    assert 'set "PY_OK="' in code, "a value left in the environment must not count"
    assert re.search(r"if not defined PY_OK\b.*goto", code)


def test_run_bat_stops_on_a_failed_sync() -> None:
    code = _bat_code()
    sync = next(i for i, line in enumerate(code) if line.startswith("call uv sync"))
    assert "errorlevel" in code[sync + 1]


def test_run_bat_checks_the_uv_installer_exit_code() -> None:
    code = _bat_code()
    install = next(i for i, line in enumerate(code) if line.startswith("call powershell"))
    assert "errorlevel" in code[install + 1]


def test_run_bat_pins_the_installer_transport() -> None:
    """The TLS floor `run.sh` has with `--tlsv1.2`, and a failure PowerShell reports."""
    line = next(line for line in _bat_code() if line.startswith("call powershell"))
    assert "https://astral.sh/uv/install.ps1" in line
    assert "SecurityProtocolType]::Tls12" in line
    assert "$ErrorActionPreference='Stop'" in line


def test_run_sh_pins_the_installer_transport() -> None:
    text = _posix_launcher()
    assert "--proto '=https' --tlsv1.2" in text


def test_no_launcher_cites_an_adr_that_does_not_exist() -> None:
    """The comment said integrity was "tracked as a separate ADR". None exists."""
    for text in (_posix_launcher(), RUN_BAT.read_text(encoding="utf-8")):
        assert "docs/decisions" not in text

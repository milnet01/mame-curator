"""`$PORT` contract for `run.sh` — the bootstrap entry point.

`run.sh` reads `$PORT`, defaults it to 8080, and converts it into an
explicit `--port` flag on the `mame-curator serve` exec. These tests pin
the four contract cases at the shell layer:

1. `$PORT` is read on startup.
2. Present and valid (integer in 1024-65535) → passed through as `--port`.
3. Absent (unset or empty) → 8080, unchanged.
4. Present and invalid → exit non-zero naming the value and the range,
   before the exec; never a silent fall-back to 8080.

The script is run for real against a stub `uv` on `PATH` that records its
argv instead of syncing or serving, so the assertion is on the exact
command line `run.sh` builds — the layer that would otherwise quietly drop
the value. `tests/cli/test_serve_port_env.py` pins the Python half.

See `src/mame_curator/cli/spec.md` § "`serve` port resolution".
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_SH = REPO_ROOT / "run.sh"

_STUB_UV = """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "${UV_LOG}"
exit 0
"""

_STUB_NOOP = """#!/usr/bin/env bash
exit 0
"""


class _Result:
    def __init__(self, returncode: int, stdout: str, stderr: str, uv_argv: list[str]):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.uv_argv = uv_argv

    @property
    def serve_argv(self) -> str | None:
        """The `uv run mame-curator serve ...` line, if the exec was reached."""
        return next((line for line in self.uv_argv if "serve" in line), None)


RunSh = Callable[[str | None], _Result]


@pytest.fixture
def run_sh(tmp_path: Path) -> RunSh:
    """Return a callable that runs a copy of `run.sh` in a sandbox.

    The sandbox has a stub `uv` first on `PATH` (recording argv to a log
    rather than syncing or binding a port), no-op browser openers, and a
    `config.yaml` so the interactive setup branch is skipped. `python3` is
    the real one — the version gate at the top of the script is part of
    what's being run.
    """
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    shutil.copy(RUN_SH, sandbox / "run.sh")
    (sandbox / "config.yaml").write_text("paths: {}\n")

    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    for name, body in (("uv", _STUB_UV), ("xdg-open", _STUB_NOOP), ("open", _STUB_NOOP)):
        stub = stub_bin / name
        stub.write_text(body)
        stub.chmod(stub.stat().st_mode | stat.S_IXUSR)

    uv_log = tmp_path / "uv.log"
    uv_log.touch()

    def _run(port: str | None) -> _Result:
        env = {
            "PATH": f"{stub_bin}{os.pathsep}{os.environ['PATH']}",
            "HOME": str(tmp_path),
            "UV_LOG": str(uv_log),
        }
        if port is not None:
            env["PORT"] = port

        # Redirect to files rather than pipes: `run.sh` backgrounds a
        # browser-opener subshell that sleeps 2s holding the inherited
        # descriptors, so a pipe would keep every test waiting on it.
        out_path, err_path = tmp_path / "stdout", tmp_path / "stderr"
        with out_path.open("w") as out, err_path.open("w") as err:
            # S603 noqa rationale: bash plus a path to the project's own
            # script, inside a tmp_path sandbox, with no untrusted input.
            proc = subprocess.run(  # noqa: S603
                ["/usr/bin/env", "bash", str(sandbox / "run.sh")],
                stdout=out,
                stderr=err,
                env=env,
                cwd=str(sandbox),
                check=False,
                timeout=60,
            )
        return _Result(
            proc.returncode,
            out_path.read_text(),
            err_path.read_text(),
            uv_log.read_text().splitlines(),
        )

    return _run


# ---- Cases 1-3: the paths that must not change -----------------------


def test_port_absent_execs_8080(run_sh: RunSh) -> None:
    """Case 3 — unset `$PORT` still execs `--port 8080`."""
    result = run_sh(None)
    assert result.returncode == 0
    assert result.serve_argv == "run mame-curator serve --port 8080"


def test_port_empty_execs_8080(run_sh: RunSh) -> None:
    """Case 3 — `PORT=` is 'absent' per bash's `${PORT:-8080}`."""
    result = run_sh("")
    assert result.returncode == 0
    assert result.serve_argv == "run mame-curator serve --port 8080"


def test_port_valid_execs_that_port(run_sh: RunSh) -> None:
    """Case 2 — a valid `$PORT` reaches the exec as an explicit flag."""
    result = run_sh("5999")
    assert result.returncode == 0
    assert result.serve_argv == "run mame-curator serve --port 5999"
    assert "http://127.0.0.1:5999/" in result.stdout, (
        "the announced URL must name the port actually bound"
    )


@pytest.mark.parametrize("raw", ["1024", "65535"])
def test_port_range_boundaries_are_accepted(run_sh: RunSh, raw: str) -> None:
    """Case 2 — the range is inclusive at both ends."""
    result = run_sh(raw)
    assert result.returncode == 0
    assert result.serve_argv == f"run mame-curator serve --port {raw}"


# ---- Case 4: the gap this contract closes ----------------------------


@pytest.mark.parametrize(
    "raw",
    [
        "abc",  # reached argparse: "invalid int value: 'abc'", no range
        "80",  # reached the bind: permission denied
        "1023",  # one below the boundary
        "65536",  # one above the boundary
        "99999",  # reached the bind: invalid port
        "999999999999999999999999",  # wider than `test -lt` can compare
        "-1",
        "80.5",
        "8080abc",
        " 8080",
    ],
)
def test_port_invalid_exits_nonzero_before_exec(run_sh: RunSh, raw: str) -> None:
    """Case 4 — named error, non-zero exit, and `serve` never reached."""
    result = run_sh(raw)
    assert result.returncode != 0, f"PORT={raw!r} must not be accepted"
    assert raw in result.stderr, f"error must name the offending value: {result.stderr!r}"
    assert "1024-65535" in result.stderr, f"error must name the expected range: {result.stderr!r}"
    # No exec at all is also the proof of "never silently falls back to
    # 8080" — a fallback would show up here as a `--port 8080` line.
    assert result.serve_argv is None, f"invalid PORT reached the server: {result.serve_argv!r}"

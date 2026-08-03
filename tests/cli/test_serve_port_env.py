"""`$PORT` contract for `mame-curator serve` — the direct-CLI entry point.

`run.sh` turns `$PORT` into an explicit `--port` flag, but it is not the
only way in: `mame-curator serve` run directly used to resolve its port as
`args.port or 8080` and ignore the environment entirely. These tests pin
the four contract cases at the Python layer, plus flag precedence:

1. `$PORT` is read on startup.
2. Present and valid (integer in 1024-65535) → bind that port.
3. Absent (unset or empty) → 8080, unchanged.
4. Present and invalid → exit non-zero naming the value and the range;
   never a silent fall-back to 8080.

The shell half of the same contract lives in
`tests/tools/test_run_sh_port.py`; the wording of the error is asserted in
both so the two entry points can't drift apart.

See `src/mame_curator/cli/spec.md` § "`serve` port resolution".
"""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

from mame_curator.cli.commands.serve import _resolve_port


def _serve_args(config: Path, port: int | None = None) -> argparse.Namespace:
    return argparse.Namespace(config=config, host="127.0.0.1", port=port)


def _config(tmp_path: Path) -> Path:
    """A config.yaml that exists — `create_app` is mocked, so contents
    beyond a parseable stub are never read."""
    config = tmp_path / "config.yaml"
    config.write_text("paths: {}\n")
    return config


# ---- _resolve_port: the four contract cases -------------------------


def test_port_absent_defaults_to_8080(monkeypatch: pytest.MonkeyPatch) -> None:
    """Case 3 — unset `$PORT` behaves exactly as before the contract."""
    monkeypatch.delenv("PORT", raising=False)
    assert _resolve_port(None) == 8080


def test_port_empty_defaults_to_8080(monkeypatch: pytest.MonkeyPatch) -> None:
    """Case 3 — `PORT=` (set but empty) is 'absent', matching bash's
    `${PORT:-8080}`, which also treats empty as unset."""
    monkeypatch.setenv("PORT", "")
    assert _resolve_port(None) == 8080


@pytest.mark.parametrize("raw", ["1024", "5998", "8080", "65535"])
def test_port_valid_is_used(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    """Case 2 — a valid `$PORT`, including both range boundaries."""
    monkeypatch.setenv("PORT", raw)
    assert _resolve_port(None) == int(raw)


@pytest.mark.parametrize(
    "raw",
    [
        "abc",  # not a number at all
        "80",  # below the range — the privileged-port bind failure
        "1023",  # one below the boundary
        "65536",  # one above the boundary
        "99999",  # well above
        "999999999",  # wider than any port
        "-1",  # sign rejected, not parsed as negative
        "80.5",  # float
        "8080abc",  # trailing junk — fullmatch, not a prefix match
        " 8080",  # leading whitespace, which bash's regex also rejects
        "8_080",  # Python's int() would accept this; the contract does not
    ],
)
def test_port_invalid_raises_naming_value_and_range(
    monkeypatch: pytest.MonkeyPatch, raw: str
) -> None:
    """Case 4 — invalid `$PORT` raises rather than falling back to 8080."""
    monkeypatch.setenv("PORT", raw)
    with pytest.raises(ValueError) as excinfo:
        _resolve_port(None)
    message = str(excinfo.value)
    assert raw in message, f"error must name the offending value: {message!r}"
    assert "1024-65535" in message, f"error must name the range: {message!r}"


def test_explicit_flag_beats_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit beats implicit — this is what keeps `run.sh` working
    unchanged, since it always passes `--port "${PORT}"`."""
    monkeypatch.setenv("PORT", "5998")
    assert _resolve_port(9000) == 9000


def test_explicit_zero_is_not_treated_as_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`--port 0` (uvicorn: 'any free port') survives resolution.

    The pre-contract `args.port or 8080` silently rewrote 0 to 8080;
    `is not None` does not.
    """
    monkeypatch.setenv("PORT", "5998")
    assert _resolve_port(0) == 0


# ---- _cmd_serve: the resolved port reaches the bind ------------------


def test_serve_binds_env_port(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The bypass path end to end — `$PORT` reaches `uvicorn.run`.

    This is the failure the contract exists to prevent: every layer
    looking correct on its own while one of them drops the value.
    """
    from mame_curator.cli.commands.serve import _cmd_serve

    monkeypatch.setenv("PORT", "5998")
    with (
        patch("mame_curator.api.create_app"),
        patch("uvicorn.run") as run_mock,
    ):
        _cmd_serve(_serve_args(_config(tmp_path)))

    assert run_mock.call_args.kwargs["port"] == 5998


def test_serve_defaults_to_8080(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Case 3 at the command layer — the untouched path."""
    from mame_curator.cli.commands.serve import _cmd_serve

    monkeypatch.delenv("PORT", raising=False)
    with (
        patch("mame_curator.api.create_app"),
        patch("uvicorn.run") as run_mock,
    ):
        _cmd_serve(_serve_args(_config(tmp_path)))

    assert run_mock.call_args.kwargs["port"] == 8080


def test_serve_exits_nonzero_on_invalid_port(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Case 4 at the command layer — non-zero exit, message on stderr,
    and `uvicorn.run` never reached."""
    from mame_curator.cli.commands.serve import _cmd_serve

    monkeypatch.setenv("PORT", "80")
    with patch("uvicorn.run") as run_mock:
        rc = _cmd_serve(_serve_args(_config(tmp_path)))

    assert rc != 0
    run_mock.assert_not_called()
    stderr = capsys.readouterr().err
    assert "80" in stderr
    assert "1024-65535" in stderr


def test_invalid_port_value_survives_rich_markup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A `$PORT` containing square brackets is still named verbatim.

    `rich` reads `[abc]` as a style tag, so an unescaped f-string printed
    `PORT=''` — dropping the one thing `cli/spec.md` § "Error messages"
    requires the message to carry. `run.sh`'s `echo` has no such hazard, so
    this is also what keeps the two entry points' messages identical.
    """
    from mame_curator.cli.commands.serve import _cmd_serve

    monkeypatch.setenv("PORT", "[abc]")
    rc = _cmd_serve(_serve_args(_config(tmp_path)))

    assert rc != 0
    assert "[abc]" in capsys.readouterr().err


def test_invalid_port_checked_before_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A bad `$PORT` is a usage error and reports as one — it must not be
    masked by the unrelated 'config file not found' branch."""
    from mame_curator.cli.commands.serve import _cmd_serve

    monkeypatch.setenv("PORT", "abc")
    rc = _cmd_serve(_serve_args(tmp_path / "does-not-exist.yaml"))

    assert rc != 0
    stderr = capsys.readouterr().err
    assert "abc" in stderr
    assert "config file not found" not in stderr

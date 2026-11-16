"""mame-curator-1226 (CR-05-7): one running copy per data folder.

`cli/spec.md` § One copy per data folder. The "other copy" is a second
`InstanceLock` taken in this process: `flock` locks belong to the open file,
so two opens conflict here as two processes would.
"""

from __future__ import annotations

import argparse
import errno
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from mame_curator.cli.commands import _single_instance
from mame_curator.cli.commands import serve as serve_mod
from mame_curator.cli.commands._single_instance import URL_NAME, InstanceLock
from mame_curator.cli.commands.serve import _cmd_serve

_PORT = 8123
_URL = f"http://127.0.0.1:{_PORT}/"


@pytest.fixture(autouse=True)
def _plain_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """No real server may start: a missed hand-over would otherwise block on uvicorn."""
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.delenv("LWSM_MANAGED", raising=False)
    with patch("uvicorn.run"):
        yield


@pytest.fixture
def config(tmp_path: Path) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text("paths: {}\n", encoding="utf-8")
    return path


@pytest.fixture
def other_copy(config: Path) -> Iterator[InstanceLock]:
    lock = InstanceLock(config.parent / "data")
    assert lock.claim(_URL)
    yield lock
    lock.release()


def _args(config: Path, *, no_open_browser: bool = False) -> argparse.Namespace:
    return argparse.Namespace(
        config=config, host="127.0.0.1", port=_PORT, no_open_browser=no_open_browser
    )


def test_second_launch_opens_the_running_copy_and_exits_0(
    config: Path, other_copy: InstanceLock, capsys: pytest.CaptureFixture[str]
) -> None:
    with (
        patch("mame_curator.api.create_app") as create_app,
        patch.object(serve_mod, "_run_server") as run_server,
        patch("webbrowser.open", return_value=True) as opened,
    ):
        rc = _cmd_serve(_args(config))

    assert rc == 0
    assert f"already running at {_URL}" in capsys.readouterr().out
    opened.assert_called_once_with(_URL)
    create_app.assert_not_called()
    run_server.assert_not_called()


def test_second_launch_respects_the_no_open_flag(config: Path, other_copy: InstanceLock) -> None:
    with (
        patch("mame_curator.api.create_app"),
        patch("webbrowser.open") as opened,
    ):
        rc = _cmd_serve(_args(config, no_open_browser=True))

    assert rc == 0
    opened.assert_not_called()


def test_second_launch_without_an_address_is_an_error(
    config: Path, other_copy: InstanceLock, capsys: pytest.CaptureFixture[str]
) -> None:
    (config.parent / "data" / URL_NAME).write_text("", encoding="utf-8")
    with (
        patch("mame_curator.api.create_app") as create_app,
        patch("webbrowser.open") as opened,
    ):
        rc = _cmd_serve(_args(config))

    assert rc == 1
    assert "already running" in capsys.readouterr().err
    opened.assert_not_called()
    create_app.assert_not_called()


def test_a_running_copy_holds_the_lock_and_records_its_address(config: Path) -> None:
    data = config.parent / "data"
    seen: dict[str, Any] = {}

    def fake_run(*_args: Any, **_kwargs: Any) -> int:
        probe = InstanceLock(data)
        seen["second_claim"] = probe.claim("http://elsewhere/")
        probe.release()
        seen["url"] = (data / URL_NAME).read_text(encoding="utf-8")
        return 130

    with (
        patch("mame_curator.api.create_app"),
        patch.object(serve_mod, "_run_server", side_effect=fake_run),
    ):
        rc = _cmd_serve(_args(config, no_open_browser=True))

    assert rc == 130
    assert seen == {"second_claim": False, "url": _URL}
    after = InstanceLock(data)
    assert after.claim(_URL), "the lock must be released when serve returns"
    after.release()


def test_a_lock_the_filesystem_refuses_still_runs_the_server(
    config: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def refuse(*_args: Any) -> None:
        raise OSError(errno.ENOLCK, "No locks available")

    monkeypatch.setattr(_single_instance, "_lock", refuse)
    with (
        caplog.at_level(logging.WARNING, logger=_single_instance.__name__),
        patch("mame_curator.api.create_app"),
        patch.object(serve_mod, "_run_server", return_value=130) as run_server,
    ):
        rc = _cmd_serve(_args(config, no_open_browser=True))

    assert rc == 130
    run_server.assert_called_once()
    assert any("without the one-copy lock" in r.getMessage() for r in caplog.records)

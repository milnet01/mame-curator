"""mame-curator-1095 § 4.11 — a frozen bundle tees stderr to a log file.

A double-clicked bundle has no terminal, so every exit-1 message would
vanish with the process. ``main()`` installs the tee first, and only when
``sys.frozen`` is set; a source-tree run keeps plain stderr.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

from mame_curator import main as main_mod


@pytest.fixture
def log_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "logs" / "mame-curator.log"
    monkeypatch.setattr(main_mod, "user_log_path", lambda: path)
    return path


def test_source_tree_run_keeps_plain_stderr(
    log_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delattr(sys, "frozen", raising=False)
    before = sys.stderr
    main_mod._tee_stderr_if_frozen()
    assert sys.stderr is before
    assert not log_path.exists()


def test_frozen_run_writes_stderr_to_both(log_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    console = io.StringIO()
    monkeypatch.setattr(sys, "stderr", console)
    main_mod._tee_stderr_if_frozen()
    print("error: port 8080 is already in use", file=sys.stderr)
    sys.stderr.flush()
    assert "port 8080" in console.getvalue()
    assert "port 8080" in log_path.read_text(encoding="utf-8")


def test_frozen_run_truncates_the_previous_log(
    log_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log_path.parent.mkdir(parents=True)
    log_path.write_text("old run\n", encoding="utf-8")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "stderr", io.StringIO())
    main_mod._tee_stderr_if_frozen()
    print("new run", file=sys.stderr)
    sys.stderr.flush()
    assert log_path.read_text(encoding="utf-8") == "new run\n"


def test_windowed_bundle_without_stderr_still_logs(
    log_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A windowed PyInstaller build starts with ``sys.stderr`` set to None."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "stderr", None)
    main_mod._tee_stderr_if_frozen()
    print("error: no config", file=sys.stderr)
    sys.stderr.flush()
    assert "no config" in log_path.read_text(encoding="utf-8")


def test_unwritable_log_dir_keeps_plain_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blocker = tmp_path / "not-a-dir"
    blocker.write_text("", encoding="utf-8")
    monkeypatch.setattr(main_mod, "user_log_path", lambda: blocker / "mame-curator.log")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    console = io.StringIO()
    monkeypatch.setattr(sys, "stderr", console)
    main_mod._tee_stderr_if_frozen()
    assert sys.stderr is console

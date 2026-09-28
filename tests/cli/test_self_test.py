"""mame-curator-1095 INV-17 — ``mame-curator self-test``.

A bundle can silently lose a stack PyInstaller did not see. The self-test
imports each one (and checks the SPA and Help pages are present) and prints
exactly one line: ``MAME_CURATOR_SELFTEST_OK`` with exit 0, or
``MAME_CURATOR_SELFTEST_FAIL: <token>`` naming the first failure with exit 1.
Contract: ``docs/specs/mame-curator-1095-desktop-bundles.md`` § 4.13.
"""

from __future__ import annotations

import sys

import pytest

from mame_curator import _selftest
from mame_curator.cli import build_parser, run


def _run_cli(capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    rc = run(build_parser().parse_args(["self-test"]))
    return rc, capsys.readouterr().out


def test_source_tree_passes(capsys: pytest.CaptureFixture[str]) -> None:
    assert _run_cli(capsys) == (0, "MAME_CURATOR_SELFTEST_OK\n")


def test_first_failure_is_named(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def boom() -> None:
        raise ImportError("gone")

    checks = (("lxml", lambda: None), ("httptools", boom), ("websockets", boom))
    monkeypatch.setattr(_selftest, "CHECKS", checks)
    assert _run_cli(capsys) == (1, "MAME_CURATOR_SELFTEST_FAIL: httptools\n")


def test_missing_stack_prints_the_sentinel_not_a_traceback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``sys.modules[name] = None`` makes ``import name`` raise ImportError."""
    monkeypatch.setitem(sys.modules, "websockets", None)
    assert _run_cli(capsys) == (1, "MAME_CURATOR_SELFTEST_FAIL: websockets\n")


def test_uvloop_is_not_required_on_windows(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "uvloop", None)
    assert _run_cli(capsys) == (0, "MAME_CURATOR_SELFTEST_OK\n")

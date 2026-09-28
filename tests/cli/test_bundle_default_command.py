"""mame-curator-1095 INV-19 — a frozen launch with no subcommand runs ``serve``.

A double-clicked bundle passes no arguments, and the CLI requires a
subcommand (exit 2). Frozen only, ``main()`` inserts ``serve`` when no
argument names a subcommand: after any leading ``-v`` / ``--verbose``, and
never when ``-h`` / ``--help`` / ``--version`` asks the root parser. A
source-tree run keeps the usage error. Contract: spec § 4.14.
"""

from __future__ import annotations

import argparse
import sys

import pytest

from mame_curator import main as main_mod
from mame_curator.cli import build_parser, subcommand_names

COMMANDS = subcommand_names(build_parser())


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        ([], ["serve"]),
        (["--no-open-browser"], ["serve", "--no-open-browser"]),
        (["-v"], ["-v", "serve"]),
        (["--verbose", "--port", "9000"], ["--verbose", "serve", "--port", "9000"]),
        (["--version"], ["--version"]),
        (["-h"], ["-h"]),
        (["self-test"], ["self-test"]),
        (["-v", "parse", "x.xml"], ["-v", "parse", "x.xml"]),
    ],
)
def test_bundle_argv(argv: list[str], expected: list[str]) -> None:
    assert main_mod._bundle_argv(argv, COMMANDS) == expected


def test_frozen_bare_launch_runs_serve(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[argparse.Namespace] = []

    def fake_serve(args: argparse.Namespace) -> int:
        seen.append(args)
        return 0

    monkeypatch.setattr("mame_curator.cli._cmd_serve", fake_serve)
    monkeypatch.setattr(main_mod, "_tee_stderr_if_frozen", lambda: None)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "argv", ["MAME_Curator", "--no-open-browser"])
    assert main_mod.main() == 0
    assert seen and seen[0].no_open_browser is True


def test_source_tree_keeps_the_usage_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(sys, "argv", ["mame-curator"])
    with pytest.raises(SystemExit) as exc:
        main_mod.main()
    assert exc.value.code == 2

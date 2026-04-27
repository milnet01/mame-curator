"""End-to-end test for `mame-curator parse <dat>`."""

import logging
from pathlib import Path

import pytest

from mame_curator.cli import build_parser, run


def test_parse_command_prints_summary(mini_dat: Path, capsys: pytest.CaptureFixture[str]) -> None:
    parser = build_parser()
    args = parser.parse_args(["parse", str(mini_dat)])
    exit_code = run(args)
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "machines: 6" in output
    assert "parents: 5" in output
    assert "clones: 1" in output
    assert "bios:" in output
    assert "devices:" in output
    assert "mechanical:" in output


def test_parse_command_unknown_path_returns_nonzero(tmp_path: Path) -> None:
    parser = build_parser()
    args = parser.parse_args(["parse", str(tmp_path / "nope.xml")])
    exit_code = run(args)
    assert exit_code != 0


def test_verbose_flag_is_accepted() -> None:
    """`--verbose` (and `-v`) toggle DEBUG logging; default is INFO.

    Per indie-review H2: logging level must be CLI-configurable, not hard-coded
    at module import time.
    """
    parser = build_parser()
    default = parser.parse_args(["parse", "placeholder.xml"])
    assert default.verbose is False
    explicit = parser.parse_args(["--verbose", "parse", "placeholder.xml"])
    assert explicit.verbose is True
    short = parser.parse_args(["-v", "parse", "placeholder.xml"])
    assert short.verbose is True


def test_main_module_import_does_not_configure_logging() -> None:
    """Per indie-review H2: importing `mame_curator.main` must NOT call
    logging.basicConfig at module level — that would mutate the global root
    logger as a side effect for every test, REPL session, or future web layer
    that imports it.
    """
    import importlib

    # Snapshot root logger handler list, re-import main, confirm unchanged.
    before_handlers = list(logging.root.handlers)
    importlib.import_module("mame_curator.main")
    after_handlers = list(logging.root.handlers)
    assert before_handlers == after_handlers


def test_error_routes_to_stderr_with_path_prefix(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Per standards §9 (G8/G9): errors → stderr, message includes input path."""
    bad_path = tmp_path / "definitely-does-not-exist.xml"
    parser = build_parser()
    args = parser.parse_args(["parse", str(bad_path)])
    exit_code = run(args)
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "error:" not in captured.out, "errors must NOT go to stdout (G8)"
    assert str(bad_path) in captured.err, "error message must include the path (G9)"
    assert "error:" in captured.err


def test_runtime_error_returns_exit_code_1_not_2(tmp_path: Path) -> None:
    """Argparse reserves exit code 2 for usage errors; runtime/data errors return 1.

    Conflating the two prevents shell scripts and CI tooling from distinguishing
    "user typed wrong" from "the file you gave me is corrupt."
    """
    parser = build_parser()
    args = parser.parse_args(["parse", str(tmp_path / "nope.xml")])
    assert run(args) == 1, "runtime errors must return 1, not collide with argparse's 2"


def test_run_with_unknown_command_raises_assertion() -> None:
    """Per cli/spec.md "Dispatch pattern": `run()` is reached only after argparse
    has accepted a known subcommand (`required=True` enforces this). A code path
    where `args.command` is anything else is a developer bug — the dispatch
    table is out of sync with `build_parser()`.

    Surfacing this as a silent `return 1` would make the bug invisible in the
    CLI's exit code (looks like a runtime error) and untestable in CI. The
    contract is: the only way to exit `run()` is via a registered handler;
    falling through is a programmer error and MUST raise `AssertionError`.
    """
    import argparse as _argparse

    forged = _argparse.Namespace(command="nonexistent", verbose=False)
    with pytest.raises(AssertionError, match="nonexistent"):
        run(forged)

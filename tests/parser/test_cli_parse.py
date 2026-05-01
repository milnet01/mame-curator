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


def test_cmd_parse_quotes_path_with_control_byte(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """FP07 A1 — `--dat` pointing at a path with a control byte must surface
    in the error message via `repr()`, NOT as a literal LF that breaks
    the single-line error contract.

    `Path` construction is pure (no syscall) so no skip clause needed;
    `parse_dat` checks `path.exists()` and raises `DATError("DAT path does
    not exist", path=path)` without touching the filesystem.
    """
    bad = tmp_path / "evil\nname.xml"
    parser = build_parser()
    args = parser.parse_args(["parse", str(bad)])
    assert run(args) == 1
    err = capsys.readouterr().err
    # Post-fix: repr-escaped form (Python source `\\n` = 2 chars `\` + `n`).
    assert "evil\\nname.xml" in err
    # Strict: the literal-LF form of the path must NOT appear (FP07 R1
    # tightened from `"\n" not in err.rstrip("\n")` — that form would
    # false-positive on any future {exc} that contains an embedded LF).
    assert "evil\nname.xml" not in err


def test_dispatch_uses_set_defaults_func_pattern() -> None:
    """Per cli/spec.md "Dispatch pattern": when the second subcommand lands,
    `run()` MUST migrate from `if/elif` to `set_defaults(func=_cmd_x)` +
    `args.func(args)`. Phase 2's `filter` subcommand is the second; the
    migration is now mandatory.

    Verifies the contract by checking that every registered subparser sets
    a `func` attribute (the dispatch hook) and that parsing a subcommand
    populates `args.func`.
    """
    parser = build_parser()
    args = parser.parse_args(["parse", "placeholder.xml"])
    assert hasattr(args, "func"), (
        "build_parser must use parse_cmd.set_defaults(func=...) so run() can "
        "dispatch via args.func(args), not via an if/elif chain on args.command"
    )
    assert callable(args.func)

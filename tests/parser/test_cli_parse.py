"""End-to-end test for `mame-curator parse <dat>`."""

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


def test_runtime_error_returns_exit_code_1_not_2(tmp_path: Path) -> None:
    """Argparse reserves exit code 2 for usage errors; runtime/data errors return 1.

    Conflating the two prevents shell scripts and CI tooling from distinguishing
    "user typed wrong" from "the file you gave me is corrupt."
    """
    parser = build_parser()
    args = parser.parse_args(["parse", str(tmp_path / "nope.xml")])
    assert run(args) == 1, "runtime errors must return 1, not collide with argparse's 2"

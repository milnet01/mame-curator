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

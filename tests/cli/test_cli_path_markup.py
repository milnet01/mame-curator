"""mame-curator-1180 — parse, filter and copy print a user's path as typed.

``rich`` reads ``[bold]`` as a style tag and drops it, so a path holding one
printed wrong. Per ``src/mame_curator/cli/spec.md`` § Error messages, every
path goes through one shared form: quoted, escaped, never ``PosixPath(...)``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mame_curator.cli import build_parser, run

FILTER_FIXTURES = Path(__file__).resolve().parents[1] / "filter" / "fixtures"
TINY_DAT = (
    '<?xml version="1.0"?><mame><machine name="x"><description>X</description></machine></mame>'
)


def _every_mention_kept(text: str, path: Path) -> None:
    """The CLI prints the path quoted, and nowhere with its brackets eaten."""
    assert f"'{path}'" in text
    assert path.name.replace("[bold]", "") not in text.replace(path.name, "")


def test_parse_failure_keeps_the_brackets(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dat = tmp_path / "[bold]games.xml"
    assert run(build_parser().parse_args(["parse", str(dat)])) == 1
    _every_mention_kept(capsys.readouterr().err, dat)


def test_a_backslash_prints_once(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A Windows path stays copyable: repr would double each backslash.

    The local stand-in for the Windows runners (local-CI.sh, caveat 1).
    """
    dat = tmp_path / "back\\slash.xml"
    assert run(build_parser().parse_args(["parse", str(dat)])) == 1
    assert f"'{dat}'" in capsys.readouterr().err


def test_parse_summary_keeps_the_brackets(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dat = tmp_path / "[bold]games.xml"
    dat.write_text(TINY_DAT, encoding="utf-8")
    assert run(build_parser().parse_args(["parse", str(dat)])) == 0
    _every_mention_kept(capsys.readouterr().out, dat)


def _filter_argv(out: Path) -> list[str]:
    return [
        "filter",
        "--dat",
        str(FILTER_FIXTURES / "snapshot_dat.xml"),
        "--listxml",
        str(FILTER_FIXTURES / "snapshot_listxml.xml"),
        "--catver",
        str(FILTER_FIXTURES / "snapshot_catver.ini"),
        "--languages",
        str(FILTER_FIXTURES / "snapshot_languages.ini"),
        "--bestgames",
        str(FILTER_FIXTURES / "snapshot_bestgames.ini"),
        "--out",
        str(out),
    ]


def test_filter_summary_keeps_the_brackets(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "[bold]report.json"
    assert run(build_parser().parse_args(_filter_argv(out))) == 0
    _every_mention_kept(capsys.readouterr().out, out)


def test_filter_write_failure_keeps_the_brackets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def refuse(*_a: object, **_kw: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr("mame_curator.cli.commands.filter.atomic_write_text", refuse)
    out = tmp_path / "[bold]report.json"
    assert run(build_parser().parse_args(_filter_argv(out))) == 1
    _every_mention_kept(capsys.readouterr().err, out)


@pytest.mark.parametrize("report_text", [None, '{"winners": []}'])
def test_copy_report_errors_keep_the_brackets(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], report_text: str | None
) -> None:
    dat = tmp_path / "tiny.xml"
    dat.write_text(TINY_DAT, encoding="utf-8")
    report = tmp_path / "[bold]report.json"
    if report_text is not None:
        report.write_text(report_text, encoding="utf-8")
    argv = ["copy", "--dry-run", "--dat", str(dat), "--listxml", str(dat)]
    argv += ["--filter-report", str(report), "--source", str(tmp_path), "--dest", str(tmp_path)]
    assert run(build_parser().parse_args(argv)) == 1
    _every_mention_kept(capsys.readouterr().err, report)

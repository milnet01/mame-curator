"""End-to-end test for `mame-curator filter`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mame_curator.cli import build_parser, run


def test_filter_subcommand_writes_report(
    fixtures_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = tmp_path / "report.json"
    parser = build_parser()
    args = parser.parse_args(
        [
            "filter",
            "--dat",
            str(fixtures_dir / "snapshot_dat.xml"),
            "--listxml",
            str(fixtures_dir / "snapshot_listxml.xml"),
            "--catver",
            str(fixtures_dir / "snapshot_catver.ini"),
            "--languages",
            str(fixtures_dir / "snapshot_languages.ini"),
            "--bestgames",
            str(fixtures_dir / "snapshot_bestgames.ini"),
            "--overrides",
            str(fixtures_dir / "snapshot_overrides.yaml"),
            "--sessions",
            str(fixtures_dir / "snapshot_sessions.yaml"),
            "--out",
            str(report),
        ]
    )
    assert run(args) == 0
    payload = json.loads(report.read_text())
    assert "winners" in payload
    assert "dropped" in payload
    captured = capsys.readouterr()
    assert "winners:" in captured.out


def test_filter_missing_dat_returns_1(
    fixtures_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Per cli/spec.md: runtime errors return 1 (not 2 — argparse reserves 2)."""
    parser = build_parser()
    args = parser.parse_args(
        [
            "filter",
            "--dat",
            str(tmp_path / "missing.xml"),
            "--listxml",
            str(fixtures_dir / "snapshot_listxml.xml"),
            "--catver",
            str(fixtures_dir / "snapshot_catver.ini"),
            "--languages",
            str(fixtures_dir / "snapshot_languages.ini"),
            "--bestgames",
            str(fixtures_dir / "snapshot_bestgames.ini"),
            "--out",
            str(tmp_path / "report.json"),
        ]
    )
    assert run(args) == 1
    captured = capsys.readouterr()
    assert "error:" in captured.err
    assert "error:" not in captured.out

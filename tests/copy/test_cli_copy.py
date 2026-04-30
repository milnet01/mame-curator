"""Smoke test for the `mame-curator copy` CLI subcommand."""

from __future__ import annotations

import json
from pathlib import Path

from mame_curator.cli import build_parser, run

PARSER_FIXTURES = Path(__file__).parent.parent / "parser" / "fixtures"
COPY_FIXTURES = Path(__file__).parent / "fixtures"


def _write_filter_report(path: Path, winners: tuple[str, ...]) -> None:
    payload = {
        "winners": list(winners),
        "dropped": {},
        "contested_groups": [],
        "warnings": [],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_copy_cli_dry_run_smoke(tmp_path: Path, source_dir: Path, dest_dir: Path) -> None:
    """`mame-curator copy --dry-run` runs end-to-end on the parser fixture."""
    report_path = tmp_path / "filter-report.json"
    _write_filter_report(report_path, ("kof94",))
    # Build a tiny DAT containing kof94 so parse_dat doesn't error.
    dat = tmp_path / "tiny.xml"
    dat.write_text(
        '<?xml version="1.0"?><mame>'
        '<machine name="kof94"><description>KoF94</description></machine>'
        "</mame>",
        encoding="utf-8",
    )
    listxml = COPY_FIXTURES / "listxml_bios.xml"

    parser = build_parser()
    args = parser.parse_args(
        [
            "copy",
            "--dry-run",
            "--dat",
            str(dat),
            "--listxml",
            str(listxml),
            "--filter-report",
            str(report_path),
            "--source",
            str(source_dir),
            "--dest",
            str(dest_dir),
        ]
    )
    assert run(args) == 0
    # Dry-run leaves dest empty.
    assert list(dest_dir.iterdir()) == []


def test_copy_cli_purge_recycle_short_circuits(tmp_path: Path) -> None:
    """`--purge-recycle` exits without doing a copy run."""
    parser = build_parser()
    # purge-recycle still requires the other args via argparse, so populate them.
    args = parser.parse_args(
        [
            "copy",
            "--dry-run",
            "--dat",
            str(tmp_path / "x.xml"),
            "--listxml",
            str(tmp_path / "x.xml"),
            "--filter-report",
            str(tmp_path / "x.json"),
            "--source",
            str(tmp_path),
            "--dest",
            str(tmp_path),
            "--purge-recycle",
        ]
    )
    # Doesn't crash even though the inputs would otherwise be invalid.
    assert run(args) == 0

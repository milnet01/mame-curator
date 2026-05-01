"""Smoke test for the `mame-curator copy` CLI subcommand."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from mame_curator.cli import build_parser, run
from mame_curator.copy.types import ConflictStrategy

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


# FP05 — B9 + B10a + B10b tests below


def _copy_args(
    *, dat: Path, listxml: Path, filter_report: Path, source: Path, dest: Path
) -> list[str]:
    return [
        "copy",
        "--dry-run",
        "--dat",
        str(dat),
        "--listxml",
        str(listxml),
        "--filter-report",
        str(filter_report),
        "--source",
        str(source),
        "--dest",
        str(dest),
    ]


def _fake_report(tmp_path: Path, status: object) -> object:
    """Build a minimal CopyReport with the given status for B10 tests."""
    from mame_curator.copy.types import CopyReport, PlanSummary

    return CopyReport(
        session_id="test-fixture",
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        status=status,  # type: ignore[arg-type]
        plan_summary=PlanSummary(
            winners_count=0,
            bios_count=0,
            conflict_strategy=ConflictStrategy.CANCEL,
            source_dir=tmp_path,
            dest_dir=tmp_path,
        ),
        succeeded=(),
        skipped=(),
        failed=(),
        overwritten=(),
        recycled=(),
        bios_included=(),
        chd_missing=(),
        bytes_copied=0,
        warnings=(),
    )


def _stub_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Build minimal-but-parseable DAT + listxml + filter-report files."""
    dat = tmp_path / "tiny.xml"
    dat.write_text(
        '<?xml version="1.0"?>'
        '<mame><machine name="x"><description>X</description></machine></mame>',
        encoding="utf-8",
    )
    listxml = tmp_path / "listxml.xml"
    listxml.write_text(
        '<?xml version="1.0"?>'
        '<mame><machine name="x"><description>X</description></machine></mame>',
        encoding="utf-8",
    )
    fr = tmp_path / "filter-report.json"
    fr.write_text(
        json.dumps({"winners": [], "dropped": [], "contested_groups": [], "warnings": []}),
        encoding="utf-8",
    )
    return dat, listxml, fr


def test_cmd_copy_oserror_on_directory_input(tmp_path: Path) -> None:
    """B9 — pointing `--filter-report` at a directory must produce a
    labelled exit-1 line, not a raw `IsADirectoryError` traceback. Mirrors
    DS01 C6's coverage on `_cmd_filter`."""
    a_directory = tmp_path / "i_am_a_dir"
    a_directory.mkdir()
    parser = build_parser()
    args = parser.parse_args(
        _copy_args(
            dat=tmp_path / "x.xml",
            listxml=tmp_path / "x.xml",
            filter_report=a_directory,
            source=tmp_path,
            dest=tmp_path,
        )
    )
    # Currently: raw IsADirectoryError leaks. Post-fix: exit 1.
    assert run(args) == 1


def test_cmd_copy_exit_130_on_cancelled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """B10a — `CopyReportStatus.CANCELLED` (SIGINT-family user-stop) → 130."""
    import mame_curator.cli as cli_module
    from mame_curator.copy.types import CopyReportStatus

    monkeypatch.setattr(
        cli_module,
        "run_copy",
        lambda *_a, **_k: _fake_report(tmp_path, CopyReportStatus.CANCELLED),
    )
    dat, listxml, fr = _stub_inputs(tmp_path)
    parser = build_parser()
    args = parser.parse_args(
        _copy_args(dat=dat, listxml=listxml, filter_report=fr, source=tmp_path, dest=tmp_path)
    )
    assert run(args) == 130


def test_cmd_copy_exit_3_on_cancelled_playlist_conflict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B10b — `CopyReportStatus.CANCELLED_PLAYLIST_CONFLICT` (deliberate
    user-prompt-cancel, distinct from SIGINT) → 3."""
    import mame_curator.cli as cli_module
    from mame_curator.copy.types import CopyReportStatus

    monkeypatch.setattr(
        cli_module,
        "run_copy",
        lambda *_a, **_k: _fake_report(tmp_path, CopyReportStatus.CANCELLED_PLAYLIST_CONFLICT),
    )
    dat, listxml, fr = _stub_inputs(tmp_path)
    parser = build_parser()
    args = parser.parse_args(
        _copy_args(dat=dat, listxml=listxml, filter_report=fr, source=tmp_path, dest=tmp_path)
    )
    assert run(args) == 3


# FP06 — A1 test below


def _raise_oserror(*_a: object, **_kw: object) -> tuple[int, int]:
    raise OSError("permission denied")


def test_cmd_copy_quotes_filter_report_with_control_byte(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """FP07 A3 — `--filter-report` path with a control byte must surface
    via `repr()` in the read-failure error message.

    `_cmd_copy` reaches the filter-report read at line 245-251 only after
    the parser-input loads succeed; we provide minimal-but-parseable DAT
    + listxml files so the function gets past line 229-243, then the
    filter-report read raises `FileNotFoundError` (an OSError subclass)
    on the LF-bearing path.
    """
    dat = tmp_path / "tiny.xml"
    dat.write_text(
        '<?xml version="1.0"?>'
        '<mame><machine name="x"><description>X</description></machine></mame>',
        encoding="utf-8",
    )
    listxml = tmp_path / "listxml.xml"
    listxml.write_text(
        '<?xml version="1.0"?>'
        '<mame><machine name="x"><description>X</description></machine></mame>',
        encoding="utf-8",
    )
    bad_report = tmp_path / "evil\nname.json"
    parser = build_parser()
    args = parser.parse_args(
        _copy_args(
            dat=dat,
            listxml=listxml,
            filter_report=bad_report,
            source=tmp_path,
            dest=tmp_path,
        )
    )
    assert run(args) == 1
    err = capsys.readouterr().err
    assert "evil\\nname.json" in err
    # FP07 R1: literal-LF-form path must not leak (tightened from the
    # weaker `"\n" not in err.rstrip("\n")` form).
    assert "evil\nname.json" not in err


def test_cmd_copy_purge_recycle_oserror_surfaces_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """FP06 A1 — `--purge-recycle` short-circuit at `cli/__init__.py:215-218`
    sits OUTSIDE the FP05 B9 `try/except OSError` block. A user with an
    unreadable recycle directory currently gets a Python traceback. Post-fix
    the early-return is wrapped in its own `try/except OSError` and surfaces
    a clean `error:` line with exit 1.
    """
    monkeypatch.setattr("mame_curator.cli.purge_recycle", _raise_oserror)
    parser = build_parser()
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
    assert run(args) == 1
    err = capsys.readouterr().err
    assert "error:" in err
    assert "Traceback" not in err

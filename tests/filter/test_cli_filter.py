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


# DS01 — Cluster C tests below


def _filter_args(fixtures_dir: Path, out: Path, **overrides: Path | str) -> list[str]:
    """Build a minimal `filter` argv with a dict of overrides for specific flags."""
    base = {
        "--dat": str(fixtures_dir / "snapshot_dat.xml"),
        "--listxml": str(fixtures_dir / "snapshot_listxml.xml"),
        "--catver": str(fixtures_dir / "snapshot_catver.ini"),
        "--languages": str(fixtures_dir / "snapshot_languages.ini"),
        "--bestgames": str(fixtures_dir / "snapshot_bestgames.ini"),
        "--out": str(out),
    }
    base.update({k: str(v) for k, v in overrides.items()})
    argv = ["filter"]
    for flag, val in base.items():
        argv.extend([flag, val])
    return argv


def test_filter_cmd_oserror_on_directory_input(
    fixtures_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """C6 — pointing `--catver` at a directory instead of a file currently
    leaks a raw Python traceback. Per `cli/spec.md` § "Errors the CLI catches
    but never raises", `_cmd_filter` must catch `OSError` and exit 1 with an
    error line on stderr."""
    a_directory = tmp_path / "i_am_a_dir"
    a_directory.mkdir()
    parser = build_parser()
    args = parser.parse_args(
        _filter_args(fixtures_dir, tmp_path / "report.json", **{"--catver": a_directory})
    )
    assert run(args) == 1
    captured = capsys.readouterr()
    assert "error:" in captured.err


def test_filter_cmd_atomic_report_write(
    fixtures_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C7 — report write is atomic: a failure mid-write must not leave a
    half-written file at `args.out`. Implementation should write via a `.tmp`
    sibling and `Path.replace` (reusing the executor.py:60-72 idiom). We
    verify the pattern indirectly: after a successful run, no `.tmp` sibling
    should remain in the output directory."""
    out = tmp_path / "report.json"
    parser = build_parser()
    args = parser.parse_args(_filter_args(fixtures_dir, out))
    assert run(args) == 0
    assert out.exists()
    leftover_tmps = list(tmp_path.glob("*.tmp"))
    assert leftover_tmps == [], f"unexpected .tmp leftovers: {leftover_tmps}"


def test_filter_cmd_unset_overrides_uses_empty_model(
    fixtures_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C8 — when `--overrides` and `--sessions` are unset, the loaders must
    NOT be called with a sentinel `Path("/nonexistent/...")`. Direct
    construction (`Overrides()` / `Sessions()`) is the contract.

    We catch the antipattern by monkey-patching `load_overrides` and
    `load_sessions` to fail loudly if they're called at all when the flags
    are unset.
    """
    import mame_curator.cli as cli_module

    def _boom_overrides(_path: Path):  # type: ignore[no-untyped-def]
        raise AssertionError("load_overrides must not be called when --overrides is unset")

    def _boom_sessions(_path: Path):  # type: ignore[no-untyped-def]
        raise AssertionError("load_sessions must not be called when --sessions is unset")

    monkeypatch.setattr(cli_module, "load_overrides", _boom_overrides)
    monkeypatch.setattr(cli_module, "load_sessions", _boom_sessions)

    out = tmp_path / "report.json"
    parser = build_parser()
    args = parser.parse_args(_filter_args(fixtures_dir, out))
    # Must succeed without invoking the patched loaders.
    assert run(args) == 0

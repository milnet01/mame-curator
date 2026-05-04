"""End-to-end tests for `mame-curator setup`.

The setup command is an interactive bootstrap wizard that writes a usable
``config.yaml`` from the user's four required path inputs (source ROMs dir,
source DAT, dest ROMs dir, RetroArch playlist target). All other config
sections fall back to AppConfig defaults so the user can run the app
immediately and refine through the Settings page later.

For test ergonomics the command supports a non-interactive path via flags
(``--source-roms`` / ``--source-dat`` / ``--dest-roms`` /
``--retroarch-playlist``) so we don't have to drive ``rich.prompt`` in unit
tests. The interactive path is exercised by a single test that stubs
``rich.prompt.Prompt.ask``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from mame_curator.api.schemas import AppConfig
from mame_curator.cli import build_parser, run


def _write_dat(path: Path) -> Path:
    """Create a tiny placeholder DAT so the path exists for validation."""
    path.write_text("<mame></mame>\n", encoding="utf-8")
    return path


def _flag_args(
    *,
    out: Path,
    source_roms: Path,
    source_dat: Path,
    dest_roms: Path,
    retroarch_playlist: Path,
    force: bool = False,
) -> list[str]:
    args = [
        "setup",
        "--out",
        str(out),
        "--source-roms",
        str(source_roms),
        "--source-dat",
        str(source_dat),
        "--dest-roms",
        str(dest_roms),
        "--retroarch-playlist",
        str(retroarch_playlist),
    ]
    if force:
        args.append("--force")
    return args


def test_setup_writes_config_with_all_four_paths(tmp_path: Path) -> None:
    """Non-interactive path: all four flags supplied → config.yaml written.

    Round-trips through ``yaml.safe_load`` + ``AppConfig`` validation so we
    know the produced file is actually usable by the rest of the app — not
    just a syntactically valid YAML blob.
    """
    source_roms = tmp_path / "roms"
    source_roms.mkdir()
    source_dat = _write_dat(tmp_path / "mame.dat.xml")
    dest_roms = tmp_path / "dest"
    retroarch = tmp_path / "mame.lpl"
    out = tmp_path / "config.yaml"

    parser = build_parser()
    args = parser.parse_args(
        _flag_args(
            out=out,
            source_roms=source_roms,
            source_dat=source_dat,
            dest_roms=dest_roms,
            retroarch_playlist=retroarch,
        )
    )
    assert run(args) == 0
    assert out.exists()

    raw = yaml.safe_load(out.read_text(encoding="utf-8"))
    cfg = AppConfig.model_validate(raw)
    assert cfg.paths.source_roms == source_roms
    assert cfg.paths.source_dat == source_dat
    assert cfg.paths.dest_roms == dest_roms
    assert cfg.paths.retroarch_playlist == retroarch


def test_setup_refuses_to_overwrite_without_force(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """File-safety: an existing config must not be silently clobbered."""
    out = tmp_path / "config.yaml"
    out.write_text("# pre-existing — do not touch\n", encoding="utf-8")
    source_roms = tmp_path / "roms"
    source_roms.mkdir()
    source_dat = _write_dat(tmp_path / "mame.dat.xml")

    parser = build_parser()
    args = parser.parse_args(
        _flag_args(
            out=out,
            source_roms=source_roms,
            source_dat=source_dat,
            dest_roms=tmp_path / "dest",
            retroarch_playlist=tmp_path / "mame.lpl",
        )
    )
    assert run(args) == 1
    assert out.read_text(encoding="utf-8") == "# pre-existing — do not touch\n"
    err = capsys.readouterr().err
    assert "error:" in err
    assert "--force" in err


def test_setup_overwrites_with_force(tmp_path: Path) -> None:
    out = tmp_path / "config.yaml"
    out.write_text("# stale\n", encoding="utf-8")
    source_roms = tmp_path / "roms"
    source_roms.mkdir()
    source_dat = _write_dat(tmp_path / "mame.dat.xml")

    parser = build_parser()
    args = parser.parse_args(
        _flag_args(
            out=out,
            source_roms=source_roms,
            source_dat=source_dat,
            dest_roms=tmp_path / "dest",
            retroarch_playlist=tmp_path / "mame.lpl",
            force=True,
        )
    )
    assert run(args) == 0
    body = out.read_text(encoding="utf-8")
    assert "# stale" not in body
    assert "source_roms" in body


def test_setup_errors_on_missing_source_roms(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--source-roms`` must point at an existing directory.

    Catching this early in the wizard is how the user finds typos before
    the backend tries to ``parse_dat`` and dies on startup.
    """
    out = tmp_path / "config.yaml"
    parser = build_parser()
    args = parser.parse_args(
        _flag_args(
            out=out,
            source_roms=tmp_path / "does-not-exist",
            source_dat=_write_dat(tmp_path / "mame.dat.xml"),
            dest_roms=tmp_path / "dest",
            retroarch_playlist=tmp_path / "mame.lpl",
        )
    )
    assert run(args) == 1
    assert not out.exists()
    err = capsys.readouterr().err
    assert "source_roms" in err or "source-roms" in err
    assert "does-not-exist" in err


def test_setup_errors_on_missing_source_dat(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "config.yaml"
    source_roms = tmp_path / "roms"
    source_roms.mkdir()
    parser = build_parser()
    args = parser.parse_args(
        _flag_args(
            out=out,
            source_roms=source_roms,
            source_dat=tmp_path / "missing.dat.xml",
            dest_roms=tmp_path / "dest",
            retroarch_playlist=tmp_path / "mame.lpl",
        )
    )
    assert run(args) == 1
    assert not out.exists()
    err = capsys.readouterr().err
    assert "source_dat" in err or "source-dat" in err
    assert "missing.dat.xml" in err


def test_setup_handles_paths_with_spaces(tmp_path: Path) -> None:
    """Quoting: paths containing spaces (common on Windows / "MAME ROMs (non-merged)")
    must round-trip correctly through YAML serialization.
    """
    spaced = tmp_path / "MAME ROMs (non-merged)"
    spaced.mkdir()
    source_dat = _write_dat(tmp_path / "mame full.dat.xml")
    out = tmp_path / "config.yaml"

    parser = build_parser()
    args = parser.parse_args(
        _flag_args(
            out=out,
            source_roms=spaced,
            source_dat=source_dat,
            dest_roms=tmp_path / "Dest Folder",
            retroarch_playlist=tmp_path / "Dest Folder" / "mame.lpl",
        )
    )
    assert run(args) == 0
    raw = yaml.safe_load(out.read_text(encoding="utf-8"))
    cfg = AppConfig.model_validate(raw)
    assert cfg.paths.source_roms == spaced
    assert cfg.paths.source_dat == source_dat


def test_setup_interactive_prompts_for_each_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """No flags → wizard prompts for each path via ``rich.prompt.Prompt.ask``.

    Stubbing ``Prompt.ask`` lets us exercise the interactive path without
    a real TTY. Order of prompts is fixed by the wizard implementation.
    """
    source_roms = tmp_path / "roms"
    source_roms.mkdir()
    source_dat = _write_dat(tmp_path / "mame.dat.xml")
    dest_roms = tmp_path / "dest"
    retroarch = tmp_path / "mame.lpl"
    out = tmp_path / "config.yaml"

    answers = iter(
        [
            str(source_roms),
            str(source_dat),
            str(dest_roms),
            str(retroarch),
        ]
    )

    def _fake_ask(*args: object, **kwargs: object) -> str:
        return next(answers)

    monkeypatch.setattr("rich.prompt.Prompt.ask", staticmethod(_fake_ask))

    parser = build_parser()
    args = parser.parse_args(["setup", "--out", str(out)])
    assert run(args) == 0

    raw = yaml.safe_load(out.read_text(encoding="utf-8"))
    cfg = AppConfig.model_validate(raw)
    assert cfg.paths.source_roms == source_roms
    assert cfg.paths.retroarch_playlist == retroarch
    # Confirm a friendly summary went to stdout (not stderr).
    captured = capsys.readouterr()
    assert "config.yaml" in captured.out or str(out) in captured.out

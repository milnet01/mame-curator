"""mame-curator-1227: the command-line error findings of the 2026-11-11 review.

Each test names the finding it locks.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import httpx
import pytest

from mame_curator.cli import build_parser, run
from mame_curator.updates.ini import INIRefreshReport

_MINI_DAT = Path(__file__).resolve().parents[1] / "parser" / "fixtures" / "mini.dat.xml"


def _parse(*argv: str) -> Any:
    return build_parser().parse_args(list(argv))


# ---- RL-28: --purge-recycle is its own mode --------------------------------


def test_purge_recycle_cannot_be_combined_with_dry_run(tmp_path: Path) -> None:
    """RL-28: `--dry-run` reads as a preview, so it must not reach a real purge."""
    inputs = ["--dat", "x", "--listxml", "x", "--filter-report", "x"]
    inputs += ["--source", str(tmp_path), "--dest", str(tmp_path)]
    with pytest.raises(SystemExit) as exited:
        _parse("copy", "--purge-recycle", "--dry-run", *inputs)
    assert exited.value.code == 2


def test_purge_recycle_needs_no_copy_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    """RL-28: the purge uses none of the copy inputs, so it asks for none."""
    monkeypatch.setattr("mame_curator.cli.commands.copy.purge_recycle", lambda: (0, 0))
    assert run(_parse("copy", "--purge-recycle")) == 0


def test_copy_without_its_inputs_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    """RL-28: `--dry-run` and `--apply` still need every input, named when missing."""
    assert run(_parse("copy", "--dry-run", "--dat", str(_MINI_DAT))) == 2
    err = capsys.readouterr().err
    for flag in ("--listxml", "--filter-report", "--source", "--dest"):
        assert flag in err
    assert "--dat" not in err.replace("--dat ", "")  # given, so not named as missing


# ---- RL-35: winners the DAT does not hold ----------------------------------


def test_winners_missing_from_the_dat_stop_the_copy(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """RL-35: such a game would be copied with no playlist entry."""
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"winners": ["pacman", "notinthedat"]}), encoding="utf-8")
    dest = tmp_path / "dest"
    dest.mkdir()
    args = _parse(
        "copy",
        "--apply",
        "--dat",
        str(_MINI_DAT),
        "--listxml",
        str(Path(__file__).resolve().parents[1] / "api" / "fixtures" / "api_listxml.xml"),
        "--filter-report",
        str(report),
        "--source",
        str(tmp_path),
        "--dest",
        str(dest),
    )
    assert run(args) == 1
    assert "notinthedat" in capsys.readouterr().err
    assert list(dest.iterdir()) == []


# ---- CR-04-12, RL-30: refresh-inis -----------------------------------------


def test_refresh_inis_unwritable_dest_is_one_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """CR-04-12: an --dest that cannot be created is an error line, not a traceback."""
    blocker = tmp_path / "a-file"
    blocker.write_text("x", encoding="utf-8")
    args = _parse("refresh-inis", "--dest", str(blocker / "inis"), "--no-config")
    assert run(args) == 1
    assert "error:" in capsys.readouterr().err


def test_refresh_inis_saves_an_absolute_dest_in_any_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RL-30: `serve` may start from another folder, so a relative --dest would move."""
    work = tmp_path / "work"
    work.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    config = elsewhere / "config.yaml"
    config.write_text("paths: {}\n", encoding="utf-8")
    monkeypatch.chdir(work)

    async def fake_refresh(*, dest_dir: Path, client: Any) -> INIRefreshReport:
        return INIRefreshReport(updated=["catver.ini"])

    monkeypatch.setattr("mame_curator.updates.refresh_inis", fake_refresh)
    args = _parse("refresh-inis", "--dest", "inis", "--config", str(config))
    assert run(args) == 0
    assert str(work / "inis" / "catver.ini") in config.read_text(encoding="utf-8")


# ---- CR-04-2: refresh-snaps ------------------------------------------------


@pytest.mark.parametrize(
    "raised",
    [
        httpx.ConnectError("offline"),
        zipfile.BadZipFile("not a zip"),
        ValueError("no pack link on the page"),
        OSError("disk gone"),
    ],
)
def test_refresh_snaps_failures_are_one_line(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    raised: Exception,
) -> None:
    """CR-04-2: being offline or a bad pack prints one `error:` line and exits 1."""

    async def failing(**_kwargs: Any) -> Any:
        raise raised

    monkeypatch.setattr("mame_curator.updates.refresh_snaps", failing)
    assert run(_parse("refresh-snaps", "--dest", str(tmp_path))) == 1
    err = capsys.readouterr().err
    assert "error:" in err
    assert "Traceback" not in err


# ---- RL-32: setup makes the folders the Settings save requires -------------


def test_setup_creates_the_destination_and_playlist_folders(tmp_path: Path) -> None:
    """RL-32: a config naming a missing destination would be refused by Settings."""
    source = tmp_path / "roms"
    source.mkdir()
    dest = tmp_path / "new" / "dest"
    playlist = tmp_path / "new" / "playlists" / "mame.lpl"
    out = tmp_path / "config.yaml"
    args = _parse(
        "setup",
        "--out",
        str(out),
        "--source-roms",
        str(source),
        "--source-dat",
        str(_MINI_DAT),
        "--dest-roms",
        str(dest),
        "--retroarch-playlist",
        str(playlist),
    )
    assert run(args) == 0
    assert dest.is_dir()
    assert playlist.parent.is_dir()


# ---- CR-04-7: the broken-install message -----------------------------------


def test_serve_broken_install_message_names_no_missing_extra(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """CR-04-7: there is no `[api]` extra to install; the packages are core."""
    import builtins

    config = tmp_path / "config.yaml"
    config.write_text("paths: {}\n", encoding="utf-8")
    real_import = builtins.__import__

    def no_uvicorn(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "uvicorn":
            raise ImportError("No module named 'uvicorn'")
        return real_import(name, *args, **kwargs)

    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.setattr(builtins, "__import__", no_uvicorn)
    rc = run(_parse("serve", "--config", str(config), "--no-open-browser"))
    assert rc == 1
    err = capsys.readouterr().err
    assert "[api]" not in err
    assert "reinstall" in err.lower()

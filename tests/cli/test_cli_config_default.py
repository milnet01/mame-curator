"""`setup`, `refresh-inis` and `refresh-snaps` use the config `serve` uses.

Without `--config` (`--out` for `setup`), each goes through
`resolve_config_path`: `./config.yaml`, then the per-user one. Before this,
each pinned `./config.yaml`, so after a browser first run `refresh-inis`
downloaded its files, updated nothing and said nothing, and `setup --force`
wrote a new `./config.yaml` that silently took over from the per-user settings.
See `src/mame_curator/cli/spec.md` § Subcommand inventory.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from mame_curator.cli import build_parser, run
from mame_curator.config_location import resolve_config_path

_STARTER = """\
# the user's own comment
paths:
  source_roms: /x/roms
  source_dat: /x/dat.xml
  dest_roms: /x/dest
  retroarch_playlist: /x/mame.lpl
"""


@pytest.fixture
def user_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Work in an empty folder, with the per-user config under `tmp_path`."""
    config = tmp_path / "userconf" / "config.yaml"
    monkeypatch.setattr("mame_curator.config_location.user_config_path", lambda: config)
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    return config


def _setup_argv(tmp_path: Path, *extra: str) -> list[str]:
    roms = tmp_path / "roms"
    roms.mkdir(exist_ok=True)
    dat = tmp_path / "mame.dat.xml"
    dat.write_text("<mame></mame>\n", encoding="utf-8")
    return [
        "setup",
        "--source-roms",
        str(roms),
        "--source-dat",
        str(dat),
        "--dest-roms",
        str(tmp_path / "dest"),
        "--retroarch-playlist",
        str(tmp_path / "mame.lpl"),
        *extra,
    ]


def _run(argv: list[str]) -> int:
    # Typed: pre-commit's mypy, given this file alone, sees run() as Any.
    code: int = run(build_parser().parse_args(argv))
    return code


# ---- setup -----------------------------------------------------------


def test_setup_writes_where_serve_reads(user_config: Path, tmp_path: Path) -> None:
    """No `./config.yaml`: the file goes to the per-user location, folder included."""
    assert _run(_setup_argv(tmp_path)) == 0

    assert not Path("config.yaml").exists()
    assert user_config.exists()
    assert resolve_config_path(None)[0] == user_config


def test_setup_force_does_not_take_over_from_the_per_user_config(
    user_config: Path, tmp_path: Path
) -> None:
    """The silent takeover: `--force` rewrites the file in use and adds no other."""
    user_config.parent.mkdir(parents=True)
    user_config.write_text(_STARTER)

    assert _run(_setup_argv(tmp_path, "--force")) == 0

    assert not Path("config.yaml").exists(), "a new ./config.yaml would shadow the per-user one"
    assert yaml.safe_load(user_config.read_text())["paths"]["source_roms"] == str(tmp_path / "roms")


def test_setup_refuses_an_existing_per_user_config_without_force(
    user_config: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    user_config.parent.mkdir(parents=True)
    user_config.write_text(_STARTER)

    assert _run(_setup_argv(tmp_path)) == 1

    assert user_config.read_text() == _STARTER
    assert not Path("config.yaml").exists()
    assert "--force" in capsys.readouterr().err


def test_setup_keeps_a_config_in_the_working_folder_first(
    user_config: Path, tmp_path: Path
) -> None:
    """`./config.yaml` wins for `serve`, so `setup` rewrites that one."""
    Path("config.yaml").write_text(_STARTER)

    assert _run(_setup_argv(tmp_path, "--force")) == 0

    assert not user_config.exists()
    assert yaml.safe_load(Path("config.yaml").read_text())["paths"]["source_roms"] == str(
        tmp_path / "roms"
    )


def test_setup_out_flag_still_wins(user_config: Path, tmp_path: Path) -> None:
    out = tmp_path / "elsewhere.yaml"

    assert _run(_setup_argv(tmp_path, "--out", str(out))) == 0

    assert out.exists()
    assert not user_config.exists()
    assert not Path("config.yaml").exists()


def test_setup_success_line_needs_no_config_flag_by_default(
    user_config: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The hint must not send the user to a flag `serve` does not need."""
    assert _run(_setup_argv(tmp_path)) == 0

    out = capsys.readouterr().out
    assert "--config" not in out
    assert str(user_config.name) in out


def test_setup_force_failed_write_leaves_the_old_config(
    user_config: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A full disk during `--force` must not cost the user their settings."""
    user_config.parent.mkdir(parents=True)
    user_config.write_text(_STARTER)

    real_write_text = Path.write_text

    def _partial_write(self: Path, data: str, **kwargs: Any) -> int:
        real_write_text(self, data[:5], **kwargs)
        raise OSError(28, "No space left on device")

    def _no_replace(*_: Any) -> None:
        raise OSError(28, "No space left on device")

    argv = _setup_argv(tmp_path, "--force")
    with (
        patch.object(Path, "write_text", _partial_write),
        patch("mame_curator._atomic.os.replace", _no_replace),
    ):
        rc = _run(argv)

    assert rc == 1
    assert user_config.read_text() == _STARTER
    assert "error:" in capsys.readouterr().err


def test_setup_error_keeps_brackets_and_prints_a_plain_path(
    user_config: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """rich reads `[mame]` as a style tag; the path must survive whole."""
    out = tmp_path / "conf[mame].yaml"
    out.write_text(_STARTER)

    assert _run(_setup_argv(tmp_path, "--out", str(out))) == 1
    err = capsys.readouterr().err
    assert "conf[mame].yaml" in err
    assert "PosixPath" not in err
    assert "WindowsPath" not in err

    missing = tmp_path / "roms[mame]"
    argv = _setup_argv(tmp_path, "--out", str(tmp_path / "new.yaml"))
    argv[argv.index("--source-roms") + 1] = str(missing)
    assert _run(argv) == 1
    assert "roms[mame]" in capsys.readouterr().err


# ---- refresh-inis ----------------------------------------------------


@pytest.fixture
def downloaded(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub the download: `catver.ini` arrives and nothing fails."""

    async def _fake(*, dest_dir: Path, client: Any) -> Any:
        return SimpleNamespace(updated=["catver.ini"], failed=[], all_succeeded=True)

    monkeypatch.setattr("mame_curator.updates.refresh_inis", _fake)


def _paths(config: Path) -> dict[str, Any]:
    paths: dict[str, Any] = yaml.safe_load(config.read_text())["paths"]
    return paths


def test_refresh_inis_updates_the_per_user_config(
    user_config: Path, downloaded: None, capsys: pytest.CaptureFixture[str]
) -> None:
    """The HIGH finding: after a browser first run the app's config gets the path.

    The path is absolute, because the per-user config is read from any folder.
    """
    user_config.parent.mkdir(parents=True)
    user_config.write_text(_STARTER)

    assert _run(["refresh-inis", "--dest", "data/ini"]) == 0

    assert _paths(user_config)["catver"] == str(Path.cwd() / "data" / "ini" / "catver.ini")
    assert str(user_config) in capsys.readouterr().out


def test_refresh_inis_prefers_the_working_folder_config(
    user_config: Path, downloaded: None
) -> None:
    user_config.parent.mkdir(parents=True)
    user_config.write_text(_STARTER)
    Path("config.yaml").write_text(_STARTER)

    assert _run(["refresh-inis", "--dest", "data/ini"]) == 0

    assert _paths(Path("config.yaml"))["catver"] == str(Path("data/ini/catver.ini"))
    assert "catver" not in _paths(user_config)


def test_refresh_inis_warns_when_there_is_no_config(
    user_config: Path, downloaded: None, capsys: pytest.CaptureFixture[str]
) -> None:
    """The silent skip: the files arrive, the app will not use them, and it must say so."""
    assert _run(["refresh-inis", "--dest", "data/ini"]) == 0

    out = capsys.readouterr().out
    assert str(user_config) in out
    assert "will not use" in out
    assert not user_config.exists(), "refresh-inis does not create a config"


def test_refresh_inis_warns_for_a_missing_explicit_config(
    user_config: Path, downloaded: None, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "conf[x].yaml"

    assert _run(["refresh-inis", "--dest", "data/ini", "--config", str(missing)]) == 0

    out = capsys.readouterr().out
    assert "conf[x].yaml" in out
    assert "will not use" in out


def test_refresh_inis_no_config_flag_stays_quiet(
    user_config: Path, downloaded: None, capsys: pytest.CaptureFixture[str]
) -> None:
    user_config.parent.mkdir(parents=True)
    user_config.write_text(_STARTER)

    assert _run(["refresh-inis", "--dest", "data/ini", "--no-config"]) == 0

    assert "catver" not in _paths(user_config)
    assert "will not use" not in capsys.readouterr().out


def test_refresh_inis_says_when_every_path_is_already_set(
    user_config: Path, downloaded: None, capsys: pytest.CaptureFixture[str]
) -> None:
    user_config.parent.mkdir(parents=True)
    user_config.write_text(_STARTER + "  catver: /mine/catver.ini\n")

    assert _run(["refresh-inis", "--dest", "data/ini"]) == 0

    assert _paths(user_config)["catver"] == "/mine/catver.ini"
    assert "already set" in capsys.readouterr().out


@pytest.mark.parametrize("body", ["- a\n- b\n", "paths: 5\n"], ids=["not-mapping", "paths-not-map"])
def test_refresh_inis_warns_when_the_config_cannot_be_updated(
    user_config: Path, downloaded: None, capsys: pytest.CaptureFixture[str], body: str
) -> None:
    user_config.parent.mkdir(parents=True)
    user_config.write_text(body)

    assert _run(["refresh-inis", "--dest", "data/ini"]) == 0

    assert user_config.read_text() == body
    assert "will not use" in capsys.readouterr().out


# ---- refresh-snaps ---------------------------------------------------


@pytest.fixture
def snaps_dest(monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    captured: dict[str, Path] = {}

    async def _fake(*, dest_dir: Path, client: Any, **_: Any) -> Any:
        captured["dest"] = dest_dir
        return SimpleNamespace(
            error=None, downloaded=False, pack_url="http://x", files_extracted=0, files_skipped=0
        )

    monkeypatch.setattr("mame_curator.updates.refresh_snaps", _fake)
    return captured


def test_refresh_snaps_reads_the_per_user_config(
    user_config: Path, snaps_dest: dict[str, Path], tmp_path: Path
) -> None:
    """The download folder follows the folder the running app reads."""
    user_config.parent.mkdir(parents=True)
    user_config.write_text(_STARTER + f"media:\n  snaps_dir: {tmp_path / 'snaps'}\n")

    assert _run(["refresh-snaps"]) == 0

    assert snaps_dest["dest"] == tmp_path / "snaps"


def test_refresh_snaps_broken_config_error_keeps_brackets(
    user_config: Path,
    snaps_dest: dict[str, Path],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    broken = tmp_path / "conf[x].yaml"
    broken.write_text("{ not yaml")

    assert _run(["refresh-snaps", "--config", str(broken)]) == 1

    # This exact phrase: the cause quotes the path too, escaped by another call.
    assert f"media.snaps_dir from '{broken}' " in capsys.readouterr().err

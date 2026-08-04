"""Where `config.yaml` lives, and what happens on a first run.

A downloaded bundle has no `config.yaml` and no terminal to run the
interactive `mame-curator setup` wizard in, so `serve` resolves its
config through three layers and creates the last one when it is absent:

1. `--config <path>` — used exactly as given, never created.
2. `./config.yaml` — the existing workflow, unchanged.
3. the per-user config directory — **created** from a starter template,
   along with the data directories the API's path validation requires.

See `docs/specs/mame-curator-1095-desktop-bundles.md` § 4.1.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from mame_curator.api.schemas import AppConfig
from mame_curator.cli.commands.serve import _cmd_serve
from mame_curator.config_location import (
    ConfigSource,
    ensure_starter_config,
    resolve_config_path,
    user_config_path,
    user_data_path,
)


@pytest.fixture
def user_dirs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path]:
    """Point the per-user config and data directories at `tmp_path`.

    The accessors are replaced rather than the `XDG_*` environment,
    because `platformdirs` ignores those on the Windows CI leg and the
    resolution logic under test is the same on every platform.
    """
    config = tmp_path / "userconf" / "config.yaml"
    data = tmp_path / "userdata"
    monkeypatch.setattr("mame_curator.config_location.user_config_path", lambda: config)
    monkeypatch.setattr("mame_curator.config_location.user_data_path", lambda: data)
    return config, data


def _serve_args(config: Path | None, **kw: Any) -> argparse.Namespace:
    return argparse.Namespace(
        config=config,
        host=kw.get("host"),
        port=kw.get("port"),
        no_open_browser=kw.get("no_open_browser", True),
    )


# ---- The per-user location itself ------------------------------------


def test_user_paths_are_not_double_nested() -> None:
    """`appauthor=False`, or Windows nests the app name twice.

    `platformdirs` defaults the author to the app name and appends it
    *before* the app name, so an unqualified call yields
    `%LOCALAPPDATA%\\mame-curator\\mame-curator`. Nothing on a Linux dev
    box shows this, which is why it is pinned rather than eyeballed.
    """
    for path in (user_config_path(), user_data_path()):
        assert str(path).count("mame-curator") == 1, f"double-nested: {path}"


# ---- resolve_config_path: three layers, first hit wins ----------------


def test_explicit_flag_wins_and_reports_its_source(tmp_path: Path) -> None:
    explicit = tmp_path / "somewhere" / "custom.yaml"
    assert resolve_config_path(explicit) == (explicit, ConfigSource.EXPLICIT)


def test_cwd_config_beats_user_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, user_dirs: tuple[Path, Path]
) -> None:
    """Layer 2 — what keeps `run.sh` and a repo-root developer unchanged."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.yaml").write_text("paths: {}\n")

    path, source = resolve_config_path(None)

    assert source is ConfigSource.CWD
    assert path == Path("config.yaml")


def test_user_config_is_the_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, user_dirs: tuple[Path, Path]
) -> None:
    """Layer 3 — reached only when the working directory has no config."""
    monkeypatch.chdir(tmp_path)
    user_config, _ = user_dirs

    path, source = resolve_config_path(None)

    assert source is ConfigSource.USER
    assert path == user_config


# ---- ensure_starter_config -------------------------------------------


def test_starter_config_and_dirs_are_created(user_dirs: tuple[Path, Path]) -> None:
    """INV-1 — the config *and* the directories the API will validate.

    `_validate_paths` rejects a PATCH naming a `source_roms`,
    `dest_roms` or playlist parent that does not exist, so a starter
    config without these directories blocks the very save that ends
    setup mode.
    """
    user_config, _user_data = user_dirs

    assert ensure_starter_config(user_config) is True

    assert user_config.is_file()
    body = yaml.safe_load(user_config.read_text())
    paths = body["paths"]
    assert Path(paths["source_roms"]).is_dir()
    assert Path(paths["dest_roms"]).is_dir()
    assert Path(paths["retroarch_playlist"]).parent.is_dir()
    assert not Path(paths["source_dat"]).exists(), (
        "the DAT is the user's own file — fabricating one would put a phantom "
        "entry in their library"
    )


def test_starter_config_is_valid_appconfig(user_dirs: tuple[Path, Path]) -> None:
    """INV-6 — `AppConfig` has four required paths and forbids extras."""
    user_config, _ = user_dirs
    ensure_starter_config(user_config)

    AppConfig.model_validate(yaml.safe_load(user_config.read_text()))


def test_existing_config_is_never_overwritten(user_dirs: tuple[Path, Path]) -> None:
    """A corrupt or hand-edited config is the user's; creation is absent-only."""
    user_config, _ = user_dirs
    user_config.parent.mkdir(parents=True)
    user_config.write_text("paths: {mine: true}\n")

    assert ensure_starter_config(user_config) is False
    assert user_config.read_text() == "paths: {mine: true}\n"


# ---- _cmd_serve: the first run end to end -----------------------------


def test_serve_starts_with_generated_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, user_dirs: tuple[Path, Path]
) -> None:
    """INV-2 — a first run reaches `uvicorn.run` rather than exiting 1."""
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.chdir(tmp_path)
    user_config, _ = user_dirs

    with (
        patch("mame_curator.api.create_app") as create_app,
        patch("uvicorn.run") as run_mock,
    ):
        rc = _cmd_serve(_serve_args(None))

    assert rc == 130, "serve returns 130 on every non-error path"
    run_mock.assert_called_once()
    assert user_config.is_file(), "the first run must leave a config behind"
    assert create_app.call_args.args[0] == user_config, (
        "the resolved path must reach create_app, not the None default"
    )


def test_explicit_missing_config_still_exits_1(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, user_dirs: tuple[Path, Path]
) -> None:
    """INV-4 — a mistyped `--config` is an error, not a reason to create one."""
    monkeypatch.delenv("PORT", raising=False)
    user_config, _ = user_dirs
    missing = tmp_path / "typo.yaml"

    with patch("uvicorn.run") as run_mock:
        rc = _cmd_serve(_serve_args(missing))

    assert rc == 1
    run_mock.assert_not_called()
    assert not missing.exists()
    assert not user_config.exists(), (
        "layer 1 must not fall through to the starter-config path — that would "
        "silently manufacture a config and mask the typo"
    )


def test_invalid_port_still_beats_config_resolution(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, user_dirs: tuple[Path, Path]
) -> None:
    """INV-3 — creation happens in stage 2, after `$PORT` validation.

    `cli/spec.md` pins `$PORT` validation before any config I/O. Hoisting
    resolution to the top of `_cmd_serve` reads naturally and reverses it.
    """
    monkeypatch.setenv("PORT", "abc")
    monkeypatch.chdir(tmp_path)
    user_config, _ = user_dirs

    rc = _cmd_serve(_serve_args(None))

    assert rc == 1
    assert not user_config.exists(), "no config I/O may happen before the $PORT raise"

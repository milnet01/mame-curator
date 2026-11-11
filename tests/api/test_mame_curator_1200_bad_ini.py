"""mame-curator-1200 — a bad reference INI must not stop the next start.

The reference INIs are optional, like the listxml (mame-curator-1168): without
one the Library still works, with less to filter on. So an INI that is missing
or cannot be read is skipped at startup with a WARNING naming it, rather than
failing the start the way it did when a Settings save named one.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import pytest

from mame_curator.api.state import build_world, ini_context_fields
from mame_curator.parser import INIError
from tests.api.conftest import LOCAL_URL

INI_KEYS = ("catver", "languages", "bestgames", "mature", "series")


def _config_with(config_file: Path, key: str, value: Path) -> Path:
    text = config_file.read_text(encoding="utf-8")
    patched, count = re.subn(rf"(?m)^  {key}: .*$", lambda _m: f"  {key}: {value}", text)
    assert count == 1, f"config fixture no longer has exactly one {key} line"
    config_file.write_text(patched, encoding="utf-8")
    return config_file


@pytest.mark.parametrize("key", INI_KEYS)
@pytest.mark.parametrize("shape", ["missing", "a folder"])
def test_bad_ini_is_skipped_at_startup(
    config_file: Path, tmp_path: Path, key: str, shape: str, caplog: pytest.LogCaptureFixture
) -> None:
    """The world builds with the games, the other INIs, and none of this one's data."""
    bad = tmp_path / f"bad-{key}.ini"
    if shape == "a folder":
        bad.mkdir()
    good = build_world(config_file).ctx

    with caplog.at_level(logging.WARNING, logger="mame_curator.api.state"):
        world = build_world(_config_with(config_file, key, bad))

    assert world.setup_required is False
    assert world.machines, "the games from the DAT must still load"
    ctx_field = {"catver": "category", "bestgames": "bestgames_tier"}.get(key, key)
    if key != "series":
        assert not getattr(world.ctx, ctx_field), f"{key} data should be empty"
    for other in ("category", "languages", "mature", "bestgames_tier"):
        if other != ctx_field:
            assert getattr(world.ctx, other) == getattr(good, other)
    assert any(bad.name in r.getMessage() for r in caplog.records), caplog.text


def test_settings_save_of_bad_ini_does_not_stop_next_start(
    config_file: Path, tmp_path: Path
) -> None:
    """The reported path: save a missing catver in Settings, then start again."""
    from fastapi.testclient import TestClient

    from mame_curator.api import create_app

    bad = tmp_path / "gone-catver.ini"
    client: Any
    with TestClient(create_app(config_file), base_url=LOCAL_URL) as client:
        saved = client.patch("/api/config", json={"paths": {"catver": str(bad)}})
        assert saved.status_code == 200, saved.text

    with TestClient(create_app(config_file), base_url=LOCAL_URL) as client:
        assert client.get("/api/setup/check").json()["setup_required"] is False
        assert client.get("/api/games").status_code == 200


def test_the_ini_refresh_preview_still_refuses_a_bad_ini(tmp_path: Path) -> None:
    """Only startup skips: the preview reports a file that will not read."""
    with pytest.raises(INIError):
        ini_context_fields(
            catver=tmp_path / "gone.ini", languages=None, bestgames=None, mature=None, series=None
        )

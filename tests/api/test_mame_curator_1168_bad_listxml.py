"""mame-curator-1168 — a bad ``paths.listxml`` must not stop the next start.

The listxml is optional: without it the Library still works, with region and
version variants shown as separate cards. So a listxml that is missing or
will not parse is skipped at startup with a WARNING, rather than failing the
start the way it did when a Settings save named a malformed one.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import pytest

from mame_curator.api.state import build_world


def _config_with_listxml(config_file: Path, listxml: Path) -> Path:
    text = config_file.read_text(encoding="utf-8")
    patched, count = re.subn(r"(?m)^  listxml: .*$", lambda _m: f"  listxml: {listxml}", text)
    assert count == 1, "config fixture no longer has exactly one listxml line"
    config_file.write_text(patched, encoding="utf-8")
    return config_file


@pytest.mark.parametrize("shape", ["malformed", "missing"])
def test_bad_listxml_is_skipped_at_startup(
    config_file: Path, tmp_path: Path, shape: str, caplog: pytest.LogCaptureFixture
) -> None:
    """The world builds with the games and without the listxml's data."""
    bad = tmp_path / "bad-listxml.xml"
    if shape == "malformed":
        bad.write_text("<mame><machine name='pacman'", encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="mame_curator.api.state"):
        world = build_world(_config_with_listxml(config_file, bad))

    assert world.setup_required is False
    assert world.machines, "the games from the DAT must still load"
    assert world.cloneof_map == {}
    assert world.bios_chain == {}
    assert world.chd_required == frozenset()
    assert any(str(bad) in r.getMessage() for r in caplog.records), caplog.text


def test_settings_save_of_bad_listxml_does_not_stop_next_start(
    config_file: Path, tmp_path: Path
) -> None:
    """The reported path: save a malformed listxml in Settings, then start again."""
    from fastapi.testclient import TestClient

    from mame_curator.api import create_app

    bad = tmp_path / "bad-listxml.xml"
    bad.write_text("<mame><machine name='pacman'", encoding="utf-8")
    client: Any
    with TestClient(create_app(config_file)) as client:
        saved = client.patch("/api/config", json={"paths": {"listxml": str(bad)}})
        assert saved.status_code == 200, saved.text

    with TestClient(create_app(config_file)) as client:
        check = client.get("/api/setup/check").json()
        assert check["setup_required"] is False
        assert check["cloneof_map_size"] == 0
        assert client.get("/api/games").status_code == 200

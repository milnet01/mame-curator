"""mame-curator-1155 — the Grouped layout is gone, and an old value still loads.

Grouped drew the same grid as Masonry, so the choice was removed. A
``config.yaml`` or Backup file saved before then can hold
``ui.layout: grouped``. Past v1.0.0 a value change must read the old form
(docs/standards/versioning-overrides.md, item 1), so both readers turn it into
the default, ``masonry``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, get_args

import pytest
from pydantic import ValidationError

from mame_curator.api.schemas import UiConfig
from mame_curator.api.state import load_app_config

_CONFIG = """\
paths:
  source_roms: /roms
  source_dat: /roms.zip
  dest_roms: /dest
  retroarch_playlist: /dest/mame.lpl
ui:
  layout: grouped
"""


def test_a_saved_grouped_layout_loads_as_masonry(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text(_CONFIG, encoding="utf-8")
    assert load_app_config(config).ui.layout == "masonry"


def test_a_backup_holding_grouped_imports_as_masonry(client: Any) -> None:
    bundle = client.post("/api/config/export").json()
    bundle["config"]["ui"]["layout"] = "grouped"
    assert client.post("/api/config/import", json=bundle).status_code == 200
    assert client.get("/api/config").json()["ui"]["layout"] == "masonry"


def test_grouped_is_no_longer_a_layout_and_unknown_ones_are_still_refused() -> None:
    assert get_args(UiConfig.model_fields["layout"].annotation) == ("masonry", "list", "covers")
    assert UiConfig(layout="grouped").layout == "masonry"  # type: ignore[arg-type]  # the old value
    with pytest.raises(ValidationError):
        UiConfig(layout="mosaic")  # type: ignore[arg-type]  # not a layout

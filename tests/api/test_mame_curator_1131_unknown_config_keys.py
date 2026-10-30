"""mame-curator-1131 / 1135 — ``load_app_config`` tolerates keys it does not know.

1131: an update adds a config key, a Settings save writes it, then "Roll
back" returns to code without that key. ``AppConfig`` is
``extra="forbid"``, so the next start refused the file before Settings
could load. The loader now drops keys it does not recognise, at any depth,
and logs one WARNING naming each.

1135: ``config.example.yaml`` carries a top-level ``picker:`` section that
``FilterConfig`` owns, but the loader never folded it into ``filters:`` as
``AppConfigPatch`` does, so a config copied from the example refused to load.

Pre-fix: every test below except the last raises ``ConfigError``.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from mame_curator.api.errors import ConfigError
from mame_curator.api.state import load_app_config

_PATHS = """\
paths:
  source_roms: /roms
  source_dat: /roms.zip
  dest_roms: /dest
  retroarch_playlist: /dest/mame.lpl
"""

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _write(tmp_path: Path, body: str) -> Path:
    config = tmp_path / "config.yaml"
    config.write_text(_PATHS + body, encoding="utf-8")
    return config


def test_unknown_top_level_section_is_dropped_with_a_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    config = _write(tmp_path, "future_section:\n  enabled: true\nui:\n  theme: light\n")
    with caplog.at_level(logging.WARNING, logger="mame_curator.api.state"):
        loaded = load_app_config(config)
    assert loaded.ui.theme == "light"
    assert "future_section" in caplog.text


def test_unknown_nested_key_is_dropped_and_its_siblings_kept(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    config = _write(tmp_path, "ui:\n  theme: light\n  future_option: 3\n")
    with caplog.at_level(logging.WARNING, logger="mame_curator.api.state"):
        loaded = load_app_config(config)
    assert loaded.ui.theme == "light"
    assert "ui.future_option" in caplog.text


def test_picker_section_folds_into_filters(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    config = _write(
        tmp_path,
        "filters:\n  drop_mature: false\npicker:\n  region_priority: [Japan, USA]\n",
    )
    with caplog.at_level(logging.WARNING, logger="mame_curator.api.state"):
        loaded = load_app_config(config)
    assert loaded.filters.region_priority == ("Japan", "USA")
    assert loaded.filters.drop_mature is False
    assert "picker" not in caplog.text


def test_config_example_yaml_loads() -> None:
    loaded = load_app_config(_REPO_ROOT / "config.example.yaml")
    assert loaded.filters.prefer_good_driver is True


def test_a_bad_value_for_a_known_key_still_refuses(tmp_path: Path) -> None:
    config = _write(tmp_path, "ui:\n  theme: no_such_theme\n")
    with pytest.raises(ConfigError):
        load_app_config(config)


@pytest.mark.parametrize(
    "body",
    ["picker: 5\n", "filters: 5\npicker:\n  region_priority: [USA]\n"],
    ids=["picker_not_a_mapping", "filters_not_a_mapping"],
)
def test_a_non_mapping_picker_or_filters_refuses(tmp_path: Path, body: str) -> None:
    """review-code 2026-10-30 #5 / #6: the picker fold must not swallow a bad
    value, nor drop a bad `picker:` as an unknown key."""
    with pytest.raises(ConfigError):
        load_app_config(_write(tmp_path, body))


def test_dropped_key_names_are_logged_escaped(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """review-code 2026-10-30 #7: a key holding a newline must not split
    the warning into a second, forged log line."""
    config = _write(tmp_path, '"evil\\nkey": 1\n')
    with caplog.at_level(logging.WARNING, logger="mame_curator.api.state"):
        load_app_config(config)
    assert "evil\\nkey" in caplog.text
    assert "evil\nkey" not in caplog.text

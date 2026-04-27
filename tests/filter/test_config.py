"""Tests for FilterConfig."""

import pytest
from pydantic import ValidationError

from mame_curator.filter.config import FilterConfig


def test_defaults_match_design_spec() -> None:
    cfg = FilterConfig()
    assert cfg.drop_bios_devices_mechanical is True
    assert cfg.drop_japanese_only_text is True
    assert cfg.drop_preliminary_emulation is True
    assert cfg.drop_chd_required is True
    assert cfg.drop_mature is True
    assert cfg.prefer_parent_over_clone is True
    assert cfg.prefer_good_driver is True
    assert cfg.region_priority == ("World", "USA", "Europe", "Japan", "Asia", "Brazil")


def test_immutable() -> None:
    cfg = FilterConfig()
    with pytest.raises(ValidationError):
        cfg.drop_chd_required = False


def test_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        FilterConfig(bogus_key=True)  # type: ignore[call-arg]


def test_year_range_independent_of_each_other() -> None:
    cfg = FilterConfig(drop_year_before=1980)
    assert cfg.drop_year_before == 1980
    assert cfg.drop_year_after is None

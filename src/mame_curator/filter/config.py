"""Pydantic schema for the filter+picker subset of config.yaml."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class FilterConfig(BaseModel):
    """The `filters:` and `picker:` sections of config.yaml.

    Defaults match the example config and the design spec §6.2.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    drop_bios_devices_mechanical: bool = True
    drop_categories: tuple[str, ...] = ()
    drop_genres: tuple[str, ...] = ()
    drop_publishers: tuple[str, ...] = ()
    drop_developers: tuple[str, ...] = ()
    drop_year_before: int | None = None
    drop_year_after: int | None = None
    drop_japanese_only_text: bool = True
    drop_preliminary_emulation: bool = True
    drop_chd_required: bool = True
    drop_mature: bool = True

    region_priority: tuple[str, ...] = ("World", "USA", "Europe", "Japan", "Asia", "Brazil")
    preferred_genres: tuple[str, ...] = ()
    preferred_publishers: tuple[str, ...] = ()
    preferred_developers: tuple[str, ...] = ()
    prefer_parent_over_clone: bool = True
    prefer_good_driver: bool = True

"""Reference-data refresh primitives.

P07 ships the slim version: ``ini.refresh_inis`` downloads the 4 mandatory
progettoSnaps reference INIs via ``mame_curator.downloads.download``.

P12 (post-v1) adds the diff-preview UI and app self-update. See
``ROADMAP.md`` § P12.
"""

from mame_curator.updates.ini import (
    INI_DEFAULT_SOURCES,
    INIRefreshReport,
    refresh_inis,
)

__all__ = ["INI_DEFAULT_SOURCES", "INIRefreshReport", "refresh_inis"]

"""Reference-data refresh primitives.

P07 ships the slim version: ``ini.refresh_inis`` downloads the 4 mandatory
progettoSnaps reference INIs via ``mame_curator.downloads.download``.

P10 chunk 3a adds ``snaps.refresh_snaps`` — downloads + extracts the
progettoSnaps snap pack (snap kind only; other kinds aren't maintained
upstream).

P12 (post-v1) adds the diff-preview UI and app self-update. See
``ROADMAP.md`` § P12.
"""

from mame_curator.updates.ini import (
    INI_DEFAULT_SOURCES,
    INIRefreshReport,
    refresh_inis,
)
from mame_curator.updates.snaps import (
    INDEX_URL as SNAPS_INDEX_URL,
)
from mame_curator.updates.snaps import (
    SNAP_PACK_MAX_BYTES,
    SnapsRefreshReport,
    discover_snap_pack_url,
    refresh_snaps,
)

__all__ = [
    "INI_DEFAULT_SOURCES",
    "SNAPS_INDEX_URL",
    "SNAP_PACK_MAX_BYTES",
    "INIRefreshReport",
    "SnapsRefreshReport",
    "discover_snap_pack_url",
    "refresh_inis",
    "refresh_snaps",
]

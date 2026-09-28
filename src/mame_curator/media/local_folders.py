"""Artwork another tool already scraped, read from a local folder (mame-curator-1126).

Two sources in the ``file://`` model ``ProgettoSnapsSource`` set: no network,
``prepare`` a no-op, ``url_for`` a ``file://`` URL when the image is on disk.

- ``EsdeSource`` — an ES-DE ``downloaded_media/<system>`` folder. ES-DE names
  each file after the ROM, which for a MAME set is the short name.
- ``RetroArchThumbnailsSource`` — a RetroArch ``thumbnails/<playlist>`` folder
  in the libretro-thumbnails layout, named by the escaped description.

Any tool that lays its folder out either way works; the names only say where
the layout comes from. Each source is off until its folder is set, and a
candidate that resolves outside the folder is refused, so a hostile name
cannot turn a lookup into a read of an arbitrary file.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import httpx

from mame_curator.media.sources import Kind
from mame_curator.media.urls import escape_libretro
from mame_curator.parser.models import Machine

_EXTENSIONS = (".png", ".jpg", ".jpeg")


class _LocalFolderSource:
    """Shared ``file://`` lookup: first existing candidate inside ``root``."""

    name: ClassVar[str]
    license_compatible: ClassVar[bool] = True
    kinds: ClassVar[frozenset[Kind]] = frozenset({"boxart", "title", "snap"})
    _FOLDERS: ClassVar[dict[Kind, str]]
    _UNSET: ClassVar[str]
    _MISSING: ClassVar[str]

    def __init__(self, root: Path | None) -> None:
        """Bind to ``root``; self-disable when it is unset or not a directory."""
        self._root: Path | None = None
        self.disabled_reason: str | None = self._UNSET
        if root is None:
            return
        try:
            is_dir = root.is_dir()
        except OSError:
            is_dir = False
        if not is_dir:
            self.disabled_reason = self._MISSING.format(root=root)
            return
        self._root = root.resolve()
        self.disabled_reason = None

    async def prepare(self, machine: Machine, *, client: httpx.AsyncClient) -> None:
        """No-op: a local folder has no per-machine lookup state."""
        return

    def _stems(self, machine: Machine) -> tuple[str, ...]:
        raise NotImplementedError

    def url_for(self, machine: Machine, kind: Kind) -> str | None:
        """``file://`` URL of the first image on disk for ``(machine, kind)``."""
        if self._root is None or kind not in self._FOLDERS:
            return None
        folder = self._root / self._FOLDERS[kind]
        for stem in self._stems(machine):
            for ext in _EXTENSIONS:
                candidate = (folder / f"{stem}{ext}").resolve()
                if candidate.is_relative_to(self._root) and candidate.is_file():
                    return candidate.as_uri()
        return None


class EsdeSource(_LocalFolderSource):
    """ES-DE scraped media: ``covers`` / ``titlescreens`` / ``screenshots``."""

    name: ClassVar[str] = "esde"
    _FOLDERS: ClassVar[dict[Kind, str]] = {
        "boxart": "covers",
        "title": "titlescreens",
        "snap": "screenshots",
    }
    _UNSET: ClassVar[str] = (
        "No ES-DE media folder set. Choose its downloaded_media/<system> folder "
        "under Settings → Media."
    )
    _MISSING: ClassVar[str] = "ES-DE media folder not found: {root}"

    def __init__(self, *, media_dir: Path | None) -> None:
        """Bind to an ES-DE ``downloaded_media/<system>`` folder."""
        super().__init__(media_dir)

    def _stems(self, machine: Machine) -> tuple[str, ...]:
        return (machine.name,)


class RetroArchThumbnailsSource(_LocalFolderSource):
    """RetroArch thumbnails: ``Named_Boxarts`` / ``Named_Titles`` / ``Named_Snaps``."""

    name: ClassVar[str] = "retroarchThumbnails"
    _FOLDERS: ClassVar[dict[Kind, str]] = {
        "boxart": "Named_Boxarts",
        "title": "Named_Titles",
        "snap": "Named_Snaps",
    }
    _UNSET: ClassVar[str] = (
        "No RetroArch thumbnails folder set. Choose its thumbnails/<playlist> "
        "folder under Settings → Media."
    )
    _MISSING: ClassVar[str] = "RetroArch thumbnails folder not found: {root}"

    def __init__(self, *, thumbnails_dir: Path | None) -> None:
        """Bind to a RetroArch ``thumbnails/<playlist>`` folder."""
        super().__init__(thumbnails_dir)

    def _stems(self, machine: Machine) -> tuple[str, ...]:
        return (escape_libretro(machine.description), machine.name)

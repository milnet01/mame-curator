"""RetroArch v6+ JSON `.lpl` playlist writer."""

from __future__ import annotations

import contextlib
import json
import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from mame_curator.copy.errors import PlaylistError
from mame_curator.copy.types import PlaylistEntry


def _build_payload(entries: Iterable[PlaylistEntry]) -> dict[str, Any]:
    items: list[dict[str, str | int]] = []
    for e in entries:
        items.append(
            {
                "path": str(e.abs_path),
                "label": e.description,
                "core_path": "DETECT",
                "core_name": "DETECT",
                "crc32": "00000000|crc",
                "db_name": "MAME.lpl",
            }
        )
    # Top-level keys in canonical RetroArch order.
    return {
        "version": "1.5",
        "default_core_path": "",
        "default_core_name": "",
        "label_display_mode": 0,
        "right_thumbnail_mode": 0,
        "left_thumbnail_mode": 0,
        "sort_mode": 0,
        "items": items,
    }


def write_lpl(playlist_path: Path, entries: Iterable[PlaylistEntry]) -> None:
    """Atomically write a RetroArch v6+ JSON playlist to `playlist_path`."""
    payload = _build_payload(entries)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"

    playlist_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = playlist_path.with_suffix(playlist_path.suffix + ".tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, playlist_path)
    except OSError as exc:
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)
        raise PlaylistError(f"failed to write playlist: {exc}", path=playlist_path) from exc


def read_lpl(playlist_path: Path) -> list[dict[str, str]]:
    """Parse an existing `.lpl` and return the items list."""
    if not playlist_path.exists():
        raise PlaylistError("playlist does not exist", path=playlist_path)
    try:
        raw = playlist_path.read_text(encoding="utf-8")
        parsed = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise PlaylistError(f"failed to parse playlist: {exc}", path=playlist_path) from exc
    items = parsed.get("items", [])
    if not isinstance(items, list):
        raise PlaylistError("playlist 'items' is not a list", path=playlist_path)
    return items

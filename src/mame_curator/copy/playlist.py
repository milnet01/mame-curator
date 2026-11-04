"""RetroArch v6+ JSON `.lpl` playlist writer."""

from __future__ import annotations

import json
import struct
import zlib
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import zstandard

from mame_curator._atomic import atomic_write_text
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
    """Atomically write a RetroArch v6+ JSON playlist to `playlist_path`.

    FP20-B: routed through ``atomic_write_text`` so the rename + parent-
    fsync + tmp cleanup-on-failure protocol matches the project-wide
    helper. Prior inline ``tmp.write_text + os.replace`` did not fsync,
    used a guessable tmp suffix (collision-prone with concurrent writers),
    and missed parent-dir fsync entirely.
    """
    payload = _build_payload(entries)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"

    try:
        atomic_write_text(playlist_path, text)
    except OSError as exc:
        raise PlaylistError(f"failed to write playlist: {exc}", path=playlist_path) from exc


_RZIP_MAGIC = b"#RZIPv"
_RZIP_HEADER = struct.Struct("<8sIQ")  # magic+version+'#', chunk size, total size
_RZIP_CHUNK_LEN = struct.Struct("<I")


def _decode_rzip(data: bytes) -> bytes:
    """Decompress RetroArch's RZIP playlist form (mame-curator-1174).

    Version 2 chunks are zstd; version 1 chunks are zlib. Raises
    ValueError on anything malformed, so the caller's parse error covers it.
    """
    if len(data) < _RZIP_HEADER.size or data[7:8] != b"#":
        raise ValueError("RZIP header is truncated")
    _, chunk_size, total = _RZIP_HEADER.unpack_from(data)
    version = data[6]
    if version not in (1, 2):
        raise ValueError(f"RZIP version {version} is not supported")
    out = bytearray()
    pos = _RZIP_HEADER.size
    while pos < len(data):
        if pos + _RZIP_CHUNK_LEN.size > len(data):
            raise ValueError("RZIP chunk length is truncated")
        (length,) = _RZIP_CHUNK_LEN.unpack_from(data, pos)
        pos += _RZIP_CHUNK_LEN.size
        chunk = data[pos : pos + length]
        if len(chunk) != length:
            raise ValueError("RZIP chunk is truncated")
        pos += length
        try:
            if version == 2:
                block = zstandard.ZstdDecompressor().decompress(chunk, max_output_size=chunk_size)
            else:
                block = zlib.decompress(chunk)
        except (zstandard.ZstdError, zlib.error) as exc:
            raise ValueError(f"RZIP chunk does not decompress: {exc}") from exc
        out += block
        if len(out) > total:
            break
    if len(out) != total:
        raise ValueError(f"RZIP holds {len(out)} bytes, header says {total}")
    return bytes(out)


def read_lpl(playlist_path: Path) -> list[dict[str, str]]:
    """Parse an existing `.lpl` and return the items list.

    Reads plain JSON and RetroArch's compressed RZIP form.
    """
    if not playlist_path.exists():
        raise PlaylistError("playlist does not exist", path=playlist_path)
    try:
        data = playlist_path.read_bytes()
        if data.startswith(_RZIP_MAGIC):
            data = _decode_rzip(data)
        parsed = json.loads(data.decode("utf-8"))
    except (OSError, ValueError) as exc:
        # ValueError covers JSONDecodeError, UnicodeDecodeError and RZIP errors.
        raise PlaylistError(f"failed to parse playlist: {exc}", path=playlist_path) from exc
    if not isinstance(parsed, dict):
        raise PlaylistError("playlist is not a JSON object", path=playlist_path)
    items = parsed.get("items", [])
    if not isinstance(items, list):
        raise PlaylistError("playlist 'items' is not a list", path=playlist_path)
    # Callers read entries with `.get` and build a Path from `path`; drop
    # anything that is not an object, or whose `path` is not a string.
    return [it for it in items if isinstance(it, dict) and isinstance(it.get("path", ""), str)]

"""mame-curator-1174 — read_lpl reads a playlist RetroArch has compressed.

RetroArch can save a playlist in its RZIP form: a 20-byte header
(``#RZIPv`` + version byte + ``#``, chunk size u32 LE, total size u64 LE),
then chunks, each a u32 LE compressed length and that many bytes.
Version 2 chunks are zstd (the user's real mame.lpl, measured 2026-11-02);
version 1 chunks are zlib.

Pre-fix: read_lpl decoded the bytes as UTF-8 and raised PlaylistError.
"""

from __future__ import annotations

import json
import struct
import zlib
from collections.abc import Callable
from pathlib import Path

import pytest
import zstandard

from mame_curator.copy.errors import PlaylistError
from mame_curator.copy.playlist import read_lpl

ITEMS = [
    {"path": "/roms/pacman.zip", "label": "Pac-Man"},
    {"path": "/roms/sf2.zip", "label": "Street Fighter II"},
]
CHUNK = 64  # small, so the payload spans several chunks


def _rzip(version: int, compress: Callable[[bytes], bytes], data: bytes) -> bytes:
    out = b"#RZIPv" + bytes([version]) + b"#" + struct.pack("<IQ", CHUNK, len(data))
    for start in range(0, len(data), CHUNK):
        block = compress(data[start : start + CHUNK])
        out += struct.pack("<I", len(block)) + block
    return out


def _zstd(block: bytes) -> bytes:
    return zstandard.ZstdCompressor().compress(block)


PAYLOAD = json.dumps({"version": "1.5", "items": ITEMS}, indent=2).encode()
GOOD_V2 = _rzip(2, _zstd, PAYLOAD)
_WHOLE = _zstd(PAYLOAD)
# One complete chunk whose length field claims five bytes past the file's end.
LENGTH_PAST_END = (
    b"#RZIPv\x02#"
    + struct.pack("<IQ", len(PAYLOAD), len(PAYLOAD))
    + struct.pack("<I", len(_WHOLE) + 5)
    + _WHOLE
)


@pytest.mark.parametrize(
    ("version", "compress"),
    [pytest.param(2, _zstd, id="v2-zstd"), pytest.param(1, zlib.compress, id="v1-zlib")],
)
def test_read_lpl_reads_rzip(
    tmp_path: Path, version: int, compress: Callable[[bytes], bytes]
) -> None:
    lpl = tmp_path / "mame.lpl"
    lpl.write_bytes(_rzip(version, compress, PAYLOAD))
    assert len(PAYLOAD) > 2 * CHUNK  # the reader must join chunks
    assert read_lpl(lpl) == ITEMS


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(b"#RZIPv\x02#" + b"\x00" * 4, id="short-header"),
        # zlib chunks, so only the version check refuses it.
        pytest.param(_rzip(9, zlib.compress, PAYLOAD), id="unknown-version"),
        pytest.param(GOOD_V2[:-5], id="truncated-chunk"),
        pytest.param(LENGTH_PAST_END, id="length-past-end"),
        pytest.param(_rzip(2, zlib.compress, PAYLOAD), id="wrong-codec"),
        pytest.param(
            GOOD_V2[:12] + struct.pack("<Q", len(PAYLOAD) + 1) + GOOD_V2[20:],
            id="size-mismatch",
        ),
    ],
)
def test_read_lpl_refuses_bad_rzip(tmp_path: Path, content: bytes) -> None:
    lpl = tmp_path / "mame.lpl"
    lpl.write_bytes(content)
    with pytest.raises(PlaylistError, match="failed to parse playlist"):
        read_lpl(lpl)

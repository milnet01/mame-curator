"""mame-curator-1225 — compressed playlists and Windows file names.

CR-02-9: an RZIP chunk must not inflate past the header's chunk size, and
a declared total past the cap is refused before anything is inflated.
CR-02-10: a short name that Windows reads as a device, or that holds a
character Windows forbids, is not a plain file name. No machine in MAME
0.287's listxml is affected (checked 2026-11-11).
"""

from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path

import pytest

from mame_curator.copy import playlist
from mame_curator.copy.errors import PlaylistError
from mame_curator.copy.paths import is_safe_short_name


def _rzip_v1(chunk_size: int, chunks: list[bytes], total: int) -> bytes:
    out = b"#RZIPv\x01#" + struct.pack("<IQ", chunk_size, total)
    for raw in chunks:
        block = zlib.compress(raw)
        out += struct.pack("<I", len(block)) + block
    return out


def _lpl(tmp_path: Path, data: bytes) -> Path:
    path = tmp_path / "mame.lpl"
    path.write_bytes(data)
    return path


def test_a_chunk_that_inflates_past_the_chunk_size_is_refused(tmp_path: Path) -> None:
    body = json.dumps({"items": []}).encode().ljust(10_000)
    data = _rzip_v1(64, [body], len(body))
    with pytest.raises(PlaylistError):
        playlist.read_lpl(_lpl(tmp_path, data))


def test_a_declared_total_past_the_cap_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = json.dumps({"items": []}).encode()
    data = _rzip_v1(64, [body[i : i + 64] for i in range(0, len(body), 64)], len(body))
    monkeypatch.setattr(playlist, "_RZIP_MAX_BYTES", len(body) - 1, raising=False)
    with pytest.raises(PlaylistError):
        playlist.read_lpl(_lpl(tmp_path, data))


@pytest.mark.parametrize(
    "name", ["con", "NUL", "Aux", "prn", "com1", "LPT9", "a*b", "a?b", 'a"b', "a<b", "a>b", "a|b"]
)
def test_a_name_windows_cannot_hold_is_refused(name: str) -> None:
    assert not is_safe_short_name(name)


@pytest.mark.parametrize("name", ["pacman", "conan", "nulla", "com", "lpt", "aux2x", "1942"])
def test_a_plain_name_is_kept(name: str) -> None:
    assert is_safe_short_name(name)

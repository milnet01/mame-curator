"""Tests for `write_lpl` / `read_lpl` RetroArch v6+ JSON playlist."""

from __future__ import annotations

import json
from pathlib import Path

from mame_curator.copy import read_lpl, write_lpl
from mame_curator.copy.types import PlaylistEntry


def _entry(short: str, desc: str, dest: Path) -> PlaylistEntry:
    return PlaylistEntry(
        short_name=short,
        description=desc,
        abs_path=(dest / f"{short}.zip").resolve(),
    )


def test_lpl_format_matches_retroarch_spec(tmp_path: Path) -> None:
    """Output is valid JSON with the canonical RetroArch v6+ schema."""
    dest = tmp_path / "mame"
    dest.mkdir()
    entries = [
        _entry("kof94", "The King of Fighters '94", dest),
        _entry("sf2ce", "Street Fighter II' - Champion Edition", dest),
    ]
    out = dest / "mame.lpl"
    write_lpl(out, entries)

    parsed = json.loads(out.read_text(encoding="utf-8"))
    # Top-level required fields per Libretro docs.
    assert parsed["version"] == "1.5"
    assert "default_core_path" in parsed
    assert "default_core_name" in parsed
    assert parsed["label_display_mode"] == 0
    assert parsed["right_thumbnail_mode"] == 0
    assert parsed["left_thumbnail_mode"] == 0
    assert parsed["sort_mode"] == 0
    assert isinstance(parsed["items"], list)
    assert len(parsed["items"]) == 2

    # Per-item fields.
    item = parsed["items"][0]
    assert item["path"].endswith("/kof94.zip")
    assert Path(item["path"]).is_absolute()
    assert item["label"] == "The King of Fighters '94"
    assert item["core_path"] == "DETECT"
    assert item["core_name"] == "DETECT"
    assert item["crc32"] == "00000000|crc"
    assert item["db_name"] == "MAME.lpl"


def test_lpl_top_level_key_order_canonical(tmp_path: Path) -> None:
    """Top-level keys appear in the exact order RetroArch expects."""
    dest = tmp_path / "mame"
    dest.mkdir()
    out = dest / "mame.lpl"
    write_lpl(out, [_entry("kof94", "KoF '94", dest)])

    text = out.read_text(encoding="utf-8")
    # Find each key's position; assert monotonic.
    positions = [
        text.find('"version"'),
        text.find('"default_core_path"'),
        text.find('"default_core_name"'),
        text.find('"label_display_mode"'),
        text.find('"right_thumbnail_mode"'),
        text.find('"left_thumbnail_mode"'),
        text.find('"sort_mode"'),
        text.find('"items"'),
    ]
    assert all(p >= 0 for p in positions), positions
    assert positions == sorted(positions)


def test_lpl_special_chars_in_description(tmp_path: Path) -> None:
    """Descriptions with `&`, `:`, `'`, `"` survive correctly into the label."""
    dest = tmp_path / "mame"
    dest.mkdir()
    nasty = 'Dungeons & Dragons: Tower of Doom (Euro 940412) — "director\'s cut"'
    out = dest / "mame.lpl"
    write_lpl(out, [_entry("ddtod", nasty, dest)])

    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert parsed["items"][0]["label"] == nasty


def test_lpl_unicode_passes_through(tmp_path: Path) -> None:
    """Multi-byte UTF-8 (Japanese description) preserved with ensure_ascii=False."""
    dest = tmp_path / "mame"
    dest.mkdir()
    jp = "ストリートファイターII" + "'"  # Street Fighter II'
    out = dest / "mame.lpl"
    write_lpl(out, [_entry("sf2", jp, dest)])

    raw = out.read_text(encoding="utf-8")
    # Should appear verbatim in the file (not as `ス...` escapes).
    assert jp in raw
    parsed = json.loads(raw)
    assert parsed["items"][0]["label"] == jp


def test_lpl_no_bom(tmp_path: Path) -> None:
    """File has no UTF-8 BOM."""
    dest = tmp_path / "mame"
    dest.mkdir()
    out = dest / "mame.lpl"
    write_lpl(out, [_entry("kof94", "KoF '94", dest)])
    assert not out.read_bytes().startswith(b"\xef\xbb\xbf")


def test_lpl_atomic_write(tmp_path: Path) -> None:
    """write_lpl uses .tmp + replace; no .tmp left after success."""
    dest = tmp_path / "mame"
    dest.mkdir()
    out = dest / "mame.lpl"
    write_lpl(out, [_entry("kof94", "KoF '94", dest)])
    assert not (out.with_suffix(".lpl.tmp")).exists()
    assert out.exists()


def test_read_lpl_roundtrip(tmp_path: Path) -> None:
    """write_lpl then read_lpl returns the same items."""
    dest = tmp_path / "mame"
    dest.mkdir()
    out = dest / "mame.lpl"
    entries = [
        _entry("kof94", "The King of Fighters '94", dest),
        _entry("sf2ce", "Street Fighter II' - Champion Edition", dest),
    ]
    write_lpl(out, entries)
    items = read_lpl(out)
    assert len(items) == 2
    assert items[0]["path"].endswith("/kof94.zip")
    assert items[1]["label"] == "Street Fighter II' - Champion Edition"

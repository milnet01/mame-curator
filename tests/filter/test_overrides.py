"""Tests for the Overrides schema and loader."""

from pathlib import Path

import pytest

from mame_curator.filter.errors import OverridesError
from mame_curator.filter.overrides import Overrides, load_overrides


def test_empty_overrides_is_valid() -> None:
    o = Overrides()
    assert o.entries == {}


def test_overrides_round_trips_via_yaml(tmp_path: Path) -> None:
    f = tmp_path / "overrides.yaml"
    f.write_text("overrides:\n  sf2: sf2ce\n  pacman: pacmanf\n")
    o = load_overrides(f)
    assert o.entries == {"sf2": "sf2ce", "pacman": "pacmanf"}


def test_missing_file_returns_empty_overrides(tmp_path: Path) -> None:
    o = load_overrides(tmp_path / "nope.yaml")
    assert o.entries == {}


def test_malformed_yaml_raises(tmp_path: Path) -> None:
    f = tmp_path / "bad.yaml"
    f.write_text("overrides: [this, is, not, a, mapping]")
    with pytest.raises(OverridesError):
        load_overrides(f)


def test_unknown_top_level_key_raises(tmp_path: Path) -> None:
    f = tmp_path / "wrong.yaml"
    f.write_text("garbage: true\n")
    with pytest.raises(OverridesError):
        load_overrides(f)


def test_yaml_syntax_error_raises(tmp_path: Path) -> None:
    f = tmp_path / "broken.yaml"
    f.write_text("overrides:\n  unbalanced: [\n")
    with pytest.raises(OverridesError, match="failed to parse"):
        load_overrides(f)


def test_top_level_not_a_mapping_raises(tmp_path: Path) -> None:
    f = tmp_path / "list.yaml"
    f.write_text("- entry1\n- entry2\n")
    with pytest.raises(OverridesError, match="not a YAML mapping"):
        load_overrides(f)


# DS01 — Cluster C tests below


def test_overrides_oversized_yaml_rejected(tmp_path: Path) -> None:
    """C3 — file size cap of 1 MB before `yaml.safe_load`. Defends against
    YAML alias-bomb DoS when P07's `setup/` ships preset downloads."""
    f = tmp_path / "huge.yaml"
    # 2 MB of valid YAML.
    payload = "overrides:\n  parent: '" + ("X" * 2_000_000) + "'\n"
    f.write_text(payload)
    with pytest.raises(OverridesError):
        load_overrides(f)


def test_overrides_oserror_wrapped(tmp_path: Path) -> None:
    """C5 — `OSError` from `read_text` (e.g. path is a directory, EIO,
    deleted-after-exists) must be wrapped in `OverridesError` per the
    loader's typed-error contract. Currently raw `OSError` escapes."""
    d = tmp_path / "is_a_dir.yaml"
    d.mkdir()
    with pytest.raises(OverridesError):
        load_overrides(d)

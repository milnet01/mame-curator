"""mame-curator-1225 CR-01-11 — the 1 MiB cap holds on the read itself.

The size came from fstat, then the file was read whole, so a file that
grew after the check, or one whose size reads as 0 (a pipe, /dev/zero),
went past the cap.
"""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from mame_curator.filter import _io


class _Refused(Exception):
    pass


def test_a_file_larger_than_its_stat_size_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "overrides.yaml"
    path.write_bytes(b"a: 1\n" * (_io._MAX_YAML_BYTES // 5 + 10))
    monkeypatch.setattr(os, "fstat", lambda fd: SimpleNamespace(st_size=10))
    with pytest.raises(_Refused):
        _io.read_capped_text(path, exc_cls=_Refused)


def test_a_file_at_the_cap_is_read(tmp_path: Path) -> None:
    path = tmp_path / "overrides.yaml"
    path.write_bytes(b"a" * _io._MAX_YAML_BYTES)
    assert len(_io.read_capped_text(path, exc_cls=_Refused)) == _io._MAX_YAML_BYTES
    assert os.path.getsize(path) == _io._MAX_YAML_BYTES

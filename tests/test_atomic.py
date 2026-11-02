"""Tests for `mame_curator._atomic.atomic_write_text` (FP05 C2 + C3)."""

from __future__ import annotations

import errno
import os
import stat
import sys
from pathlib import Path

import pytest


def test_atomic_write_text_cleans_tmp_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C2 — when `os.replace` raises mid-write, the helper must clean the
    `.tmp` sibling so a subsequent run doesn't see a stale half-written
    file. The `try/finally` cleanup is the load-bearing line."""
    from mame_curator._atomic import atomic_write_text

    target = tmp_path / "report.json"

    def _fail(*_args: object, **_kwargs: object) -> None:
        raise OSError(errno.EIO, "synthetic disk error")

    monkeypatch.setattr(os, "replace", _fail)

    with pytest.raises(OSError):
        atomic_write_text(target, "should-never-land")

    # No `.tmp` leftover anywhere in the parent directory.
    leftovers = [p for p in tmp_path.iterdir() if p.suffix == ".tmp" or ".tmp" in p.name]
    assert leftovers == [], f"unexpected .tmp leftovers: {leftovers}"
    # The target itself must not have been created either.
    assert not target.exists()


def test_atomic_write_text_exdev_raises_typed_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C3 — `os.replace` raising EXDEV (cross-filesystem rename, e.g.
    target resolves through a symlink across mount points) must be
    re-raised with EXDEV identifiable. The current implementation lets
    raw OSError(EXDEV) escape; the helper should distinguish EXDEV from
    a generic OSError so callers can present a meaningful error."""
    from mame_curator._atomic import atomic_write_text

    target = tmp_path / "report.json"

    def _exdev(*_args: object, **_kwargs: object) -> None:
        raise OSError(errno.EXDEV, "Invalid cross-device link")

    monkeypatch.setattr(os, "replace", _exdev)

    with pytest.raises(OSError) as excinfo:
        atomic_write_text(target, "doesnt-matter")
    assert excinfo.value.errno == errno.EXDEV


def test_atomic_write_text_round_trip(tmp_path: Path) -> None:
    """Sanity check: golden path writes the text and leaves no tmp."""
    from mame_curator._atomic import atomic_write_text

    target = tmp_path / "config.json"
    atomic_write_text(target, '{"hello": "world"}\n')
    assert target.read_text() == '{"hello": "world"}\n'
    leftovers = [p for p in tmp_path.iterdir() if ".tmp" in p.name]
    assert leftovers == []


# --- a symlink at the destination (mame-curator-1145 review, Group 4) -------


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks need privilege on Windows")
@pytest.mark.parametrize("kind", ["bytes", "text"])
def test_atomic_write_through_a_symlink_keeps_the_link(tmp_path: Path, kind: str) -> None:
    from mame_curator._atomic import atomic_write_bytes, atomic_write_text

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    real = elsewhere / "config.yaml"
    real.write_text("old", encoding="utf-8")
    real.chmod(0o600)
    link_dir = tmp_path / "linkdir"
    link_dir.mkdir()
    link = link_dir / "config.yaml"
    link.symlink_to(real)

    if kind == "bytes":
        atomic_write_bytes(link, b"new")
    else:
        atomic_write_text(link, "new")

    assert link.is_symlink()
    assert real.read_text(encoding="utf-8") == "new"
    # The project's one mode: see test_fp25_atomic_perms.py's re-write pin.
    assert stat.S_IMODE(real.stat().st_mode) == 0o644
    assert sorted(p.name for p in elsewhere.iterdir()) == ["config.yaml"]
    assert sorted(p.name for p in link_dir.iterdir()) == ["config.yaml"]


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks need privilege on Windows")
def test_atomic_write_through_a_dangling_symlink_creates_the_target(tmp_path: Path) -> None:
    from mame_curator._atomic import atomic_write_bytes

    real = tmp_path / "not-yet" / "config.yaml"
    link = tmp_path / "config.yaml"
    link.symlink_to(real)

    atomic_write_bytes(link, b"new")

    assert link.is_symlink()
    assert real.read_bytes() == b"new"


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks need privilege on Windows")
def test_replace_keeping_links_keeps_the_link_across_filesystems(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A restore stages under data/; the config's real file may be on another disk."""
    from mame_curator.api.persist import restore_snapshot

    real_replace = os.replace
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    real = elsewhere / "config.yaml"
    real.write_text("old", encoding="utf-8")
    link = tmp_path / "config.yaml"
    link.symlink_to(real)
    snap = tmp_path / "snapshots" / "s1"
    snap.mkdir(parents=True)
    (snap / "config.yaml").write_text("new", encoding="utf-8")

    def cross_device(src: object, dst: object) -> None:
        if ".tmp" not in str(src):  # The helper's own temp file is beside its target.
            raise OSError(errno.EXDEV, "cross-device link")
        real_replace(src, dst)  # type: ignore[arg-type]  # paths, as os.replace was called.

    monkeypatch.setattr(os, "replace", cross_device)

    restore_snapshot(tmp_path / "snapshots", "s1", {"config.yaml": link})

    assert link.is_symlink()
    assert real.read_text(encoding="utf-8") == "new"

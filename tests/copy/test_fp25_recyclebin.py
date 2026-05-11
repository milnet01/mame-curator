"""FP25-C + FP25-F: recyclebin manifest atomicity envelope + tests.

Pre-FP25-C, ``copy/recyclebin.py:recycle_file`` moved the file with
``shutil.move`` and then wrote the manifest via ``atomic_write_text``.
If the manifest write raised ``OSError`` (disk full, permission denied,
EROFS), the move had already succeeded — the file sat in the recycle
directory with no ``manifest.json``, and the raw ``OSError`` bypassed
the ``RecycleError`` envelope established earlier in the function.

FP25-C wraps the manifest write in a try/except that:

- raises ``RecycleError`` (preserves the typed-error envelope);
- attempts to roll the move back so the file ends up at its original
  location (the all-or-nothing invariant). If the rollback itself
  fails, the error is logged so forensics can find the orphan, but
  the original ``RecycleError`` still propagates.

FP25-F additionally locks the crash-safety contract by monkeypatching
``os.replace`` to fail mid-``atomic_write_text`` and asserting no
``manifest.json`` and no ``manifest.json.*.tmp`` survive.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from mame_curator.copy import recycle_file
from mame_curator.copy.errors import CopyError, RecycleError


def test_fp25_c_recycle_error_raised_when_manifest_write_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``OSError`` from the manifest write wraps as ``RecycleError``.

    The pre-FP25-C path let the raw ``OSError`` propagate, bypassing the
    ``RecycleError`` envelope used for the move-failure case at the top
    of the function. Now both failure modes share the same typed error.
    """
    src = tmp_path / "sf2.zip"
    src.write_bytes(b"some content")
    recycle_root = tmp_path / "recycle"

    def failing_atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
        raise OSError("simulated ENOSPC during manifest write")

    monkeypatch.setattr("mame_curator.copy.recyclebin.atomic_write_text", failing_atomic_write_text)

    with pytest.raises(RecycleError) as exc_info:
        recycle_file(
            src,
            reason="REPLACE_AND_RECYCLE",
            session_id="01HZZ",
            recycle_root=recycle_root,
        )
    assert isinstance(exc_info.value, CopyError)


def test_fp25_c_recycle_rollback_returns_file_to_original_on_manifest_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """On manifest failure, the recycled file is moved back to its original location.

    All-or-nothing: callers that catch ``RecycleError`` should see the
    filesystem in the same state it was in before the call.
    """
    src = tmp_path / "sf2.zip"
    original_content = b"some content"
    src.write_bytes(original_content)
    recycle_root = tmp_path / "recycle"

    def failing_atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
        raise OSError("simulated ENOSPC during manifest write")

    monkeypatch.setattr("mame_curator.copy.recyclebin.atomic_write_text", failing_atomic_write_text)

    with pytest.raises(RecycleError):
        recycle_file(
            src,
            reason="REPLACE_AND_RECYCLE",
            session_id="01HZZ",
            recycle_root=recycle_root,
        )

    # Rollback puts the file back at its original location.
    assert src.exists(), "rollback must restore the source file"
    assert src.read_bytes() == original_content
    # No half-recycled file lingering in the target dir.
    target = recycle_root / "01HZZ" / "sf2.zip"
    assert not target.exists(), "rolled-back file must not remain in recycle dir"


def _install_failing_manifest_replace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replace ``os.replace`` with a version that fails ONLY when the
    destination ends in ``manifest.json``; non-manifest renames pass
    through to the real ``os.replace``.

    ``_atomic.atomic_write_text`` calls ``os.replace(tmp, dst)``; on POSIX
    ``shutil.move`` uses ``os.rename`` rather than ``os.replace`` for the
    same-filesystem case, so this monkeypatch only intercepts the
    manifest-write rename step inside the atomic helper.
    """
    real_replace = os.replace

    def failing_replace(src_path: str, dst_path: str) -> None:
        if str(dst_path).endswith("manifest.json"):
            raise OSError("simulated EROFS during manifest replace")
        real_replace(src_path, dst_path)

    monkeypatch.setattr(os, "replace", failing_replace)


def test_fp25_f_no_manifest_json_on_atomic_replace_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Monkeypatch ``os.replace`` inside ``atomic_write_text`` to fail;
    assert no ``manifest.json`` is left behind.

    Locks the crash-safety contract: a power loss / kernel ENOSPC at the
    tmp→target rename step never produces a half-written manifest the
    next reader would misinterpret.
    """
    src = tmp_path / "sf2.zip"
    src.write_bytes(b"x")
    recycle_root = tmp_path / "recycle"

    _install_failing_manifest_replace(monkeypatch)

    with pytest.raises(RecycleError):
        recycle_file(
            src,
            reason="REPLACE_AND_RECYCLE",
            session_id="01HZZ",
            recycle_root=recycle_root,
        )

    target_dir = recycle_root / "01HZZ"
    if target_dir.exists():
        assert not (target_dir / "manifest.json").exists(), (
            "no half-written manifest.json may remain after atomic_write_text failure"
        )


def test_fp25_f_no_tmp_files_remain_on_atomic_replace_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same monkeypatch as above; assert no ``manifest.json.*.tmp`` lingers.

    ``_atomic.atomic_write_text``'s ``if not completed: tmp_path.unlink``
    cleanup must run even when the failure happens at the ``os.replace``
    step. Without this, ``.tmp`` siblings accumulate over time and the
    recycle dir becomes confused for diff/forensics tools.
    """
    src = tmp_path / "sf2.zip"
    src.write_bytes(b"x")
    recycle_root = tmp_path / "recycle"

    _install_failing_manifest_replace(monkeypatch)

    with pytest.raises(RecycleError):
        recycle_file(
            src,
            reason="REPLACE_AND_RECYCLE",
            session_id="01HZZ",
            recycle_root=recycle_root,
        )

    target_dir = recycle_root / "01HZZ"
    if target_dir.exists():
        leftover_tmps = list(target_dir.glob("manifest.json.*.tmp"))
        assert not leftover_tmps, (
            f"no manifest tmp files may remain after atomic_write_text failure, "
            f"found: {leftover_tmps}"
        )

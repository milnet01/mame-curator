"""FP25-F: recyclebin atomic-write crash-safety contract.

``copy/recyclebin.py:recycle_file`` writes a per-file
``<basename>.manifest.json`` via ``_atomic.atomic_write_text``
**before** the source is moved (FP21-D ordering — see
``src/mame_curator/copy/spec.md:260``). The atomic helper's
``tmp+rename+fsync`` envelope means a crash mid-write leaves either
the prior manifest or no manifest at all — never a half-written
record. These tests monkeypatch ``os.replace`` to fail mid-write and
assert no ``*.manifest.json`` and no ``*.manifest.json.*.tmp``
siblings linger in the recycle tree.

(The pre-FP21-D move-then-write-then-rollback envelope tracked by
FP25-C was retired when manifest-first ordering landed. DS04 T1.1
removed the matching rollback tests; the contract they locked is
no longer live behaviour.)
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from mame_curator.copy import recycle_file
from mame_curator.copy.errors import RecycleError


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

    # Glob over the entire recycle root: post-FP21-D the manifest writes
    # before the move, so on failure the target_dir may not even exist.
    # The crash-safety contract is "no half-written manifest.json
    # ANYWHERE in the recycle tree".
    # FP21-D: glob matches both the legacy `manifest.json` shape and
    # the per-file `<basename>.manifest.json` shape.
    leftover_manifests = list(recycle_root.rglob("*manifest.json"))
    assert leftover_manifests == [], (
        f"no half-written manifest may remain after atomic_write_text "
        f"failure, found: {leftover_manifests}"
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

    # Glob over the entire recycle tree (target_dir may not exist
    # post-FP21-D when manifest writes first). The contract being
    # locked here is `_atomic.atomic_write_text`'s `if not completed:
    # tmp_path.unlink(missing_ok=True)` cleanup path — proving no
    # `.tmp` siblings linger anywhere.
    # FP21-D: glob matches both legacy and per-file manifest tmp shapes.
    leftover_tmps = list(recycle_root.rglob("*manifest.json.*.tmp"))
    assert leftover_tmps == [], (
        f"no manifest tmp files may remain after atomic_write_text failure, found: {leftover_tmps}"
    )

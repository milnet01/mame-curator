"""Project-wide atomic-write helper (FP05 C2).

The `.tmp` + `os.replace` idiom existed inline in two sites pre-FP05
(`copy/executor.py:60-79` for binary copies; `cli/__init__.py:189-203`
for the filter report — added by DS01 R2). Two correct copies of a
6-line idiom that both have to handle cleanup-on-failure is the threshold
where Rule of Three flips. This helper is the third site's solution.

`tempfile.NamedTemporaryFile` provides a unique tmp-name so concurrent
callers and stale `.tmp` from prior crashes don't collide. On Windows,
holding a file handle prevents `os.replace` over the same path; the
helper closes the handle before the replace, not relying on context-
manager exit.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Atomically write `data` to `path`. Same protocol as `atomic_write_text`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_handle = tempfile.NamedTemporaryFile(  # noqa: SIM115
        mode="wb",
        dir=path.parent,
        prefix=path.name + ".",
        suffix=".tmp",
        delete=False,
    )
    tmp_path = Path(tmp_handle.name)
    completed = False
    try:
        try:
            tmp_handle.write(data)
            tmp_handle.flush()
            with contextlib.suppress(OSError):
                os.fsync(tmp_handle.fileno())
        finally:
            tmp_handle.close()
        os.replace(tmp_path, path)
        # FP09 B9: spec § Atomic-write protocol step 4 — parent-dir fsync
        # so the rename is durable on power loss. Best-effort: tmpfs and
        # some networked filesystems reject parent-dir fsync.
        _fsync_parent_dir(path)
        completed = True
    finally:
        if not completed:
            with contextlib.suppress(OSError):
                tmp_path.unlink(missing_ok=True)


def _fsync_parent_dir(path: Path) -> None:
    """Best-effort fsync of `path`'s parent directory."""
    try:
        fd = os.open(path.parent, os.O_RDONLY)
    except OSError:
        return
    try:
        with contextlib.suppress(OSError):
            os.fsync(fd)
    finally:
        with contextlib.suppress(OSError):
            os.close(fd)


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    """Atomically write `text` to `path`.

    Writes to a unique `.tmp` sibling, fsyncs the file (best-effort), then
    `os.replace`s onto the target. Cleans the tmp on any exception. EXDEV
    (cross-filesystem rename) propagates as a distinguishable `OSError`
    with `errno.EXDEV` for callers that want to surface the failure mode
    cleanly.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # `delete=False` because we want to control deletion ourselves; the
    # context-manager exit on Windows would close the file but leave it,
    # whereas we need to close-before-replace. Using a bare assignment
    # rather than `with` is deliberate — the close+unlink ordering
    # below cannot be expressed via `__exit__` on Windows.
    tmp_handle = tempfile.NamedTemporaryFile(  # noqa: SIM115
        mode="w",
        encoding=encoding,
        dir=path.parent,
        prefix=path.name + ".",
        suffix=".tmp",
        delete=False,
    )
    tmp_path = Path(tmp_handle.name)
    completed = False
    try:
        try:
            tmp_handle.write(text)
            tmp_handle.flush()
            with contextlib.suppress(OSError):
                # fsync is best-effort: some filesystems / containers reject
                # it (e.g. tmpfs without O_DIRECT). Power-cut robustness is
                # a defense-in-depth concern, not a hard contract.
                os.fsync(tmp_handle.fileno())
        finally:
            tmp_handle.close()
        # Windows: must close before replace. Linux/macOS would tolerate
        # the open handle; the close-first ordering works on all platforms.
        # OSError (including EXDEV for cross-filesystem renames, perm-denied,
        # disk-full) propagates with errno preserved; the `finally` cleans
        # the tmp.
        os.replace(tmp_path, path)
        # FP09 B9: spec § Atomic-write protocol step 4 — parent-dir fsync
        # so the rename is durable on power loss. Mirrors the new
        # atomic_write_bytes pattern for symmetry.
        _fsync_parent_dir(path)
        completed = True
    finally:
        if not completed:
            with contextlib.suppress(OSError):
                tmp_path.unlink(missing_ok=True)

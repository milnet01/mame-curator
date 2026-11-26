"""Atomic file writes: the target is always the old file or the new one, never a torn mix.

Every write goes to a unique `.tmp` sibling, is fsynced, given its mode, then
renamed over the target. `copy.executor.copy_one` is the one deliberate
exception: it streams large zips with its own fixed `.tmp` name.
"""

from __future__ import annotations

import contextlib
import errno
import os
import sys
import tempfile
from pathlib import Path


def atomic_write_bytes(path: Path, data: bytes, *, mode: int = 0o644) -> None:
    """Atomically write `data` to `path` with POSIX file mode `mode`.

    OSError propagates with its errno (EXDEV for a cross-disk rename, among
    others); the tmp is removed on any exception. `mode` is set on the tmp
    before the rename, so a 0o600 secret is never briefly world-readable.
    A symlink at `path` survives: the write lands on the file it points to.
    """
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Not `with`: Windows cannot rename over a file that is still open, and
    # `__exit__` would close it only after the rename.
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
            # Best-effort: tmpfs and some containers reject fsync.
            with contextlib.suppress(OSError):
                os.fsync(tmp_handle.fileno())
            # The tmp starts at 0o600. Windows has no mode bits, and its
            # typeshed has no `os.fchmod`, hence the platform gate.
            if sys.platform != "win32":
                with contextlib.suppress(OSError):
                    os.fchmod(tmp_handle.fileno(), mode)
        finally:
            tmp_handle.close()
        os.replace(tmp_path, path)
        fsync_parent_dir(path)  # makes the rename survive a power cut
        completed = True
    finally:
        if not completed:
            with contextlib.suppress(OSError):
                tmp_path.unlink(missing_ok=True)


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8", mode: int = 0o644) -> None:
    """Atomically write `text` to `path`, as `atomic_write_bytes` does.

    Line endings are written as given, on every platform.
    """
    atomic_write_bytes(path, text.encode(encoding), mode=mode)


def replace_keeping_links(src: Path, dst: Path) -> None:
    """Move `src` onto `dst`; a symlink at `dst` survives, as in the writers above.

    The real file may be on another disk than `src`, which a rename cannot reach.
    """
    target = dst.resolve()
    try:
        os.replace(src, target)
    except OSError as exc:
        if exc.errno != errno.EXDEV:
            raise
        atomic_write_bytes(target, src.read_bytes())


def fsync_parent_dir(path: Path) -> None:
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

"""One running copy per data folder (`cli/spec.md` § One copy per data folder)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import BinaryIO

logger = logging.getLogger(__name__)

LOCK_NAME = "instance.lock"
URL_NAME = "instance.url"
_MAX_URL_BYTES = 512


class _HeldElsewhere(Exception):
    """Another process holds the lock."""


def _lock(handle: BinaryIO) -> None:
    """Take an exclusive, non-blocking lock on `handle`.

    Raises:
        _HeldElsewhere: another process holds it.
        OSError: the filesystem cannot take the lock at all.
    """
    if sys.platform == "win32":
        import msvcrt

        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            # msvcrt reports a held region and an unsupported one alike.
            raise _HeldElsewhere from exc
    else:
        import fcntl

        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise _HeldElsewhere from exc


class InstanceLock:
    """The claim on one data folder, held from `claim` until `release`."""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._handle: BinaryIO | None = None

    def claim(self, url: str) -> bool:
        """Lock the folder and record `url`; False when another copy holds it.

        A lock the filesystem cannot take is not a held one: that logs a
        WARNING and returns True, so the server still runs, unlocked.
        """
        try:
            self._data_dir.mkdir(parents=True, exist_ok=True)
            handle = (self._data_dir / LOCK_NAME).open("a+b")
        except OSError as exc:
            logger.warning("running without the one-copy lock: %r", str(exc))
            return True
        try:
            _lock(handle)
        except _HeldElsewhere:
            handle.close()
            return False
        except OSError as exc:
            handle.close()
            logger.warning("running without the one-copy lock: %r", str(exc))
            return True
        self._handle = handle
        try:
            (self._data_dir / URL_NAME).write_text(url, encoding="utf-8")
        except OSError as exc:
            # The lock still guards the folder; a second launch then says
            # only that a copy runs, without its address.
            logger.warning("could not record this copy's address: %r", str(exc))
        return True

    def release(self) -> None:
        """Drop the lock; closing the file is what releases it."""
        if self._handle is not None:
            self._handle.close()
            self._handle = None


def running_url(data_dir: Path) -> str | None:
    """The address the running copy recorded, or None when there is no usable one."""
    try:
        raw = (data_dir / URL_NAME).read_bytes()[:_MAX_URL_BYTES]
        url = raw.decode("utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return None
    if not url.startswith("http://") or not url.isprintable() or " " in url:
        return None
    return url

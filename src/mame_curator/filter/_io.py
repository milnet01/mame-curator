"""Shared text-file reader for the filter/ YAML loaders (FP05 C1 + C5 + B5).

`load_overrides` and `load_sessions` both need to: cap input file size
(defends against alias-bomb DoS), wrap `OSError` into a typed loader
error, and avoid TOCTOU between size-check and read. This helper does
all three with one open file descriptor.
"""

from __future__ import annotations

import os
from pathlib import Path

# Defends against YAML alias-bomb DoS when P07's `setup/` ships preset
# downloads. Self-authored configs are nowhere near this size.
_MAX_YAML_BYTES = 1 * 1024 * 1024  # 1 MiB


def read_capped_text(path: Path, *, exc_cls: type[Exception]) -> str:
    """Read `path` as UTF-8 text, enforcing the 1 MiB cap.

    Wraps every `OSError` (including `IsADirectoryError`, perm-denied,
    EIO, NFS hiccups) into the caller-supplied `exc_cls` so the loader's
    typed-error contract is preserved. Closes the size-vs-content TOCTOU
    by reading both from one file descriptor (FP05 B5).
    """
    try:
        with path.open("rb") as fh:
            try:
                size = os.fstat(fh.fileno()).st_size
            except OSError as exc:
                # FP06 B3: quote `path` via repr() so newlines / terminal
                # control bytes in user-controlled filenames can't break
                # the single-line error contract or spoof legitimate output.
                raise exc_cls(f"failed to stat {path!r}: {exc}") from exc
            if size > _MAX_YAML_BYTES:
                raise exc_cls(
                    f"{path!r} exceeds 1 MiB cap ({_MAX_YAML_BYTES} bytes; "
                    f"actual: {size}); refusing to parse to defend against YAML alias bombs"
                )
            return fh.read().decode("utf-8")
    except OSError as exc:
        raise exc_cls(f"failed to read {path!r}: {exc}") from exc

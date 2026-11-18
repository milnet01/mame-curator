"""Shared reading for the filter/ YAML loaders (FP05 C1 + C5 + B5).

Each loader needs to: cap input file size (defends against alias-bomb DoS),
wrap `OSError` into a typed loader error, and avoid TOCTOU between
size-check and read. `read_capped_text` does all three with one open file
descriptor; `read_yaml_mapping` adds the parse and the top-level shape.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

# Defends against YAML alias-bomb DoS. The largest file the app writes is
# state.yaml, one line per game: about 3.5 MB for 100k games (mame-curator-1236).
_MAX_YAML_BYTES = 8 * 1024 * 1024


def _too_big(path: Path, detail: str) -> str:
    cap_mib = _MAX_YAML_BYTES // (1024 * 1024)
    return (
        f"{path!r} exceeds the {cap_mib} MiB cap ({_MAX_YAML_BYTES} bytes{detail}); "
        "refusing to parse to defend against YAML alias bombs"
    )


def read_capped_text(path: Path, *, exc_cls: type[Exception]) -> str:
    """Read `path` as UTF-8 text, refusing more than `_MAX_YAML_BYTES`.

    Wraps every `OSError` (including `IsADirectoryError`, perm-denied,
    EIO, NFS hiccups) and any undecodable byte into the caller-supplied
    `exc_cls` so the loader's typed-error contract is preserved. Closes the size-vs-content TOCTOU
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
                raise exc_cls(_too_big(path, f"; actual: {size}"))
            # mame-curator-1225: the cap holds on the read too — the file may
            # grow after fstat, or report size 0 (a pipe or a device).
            data = fh.read(_MAX_YAML_BYTES + 1)
            if len(data) > _MAX_YAML_BYTES:
                raise exc_cls(_too_big(path, ""))
            return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise exc_cls(f"{path!r} is not valid UTF-8: {exc}") from exc
    except OSError as exc:
        raise exc_cls(f"failed to read {path!r}: {exc}") from exc


def read_yaml_mapping(path: Path, *, exc_cls: type[Exception]) -> dict[str, Any] | None:
    """Read `path` as a YAML mapping; `None` for a missing, empty or `null` file.

    Any other top-level value, and any read or parse failure, raises `exc_cls`.
    """
    if not path.exists():
        return None
    text = read_capped_text(path, exc_cls=exc_cls)
    try:
        raw: Any = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        # FP06 B3: quote user-controlled paths via repr().
        raise exc_cls(f"failed to parse {path!r}: {exc}") from exc
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise exc_cls(f"{path!r} is not a YAML mapping")
    return raw

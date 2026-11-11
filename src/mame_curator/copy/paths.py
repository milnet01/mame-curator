"""Where a short name may lead: one zip directly inside one folder.

Short names come from a DAT, a listxml, a saved filter report or an API
request, and each becomes a path, so `../x` would reach outside the folder.
The check is on the name, not on a resolved path: a zip in the folder may be a
symlink to another disk, and that stays allowed.
"""

from __future__ import annotations

from pathlib import Path

from mame_curator.copy.errors import UnsafeShortNameError

_NOT_IN_A_FILE_NAME = frozenset('/\\:\0*?"<>|')
# mame-curator-1225: Windows opens these as devices, whatever the extension, so
# `con.zip` would block a copy worker. No MAME 0.287 machine has one.
_WINDOWS_DEVICES = frozenset(
    {"con", "prn", "aux", "nul"} | {f"com{n}" for n in range(10)} | {f"lpt{n}" for n in range(10)}
)


def is_safe_short_name(short: str) -> bool:
    """True when `short` is one plain file name on every platform we run on."""
    return (
        short not in ("", ".", "..")
        and _NOT_IN_A_FILE_NAME.isdisjoint(short)
        and short.lower() not in _WINDOWS_DEVICES
    )


def zip_path(folder: Path, short: str) -> Path:
    """`folder / <short>.zip`; raises `UnsafeShortNameError` if it could leave `folder`."""
    if not is_safe_short_name(short):
        raise UnsafeShortNameError(f"not a plain game name, so not used: {short!r}")
    return folder / f"{short}.zip"

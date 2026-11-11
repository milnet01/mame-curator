"""Filesystem sandbox: allowlist composition, path validation, drive-root enumeration.

Per ``docs/specs/P04-http-api.md`` § Filesystem sandbox.
"""

from __future__ import annotations

import contextlib
import hashlib
import logging
import os
import re
import string
from pathlib import Path

from mame_curator.api.errors import (
    FsNotFoundError,
    FsPathInvalidError,
    FsSandboxError,
)
from mame_curator.api.schemas import AppConfig, FsAllowedRoot

logger = logging.getLogger(__name__)


def _hash_root_id(p: Path) -> str:
    """Stable 12-char id for a resolved absolute path."""
    return hashlib.sha256(str(p).encode("utf-8")).hexdigest()[:12]


def compose_allowlist(config: AppConfig, *, log_stale: bool = True) -> tuple[FsAllowedRoot, ...]:
    """Build the allowlist: home + 4 config-derived paths + granted roots.

    Each entry is resolved to a canonical absolute path. Granted roots that
    overlap a config-derived root take the ``"config"`` source label. A dropped
    granted root logs at INFO when ``log_stale``, else at DEBUG: ``replace_world``
    runs this on every save, and an unchanged list needs no new INFO line.
    """
    config_roots: dict[Path, FsAllowedRoot] = {}

    def _add_config(p: Path) -> None:
        try:
            resolved = p.resolve(strict=False)
        except (OSError, ValueError):  # ValueError: a NUL byte in the path.
            return
        if resolved in config_roots:
            return
        config_roots[resolved] = FsAllowedRoot(
            id=_hash_root_id(resolved), path=str(resolved), source="config"
        )

    _add_config(Path.home())
    _add_config(config.paths.source_roms)
    _add_config(config.paths.source_dat.parent)
    _add_config(config.paths.dest_roms)
    _add_config(config.paths.retroarch_playlist.parent)

    granted: dict[Path, FsAllowedRoot] = {}
    for raw in config.fs.granted_roots:
        try:
            resolved = Path(raw).resolve(strict=False)
        except (OSError, ValueError):  # ValueError: a NUL byte in the path.
            continue
        # FP20-D: drop granted entries whose target is no longer an existing
        # directory. ``resolve(strict=False)`` is happy with ghosts, but
        # admitting a ghost means anything later created (file, symlink,
        # re-made dir) is silently inside the sandbox without an explicit
        # re-grant. The INFO log gives the Settings UI a signal to surface
        # "your granted root ``<path>`` is gone" to the user.
        if not resolved.exists() or not resolved.is_dir():
            logger.log(
                logging.INFO if log_stale else logging.DEBUG,
                "compose_allowlist: dropping stale granted root %s "
                "(no longer an existing directory)",
                resolved,
            )
            continue
        if resolved in config_roots or resolved in granted:
            continue
        granted[resolved] = FsAllowedRoot(
            id=_hash_root_id(resolved), path=str(resolved), source="granted"
        )

    return tuple(config_roots.values()) + tuple(granted.values())


def missing_granted_roots(config: AppConfig) -> tuple[FsAllowedRoot, ...]:
    """The granted roots ``compose_allowlist`` drops: no longer an existing directory.

    mame-curator-1175: listed so the user can see them and revoke them; they
    are never in the sandbox.
    """
    missing: dict[Path, FsAllowedRoot] = {}
    for raw in config.fs.granted_roots:
        try:
            resolved = Path(raw).resolve(strict=False)
        except (OSError, ValueError):  # ValueError: a NUL byte in the path.
            continue
        if not resolved.is_dir() and resolved not in missing:
            missing[resolved] = FsAllowedRoot(
                id=_hash_root_id(resolved), path=str(resolved), source="granted"
            )
    return tuple(missing.values())


def resolve_path(raw: str) -> Path:
    """Resolve a user-supplied path; reject empty / NUL-byte inputs."""
    if not raw:
        raise FsPathInvalidError(f"path is empty: {raw!r}")
    if "\0" in raw:
        raise FsPathInvalidError(f"path contains NUL byte: {raw!r}")
    return Path(raw).resolve(strict=False)


def validate_within_allowlist(requested: Path, allowlist: tuple[FsAllowedRoot, ...]) -> None:
    """Raise ``FsSandboxError`` if ``requested`` is outside every allowlist root."""
    for root in allowlist:
        try:
            if requested.is_relative_to(Path(root.path)):
                return
        except ValueError:  # different drive on Windows
            continue
    raise FsSandboxError(f"path outside allowlist: {str(requested)!r}")


def validate_fs_path(
    raw: str, allowlist: tuple[FsAllowedRoot, ...], *, require_dir: bool = False
) -> Path:
    """Combined resolve + sandbox + existence + is-dir check."""
    requested = resolve_path(raw)
    validate_within_allowlist(requested, allowlist)
    if not requested.exists():
        raise FsNotFoundError(f"path does not exist: {str(requested)!r}")
    if require_dir and not requested.is_dir():
        raise FsPathInvalidError(f"path is not a directory: {str(requested)!r}")
    return requested


_PROC_MOUNTS = Path("/proc/mounts")
_VOLUMES = Path("/Volumes")

# Filesystems that hold no user files.
_PSEUDO_FS = frozenset(
    {
        "autofs", "binfmt_misc", "bpf", "cgroup", "cgroup2", "configfs", "debugfs",
        "devpts", "devtmpfs", "efivarfs", "fuse.gvfsd-fuse", "fuse.portal", "fusectl",
        "hugetlbfs", "mqueue", "nsfs", "overlay", "proc", "pstore", "ramfs",
        "rpc_pipefs", "securityfs", "selinuxfs", "squashfs", "sysfs", "tmpfs", "tracefs",
    }
)  # fmt: skip
# The system's own mounts. Granting one would let the app see system files.
_SYSTEM_PREFIXES = (
    "/.snapshots", "/bin", "/boot", "/dev", "/etc", "/lib", "/lib64", "/opt",
    "/proc", "/root", "/run", "/sbin", "/snap", "/srv", "/sys", "/usr", "/var",
)  # fmt: skip
# Each of these covers far more than one drive.
_TOO_WIDE = frozenset({"/", "/home"})


def _unescape_mount(field: str) -> str:
    r"""``/proc/mounts`` writes a space as ``\040``, a tab as ``\011``, and so on."""
    return re.sub(r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), field)


def _is_system_mount(point: str) -> bool:
    if point.startswith("/run/media/"):  # Where udisks mounts a USB drive.
        return False
    return point in _TOO_WIDE or any(
        point == p or point.startswith(p + "/") for p in _SYSTEM_PREFIXES
    )


def mount_roots(mounts_text: str) -> tuple[str, ...]:
    """The user's drives in a ``/proc/mounts`` text, first mention first.

    mame-curator-1170: offered instead of ``/``, so a grant covers one drive.
    """
    roots: list[str] = []
    for line in mounts_text.splitlines():
        fields = line.split()
        if len(fields) < 3:
            continue
        source, point, fstype = fields[0], _unescape_mount(fields[1]), fields[2]
        if fstype in _PSEUDO_FS or source.startswith("/dev/loop"):  # A loop is a snap.
            continue
        if _is_system_mount(point) or point in roots:
            continue
        roots.append(point)
    return tuple(roots)


def _posix_drive_roots() -> tuple[str, ...]:
    try:
        candidates = mount_roots(_PROC_MOUNTS.read_text(encoding="utf-8", errors="replace"))
    except OSError:  # No /proc: macOS mounts each drive under /Volumes.
        try:
            candidates = tuple(
                str(p) for p in sorted(_VOLUMES.iterdir()) if p.resolve() != Path("/")
            )
        except OSError:
            return ()
    return tuple(p for p in candidates if Path(p).is_dir())


def os_drive_roots() -> tuple[str, ...]:
    """OS drive/mount roots for the Browse picker (informational only).

    Windows: the drive letters. Elsewhere: the mounted drives, never ``/``.
    """
    if os.name == "nt":
        roots: list[str] = []
        # Python 3.12+ exposes os.listdrives() on Windows.
        listdrives = getattr(os, "listdrives", None)
        if callable(listdrives):
            with contextlib.suppress(OSError):
                roots.extend(listdrives())
        if not roots:
            for letter in string.ascii_uppercase:
                p = Path(f"{letter}:\\")
                if p.exists():
                    roots.append(str(p))
        return tuple(roots)
    return _posix_drive_roots()

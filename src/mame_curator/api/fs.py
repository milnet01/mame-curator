"""Filesystem sandbox: allowlist composition, path validation, drive-root enumeration.

Per ``docs/specs/P04.md`` § Filesystem sandbox.
"""

from __future__ import annotations

import contextlib
import hashlib
import logging
import os
import string
from pathlib import Path

from mame_curator.api.errors import (
    FsNotFoundError,
    FsPathInvalidError,
    FsSandboxError,
)
from mame_curator.api.schemas import AppConfig, FsAllowedRoot

logger = logging.getLogger(__name__)

# FP25-K(6): dedupe the FP20-D "dropping stale granted root" INFO log.
# compose_allowlist fires at world build AND every replace_world (i.e.
# every config PATCH); without this, a stale granted_root drains the
# same INFO line every cycle. Entries are added on first-seen-stale and
# discarded when the path becomes valid again, so a later re-deletion
# re-logs cleanly.
_logged_stale_granted_roots: set[Path] = set()


def _hash_root_id(p: Path) -> str:
    """Stable 12-char id for a resolved absolute path."""
    return hashlib.sha256(str(p).encode("utf-8")).hexdigest()[:12]


def compose_allowlist(config: AppConfig) -> tuple[FsAllowedRoot, ...]:
    """Build the allowlist: home + 4 config-derived paths + granted roots.

    Each entry is resolved to a canonical absolute path. Granted roots that
    overlap a config-derived root take the ``"config"`` source label.
    """
    config_roots: dict[Path, FsAllowedRoot] = {}

    def _add_config(p: Path) -> None:
        try:
            resolved = p.resolve(strict=False)
        except OSError:
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
        except OSError:
            continue
        # FP20-D: drop granted entries whose target is no longer an existing
        # directory. ``resolve(strict=False)`` is happy with ghosts, but
        # admitting a ghost means anything later created (file, symlink,
        # re-made dir) is silently inside the sandbox without an explicit
        # re-grant. The INFO log gives the Settings UI a signal to surface
        # "your granted root ``<path>`` is gone" to the user.
        # FP25-K(6): dedupe the INFO log under polling load. compose_allowlist
        # runs at world build + every replace_world; without this, a config
        # PATCH that leaves a stale granted_root drains the same INFO line
        # to the log every time. Track first-seen-stale paths in a module
        # set and clear the entry once the path becomes valid again, so a
        # later re-deletion logs again.
        if not resolved.exists() or not resolved.is_dir():
            if resolved not in _logged_stale_granted_roots:
                logger.info(
                    "compose_allowlist: dropping stale granted root %s "
                    "(no longer an existing directory)",
                    resolved,
                )
                _logged_stale_granted_roots.add(resolved)
            continue
        # Path is valid again — drop any prior dedup entry so a future
        # deletion re-logs.
        _logged_stale_granted_roots.discard(resolved)
        if resolved in config_roots or resolved in granted:
            continue
        granted[resolved] = FsAllowedRoot(
            id=_hash_root_id(resolved), path=str(resolved), source="granted"
        )

    return tuple(config_roots.values()) + tuple(granted.values())


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


def os_drive_roots() -> tuple[str, ...]:
    """OS drive/mount roots for the Browse picker (informational only)."""
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
    return ("/",)

"""Filesystem sandbox: allowlist composition, path validation, drive-root enumeration.

Per ``docs/specs/P04.md`` § Filesystem sandbox.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import string
from pathlib import Path

from mame_curator.api.errors import (
    FsNotFoundError,
    FsPathInvalidError,
    FsSandboxError,
)
from mame_curator.api.schemas import AppConfig, FsAllowedRoot


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

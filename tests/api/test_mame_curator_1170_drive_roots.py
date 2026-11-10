"""mame-curator-1170 — the folder picker lists real drives, never the whole disk.

On Linux, ``GET /api/fs/roots`` offered only ``/``. Reaching a game drive
meant pressing ``/`` and then "Allow /", which let the app see the whole
disk. By the user's decision of 2026-11-10 it lists mounted drives instead,
so a grant covers one drive. System mounts and pseudo filesystems are left
out, and so are ``/`` and ``/home``: either would cover far more than a drive.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from mame_curator.api import fs

# A trimmed copy of a real openSUSE /proc/mounts, plus a USB stick whose label
# has a space, a second drive under /media, a snap and a loop-mounted image.
_MOUNTS = r"""/dev/nvme0n1p2 / btrfs rw,relatime 0 0
devtmpfs /dev devtmpfs rw,nosuid 0 0
tmpfs /dev/shm tmpfs rw,nosuid,nodev 0 0
sysfs /sys sysfs rw,nosuid 0 0
proc /proc proc rw,nosuid 0 0
tmpfs /run tmpfs rw,nosuid 0 0
/dev/nvme0n1p2 /.snapshots btrfs rw,relatime 0 0
/dev/nvme0n1p2 /home btrfs rw,relatime 0 0
/dev/nvme0n1p2 /opt btrfs rw,relatime 0 0
/dev/nvme0n1p2 /usr/local btrfs rw,relatime 0 0
/dev/nvme0n1p2 /var btrfs rw,relatime 0 0
tmpfs /tmp tmpfs rw,nosuid 0 0
/dev/nvme0n1p1 /boot/efi vfat rw,relatime 0 0
/dev/sda1 /mnt/Emulators ext4 rw,relatime 0 0
/dev/sdb1 /mnt/Games ext4 rw,relatime 0 0
/dev/sdc1 /run/media/me/USB\040STICK exfat rw,nosuid 0 0
/dev/sdd1 /media/backup ntfs3 rw,relatime 0 0
tmpfs /run/user/1000 tmpfs rw,nosuid 0 0
gvfsd-fuse /run/user/1000/gvfs fuse.gvfsd-fuse rw,nosuid 0 0
overlay /var/lib/docker/overlay overlay rw,relatime 0 0
/dev/loop3 /snap/core/123 squashfs ro,nodev 0 0
/dev/loop5 /mnt/disc-image iso9660 ro 0 0
/dev/sdb1 /mnt/Games ext4 rw,relatime 0 0
"""


def test_mount_roots_lists_the_drives_and_nothing_wider() -> None:
    assert fs.mount_roots(_MOUNTS) == (
        "/mnt/Emulators",
        "/mnt/Games",
        "/run/media/me/USB STICK",
        "/media/backup",
    )


def test_mount_roots_skips_a_malformed_line() -> None:
    assert fs.mount_roots("garbage\n/dev/sdb1 /mnt/Games ext4 rw 0 0\n") == ("/mnt/Games",)


@pytest.mark.skipif(os.name == "nt", reason="the Linux and macOS branch")
def test_drive_roots_on_linux_are_existing_mounted_drives(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    there = tmp_path / "games"
    there.mkdir()
    mounts = tmp_path / "mounts"
    mounts.write_text(
        f"/dev/sdb1 {there} ext4 rw 0 0\n/dev/sdc1 {tmp_path / 'gone'} ext4 rw 0 0\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(fs, "_PROC_MOUNTS", mounts)
    assert fs.os_drive_roots() == (str(there),)


@pytest.mark.skipif(os.name == "nt", reason="the Linux and macOS branch")
def test_drive_roots_on_macos_are_the_volumes_but_not_the_system_disk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    volumes = tmp_path / "Volumes"
    (volumes / "Games").mkdir(parents=True)
    (volumes / "Macintosh HD").symlink_to("/")
    monkeypatch.setattr(fs, "_PROC_MOUNTS", tmp_path / "no-proc-mounts")
    monkeypatch.setattr(fs, "_VOLUMES", volumes)
    assert fs.os_drive_roots() == (str(volumes / "Games"),)

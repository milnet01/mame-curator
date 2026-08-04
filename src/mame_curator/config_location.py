"""Where `config.yaml` lives, and the starter config a first run writes.

A downloaded bundle has no `config.yaml` and no terminal to answer the
interactive `mame-curator setup` wizard in, so `serve` resolves its
config through three layers — flag, working directory, per-user
directory — and creates the last one when it is absent.

See `docs/specs/mame-curator-1095-desktop-bundles.md` § 4.1.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

import platformdirs
import yaml

_APP_NAME = "mame-curator"

#: Banner written above any generated config. Shared with
#: `cli/commands/setup.py` so the wizard and the starter config cannot
#: drift into two different headers.
STARTER_HEADER = """\
# MAME Curator configuration.
# Edit by hand or via the in-app Settings page. See config.example.yaml
# in the repo for a fully-commented template covering every section
# (filters, picker, ui, updates, …). Sections omitted here fall back to
# AppConfig defaults.

"""


class ConfigSource(StrEnum):
    """Which layer of `resolve_config_path` supplied the path."""

    EXPLICIT = "explicit"
    CWD = "cwd"
    USER = "user"


def user_config_path() -> Path:
    r"""The per-user `config.yaml`.

    `appauthor=False` is load-bearing: `platformdirs` otherwise defaults
    the author to the app name and inserts it *before* the app name, so
    Windows would nest `mame-curator\\mame-curator`.
    """
    return Path(platformdirs.user_config_dir(_APP_NAME, appauthor=False)) / "config.yaml"


def user_data_path() -> Path:
    """The per-user data directory the starter config points into."""
    return Path(platformdirs.user_data_dir(_APP_NAME, appauthor=False))


def user_log_path() -> Path:
    """Where a frozen bundle tees its stderr, so a GUI failure leaves a trace."""
    return Path(platformdirs.user_log_dir(_APP_NAME, appauthor=False)) / "mame-curator.log"


def resolve_config_path(explicit: Path | None) -> tuple[Path, ConfigSource]:
    """Resolve the config path: ``--config`` → ``./config.yaml`` → per-user.

    Returns the path **and which layer produced it**. The source is not
    decoration: only `ConfigSource.USER` may be created, and a caller
    that re-derives that from the path alone will happily manufacture a
    config for a mistyped ``--config`` (spec INV-4).
    """
    if explicit is not None:
        return explicit, ConfigSource.EXPLICIT
    cwd_config = Path("config.yaml")
    if cwd_config.exists():
        return cwd_config, ConfigSource.CWD
    return user_config_path(), ConfigSource.USER


def ensure_starter_config(path: Path) -> bool:
    """Create `path` and the data directories it names, if it is absent.

    Returns True when it created the file. An existing config is never
    touched — a corrupt or hand-edited one is still the user's.

    The directories matter as much as the file: `api/routes/config.py`'s
    `_validate_paths` rejects a `PATCH /api/config` naming a
    `source_roms`, `dest_roms` or playlist parent that does not exist,
    so a starter config without them blocks the very save that ends
    setup mode. `source_dat` is deliberately not fabricated — it must be
    the user's own file.

    Raises:
        OSError: the config directory cannot be created or written.
    """
    if path.exists():
        return False

    data = user_data_path()
    source_roms = data / "source-roms"
    dest_roms = data / "dest-roms"
    playlist = data / "playlists" / "mame.lpl"
    for directory in (source_roms, dest_roms, playlist.parent):
        directory.mkdir(parents=True, exist_ok=True)

    body = {
        "paths": {
            "source_roms": str(source_roms),
            "source_dat": str(data / "source-dat.xml"),
            "dest_roms": str(dest_roms),
            "retroarch_playlist": str(playlist),
        },
        "server": {"host": "127.0.0.1", "port": 8080, "open_browser_on_start": True},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(STARTER_HEADER + yaml.safe_dump(body, sort_keys=False), encoding="utf-8")
    return True

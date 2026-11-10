"""mame-curator-1146 — the picture the user chose for a game, in ``pictures.json``.

Per ``docs/specs/mame-curator-1146-picture-choice.md`` §4.2. A choice is a
``(source, kind)`` pair, keyed by short name. A picture is cosmetic, so a file
that cannot be read loads as no choices rather than stopping the app.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from mame_curator.api.persist import snapshot_files, write_json_atomic
from mame_curator.media import Kind

logger = logging.getLogger(__name__)


class PictureChoice(BaseModel):
    """One game's chosen picture: which source, and which of its kinds."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    # Any name, not only a known one: a source a later release drops then
    # falls back at the picture address instead of failing the load.
    source: str = Field(min_length=1, max_length=64)
    kind: Kind


class PictureChoices(BaseModel):
    """Every stored choice: the whole of ``pictures.json``."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    pictures: dict[Annotated[str, Field(max_length=64)], PictureChoice] = {}


def pictures_path(data_dir: Path) -> Path:
    """Where the choices live; the literal name ``versioning-overrides.md`` greps."""
    return data_dir / "pictures.json"


def load_pictures(path: Path) -> PictureChoices:
    """The stored choices; none when the file is missing, unreadable or invalid.

    A bad file logs one WARNING and is left on disk as it is.
    """
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return PictureChoices()
    except OSError as exc:
        logger.warning("picture choices unreadable, using none: %r: %s", str(path), exc)
        return PictureChoices()
    try:
        return PictureChoices.model_validate(json.loads(raw.decode("utf-8")))
    except (ValueError, ValidationError) as exc:  # ValueError: bad JSON or UTF-8.
        logger.warning("picture choices invalid, using none: %r: %s", str(path), exc)
        return PictureChoices()


def write_pictures(data_dir: Path, choices: PictureChoices) -> None:
    """Snapshot the current file, when there is one, then write ``choices``."""
    path = pictures_path(data_dir)
    if path.exists():
        snapshot_files(data_dir / "snapshots", {"pictures.json": path})
    write_json_atomic(path, choices.model_dump(mode="json"))

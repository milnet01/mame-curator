"""Reading ``data/notes.json``, the user's notes on each game.

One reader for start-up and snapshot restore (mame-curator-1229). An
unreadable file is renamed aside and logged, never read as empty and left in
place, where the next note save would write over it.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class NotesUnreadableError(ValueError):
    """``notes.json`` cannot be read, is not JSON, or is not a JSON object."""


def load_notes(path: Path) -> dict[str, str]:
    """The notes in ``path``; ``{}`` when the file is absent.

    Raises:
        NotesUnreadableError: the file is there but is not a JSON object.
    """
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:  # ValueError: bad JSON, or bad UTF-8.
        raise NotesUnreadableError(f"{str(path)!r}: {exc}") from exc
    if not isinstance(raw, dict):
        raise NotesUnreadableError(f"{str(path)!r} is not a JSON object")
    return {str(k): str(v) for k, v in raw.items()}


def load_notes_or_set_aside(path: Path) -> dict[str, str]:
    """``load_notes``, but an unreadable file is renamed aside and logged.

    The aside name is ``notes.json.unreadable-<UTC time>``, so a later one
    never replaces it. The app then starts with no notes.
    """
    try:
        return load_notes(path)
    except NotesUnreadableError as exc:
        aside = path.with_name(f"{path.name}.unreadable-{datetime.now(UTC):%Y%m%dT%H%M%S_%fZ}")
        try:
            path.rename(aside)
        except OSError:
            logger.exception("notes unreadable, and could not be moved aside: %s", exc)
        else:
            logger.warning("notes unreadable, moved to %r: %s", str(aside), exc)
        return {}

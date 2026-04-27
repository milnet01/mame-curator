"""Schema + loader for sessions.yaml (continuation-mode session focuses)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from mame_curator.filter.errors import SessionsError


class Session(BaseModel):
    """A named filter that slices the visible set to a working subset."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    include_genres: tuple[str, ...] = ()
    include_publishers: tuple[str, ...] = ()
    include_developers: tuple[str, ...] = ()
    include_year_range: tuple[int, int] | None = None

    @classmethod
    def from_raw(cls, name: str, raw: dict[str, Any]) -> Session:
        """Validate one session block from the YAML and reject empty ones."""
        try:
            session = cls.model_validate(raw)
        except ValidationError as exc:
            raise SessionsError(f"session '{name}': {exc}") from exc
        if (
            not session.include_genres
            and not session.include_publishers
            and not session.include_developers
            and session.include_year_range is None
        ):
            raise SessionsError(f"session '{name}' has no include rules")
        if session.include_year_range is not None:
            lo, hi = session.include_year_range
            if lo > hi:
                raise SessionsError(f"session '{name}' year range {lo}..{hi} is reversed")
        return session


class Sessions(BaseModel):
    """Top-level sessions.yaml: a name → Session map plus the active key."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    active: str | None = None
    sessions: dict[str, Session] = Field(default_factory=dict)


def load_sessions(path: Path) -> Sessions:
    """Read and validate `sessions.yaml`. Missing file → empty Sessions."""
    if not path.exists():
        return Sessions()
    try:
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise SessionsError(f"failed to parse {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise SessionsError(f"{path} is not a YAML mapping")

    active = raw.get("active")
    sessions_raw = raw.get("sessions") or {}
    if not isinstance(sessions_raw, dict):
        raise SessionsError(f"{path} 'sessions' must be a mapping")

    validated: dict[str, Session] = {
        name: Session.from_raw(name, body or {}) for name, body in sessions_raw.items()
    }
    if active is not None and active not in validated:
        raise SessionsError(f"active session '{active}' is not defined in 'sessions'")
    return Sessions(active=active, sessions=validated)

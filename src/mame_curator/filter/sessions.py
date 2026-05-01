"""Schema + loader for sessions.yaml (continuation-mode session focuses)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from mame_curator.filter.errors import SessionsError

# Defends against YAML alias-bomb DoS when P07's `setup/` ships preset
# downloads. Self-authored configs are nowhere near this size.
_MAX_YAML_BYTES = 1 * 1024 * 1024  # 1 MiB


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

    @model_validator(mode="after")
    def _active_must_reference_a_defined_session(self) -> Sessions:
        # Programmatic construction must respect the same invariant the YAML
        # loader enforces — `active` referencing a non-existent session is a
        # bug, not a runtime-discoverable surprise (DS01 C1).
        if self.active is not None and self.active not in self.sessions:
            raise SessionsError(f"active session '{self.active}' is not defined in 'sessions'")
        return self


def _read_yaml_text(path: Path) -> str:
    """Read `path` as UTF-8 text, enforcing the 1 MiB cap and wrapping `OSError`.

    OSError is raised by `read_text` on directories, EIO, perm-denied, NFS
    hiccups; the bare-OSError escape was a TOCTOU finding from the pre-P03
    indie-review (DS01 C5). The size cap (DS01 C3) defends against alias-bombs.
    """
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise SessionsError(f"failed to stat {path}: {exc}") from exc
    if size > _MAX_YAML_BYTES:
        raise SessionsError(
            f"{path} exceeds {_MAX_YAML_BYTES}-byte cap "
            f"(actual: {size}); refusing to parse to defend against YAML alias bombs"
        )
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SessionsError(f"failed to read {path}: {exc}") from exc


def load_sessions(path: Path) -> Sessions:
    """Read and validate `sessions.yaml`. Missing file → empty Sessions."""
    if not path.exists():
        return Sessions()
    text = _read_yaml_text(path)
    try:
        raw_obj: Any = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise SessionsError(f"failed to parse {path}: {exc}") from exc

    # Empty file or YAML `null` at the top level is the legitimate "no
    # sessions" default — same shape as a missing file.
    if raw_obj is None:
        return Sessions()
    if not isinstance(raw_obj, dict):
        raise SessionsError(f"{path} is not a YAML mapping")

    active = raw_obj.get("active")
    # Explicit None semantics (DS01 C4): YAML `null` (Python `None`) is the
    # legitimate "no sessions defined" default; `[]`, `0`, `""`, or any other
    # non-mapping non-None value is malformed and must be rejected — `or {}`
    # silently coerced all four to an empty map and masked malformed input.
    sessions_raw = raw_obj.get("sessions")
    if sessions_raw is None:
        sessions_dict: dict[str, Any] = {}
    elif isinstance(sessions_raw, dict):
        sessions_dict = sessions_raw
    else:
        raise SessionsError(
            f"{path} 'sessions' must be a mapping or null (got {type(sessions_raw).__name__})"
        )

    validated: dict[str, Session] = {}
    for name, body in sessions_dict.items():
        # Same explicit-None semantics for per-session bodies — `null` means
        # "no fields set" (caught by `from_raw`'s no-include-rules check),
        # but a stray `[]` / `""` / `0` is malformed.
        if body is None:
            body_dict: dict[str, Any] = {}
        elif isinstance(body, dict):
            body_dict = body
        else:
            raise SessionsError(
                f"session '{name}' body must be a mapping or null (got {type(body).__name__})"
            )
        validated[name] = Session.from_raw(name, body_dict)
    if active is not None and active not in validated:
        raise SessionsError(f"active session '{active}' is not defined in 'sessions'")
    return Sessions(active=active, sessions=validated)

"""Schema + loader for sessions.yaml (continuation-mode session focuses)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from mame_curator.filter._io import read_capped_text
from mame_curator.filter.errors import SessionsError


class Session(BaseModel):
    """A named filter that slices the visible set to a working subset."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    include_genres: tuple[str, ...] = ()
    include_publishers: tuple[str, ...] = ()
    include_developers: tuple[str, ...] = ()
    include_year_range: tuple[int, int] | None = None

    @model_validator(mode="after")
    def _validate_session(self) -> Session:
        # Direct-construction invariants (FP05 B7). `from_raw` wraps the
        # raised `ValueError`/`ValidationError` into `SessionsError`; direct
        # callers see Pydantic's `ValidationError` with this `ValueError`
        # as `__cause__`.
        if (
            not self.include_genres
            and not self.include_publishers
            and not self.include_developers
            and self.include_year_range is None
        ):
            raise ValueError("session has no include rules")
        if self.include_year_range is not None:
            lo, hi = self.include_year_range
            if lo > hi:
                raise ValueError(f"year range {lo}..{hi} is reversed")
        return self

    @classmethod
    def from_raw(cls, name: str, raw: dict[str, Any]) -> Session:
        """Validate one session block from the YAML and reject empty ones."""
        try:
            return cls.model_validate(raw)
        except ValidationError as exc:
            raise SessionsError(f"session '{name}': {exc}") from exc


class Sessions(BaseModel):
    """Top-level sessions.yaml: a name → Session map plus the active key."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    active: str | None = None
    sessions: dict[str, Session] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _active_must_reference_a_defined_session(self) -> Sessions:
        # Programmatic construction must respect the same invariants the YAML
        # loader enforces (DS01 C1, FP05 A2):
        #   - `active` is None or a real session key.
        #   - empty-string `active` is rejected (would silently match a `""`
        #     session key).
        #   - empty-string session keys are rejected at load time (FP05 A2b).
        if self.active is not None and self.active not in self.sessions:
            raise SessionsError(f"active session '{self.active}' is not defined in 'sessions'")
        if self.active == "":
            raise SessionsError("active session name must be non-empty")
        if "" in self.sessions:
            raise SessionsError("session keys must be non-empty strings")
        return self


def load_sessions(path: Path) -> Sessions:
    """Read and validate `sessions.yaml`. Missing file → empty Sessions."""
    if not path.exists():
        return Sessions()
    text = read_capped_text(path, exc_cls=SessionsError)
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
        # Reject empty-string session keys at load time (FP05 A2b) — they
        # are valid Python dict keys and would silently match an `active: ""`.
        if name == "":
            raise SessionsError("session keys must be non-empty strings")
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
    # Build via `Sessions(...)` so the `_active_must_reference_a_defined_session`
    # model_validator runs (catches active-not-in-sessions, empty-active,
    # empty-key residuals — FP05 L4 removes the duplicate explicit check
    # this used to do).
    try:
        return Sessions(active=active, sessions=validated)
    except ValidationError as exc:
        raise SessionsError(f"{path}: {exc}") from exc

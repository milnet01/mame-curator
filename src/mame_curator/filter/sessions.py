"""Schema + loader for sessions.yaml (continuation-mode session focuses)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from mame_curator.filter._io import read_yaml_mapping
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
        # callers see Pydantic's `ValidationError`. FP06 R1: the original
        # `ValueError` is accessible via
        # `validation_error.errors()[0]["ctx"]["error"]` (Pydantic v2.x);
        # `__cause__` is `None` (Pydantic does not chain validator
        # exceptions through `from`).
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
            # FP06 B3: quote `name` via repr() — session names come from the
            # YAML file (user-controlled) and may contain control bytes.
            raise SessionsError(f"session {name!r}: {exc}") from exc


class Sessions(BaseModel):
    """Top-level sessions.yaml: a name → Session map plus the active key."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    active: str | None = None
    sessions: dict[str, Session] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _active_must_reference_a_defined_session(self) -> Sessions:
        # Programmatic construction must respect the same invariants the YAML
        # loader enforces (DS01 C1, FP05 A2). FP06 B2 + R1: raise `ValueError`
        # (matching `Session._validate_session`'s convention) so Pydantic
        # wraps in `ValidationError`; the loader's `try: ... except
        # ValidationError → SessionsError(f"{path!r}: {exc}")` rewrap then
        # adds path context. Direct callers see `ValidationError` (a
        # `ValueError` subclass in Pydantic v2.x); `errors()[0]["ctx"]["error"]`
        # carries the raw `ValueError` for structural assertions.
        #   - `active` is None or a real session key.
        #   - empty-string `active` is rejected (would silently match a `""`
        #     session key).
        #   - empty-string session keys are rejected (FP05 A2b); the loader
        #     relies on this check.
        if self.active is not None and self.active not in self.sessions:
            # FP06 R2 (Cluster R): `self.active` comes from YAML
            # (user-controlled). Quote via repr() so a control byte in the
            # active key can't break the single-line error contract.
            raise ValueError(f"active session {self.active!r} is not defined in 'sessions'")
        if self.active == "":
            raise ValueError("active session name must be non-empty")
        if "" in self.sessions:
            raise ValueError("session keys must be non-empty strings")
        return self


def load_sessions(path: Path) -> Sessions:
    """Read and validate `sessions.yaml`. Missing, empty or `null` → empty Sessions."""
    raw_obj = read_yaml_mapping(path, exc_cls=SessionsError)
    if raw_obj is None:
        return Sessions()

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
            f"{path!r} 'sessions' must be a mapping or null (got {type(sessions_raw).__name__})"
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
            # FP06 B3: name comes from YAML (user-controlled); quote via repr().
            raise SessionsError(
                f"session {name!r} body must be a mapping or null (got {type(body).__name__})"
            )
        validated[name] = Session.from_raw(name, body_dict)
    # Build via `Sessions(...)` so the `_active_must_reference_a_defined_session`
    # model_validator runs: it refuses an `active` that is not a session, an
    # empty `active` and an empty session key. Its `ValueError` reaches here
    # as `ValidationError`, rewrapped to `SessionsError` with the path.
    try:
        return Sessions(active=active, sessions=validated)
    except ValidationError as exc:
        raise SessionsError(f"{path!r}: {exc}") from exc

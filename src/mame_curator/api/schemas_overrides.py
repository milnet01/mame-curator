"""Overrides + sessions wire-models — extracted from schemas.py by DS02 A5.

Re-exported from ``mame_curator.api.schemas`` so existing
``from mame_curator.api.schemas import OverridesView, ...`` callers keep
working unchanged.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from mame_curator.filter.sessions import Session


class OverridesEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    parent: str
    winner: str


class OverridesView(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    entries: dict[str, str]
    warnings: tuple[str, ...] = ()


class SessionsListing(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    active: str | None
    sessions: dict[str, Session]


class SessionUpsertRequest(BaseModel):
    """Body for R11 POST /api/sessions.

    The ``name`` regex is enforced in the route handler (raising
    ``SessionNameInvalidError``) rather than via a Pydantic ``Field(pattern=...)``
    so the wire-level error code is ``session_name_invalid`` rather than the
    generic ``validation_error``.

    FP11 § G3: frozen=True flipped on to match the rest of `schemas.py`.
    The route handler reads `body.name` / `body.session` and never mutates,
    so the freeze is purely a consistency fix — every public input/output
    surface in this module is `frozen=True, extra="forbid"`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str
    session: Session

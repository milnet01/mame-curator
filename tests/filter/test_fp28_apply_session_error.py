"""FP28 B5 — `_apply_session` must raise typed `SessionsError`, not bare `KeyError`.

At ``filter/runner.py:100`` the call ``sessions.sessions[sessions.active]`` is
a bare ``dict`` subscript: a stale ``active`` value (one that points at a
session key no longer in ``sessions.sessions``) raises raw ``KeyError`` rather
than the project's typed ``SessionsError(FilterError)`` hierarchy.

The ``Sessions`` model has a ``model_validator(mode="after")`` at
``filter/sessions.py:66-89`` that blocks direct construction with a stale
``active`` (``Sessions(active="ghost", sessions={})`` raises ``ValidationError``
at validation). The runtime gap is reachable via ``model_copy(update=...)``:
Pydantic v2 ``model_copy`` skips validators, so a valid instance can be
mutated into a stale state that survives all the way to ``_apply_session``.

Post-fix wraps the subscript in ``try / except KeyError`` and re-raises as
``SessionsError(f"sessions.active = {sessions.active!r} but session not in
sessions.sessions")``.

Pre-fix: ``pytest.raises(SessionsError)`` doesn't catch ``KeyError`` — test fails.
Post-fix: ``SessionsError`` raised; ``isinstance(exc, FilterError)`` is True.

See ``docs/specs/FP28.md`` § B5.
"""

from __future__ import annotations

import pytest

from mame_curator.filter.config import FilterConfig
from mame_curator.filter.errors import FilterError, SessionsError
from mame_curator.filter.overrides import Overrides
from mame_curator.filter.runner import run_filter
from mame_curator.filter.sessions import Session, Sessions


def test_apply_session_raises_typed_error_on_stale_active() -> None:
    # Build a valid Sessions first; Sessions has frozen=True and a model
    # validator that rejects stale active at construction.
    valid = Sessions(
        active="real",
        sessions={"real": Session(include_genres=("Action",))},
    )
    # model_copy skips validators in Pydantic v2 — the stale state survives.
    stale = valid.model_copy(update={"sessions": {}})
    assert stale.active == "real"
    assert stale.sessions == {}

    from tests.filter.conftest import make_empty_ctx

    ctx = make_empty_ctx()

    with pytest.raises(SessionsError) as excinfo:
        run_filter({}, ctx, FilterConfig(), Overrides(), stale)

    assert isinstance(excinfo.value, FilterError)
    assert "sessions.active = 'real'" in str(excinfo.value)

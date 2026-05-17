"""Unit tests for ``api.state`` — WorldState construction + replace_world (P14).

The route-level tests live in ``tests/api/test_state_routes.py`` (chunk 4).
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from mame_curator.api.state import replace_world
from mame_curator.filter import ReviewState, ReviewStateValue


def test_replace_world_review_state_param_passes_through_field(
    client: TestClient, app: Any
) -> None:
    """P14 INV-4 — ``replace_world(review_state=...)`` is a passive swap.

    The returned world's ``review_state`` reflects the new value, AND
    its ``filter_result`` is ``is``-identical to the base's. Review
    state does NOT gate machine eligibility, so the filter never
    needs to re-run for a review-state-only swap.
    """
    # `client` triggers FastAPI lifespan that attaches `world` to `app.state`.
    del client
    base = app.state.world
    new_state = ReviewState.model_validate({"entries": {"pacman": ReviewStateValue.REVIEWED}})

    new_world = replace_world(base=base, review_state=new_state)

    assert new_world.review_state.entries == {"pacman": ReviewStateValue.REVIEWED}
    # The new world is a distinct WorldState instance...
    assert new_world is not base
    # ...but `filter_result` is byte-identical AND object-identical — no
    # `run_filter` was called for the review-state-only swap.
    assert new_world.filter_result is base.filter_result


def test_replace_world_review_state_default_preserves_base(client: TestClient, app: Any) -> None:
    """Omitting ``review_state`` carries through the existing field unchanged."""
    del client
    base = app.state.world

    # Other-input swap (notes-only) must not lose the review state.
    new_world = replace_world(base=base, notes={"pacman": "yum"})

    assert new_world.review_state is base.review_state
    assert new_world.notes == {"pacman": "yum"}

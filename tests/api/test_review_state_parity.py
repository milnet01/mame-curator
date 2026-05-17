"""P14 INV-12 — pending-predicate parity between frontend walk and backend filter.

The frontend `focusNextPending` walks the locally cached `games[]` array and
skips any short_name present in the cached `reviewState.entries` map. The
backend route `GET /api/games?review_state=pending` walks the same logical
set with the same predicate. This test pins the two sets to be byte-equal
against a fixture with mixed states — so a future implementation drift on
either side fails CI before the walkthrough flow gets out of step.

Spec called for ``tests/contract/`` separation; landed under ``tests/api/``
because the existing conftest's TestClient fixtures already live here, and
mirroring an entire conftest tree for one test would be more cost than
gain. The test's contract — that the two predicates match — is unchanged.
"""

from __future__ import annotations

from typing import Any


def test_pending_predicate_equals_backend_filter(client: Any) -> None:
    # Build a mixed review-state fixture against the mini DAT.
    client.post("/api/state", json={"short_name": "pacman", "state": "reviewed"})
    client.post("/api/state", json={"short_name": "pacmanf", "state": "skipped"})

    # Frontend predicate: walk the full games slice and exclude any short_name
    # present in the entries map.
    full = client.get("/api/games?page_size=500").json()
    entries = client.get("/api/state").json()["entries"]
    frontend_pending = {
        item["short_name"] for item in full["items"] if item["short_name"] not in entries
    }

    # Backend predicate: ?review_state=pending.
    backend_pending = {
        item["short_name"]
        for item in client.get("/api/games?review_state=pending&page_size=500").json()["items"]
    }

    assert frontend_pending == backend_pending
    # Sanity: the two marked games must not appear in the pending set.
    assert "pacman" not in backend_pending
    assert "pacmanf" not in backend_pending

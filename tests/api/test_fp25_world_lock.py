"""FP25-A: ``world_lock`` covers all seven remaining mutation routes.

FP20-C wired the lock across five of the seven routes named in
``docs/specs/P04.md`` lines 104-115 (PATCH /api/config, two snapshot
restore-shaped routes, fs grant/revoke). The remaining seven are in
``api/routes/curate.py`` (overrides POST/DELETE; sessions POST/DELETE,
activate, _deactivate) and ``api/routes/games.py`` (notes PUT). All seven
mutate ``app.state.world`` via the read-merge-write-set_world pattern, so
they must run under ``async with request.app.state.world_lock``.

Tests:

1. Each of the seven routes is an ``async def`` (introspection — sync
   handlers run in Starlette's threadpool which would race on the
   read-merge-write block even before the missing-lock issue).
2. Each route acquires ``app.state.world_lock`` during execution. The
   lock is monkey-patched to a tracking subclass that records every
   acquire/release pair.
3. Two ``asyncio.gather``-ed mutations across *different* routes
   (POST /api/overrides + POST /api/sessions) both land — neither edit
   is silently overwritten by the other's set_world.
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest

# The seven routes named in P04 spec lines 104-115 that FP25-A converts.
CURATE_ROUTE_FUNCS = (
    "post_override",
    "delete_override",
    "upsert_session",
    "delete_session",
    "deactivate_session",
    "activate_session",
)
GAMES_ROUTE_FUNCS = ("put_notes",)


@pytest.mark.parametrize("name", CURATE_ROUTE_FUNCS)
def test_fp25_a_curate_route_is_async(name: str) -> None:
    """Each curate.py mutation route must be ``async def``.

    Sync handlers run in Starlette's threadpool — the read-merge-write
    block races with itself across threads. Converting to async + lock
    eliminates the threadpool race entirely.
    """
    import mame_curator.api.routes.curate as curate

    fn = getattr(curate, name)
    assert inspect.iscoroutinefunction(fn), (
        f"{name} must be `async def` after FP25-A (currently sync — "
        "see ROADMAP § FP25-A and docs/specs/P04.md lines 104-115)"
    )


@pytest.mark.parametrize("name", GAMES_ROUTE_FUNCS)
def test_fp25_a_games_route_is_async(name: str) -> None:
    """``put_notes`` must be ``async def`` for the same reason."""
    import mame_curator.api.routes.games as games

    fn = getattr(games, name)
    assert inspect.iscoroutinefunction(fn), (
        f"{name} must be `async def` after FP25-A "
        "(see ROADMAP § FP25-A and docs/specs/P04.md lines 104-115)"
    )


class _TrackingLock:
    """``asyncio.Lock`` wrapper that records each acquire/release.

    Drop-in compatible with ``async with`` (returns ``self`` from
    ``__aenter__``). The real lock is held for the duration of the
    critical section; we only intercept the boundary.
    """

    def __init__(self, inner: asyncio.Lock) -> None:
        self._inner = inner
        self.acquires = 0
        self.releases = 0

    async def __aenter__(self) -> _TrackingLock:
        await self._inner.acquire()
        self.acquires += 1
        return self

    async def __aexit__(self, *exc: object) -> None:
        self.releases += 1
        self._inner.release()

    # Some FastAPI internals may call ``.locked()``; surface it.
    def locked(self) -> bool:
        return self._inner.locked()


@pytest.fixture
def tracking_client(client: Any) -> Iterator[tuple[Any, _TrackingLock]]:
    """Yield a TestClient whose app.state.world_lock is wrapped in a tracker."""
    real_lock = client.app.state.world_lock
    tracker = _TrackingLock(real_lock)
    client.app.state.world_lock = tracker
    try:
        yield client, tracker
    finally:
        client.app.state.world_lock = real_lock


def test_fp25_a_post_override_acquires_world_lock(tracking_client: Any) -> None:
    client, tracker = tracking_client
    resp = client.post("/api/overrides", json={"parent": "pacman", "winner": "pacmanf"})
    assert resp.status_code == 200
    assert tracker.acquires >= 1, "post_override must acquire world_lock"
    assert tracker.releases == tracker.acquires


def test_fp25_a_delete_override_acquires_world_lock(tracking_client: Any) -> None:
    client, tracker = tracking_client
    client.post("/api/overrides", json={"parent": "pacman", "winner": "pacmanf"})
    tracker.acquires = 0
    tracker.releases = 0
    resp = client.delete("/api/overrides/pacman")
    assert resp.status_code == 200
    assert tracker.acquires >= 1, "delete_override must acquire world_lock"
    assert tracker.releases == tracker.acquires


def test_fp25_a_upsert_session_acquires_world_lock(tracking_client: Any) -> None:
    client, tracker = tracking_client
    resp = client.post(
        "/api/sessions",
        json={"name": "s1", "session": {"include_genres": ["Shooter*"]}},
    )
    assert resp.status_code == 200
    assert tracker.acquires >= 1, "upsert_session must acquire world_lock"


def test_fp25_a_delete_session_acquires_world_lock(tracking_client: Any) -> None:
    client, tracker = tracking_client
    client.post(
        "/api/sessions",
        json={"name": "s1", "session": {"include_genres": ["X"]}},
    )
    tracker.acquires = 0
    tracker.releases = 0
    resp = client.delete("/api/sessions/s1")
    assert resp.status_code == 200
    assert tracker.acquires >= 1, "delete_session must acquire world_lock"


def test_fp25_a_activate_session_acquires_world_lock(tracking_client: Any) -> None:
    client, tracker = tracking_client
    client.post(
        "/api/sessions",
        json={"name": "s1", "session": {"include_genres": ["X"]}},
    )
    tracker.acquires = 0
    tracker.releases = 0
    resp = client.post("/api/sessions/s1/activate", json={})
    assert resp.status_code == 200
    assert tracker.acquires >= 1, "activate_session must acquire world_lock"


def test_fp25_a_deactivate_session_acquires_world_lock(tracking_client: Any) -> None:
    client, tracker = tracking_client
    client.post(
        "/api/sessions",
        json={"name": "s1", "session": {"include_genres": ["X"]}},
    )
    client.post("/api/sessions/s1/activate", json={})
    tracker.acquires = 0
    tracker.releases = 0
    resp = client.post("/api/sessions/_deactivate", json={})
    assert resp.status_code == 200
    assert tracker.acquires >= 1, "deactivate_session must acquire world_lock"


def test_fp25_a_put_notes_acquires_world_lock(tracking_client: Any) -> None:
    client, tracker = tracking_client
    resp = client.put("/api/games/pacman/notes", json={"notes": "test note"})
    assert resp.status_code == 200
    assert tracker.acquires >= 1, "put_notes must acquire world_lock"


def test_fp25_a_concurrent_cross_route_mutations_both_land(app: Any, config_file: Path) -> None:
    """Two ``asyncio.gather``-ed mutations across different routes both land.

    Without the lock, two concurrent mutations would each read the same
    ``app.state.world``, compute a new world that includes only their own
    edit, and the later set_world overwrites the earlier — losing one
    user edit silently. P04 spec lines 104-115 mandate the lock contract.

    The test fires POST /api/overrides + POST /api/sessions concurrently
    against the same app instance via ``httpx.AsyncClient`` + ASGI
    transport (so the requests actually run on the event loop, not
    serialised by TestClient). Both edits must be visible afterwards.
    """

    async def _drive() -> None:
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
                ra, rb = await asyncio.gather(
                    ac.post(
                        "/api/overrides",
                        json={"parent": "pacman", "winner": "pacmanf"},
                    ),
                    ac.post(
                        "/api/sessions",
                        json={
                            "name": "s_concurrent",
                            "session": {"include_genres": ["Shooter*"]},
                        },
                    ),
                )
                assert ra.status_code == 200, ra.text
                assert rb.status_code == 200, rb.text

                # Verify BOTH edits are visible — not just one.
                overrides_view = ra.json()
                assert "pacman" in overrides_view["entries"], (
                    "post_override edit lost — concurrent set_world race"
                )

                sessions_resp = await ac.get("/api/sessions")
                assert sessions_resp.status_code == 200
                assert "s_concurrent" in sessions_resp.json()["sessions"], (
                    "upsert_session edit lost — concurrent set_world race"
                )

    asyncio.run(_drive())

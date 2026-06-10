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


# (module, func) for every mutation route FP25-A converts to async + lock.
ASYNC_MUTATION_ROUTES = [
    *(("mame_curator.api.routes.curate", n) for n in CURATE_ROUTE_FUNCS),
    *(("mame_curator.api.routes.games", n) for n in GAMES_ROUTE_FUNCS),
]


@pytest.mark.parametrize(("module", "name"), ASYNC_MUTATION_ROUTES)
def test_fp25_a_mutation_route_is_async(module: str, name: str) -> None:
    """Each of the seven P04-spec mutation routes must be ``async def``.

    Sync handlers run in Starlette's threadpool — the read-merge-write block
    races with itself across threads. Converting to async + lock eliminates
    the threadpool race entirely. (``docs/specs/P04.md`` lines 104-115;
    ROADMAP § FP25-A.)
    """
    import importlib

    fn = getattr(importlib.import_module(module), name)
    assert inspect.iscoroutinefunction(fn), (
        f"{name} must be `async def` after FP25-A (see ROADMAP § FP25-A "
        "and docs/specs/P04.md lines 104-115)"
    )


class _TrackingLock:
    """``asyncio.Lock`` wrapper that records each acquire/release pair
    AND exposes a ``held`` flag for use by a ``set_world`` patch that
    asserts the critical-section invariant.

    Drop-in compatible with ``async with`` (returns ``self`` from
    ``__aenter__``). The real lock is held for the duration of the
    critical section; we intercept the boundary to keep books.

    FP26-A — strengthens the L1-H1 / L1-H2 indie-review findings: the
    per-route tests now prove ``set_world`` runs INSIDE the
    ``async with`` block, not just that ``__aenter__`` fired.

    FP26-N: deliberately NOT subclassing ``asyncio.Lock``. The lock's
    internal state (waiters list, locked-flag manipulation) is private
    and unstable across CPython minor versions; subclassing risks
    breaking on a 3.13 → 3.14 upgrade. The duck-type pattern is enough
    because no production code does ``isinstance(lock, asyncio.Lock)``
    (verified by ``grep -rn 'isinstance.*Lock' src/``).
    """

    def __init__(self, inner: asyncio.Lock) -> None:
        self._inner = inner
        self.acquires = 0
        self.releases = 0
        self.held = False

    async def __aenter__(self) -> _TrackingLock:
        await self._inner.acquire()
        self.acquires += 1
        self.held = True
        return self

    async def __aexit__(self, *exc: object) -> None:
        self.held = False
        self.releases += 1
        self._inner.release()

    # Some FastAPI internals may call ``.locked()``; surface it.
    def locked(self) -> bool:
        return self._inner.locked()


@pytest.fixture
def tracking_client(
    client: Any, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[Any, _TrackingLock]]:
    """Yield a TestClient whose ``app.state.world_lock`` is wrapped in a
    tracker AND whose ``set_world`` is intercepted to assert the lock is
    held at every call.

    FP26-A: prior to this hardening, a route that did
    ``async with lock: pass`` and then ran set_world OUTSIDE the lock
    would have passed the per-route tests. Now any such regression fires
    an ``AssertionError`` at the set_world call site itself.
    """
    real_lock = client.app.state.world_lock
    tracker = _TrackingLock(real_lock)
    client.app.state.world_lock = tracker

    # Patch ``set_world`` at every import site (`_deps` is the source of
    # truth; ``curate`` and ``games`` import it by name, so the
    # ``from mame_curator.api.routes._deps import set_world`` binding
    # captured a reference at import time — patching ``_deps.set_world``
    # alone doesn't reach the route modules' local names).
    from mame_curator.api.routes import _deps, curate
    from mame_curator.api.routes import games as games_module

    real_set_world = _deps.set_world

    def asserted_set_world(request: Any, world: Any) -> None:
        assert tracker.held, (
            "FP26-A: set_world called outside world_lock — the critical-section invariant is broken"
        )
        real_set_world(request, world)

    monkeypatch.setattr(_deps, "set_world", asserted_set_world)
    monkeypatch.setattr(curate, "set_world", asserted_set_world)
    monkeypatch.setattr(games_module, "set_world", asserted_set_world)
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
    # FP31: also pin releases==acquires so a route that acquires but never
    # releases (production deadlock) cannot silently pass this test.
    assert tracker.releases == tracker.acquires


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
    assert tracker.releases == tracker.acquires


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
    assert tracker.releases == tracker.acquires


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
    assert tracker.releases == tracker.acquires


def test_fp25_a_put_notes_acquires_world_lock(tracking_client: Any) -> None:
    client, tracker = tracking_client
    resp = client.put("/api/games/pacman/notes", json={"notes": "test note"})
    assert resp.status_code == 200
    assert tracker.acquires >= 1, "put_notes must acquire world_lock"
    assert tracker.releases == tracker.acquires


def test_fp25_a_concurrent_cross_route_mutations_both_land(
    app: Any, config_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two ``asyncio.gather``-ed mutations across different routes both
    land — AND every ``set_world`` call happens inside the lock.

    Without the lock, two concurrent mutations would each read the same
    ``app.state.world``, compute a new world that includes only their own
    edit, and the later set_world overwrites the earlier — losing one
    user edit silently. P04 spec lines 104-115 mandate the lock contract.

    FP26-A strengthening: the prior test asserted "both responses 200"
    and "both edits visible afterwards", but the current sync-body
    handlers never yield mid-critical-section, so the test passed even
    with the lock removed. Adds the ``asserted_set_world`` pattern from
    the per-route fixture: every ``set_world`` call MUST observe the
    tracking lock as held, otherwise the test fails at the call site.
    Catches "lock acquired but set_world ran outside the `async with`"
    refactor regressions even when no real race fires.
    """

    async def _drive() -> None:
        async with app.router.lifespan_context(app):
            # Wrap the lock + intercept set_world inside the lifespan so
            # the world_lock from build_world is the one we observe.
            real_lock = app.state.world_lock
            tracker = _TrackingLock(real_lock)
            app.state.world_lock = tracker

            from mame_curator.api.routes import _deps, curate
            from mame_curator.api.routes import games as games_module

            real_set_world = _deps.set_world
            held_observations: list[bool] = []

            def asserted_set_world(request: Any, world: Any) -> None:
                held_observations.append(tracker.held)
                real_set_world(request, world)

            monkeypatch.setattr(_deps, "set_world", asserted_set_world)
            monkeypatch.setattr(curate, "set_world", asserted_set_world)
            monkeypatch.setattr(games_module, "set_world", asserted_set_world)

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

                # FP26-A critical-section invariant: every set_world saw
                # lock held.
                assert len(held_observations) == 2, (
                    f"expected 2 set_world calls, got {len(held_observations)}"
                )
                assert all(held_observations), (
                    "FP26-A: at least one set_world ran outside world_lock"
                )

                # FP26-A (L1-M2): verify edits via independent GETs, not
                # via the same response that did the override — the prior
                # form was tautological.
                sessions_resp = await ac.get("/api/sessions")
                assert sessions_resp.status_code == 200
                assert "s_concurrent" in sessions_resp.json()["sessions"], (
                    "upsert_session edit lost — concurrent set_world race"
                )
                # post_override has no GET endpoint; assert via the
                # world state directly through the test client's app
                # reference.
                world = app.state.world
                assert "pacman" in world.overrides.entries, (
                    "post_override edit lost — concurrent set_world race"
                )

    asyncio.run(_drive())

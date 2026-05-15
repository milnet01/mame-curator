"""DS02 G2 — `WorldState.bytes_by_machine` precomputes total ROM bytes per machine.

`api/routes/games.py` recomputes total-bytes-per-result on every
`GET /api/games` (line ~144) and on every `GET /api/games/cart` (lines
~374, 384) via a triple-nested sum-over-roms. The DAT has ~43k
machines * ~10 ROMs each — every request walks the whole graph even
though `Machine.roms` is immutable post-parse.

G2 moves the work to `WorldState` construction: walk each machine
once at boot, store `name -> total_bytes` on `WorldState.bytes_by_
machine` as part of the frozen state. Per-request work drops to
``sum(world.bytes_by_machine.get(s, 0) for s in filtered)`` —
O(|filtered|) instead of O(M * R).

Test contract:
1. `WorldState` accepts a `bytes_by_machine: Mapping[str, int]` field.
2. After ``build_world(...)``, the field is populated for every
   machine in the parsed DAT.
3. Each entry equals ``sum(r.size or 0 for r in machine.roms)`` —
   the regression-lock against accidental drift between the cache
   and the truth.
4. `GET /api/games` reports the same ``total_bytes`` post-refactor —
   purely a caching change, no behaviour delta.

RED markers: each test carries `@pytest.mark.xfail(strict=True)` so
the pre-commit `pytest-fast` hook passes during the RED phase. Step 4
implementation drops each marker as its assertion becomes GREEN.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


def _expected_bytes(machine: Any) -> int:
    return sum((r.size or 0) for r in machine.roms)


def test_world_state_exposes_bytes_by_machine(client: TestClient, app: Any) -> None:
    """The world state must carry a `bytes_by_machine` mapping."""
    # `client` is required so the TestClient context manager fires the
    # FastAPI lifespan that builds WorldState; without it `app.state.world`
    # never gets attached.
    del client
    world = app.state.world
    assert hasattr(world, "bytes_by_machine"), (
        "WorldState is missing `bytes_by_machine`; "
        "DS02 G2 adds this precomputed mapping to drop the per-request "
        "O(M * R) sum in api/routes/games.py."
    )
    bbm = world.bytes_by_machine
    # Mapping-shape, not list. Keys are machine short names.
    assert hasattr(bbm, "__getitem__")
    assert hasattr(bbm, "__iter__")
    assert len(bbm) > 0


def test_bytes_by_machine_matches_sum_over_roms(client: TestClient, app: Any) -> None:
    """Every machine's cache entry equals the live recompute."""
    del client  # see test_world_state_exposes_bytes_by_machine for rationale
    world = app.state.world
    bbm = world.bytes_by_machine
    mismatches: list[str] = []
    for short, machine in world.machines.items():
        expected = _expected_bytes(machine)
        cached = bbm.get(short)
        if cached != expected:
            mismatches.append(f"{short}: cache={cached!r} live={expected!r}")
    assert not mismatches, "bytes_by_machine drift:\n" + "\n".join(mismatches)


def test_games_endpoint_total_bytes_unchanged(client: TestClient, app: Any) -> None:
    """`GET /api/games` reports the same total_bytes the cache implies.

    Regression-lock that the post-G2 refactor at api/routes/games.py
    keeps the wire shape identical — only the implementation path
    changes from per-request walk to cached lookup.
    """
    response = client.get("/api/games")
    assert response.status_code == 200
    body = response.json()
    assert "total_bytes" in body

    # The endpoint sums over `body["items"]` (the filtered page or
    # full result, per its own contract). Whichever shape it reports,
    # the post-fix path uses bytes_by_machine for each member name.
    world = app.state.world
    expected = sum(world.bytes_by_machine.get(item["short_name"], 0) for item in body["items"])
    assert body["total_bytes"] == expected, (
        f"total_bytes drift: endpoint reports {body['total_bytes']}, "
        f"sum(bytes_by_machine[item.short_name]) = {expected}"
    )

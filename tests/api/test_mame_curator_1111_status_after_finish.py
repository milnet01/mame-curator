"""mame-curator-1111 — the copy status stream must replay a job that has
already finished.

INV-1: a client that subscribes to ``GET /api/copy/status`` only after the
copy job has finished still gets 200 and a replay running from
``job_started`` to ``job_finished``.

Pre-fix: ``JobManager`` cleared ``_current`` on finish, so the route raised
``JobNotFoundError`` (404). The frontend's EventSource then received nothing
and the copy modal sat on "Copying" with no total. The race is made
deterministic here by waiting until the manager reports no current job.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any


def test_status_replays_a_job_that_finished_before_subscribe(app: Any) -> None:
    import httpx

    async def _drive() -> list[str]:
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                start = await client.post(
                    "/api/copy/start",
                    json={"selected_names": ["pacman"], "conflict_strategy": "OVERWRITE"},
                )
                assert start.status_code == 200, start.text

                # Wait until the job has finished and been retired, so the
                # subscription below is guaranteed to arrive late.
                jobs = app.state.job
                for _ in range(500):
                    if jobs.current is None:
                        break
                    await asyncio.sleep(0.01)
                assert jobs.current is None, "copy job did not finish in time"

                events: list[str] = []
                async with client.stream("GET", "/api/copy/status") as response:
                    assert response.status_code == 200, (
                        f"late subscriber got {response.status_code}; a finished job "
                        "must still replay (mame-curator-1111)"
                    )
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        events.append(json.loads(line.removeprefix("data:").strip())["event"])
                        if events[-1] in ("job_finished", "job_aborted"):
                            break
                return events

    events = asyncio.run(asyncio.wait_for(_drive(), timeout=15))
    assert events[0] == "job_started", events
    assert events[-1] == "job_finished", events

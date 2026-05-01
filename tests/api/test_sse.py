"""L01 — SSE copy-progress event-stream test.

Per ``docs/specs/P04.md`` § Tests, L01:

> ``httpx.AsyncClient`` consumer reads
> ``job_started → file_started* → file_progress* → file_finished* → job_finished``
> for a 3-file fixture plan. Fixture must be a non-dry-run, non-idempotent
> plan (real source files ≥ 2 MiB so ``_chunked_copy`` emits ≥2 ticks per
> file); otherwise ``file_progress*`` matches zero and the test would pass
> vacuously.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest


@pytest.mark.asyncio
async def test_sse_copy_progress_streams_events(app: Any, source_dir: Path) -> None:
    """L01 — full SSE event sequence on a 3-file plan."""
    # Per the L01 fixture note: real source files must be ≥ 2 MiB so that
    # _chunked_copy (1 MiB chunks) emits multiple file_progress ticks per file.
    for short in ("pacman", "neogeo", "pacmanf"):
        zip_path = source_dir / f"{short}.zip"
        zip_path.write_bytes(b"PK\x05\x06" + b"\0" * (3 * 1024 * 1024))  # ~3 MiB

    transport = httpx.ASGITransport(app=app)
    # httpx.ASGITransport does not run the FastAPI lifespan automatically;
    # drive it manually so app.state.world / .job exist when handlers fire.
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as client,
    ):
        # Start the copy job.
        start = await client.post(
            "/api/copy/start",
            json={
                "selected_names": ["pacman", "neogeo", "pacmanf"],
                "conflict_strategy": "OVERWRITE",
            },
        )
        assert start.status_code == 200

        # Consume the SSE stream.
        events: list[dict[str, Any]] = []
        async with client.stream("GET", "/api/copy/status") as response:
            assert response.status_code == 200
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                payload = line.removeprefix("data:").strip()
                events.append(json.loads(payload))
                if events[-1].get("event") in ("job_finished", "job_aborted"):
                    break

    event_types = [e["event"] for e in events]
    assert event_types[0] == "job_started", "first event must be job_started"
    assert event_types[-1] == "job_finished", "last event must be job_finished"
    assert "file_started" in event_types
    assert "file_progress" in event_types, "≥2 MiB fixture must emit file_progress"
    assert "file_finished" in event_types
    # The order: every file_started precedes its matching file_finished.
    file_started_shorts = [
        e["payload"]["short_name"] for e in events if e["event"] == "file_started"
    ]
    file_finished_shorts = [
        e["payload"]["short_name"] for e in events if e["event"] == "file_finished"
    ]
    assert file_started_shorts == file_finished_shorts, "file_started/finished mis-ordered"

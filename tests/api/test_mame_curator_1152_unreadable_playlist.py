"""mame-curator-1152 — POST /api/copy/start refuses a playlist it cannot read.

Pre-fix: the start succeeded and the copy replaced the playlist. The refusal
has to come from the start itself: useCopySession drops a job_aborted reason,
so an abort from the worker would tell the browser nothing.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import httpx


def test_start_refuses_append_on_unreadable_playlist(app: Any, dest_dir: Path) -> None:
    playlist = dest_dir / "mame.lpl"
    playlist.write_bytes(b"not json")

    async def _drive() -> httpx.Response:
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.post(
                    "/api/copy/start",
                    json={"selected_names": ["pacman"], "conflict_strategy": "APPEND"},
                )

    response = asyncio.run(asyncio.wait_for(_drive(), timeout=15))

    assert response.status_code == 409, response.text
    assert response.json()["code"] == "playlist_unreadable"
    assert app.state.job.replayable is None
    assert playlist.read_bytes() == b"not json"

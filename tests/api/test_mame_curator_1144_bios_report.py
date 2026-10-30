"""mame-curator-1144 — the copy reports the BIOS files it could not find.

A BIOS missing from the ROM folder is skipped, not failed, so the job still
ends OK. The dry run and ``job_finished`` have to say so, or the guide
promises a BIOS file that will not arrive.
"""

from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

# In tests/api/fixtures/api_listxml.xml, kof94 runs on the neogeo BIOS.
REQUEST = {"selected_names": ["kof94"], "conflict_strategy": "OVERWRITE"}


def _dry_run_counts(client: Any) -> dict[str, int]:
    response = client.post("/api/copy/dry-run", json=REQUEST)
    assert response.status_code == 200, response.text
    counts: dict[str, int] = response.json()["counts"]
    return counts


def test_dry_run_counts_a_bios_missing_from_the_rom_folder(client: Any, source_dir: Path) -> None:
    (source_dir / "neogeo.zip").unlink()

    counts = _dry_run_counts(client)

    assert counts["bios"] == 1
    assert counts["bios_missing_source"] == 1


def test_dry_run_counts_no_missing_bios_when_it_is_there(client: Any, source_dir: Path) -> None:
    counts = _dry_run_counts(client)

    assert counts["bios"] == 1
    assert counts["bios_missing_source"] == 0


async def _finished_payload(app: Any) -> dict[str, Any]:
    import httpx

    transport = httpx.ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as client,
    ):
        start = await client.post("/api/copy/start", json=REQUEST)
        assert start.status_code == 200, start.text
        async with client.stream("GET", "/api/copy/status") as response:
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                event = json.loads(line.removeprefix("data:").strip())
                if event["event"] == "job_finished":
                    payload: dict[str, Any] = event["payload"]
                    return payload
                assert event["event"] != "job_aborted", event
    pytest.fail("the stream ended with no job_finished")


@pytest.mark.parametrize(("bios_there", "expected"), [(True, 0), (False, 1)])
def test_job_finished_counts_the_bios_files_it_skipped(
    app: Any, source_dir: Path, *, bios_there: bool, expected: int
) -> None:
    (source_dir / "kof94.zip").write_bytes(b"kof94")
    if not bios_there:
        (source_dir / "neogeo.zip").unlink()

    payload = asyncio.run(_finished_payload(app))

    assert payload["status"] == "OK"
    assert payload["bios_missing"] == expected


def test_job_finished_counts_no_missing_winner_as_a_bios(app: Any, source_dir: Path) -> None:
    # kof94.zip is not in the fixture's ROM folder, so the game itself is skipped.
    assert not (source_dir / "kof94.zip").exists()

    payload = asyncio.run(_finished_payload(app))

    assert payload["bios_missing"] == 0


def test_job_finished_counts_no_bios_already_at_the_destination(
    app: Any, source_dir: Path, dest_dir: Path
) -> None:
    (source_dir / "kof94.zip").write_bytes(b"kof94")
    shutil.copy2(source_dir / "neogeo.zip", dest_dir / "neogeo.zip")

    payload = asyncio.run(_finished_payload(app))

    assert payload["bios_missing"] == 0

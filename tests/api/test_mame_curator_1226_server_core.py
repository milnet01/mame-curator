"""mame-curator-1226: the web-server core findings from the 2026-11-11 code review.

One test (or one small group) per finding; each finding's id is in its test's
docstring.
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from tests.api.conftest import LOCAL_URL


class _BodyPayload(BaseModel):
    """A request model whose one field is named `body` (RL-23)."""

    body: int


# ---- CR-05-1, CR-05-12: the SPA mount --------------------------------------


@pytest.fixture
def spa_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, config_file: Path) -> TestClient:
    from mame_curator.api import app as app_module
    from mame_curator.api import create_app

    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>SPA</title>", encoding="utf-8")
    monkeypatch.setattr(app_module, "frontend_dist", lambda: dist)
    return TestClient(create_app(config_file), base_url=LOCAL_URL)


def test_root_url_shell_must_revalidate(spa_client: TestClient, fake_home: Path) -> None:
    """CR-05-1: `/` serves index.html, so it carries the same no-cache header."""
    response = spa_client.get("/")
    assert response.status_code == 200
    assert "<title>SPA</title>" in response.text
    assert response.headers.get("cache-control") == "no-cache, must-revalidate"


@pytest.mark.parametrize("path", ["/api", "/media", "/assets"])
def test_bare_reserved_prefix_is_404_not_the_shell(
    spa_client: TestClient, fake_home: Path, path: str
) -> None:
    """CR-05-12: a bare `/api` or `/media` is a missing route, not a page."""
    response = spa_client.get(path)
    assert response.status_code == 404
    assert "<title>SPA</title>" not in response.text


# ---- CR-05-14: the OpenAPI version -----------------------------------------


def test_openapi_reports_the_package_version(app: Any) -> None:
    """CR-05-14: the OpenAPI document names the version that is running."""
    from mame_curator import __version__

    assert app.openapi()["info"]["version"] == __version__


# ---- RL-23: a request field literally named `body` -------------------------


def test_a_field_named_body_keeps_its_name_in_loc() -> None:
    """RL-23: only FastAPI's leading `body` part is dropped from `loc`."""
    from mame_curator.api.errors import install_handlers

    probe = FastAPI()
    install_handlers(probe)

    @probe.post("/probe")
    def _probe(payload: _BodyPayload) -> None:  # pragma: no cover - never reached
        return None

    response = TestClient(probe).post("/probe", json={"body": "not a number"})
    assert response.status_code == 422
    assert [f["loc"] for f in response.json()["fields"]] == ["body"]


# ---- CR-05-8: a copy report that could not be saved ------------------------


def _finished_report() -> Any:
    from mame_curator.copy import ConflictStrategy
    from mame_curator.copy.types import CopyReport, CopyReportStatus, PlanSummary

    when = datetime(2026, 11, 16, tzinfo=UTC)
    return CopyReport(
        session_id="s",
        started_at=when,
        finished_at=when,
        status=CopyReportStatus.OK,
        plan_summary=PlanSummary(
            winners_count=0,
            bios_count=0,
            conflict_strategy=ConflictStrategy.CANCEL,
            source_dir=Path("roms"),
            dest_dir=Path("dest"),
        ),
    )


def _job(tmp_path: Path) -> Any:
    import threading

    from mame_curator.api.jobs import Job
    from mame_curator.copy import ConflictStrategy, CopyController, CopyPlan

    plan = CopyPlan(
        winners=(),
        machines={},
        bios_chain={},
        chd_required=frozenset(),
        source_dir=tmp_path,
        dest_dir=tmp_path,
        conflict_strategy=ConflictStrategy.OVERWRITE,
        append_decisions={},
    )
    return Job(
        id="20261116T000000Z-00000000",
        plan=plan,
        started_at=datetime.now(UTC),
        controller=CopyController(),
        thread=threading.Thread(target=lambda: None),
        files_total=0,
        bytes_total=0,
        state="running",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("saved", [True, False])
async def test_job_finished_says_whether_the_report_was_saved(tmp_path: Path, saved: bool) -> None:
    """CR-05-8: `job_finished` no longer points at a report that was never written."""
    from mame_curator.api.jobs import JobManager

    history = tmp_path / "history"
    if not saved:
        history.write_text("a file where the folder should be", encoding="utf-8")
    manager = JobManager(history, loop=asyncio.get_running_loop())
    job = _job(tmp_path)
    manager._current = job

    manager._on_worker_done(_finished_report())

    finished = job.lifecycle_history[-1]
    assert finished.event == "job_finished"
    assert finished.payload["report_saved"] is saved


# ---- CR-06-6: paths.retroarch must be a file -------------------------------


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX execute-bit check")
def test_config_patch_rejects_a_folder_as_retroarch(client: Any, tmp_path: Path) -> None:
    """CR-06-6: a folder has the execute bit, but it is not a program."""
    folder = tmp_path / "retroarch-folder"
    folder.mkdir()
    assert os.access(folder, os.X_OK)
    response = client.patch("/api/config", json={"paths": {"retroarch": str(folder)}})
    assert response.status_code == 422
    assert any(f["loc"] == "paths.retroarch" for f in response.json()["fields"])


# ---- CR-06-9: help files that cannot be read -------------------------------


@pytest.mark.parametrize("kind", ["folder", "not-utf8"])
def test_unreadable_help_topic_is_404(
    client: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """CR-06-9: a folder named `x.md`, or a file that is not UTF-8, is no topic."""
    help_dir = tmp_path / "help"
    help_dir.mkdir()
    if kind == "folder":
        (help_dir / "broken.md").mkdir()
    else:
        (help_dir / "broken.md").write_bytes(b"# Title\n\n\xff\xfe not utf-8\n")
    monkeypatch.setenv("MAME_CURATOR_HELP_DIR", str(help_dir))

    response = client.get("/api/help/broken")
    assert response.status_code == 404
    assert response.json()["code"] == "help_topic_not_found"


# ---- RL-26: the "not configured" message -----------------------------------


def test_retroarch_not_configured_message_does_not_ask_for_a_restart(client: Any) -> None:
    """RL-26: launch reads the paths on every request, so no restart is needed."""
    response = client.post("/api/games/pacman/launch")
    body = response.json()
    assert body["code"] == "retroarch_not_configured"
    assert "restart" not in body["detail"].lower()


# ---- CR-05-6, CR-05-3: config read and validation errors -------------------


def test_unreadable_config_is_a_config_error(tmp_path: Path) -> None:
    """CR-05-6: a config path that cannot be read raises ConfigError, not OSError."""
    from mame_curator.api.errors import ConfigError
    from mame_curator.api.state import load_app_config

    folder = tmp_path / "config.yaml"
    folder.mkdir()
    with pytest.raises(ConfigError):
        load_app_config(folder)


def test_config_validation_detail_is_one_line_without_values(tmp_path: Path) -> None:
    """CR-05-3: the detail names the field, on one line, and never echoes its value."""
    from mame_curator.api.errors import ConfigError
    from mame_curator.api.state import load_app_config

    config = tmp_path / "config.yaml"
    config.write_text("server:\n  port: secret-looking-value\n", encoding="utf-8")
    with pytest.raises(ConfigError) as caught:
        load_app_config(config)
    detail = str(caught.value)
    assert "\n" not in detail
    assert "secret-looking-value" not in detail
    assert "server.port" in detail
    assert any(f.loc == "server.port" for f in caught.value.fields)


# ---- CR-07-3: the filter re-run leaves the event loop ----------------------


@pytest.fixture
def filter_threads(monkeypatch: pytest.MonkeyPatch) -> list[bool]:
    """Record, for each filter run, whether it ran on an event loop."""
    from mame_curator.api import state as state_module
    from mame_curator.filter import run_filter as real

    on_loop: list[bool] = []

    def recording(*args: Any, **kwargs: Any) -> Any:
        try:
            asyncio.get_running_loop()
            on_loop.append(True)
        except RuntimeError:
            on_loop.append(False)
        return real(*args, **kwargs)

    monkeypatch.setattr(state_module, "run_filter", recording)
    return on_loop


@pytest.mark.parametrize(
    ("method", "url", "payload"),
    [
        ("post", "/api/overrides", {"parent": "pacman", "winner": "pacmanf"}),
        ("post", "/api/sessions", {"name": "s1", "session": {"include_genres": ["X"]}}),
        ("patch", "/api/config", {"ui": {"theme": "light"}}),
    ],
)
def test_saves_rerun_the_filter_off_the_event_loop(
    client: Any, filter_threads: list[bool], method: str, url: str, payload: dict[str, Any]
) -> None:
    """CR-07-3: a save's filter re-run must not stall every other request."""
    response = getattr(client, method)(url, json=payload)
    assert response.status_code == 200, response.text
    assert filter_threads, "the save re-ran no filter"
    assert not any(filter_threads)


def test_folder_grant_reruns_the_filter_off_the_event_loop(
    client: Any, filter_threads: list[bool], tmp_path: Path
) -> None:
    """CR-07-3: the same holds for a config change made by granting a folder."""
    folder = tmp_path / "granted"
    folder.mkdir()
    response = client.post("/api/fs/allowed-roots", json={"path": str(folder)})
    assert response.status_code == 200, response.text
    assert filter_threads, "the grant re-ran no filter"
    assert not any(filter_threads)


# ---- CR-07-4: a failed activity append keeps the review mark ---------------


@pytest.fixture
def lenient_client(app: Any) -> Iterator[TestClient]:
    with TestClient(app, base_url=LOCAL_URL, raise_server_exceptions=False) as c:
        yield c


def test_failed_activity_append_does_not_undo_the_mark_later(
    lenient_client: TestClient, monkeypatch: pytest.MonkeyPatch, config_file: Path
) -> None:
    """CR-07-4: the world swap follows the YAML write, so the next mark keeps this one."""
    from mame_curator.api.routes import curate
    from mame_curator.copy.activity import append_activity as real

    calls = {"n": 0}

    def fail_first(*args: Any, **kwargs: Any) -> None:
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("log disk full")
        real(*args, **kwargs)

    monkeypatch.setattr(curate, "append_activity", fail_first)

    first = lenient_client.post("/api/state", json={"short_name": "pacman", "state": "reviewed"})
    assert first.status_code == 500
    second = lenient_client.post("/api/state", json={"short_name": "pacmanf", "state": "skipped"})
    assert second.status_code == 200

    entries = lenient_client.get("/api/state").json()["entries"]
    assert entries == {"pacman": "reviewed", "pacmanf": "skipped"}
    on_disk = (config_file.parent / "data" / "state.yaml").read_text(encoding="utf-8")
    assert "pacman" in on_disk
    assert "pacmanf" in on_disk


# ---- CR-05-11: shutdown order ----------------------------------------------


@pytest.mark.asyncio
async def test_shutdown_stops_the_job_first_and_closes_every_client() -> None:
    """CR-05-11: cancel, join off the loop, then close each client in its own `try`."""
    from types import SimpleNamespace

    import httpx

    from mame_curator.api.app import _shut_down

    order: list[str] = []

    class _Client:
        def __init__(self, name: str, *, fails: bool) -> None:
            self.name, self.fails = name, fails

        async def aclose(self) -> None:
            order.append(self.name)
            if self.fails:
                raise httpx.TransportError("already broken")

    class _Thread:
        def join(self, timeout: float) -> None:
            try:
                asyncio.get_running_loop()
                order.append("join on the loop")
            except RuntimeError:
                order.append("join")

        def is_alive(self) -> bool:
            return False

    job = SimpleNamespace(
        controller=SimpleNamespace(cancel=lambda: order.append("cancel")),
        thread=_Thread(),
        id="j",
    )
    app: Any = SimpleNamespace(
        state=SimpleNamespace(
            job=SimpleNamespace(current=job),
            media_client=_Client("media", fails=True),
            updates_client=_Client("updates", fails=False),
        )
    )

    await _shut_down(app)

    assert order == ["cancel", "join", "media", "updates"]

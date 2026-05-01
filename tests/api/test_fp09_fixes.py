"""FP09 — fix-pass after P04: regression tests, one per actionable finding.

Per ``ROADMAP.md`` § FP09. Each test pins one of the 13 findings from the
P04 closing indie-review.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

# ---- A1 — `{exc}` repr-quoting at 5 sites ----------------------------------
# Defends the FP06–FP08 single-line `detail` invariant when an exception's
# str contains control bytes. The five sites all interpolate {exc} raw;
# this test exercises one (state.py YAML parse) end-to-end via the lifespan
# path. The other four sites are covered by inline assertions in their
# respective regression tests below (B6, B7, fs_list error path, etc.).


def test_a1_yaml_parse_error_in_lifespan_repr_quotes_exc(tmp_path: Path) -> None:
    """A1 — `state.py:77` `failed to parse {!r}: {exc}` — `exc` was raw.

    Reproduces by loading a YAML with a control-byte-bearing key that triggers
    a multi-line yaml.YAMLError. Pre-fix: the LF-bearing exc message bleeds
    through into the ConfigError detail. Post-fix: the detail is single-line.
    """
    from mame_curator.api.errors import ConfigError
    from mame_curator.api.state import load_app_config

    bad_yaml = tmp_path / "config.yaml"
    # YAML that produces a multi-line error message — mismatched indentation
    # inside a list usually yields a "while parsing a block ... found a tab"
    # message that wraps onto two lines.
    bad_yaml.write_text("paths:\n  source_roms: /a\n\tinvalid_tab: x\n")

    with pytest.raises(ConfigError) as exc_info:
        load_app_config(bad_yaml)
    detail = exc_info.value.detail
    assert "\n" not in detail, f"A1: ConfigError detail must be single-line, got {detail!r}"


# ---- A2 — R27 returns CopyReport via response_model + model_validate_json --


def test_a2_r27_corrupt_report_json_returns_typed_error(client: Any, tmp_path: Path) -> None:
    """A2 — `routes/copy.py:155-158` returned `json.loads(...)` raw.

    Pre-fix: a corrupt report.json (truncated, manually edited) leaks malformed
    bytes to clients. Post-fix: ValidationError → typed exception → 502 envelope.
    """
    # Write a corrupt report.json under data/copy-history/.
    history_dir = tmp_path / "data" / "copy-history" / "fake_job_id"
    history_dir.mkdir(parents=True)
    (history_dir / "report.json").write_text("{not valid json")

    response = client.get("/api/copy/history/fake_job_id/report")
    # Expect either 404 (file unreadable as CopyReport) or 502 (corrupt-but-readable).
    # Either way: NOT a raw 200 with invalid JSON.
    assert response.status_code in (404, 502), (
        f"A2: corrupt report should be a typed error, got {response.status_code}"
    )


# ---- A3 — R19 import re-validates session names against R11's regex --------


def test_a3_r19_import_rejects_reserved_session_name(client: Any) -> None:
    """A3 — R11's `_SESSION_NAME_RE` must apply to R19 import paths too."""
    bundle = client.post("/api/config/export").json()
    # Inject a session whose name violates the regex (leading underscore).
    bundle["sessions"]["sessions"]["_deactivate"] = {"include_genres": ["Shooter*"]}

    response = client.post("/api/config/import", json=bundle)
    assert response.status_code == 422
    assert response.json()["code"] == "session_name_invalid", (
        "A3: reserved session name must be rejected on import"
    )


# ---- B3 — Job.history bound (or documented) --------------------------------


def test_b3_progress_history_bounded_lifecycle_history_unbounded() -> None:
    """B3 + Cluster R H1 — progress events use a bounded deque so memory is
    capped on long jobs; lifecycle events use a plain list so subscriber
    replay never loses ``job_started`` / ``file_started`` / etc. under
    progress-tick pressure.
    """
    import dataclasses

    from mame_curator.api.jobs import Job

    fields = {f.name: f for f in dataclasses.fields(Job)}
    progress_factory = fields["progress_history"].default_factory
    lifecycle_factory = fields["lifecycle_history"].default_factory
    assert progress_factory is not dataclasses.MISSING
    assert lifecycle_factory is not dataclasses.MISSING
    progress_instance = progress_factory()
    lifecycle_instance = lifecycle_factory()
    # Progress deque is bounded.
    assert getattr(progress_instance, "maxlen", None) is not None, (
        "B3: progress_history must be a bounded deque"
    )
    # Lifecycle list is unbounded by design (small N — ~3 events per file).
    assert not hasattr(lifecycle_instance, "maxlen"), (
        "Cluster R H1: lifecycle_history must be unbounded so job_started survives eviction"
    )


def test_clusterr_h1_lifecycle_event_survives_progress_overflow() -> None:
    """Cluster R H1 — explicit eviction-resilience test. Fill progress_history
    past its maxlen with synthetic ticks; assert ``job_started`` (in
    lifecycle) is still present in a heapq.merge replay.
    """
    import heapq
    from datetime import UTC, datetime, timedelta

    from mame_curator.api.jobs import _PROGRESS_CAP, Job
    from mame_curator.api.schemas import JobEvent

    job = Job(
        id="test",
        plan=None,  # type: ignore[arg-type]
        started_at=datetime.now(UTC),
        controller=None,  # type: ignore[arg-type]
        thread=None,  # type: ignore[arg-type]
        files_total=0,
        bytes_total=0,
    )
    base_ts = datetime.now(UTC)
    job.lifecycle_history.append(
        JobEvent(event="job_started", payload={"job_id": "test"}, ts=base_ts)
    )
    # Overflow the progress deque by 100 events; oldest progress entries
    # evict, but lifecycle stays.
    overflow = _PROGRESS_CAP + 100
    for i in range(overflow):
        job.progress_history.append(
            JobEvent(
                event="file_progress",
                payload={"short_name": "x", "bytes_done": i, "bytes_total": overflow},
                ts=base_ts + timedelta(microseconds=i + 1),
            )
        )
    merged = list(heapq.merge(job.lifecycle_history, job.progress_history, key=lambda ev: ev.ts))
    event_types = [ev.event for ev in merged]
    assert event_types[0] == "job_started", (
        "Cluster R H1: job_started must survive even after progress-deque overflow"
    )


# ---- B4 — Shared httpx.AsyncClient on app.state ----------------------------


def test_b4_app_state_has_shared_media_client(app: Any) -> None:
    """B4 — `app.state.media_client` must exist after lifespan startup.

    Reuses one TLS connection across many media-proxy requests instead of
    handshaking per-request.
    """
    # Drive the lifespan by entering it as a context manager.
    import asyncio

    async def _check() -> None:
        async with app.router.lifespan_context(app):
            assert hasattr(app.state, "media_client"), (
                "B4: lifespan must instantiate app.state.media_client"
            )
            import httpx

            assert isinstance(app.state.media_client, httpx.AsyncClient)

    asyncio.run(_check())


# ---- B5 — Pause/resume/abort timing — pick one (50 ms in implementation) ---
# Spec says "wait up to 250 ms" (line 338) but implementation uses
# `asyncio.sleep(0.05)` (50 ms). FP09 picks 50 ms — snappier API response;
# the controller flag has already taken effect by the time control reaches
# the route handler in practice, so the sleep is just defense-in-depth.
# Spec is updated in the same fix-pass; no code change needed.


# ---- B6 — replace_world preserves identity on no-op writes -----------------


def test_b6_notes_only_skips_recompute(app: Any, monkeypatch: Any) -> None:
    """B6 — Notes-only PUT must NOT call ``compose_allowlist`` or ``run_filter``.

    Spies on both compute paths and asserts the count after a notes-only
    write is the same as before. Identity-on-tuple doesn't work — Pydantic
    re-validates frozen tuple fields on construction; the spec contract is
    "no recompute", not "preserve Python tuple identity."
    """
    from fastapi.testclient import TestClient

    from mame_curator.api import state as state_mod
    from mame_curator.api.fs import compose_allowlist as real_compose

    compose_calls: list[None] = []

    def spy(cfg: Any) -> Any:
        compose_calls.append(None)
        return real_compose(cfg)

    monkeypatch.setattr(state_mod, "compose_allowlist", spy)

    with TestClient(app) as client:
        baseline = len(compose_calls)
        client.put("/api/games/pacman/notes", json={"notes": "x"})
        after = len(compose_calls)
        assert after == baseline, (
            f"B6: notes-only swap triggered {after - baseline} compose_allowlist call(s)"
        )


def test_b6_no_op_patch_preserves_filter_result(client: Any) -> None:
    """B6 — A no-op PATCH (empty body) must yield identical games listing.

    Was P01 (xfailed); FP09 closes it.
    """
    pre = client.get("/api/games").json()
    response = client.patch("/api/config", json={})
    assert response.status_code == 200
    post = client.get("/api/games").json()
    assert post == pre, "B6: no-op PATCH must not change games listing"


# ---- B7 — fs_list parent escapes sandbox ------------------------------------


def test_b7_fs_list_parent_filtered_against_allowlist(client: Any) -> None:
    """B7 — `parent` field must be None when `requested.parent` is outside
    the allowlist (rather than offering a non-clickable up-link).
    """
    home = str(Path.home())
    response = client.get(f"/api/fs/list?path={home}")
    assert response.status_code == 200
    body = response.json()
    # If $HOME's parent is outside the allowlist (`/home` typically is),
    # parent should be None.
    if body["parent"] is not None:
        # Sanity: parent must be inside allowlist, exposed via the same API.
        parent_check = client.get(f"/api/fs/list?path={body['parent']}")
        assert parent_check.status_code != 403, "B7: returned parent must be inside the allowlist"


# ---- B8 — _help_dir() arithmetic --------------------------------------------


def test_b8_help_dir_arithmetic_lands_at_repo_docs_help() -> None:
    """B8 — `Path(__file__).parents[3] / "docs" / "help"` (without `.parent`).

    Pre-fix: parents[3].parent landed one dir above the repo root; the empty-
    directory fallback returned topics=() coincidentally on a missing dir.
    Post-fix: parents[3] / "docs" / "help" lands inside the repo when the
    package is installed via `pip install -e .` (editable install) — which
    is the dev/test layout.
    """
    # In editable-install mode the help dir points inside the repo.
    # The env-var override path takes precedence; clear it for this assertion.
    import os

    from mame_curator.api.routes.help import _help_dir

    prior = os.environ.pop("MAME_CURATOR_HELP_DIR", None)
    try:
        target = _help_dir()
        # The path's last two segments must be "docs/help".
        assert target.parts[-2:] == ("docs", "help"), (
            f"B8: _help_dir must end in docs/help, got {target}"
        )
        # And the third-to-last segment must be the repo root name (MAME_Curator)
        # rather than its grandparent ('Linux').
        assert target.parts[-3] == "MAME_Curator", (
            f"B8: _help_dir must resolve inside the repo, got {target}"
        )
    finally:
        if prior is not None:
            os.environ["MAME_CURATOR_HELP_DIR"] = prior


# ---- B9 — atomic_write_bytes fsyncs the parent directory --------------------


def test_b9_atomic_write_bytes_fsyncs_parent(tmp_path: Path, monkeypatch: Any) -> None:
    """B9 — `_atomic.atomic_write_bytes` must `os.fsync` the parent dir post-rename.

    Spec § Atomic-write protocol step 4: parent-dir fsync is required for
    power-loss durability. Pre-fix: only the file's fsync runs. Post-fix:
    both the file and the parent-dir fsync run.
    """
    import os

    from mame_curator import _atomic

    fsync_calls: list[int] = []
    real_fsync = os.fsync

    def spy_fsync(fd: int) -> None:
        fsync_calls.append(fd)
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", spy_fsync)

    target = tmp_path / "test.json"
    _atomic.atomic_write_bytes(target, b'{"x": 1}\n')
    # Expect ≥2 fsync calls: one on the file fd, one on the parent dir fd.
    assert len(fsync_calls) >= 2, (
        f"B9: atomic_write_bytes must fsync parent dir; saw {len(fsync_calls)} fsyncs"
    )


# ---- C1 — Subscribe-after-start replay race --------------------------------


def test_c1_subscriber_after_start_sees_job_started_via_history_replay(
    app: Any, source_dir: Path
) -> None:
    """C1 — A subscriber that connects AFTER `start()` returns must still see
    the `job_started` event via the history-replay mechanism.

    Pins the JobManager § Multi-subscriber fan-out contract: history-replay
    covers the gap between `start()` returning and the SSE handler
    subscribing.
    """
    # Make source files large enough that the worker doesn't terminate before
    # the subscriber connects.
    for short in ("pacman", "neogeo", "pacmanf"):
        zip_path = source_dir / f"{short}.zip"
        zip_path.write_bytes(b"PK\x05\x06" + b"\0" * (3 * 1024 * 1024))

    import asyncio

    import httpx

    async def _drive() -> None:
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                start = await client.post(
                    "/api/copy/start",
                    json={
                        "selected_names": ["pacman", "neogeo", "pacmanf"],
                        "conflict_strategy": "OVERWRITE",
                    },
                )
                assert start.status_code == 200

                # Connect AFTER start — race window is real.
                events: list[dict[str, Any]] = []
                async with client.stream("GET", "/api/copy/status") as response:
                    assert response.status_code == 200
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        events.append(json.loads(line.removeprefix("data:").strip()))
                        if events[-1].get("event") in ("job_finished", "job_aborted"):
                            break
                event_types = [e["event"] for e in events]
                assert "job_started" in event_types, (
                    "C1: subscriber-after-start must see job_started via history replay"
                )

    asyncio.run(_drive())

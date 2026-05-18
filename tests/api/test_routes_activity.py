"""R28 shape test + L11 behavioral test (paginated activity log).

Per ``docs/specs/P04.md`` § Routes (Activity) and § Tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


def test_route_r28_shape_activity(client: Any) -> None:
    response = client.get("/api/activity")
    assert response.status_code == 200
    body = response.json()
    for key in ("items", "page", "page_size", "total"):
        assert key in body


def test_route_r28_missing_file_returns_empty_page(client: Any) -> None:
    """Spec line ~173: missing data/activity.jsonl → empty page, never 404/500."""
    response = client.get("/api/activity")
    assert response.status_code == 200
    body = response.json()
    # On a fresh fixture install, no copy has run → activity.jsonl is absent.
    assert body["total"] == 0
    assert body["items"] == []


def test_activity_log_paginated(client: Any, tmp_path: Path) -> None:
    """L11 — paginated + filterable by event_type, since, until."""
    # Synthesize 50 events into data/activity.jsonl by running 50 mini-copies
    # (the runner appends one ActivityEvent per copy session). For the Step-3
    # red state, the assertions below will fail at fixture setup; once
    # implemented, the test seeds the file and asserts pagination.
    activity_file = tmp_path / "data" / "activity.jsonl"
    activity_file.parent.mkdir(parents=True, exist_ok=True)
    events: list[dict[str, Any]] = [
        {
            "timestamp": f"2026-05-01T00:00:{i:02d}Z",
            "event_type": "copy_finished" if i % 2 == 0 else "override_set",
            "summary": f"event {i}",
            "details": {},
        }
        for i in range(50)
    ]
    activity_file.write_text("\n".join(json.dumps(e) for e in events) + "\n")

    page1 = client.get("/api/activity?page=1&page_size=10")
    assert page1.status_code == 200
    page1_items = page1.json()["items"]
    # 50 valid events written above, page_size=10 → exactly 10.
    assert len(page1_items) == 10, f"expected 10 items on page 1, got {len(page1_items)}"

    filtered = client.get("/api/activity?event_type=copy_finished")
    assert filtered.status_code == 200
    filtered_items = filtered.json()["items"]
    # 25 of the 50 fixture events are copy_finished — assert non-empty before
    # checking the type filter so a zero-items regression cannot pass silently.
    assert len(filtered_items) >= 1, "expected at least one copy_finished event after filter"
    assert all(e["event_type"] == "copy_finished" for e in filtered_items)


# ---------------------------------------------------------------------------
# FP27 B5 — GET /api/activity streams the JSONL log line-by-line
#
# `api/routes/activity.py:32` calls `log_path.read_text(...).splitlines()`,
# reading the entire JSONL into RAM before pagination. The route's
# `page` + `page_size` apply *after* the parse, so the per-request RAM
# cost scales with the whole file regardless of which page was asked
# for.
#
# Fix: stream the file line-by-line; maintain a running `total` counter
# (preserves the response's `total` field semantic); maintain
# `deque(maxlen=page * page_size)` of matching dicts in file order;
# slice the deque to extract page-N items in newest-first order.
#
# Pre-fix: a 10 MB log → tracemalloc peak ≈ 10 MB → fails.
# Post-fix: peak ≪ 1 MB regardless of total log size.
# ---------------------------------------------------------------------------


@pytest.fixture
def planted_50k_activity_log(client: Any) -> Path:
    """Write a 50,000-event JSONL log under the test world's data_dir.

    Each event carries a monotonic `details.report_path` (``sample://N``)
    so newest-first pagination can be audited byte-precisely.

    Function-scoped — the underlying ``client`` fixture is too, so each
    test gets its own world. DS04 T1.10 hoisted this from a per-test
    helper to a shared fixture for the audit trail; the I/O cost stays
    one plant per test until the client fixture itself moves to a
    broader scope.
    """
    # `client.app.state.world.data_dir` is typed Any (Starlette
    # app.state is untyped); cast to Path for the helper return.
    activity_log = Path(client.app.state.world.data_dir) / "activity.jsonl"
    activity_log.parent.mkdir(parents=True, exist_ok=True)

    from datetime import UTC, datetime, timedelta

    base_ts = datetime(2026, 1, 1, tzinfo=UTC)
    with activity_log.open("w", encoding="utf-8") as fh:
        for i in range(50_000):
            ts = (base_ts + timedelta(seconds=i)).isoformat()
            # NB: `details.event_type` must match the outer
            # `event_type` (discriminated union) — index lives inside
            # details so the parsed schema accepts it.
            fh.write(
                json.dumps(
                    {
                        "timestamp": ts,
                        "event_type": "copy_finished",
                        "summary": "x",
                        "session_id": "s",
                        "details": {
                            "event_type": "copy_finished",
                            "report_path": f"sample://{i}",
                            "outcome": "ok",
                        },
                    }
                )
                + "\n"
            )
    return activity_log


@pytest.mark.slow
def test_activity_route_streams_log_does_not_buffer_full_file(
    client: Any, planted_50k_activity_log: Path
) -> None:
    """A 10 MB JSONL log → GET /api/activity?page=1&page_size=20 must
    keep tracemalloc peak under 1 MB.

    The 1 MB upper bound clearly distinguishes pre-fix (10 MB whole-file
    resident) from post-fix (~13 KB deque + miscellaneous overhead),
    with plenty of headroom for the JSON-decode allocator + Pydantic
    model validation overhead per response.
    """
    import tracemalloc

    _ = planted_50k_activity_log  # fixture seeds the log

    tracemalloc.start()
    try:
        # Reset traces right before the request so fixture-setup
        # allocations don't inflate the baseline. Without this clear,
        # a heavy prior test can leave the tracemalloc state above
        # the 1 MB threshold even if the request itself is streaming.
        tracemalloc.clear_traces()
        response = client.get("/api/activity?page=1&page_size=20")
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 50_000, (
        f"FP27 B5 — streaming counter must preserve `total` (got {body['total']})."
    )
    assert len(body["items"]) == 20

    upper = 1 * 1024 * 1024  # 1 MB
    assert peak < upper, (
        f"FP27 B5 — GET /api/activity must stream line-by-line; "
        f"tracemalloc peak {peak} ≥ {upper} suggests the whole file is "
        f"still buffered. See `docs/specs/FP27.md` § B5."
    )


@pytest.mark.slow
def test_activity_route_page2_slice_correct(client: Any, planted_50k_activity_log: Path) -> None:
    """Page 2 of the newest-first ordering must contain entries
    49,979 .. 49,960 (by file order), in newest-first order.

    Pins the deque-slice formula against off-by-one regressions
    on pages > 1.
    """
    _ = planted_50k_activity_log  # fixture seeds the log

    response = client.get("/api/activity?page=2&page_size=20")
    assert response.status_code == 200
    body = response.json()
    items = body["items"]
    assert len(items) == 20
    # Newest-first: page 2 holds index 49979..49960 (chronologically
    # second-most-recent 20). The route emits the parsed-via-Pydantic
    # view; check the inner `details.report_path` which carries the
    # original index encoded as ``sample://N`` (set by the planter).
    indexes: list[int] = []
    for item in items:
        rp = item.get("details", {}).get("report_path", "")
        if rp.startswith("sample://"):
            indexes.append(int(rp[len("sample://") :]))
    assert indexes[0] == 49_979, (
        f"FP27 B5 — page-2 newest item index expected 49979, got {indexes[0]}. "
        f"See `docs/specs/FP27.md` § B5."
    )
    assert indexes[-1] == 49_960, (
        f"FP27 B5 — page-2 oldest item index expected 49960, got {indexes[-1]}."
    )

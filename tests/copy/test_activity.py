"""Tests for activity log (`data/activity.jsonl`)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from mame_curator.copy import append_activity, read_activity
from mame_curator.copy.types import (
    ActivityEvent,
    ActivityEventType,
    ConflictStrategy,
    CopyStartedDetails,
    FileRecycledDetails,
    PlanSummary,
    ReviewStateDetails,
)


def _started_event(session_id: str = "01HZZ") -> ActivityEvent:
    return ActivityEvent(
        timestamp=datetime(2026, 4, 30, 12, 0, 0, tzinfo=UTC),
        event_type=ActivityEventType.COPY_STARTED,
        summary="copy started: 5 winners + 2 BIOS",
        session_id=session_id,
        details=CopyStartedDetails(
            plan_summary=PlanSummary(
                winners_count=5,
                bios_count=2,
                conflict_strategy=ConflictStrategy.APPEND,
                source_dir=Path("/src"),
                dest_dir=Path("/dst"),
            ),
            conflict_strategy=ConflictStrategy.APPEND,
        ),
    )


def test_activity_log_append_writes_one_line(tmp_path: Path) -> None:
    """A single `append_activity` call writes exactly one JSONL line carrying
    the event's `event_type` and `session_id`."""
    log_path = tmp_path / "activity.jsonl"
    append_activity(_started_event(), log_path=log_path)
    text = log_path.read_text(encoding="utf-8")
    lines = text.strip().split("\n")
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["event_type"] == "copy_started"
    assert parsed["session_id"] == "01HZZ"


def test_activity_log_append_is_append_only(tmp_path: Path) -> None:
    """Multiple appends preserve all prior lines."""
    log_path = tmp_path / "activity.jsonl"
    e1 = _started_event(session_id="01")
    e2 = _started_event(session_id="02")
    e3 = _started_event(session_id="03")
    append_activity(e1, log_path=log_path)
    append_activity(e2, log_path=log_path)
    append_activity(e3, log_path=log_path)
    lines = log_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 3
    assert json.loads(lines[0])["session_id"] == "01"
    assert json.loads(lines[1])["session_id"] == "02"
    assert json.loads(lines[2])["session_id"] == "03"


def test_activity_log_creates_parent_dir_if_missing(tmp_path: Path) -> None:
    """Append to a nested path creates parents."""
    log_path = tmp_path / "data" / "deep" / "activity.jsonl"
    append_activity(_started_event(), log_path=log_path)
    assert log_path.exists()


def test_read_activity_yields_newest_first(tmp_path: Path) -> None:
    """`read_activity` returns events in reverse-append (newest-first) order so
    the most recent activity surfaces at the top of the log view."""
    log_path = tmp_path / "activity.jsonl"
    for i in range(5):
        append_activity(_started_event(session_id=f"0{i}"), log_path=log_path)
    events = list(read_activity(log_path))
    assert [e.session_id for e in events] == ["04", "03", "02", "01", "00"]


def test_read_activity_tolerates_corrupt_line(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A non-JSON line is skipped with a warning, not an exception."""
    log_path = tmp_path / "activity.jsonl"
    append_activity(_started_event(session_id="ok"), log_path=log_path)
    # Inject a corrupt line.
    with log_path.open("a", encoding="utf-8") as f:
        f.write("this is not json\n")
    append_activity(_started_event(session_id="ok2"), log_path=log_path)

    events = list(read_activity(log_path))
    # Two valid events; corrupt line skipped.
    assert len(events) == 2
    assert {e.session_id for e in events} == {"ok", "ok2"}


def test_activity_log_append_uses_single_os_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FP20-B: a single ``append_activity`` call must produce exactly one
    ``os.write`` syscall, regardless of line size.

    Python's ``BufferedWriter.write`` may split a logical write across
    multiple syscalls when the buffer fills (default 8 KiB), breaking
    the spec's POSIX O_APPEND atomicity claim for >4 KiB events. The
    fix bypasses the buffer with ``os.open(... O_APPEND ...)`` +
    ``os.write(fd, line_bytes)`` so the kernel sees one atomic
    record, no matter how large the JSON serialisation grew.
    """
    import os as os_mod

    log_path = tmp_path / "activity.jsonl"
    write_calls: list[tuple[int, int]] = []
    real_write = os_mod.write

    def tracking_write(fd: int, data: bytes) -> int:
        write_calls.append((fd, len(data)))
        return real_write(fd, data)

    monkeypatch.setattr(os_mod, "write", tracking_write)

    # Force a large event by stuffing a long summary string. Default
    # buffered writer would split this across two os.write calls.
    big_summary = "x" * 16_384
    big_event = ActivityEvent(
        timestamp=datetime(2026, 4, 30, tzinfo=UTC),
        event_type=ActivityEventType.COPY_STARTED,
        summary=big_summary,
        session_id="big",
        details=CopyStartedDetails(
            plan_summary=PlanSummary(
                winners_count=1,
                bios_count=0,
                conflict_strategy=ConflictStrategy.APPEND,
                source_dir=Path("/s"),
                dest_dir=Path("/d"),
            ),
            conflict_strategy=ConflictStrategy.APPEND,
        ),
    )
    append_activity(big_event, log_path=log_path)

    # Filter to writes that targeted *our* fd: tmp_path I/O would also
    # show up here. The append-path writes the entire JSON in one go,
    # so at least one of the recorded writes must be ≥ len(serialised).
    body_size = len(big_event.model_dump_json().encode("utf-8"))
    matching = [c for c in write_calls if c[1] >= body_size]
    assert len(matching) == 1, (
        f"expected exactly one os.write of ≥ {body_size} bytes (atomic "
        f"line append), got {len(matching)}: {[c[1] for c in write_calls]}"
    )


def test_activity_event_discriminator_round_trip() -> None:
    """Each details type round-trips through serialisation."""
    e = ActivityEvent(
        timestamp=datetime(2026, 4, 30, tzinfo=UTC),
        event_type=ActivityEventType.FILE_RECYCLED,
        summary="recycled sf2.zip",
        session_id="01HZZ",
        details=FileRecycledDetails(path="/dst/sf2.zip", reason="REPLACE_AND_RECYCLE"),
    )
    raw = e.model_dump_json()
    revived = ActivityEvent.model_validate_json(raw)
    assert revived.event_type == ActivityEventType.FILE_RECYCLED
    assert isinstance(revived.details, FileRecycledDetails)
    assert revived.details.path == "/dst/sf2.zip"


def test_review_state_event_round_trip() -> None:
    """P14 — the `review_state` discriminator round-trips through JSON."""
    e = ActivityEvent(
        timestamp=datetime(2026, 5, 17, tzinfo=UTC),
        event_type=ActivityEventType.REVIEW_STATE,
        summary="marked sf2 as reviewed",
        session_id="",
        details=ReviewStateDetails(
            short_name="sf2",
            state="reviewed",
            previous="pending",
        ),
    )
    raw = e.model_dump_json()
    revived = ActivityEvent.model_validate_json(raw)
    assert revived.event_type == ActivityEventType.REVIEW_STATE
    assert isinstance(revived.details, ReviewStateDetails)
    assert revived.details.short_name == "sf2"
    assert revived.details.state == "reviewed"
    assert revived.details.previous == "pending"
    assert revived.session_id == ""

"""mame-curator-1199: Activity can name the games a copy skipped or failed."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mame_curator.copy.types import (
    ConflictStrategy,
    CopyOutcome,
    CopyOutcomeStatus,
    CopyReport,
    CopyReportStatus,
    PlanSummary,
)

_SESSION = "20261110T120001Z-0badc0de"
_WHEN = datetime(2026, 11, 10, 12, 0, 1, tzinfo=UTC)


def _outcome(name: str, status: CopyOutcomeStatus, **extra: Any) -> CopyOutcome:
    return CopyOutcome(
        short_name=name,
        role=extra.pop("role", "winner"),
        status=status,
        src=Path("roms") / f"{name}.zip",
        dst=Path("dest") / f"{name}.zip",
        **extra,
    )


def _write_report(tmp_path: Path, job_id: str, session_id: str) -> Path:
    report = CopyReport(
        session_id=session_id,
        started_at=_WHEN,
        finished_at=_WHEN,
        status=CopyReportStatus.PARTIAL_FAILURE,
        plan_summary=PlanSummary(
            winners_count=3,
            bios_count=1,
            conflict_strategy=ConflictStrategy.CANCEL,
            source_dir=Path("roms"),
            dest_dir=Path("dest"),
        ),
        succeeded=(_outcome("pacman", CopyOutcomeStatus.SUCCEEDED),),
        skipped=(
            _outcome("galaga", CopyOutcomeStatus.SKIPPED_MISSING_SOURCE),
            _outcome("neogeo", CopyOutcomeStatus.SKIPPED_IDEMPOTENT, role="bios"),
        ),
        failed=(_outcome("dkong", CopyOutcomeStatus.FAILED, error="disk full"),),
    )
    report_dir = tmp_path / "data" / "copy-history" / job_id
    report_dir.mkdir(parents=True)
    path = report_dir / "report.json"
    # As the job manager writes it (api/jobs.py, _persist_report).
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return path


def test_names_come_from_the_copy_report_with_their_reasons(client: Any, tmp_path: Path) -> None:
    _write_report(tmp_path, "20261110T120000Z-00000001", "20261110T115959Z-00000002")
    _write_report(tmp_path, "20261110T120000Z-0000abcd", _SESSION)

    reply = client.get(f"/api/activity/copy/{_SESSION}/names")

    assert reply.status_code == 200
    assert reply.json() == {
        "skipped": [
            {
                "short_name": "galaga",
                "role": "winner",
                "status": "SKIPPED_MISSING_SOURCE",
                "error": None,
            },
            {"short_name": "neogeo", "role": "bios", "status": "SKIPPED_IDEMPOTENT", "error": None},
        ],
        "failed": [
            {"short_name": "dkong", "role": "winner", "status": "FAILED", "error": "disk full"}
        ],
    }


def test_a_copy_with_no_report_says_the_names_are_not_available(
    client: Any, tmp_path: Path
) -> None:
    url = f"/api/activity/copy/{_SESSION}/names"
    assert client.get(url).status_code == 404  # no copy has run
    _write_report(tmp_path, "20261110T120000Z-00000001", "20261110T115959Z-00000002")
    # A job that crashed before its report was written leaves an empty folder.
    (tmp_path / "data" / "copy-history" / "20261110T120000Z-0000abcd").mkdir()
    reply = client.get(url)
    assert reply.status_code == 404
    assert reply.json()["code"] == "job_not_found"


def test_an_unreadable_report_says_so(client: Any, tmp_path: Path) -> None:
    path = _write_report(tmp_path, "20261110T120000Z-0000abcd", _SESSION)
    path.write_text(path.read_text(encoding="utf-8")[:200], encoding="utf-8")
    reply = client.get(f"/api/activity/copy/{_SESSION}/names")
    assert reply.status_code == 502
    assert reply.json()["code"] == "copy_report_corrupt"

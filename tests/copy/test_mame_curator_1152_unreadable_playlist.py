"""mame-curator-1152 — an APPEND copy refuses a playlist it cannot read.

Pre-fix: ``_resolve_conflicts`` caught ``PlaylistError``, recorded a warning
no browser ever saw, and the copy rewrote the playlist without its old
entries, reporting OK.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mame_curator.cli import build_parser, run
from mame_curator.copy import run_copy
from mame_curator.copy.errors import PlaylistError
from mame_curator.copy.types import ConflictStrategy, CopyPlan, CopyReportStatus
from mame_curator.parser.listxml import BIOSChainEntry
from tests.copy._runner_helpers import _machine

COPY_FIXTURES = Path(__file__).parent / "fixtures"

UNREADABLE = pytest.mark.parametrize(
    "content",
    [
        pytest.param(b"Pac-Man\n/roms/pacman.zip\nDETECT\nDETECT\n0|crc\nMAME.lpl\n", id="legacy"),
        pytest.param(b'{"items": [', id="truncated-json"),
        pytest.param(b"[]", id="not-an-object"),
        pytest.param(b'{"items": "pacman"}', id="items-not-a-list"),
        pytest.param(b"\xff\xfe", id="not-utf8"),
    ],
)


def _plan(
    source_dir: Path,
    dest_dir: Path,
    bios_chain: dict[str, BIOSChainEntry],
    *,
    dry_run: bool = False,
) -> CopyPlan:
    return CopyPlan(
        winners=("kof94",),
        machines={"kof94": _machine("kof94")},
        bios_chain=bios_chain,
        source_dir=source_dir,
        dest_dir=dest_dir,
        conflict_strategy=ConflictStrategy.APPEND,
        dry_run=dry_run,
    )


@UNREADABLE
def test_append_refuses_unreadable_playlist_and_changes_nothing(
    tmp_path: Path,
    source_dir: Path,
    dest_dir: Path,
    bios_chain: dict[str, BIOSChainEntry],
    content: bytes,
) -> None:
    playlist = dest_dir / "mame.lpl"
    playlist.write_bytes(content)
    data_dir = tmp_path / "data"

    with pytest.raises(PlaylistError):
        run_copy(_plan(source_dir, dest_dir, bios_chain), data_dir=data_dir)

    assert playlist.read_bytes() == content
    assert [p.name for p in dest_dir.iterdir()] == ["mame.lpl"]
    # No copy started, so the activity log must not say one did.
    assert not (data_dir / "activity.jsonl").exists()


def test_dry_run_append_refuses_unreadable_playlist(
    tmp_path: Path,
    source_dir: Path,
    dest_dir: Path,
    bios_chain: dict[str, BIOSChainEntry],
) -> None:
    """A dry run reports the refusal the real run would hit."""
    (dest_dir / "mame.lpl").write_bytes(b"not json")
    with pytest.raises(PlaylistError):
        run_copy(
            _plan(source_dir, dest_dir, bios_chain, dry_run=True),
            data_dir=tmp_path / "data",
        )


def test_append_still_keeps_entries_of_a_readable_playlist(
    tmp_path: Path,
    source_dir: Path,
    dest_dir: Path,
    bios_chain: dict[str, BIOSChainEntry],
) -> None:
    """The read moved earlier in run_copy; a good playlist still merges."""
    playlist = dest_dir / "mame.lpl"
    playlist.write_text(
        json.dumps({"items": [{"path": "/roms/pacman.zip", "label": "Pac-Man"}]}),
        encoding="utf-8",
    )
    report = run_copy(_plan(source_dir, dest_dir, bios_chain), data_dir=tmp_path / "data")

    assert report.status is CopyReportStatus.OK
    paths = [item["path"] for item in json.loads(playlist.read_text(encoding="utf-8"))["items"]]
    assert "/roms/pacman.zip" in paths
    assert any(path.endswith("kof94.zip") for path in paths)


def test_overwrite_still_replaces_an_unreadable_playlist(
    tmp_path: Path,
    source_dir: Path,
    dest_dir: Path,
    bios_chain: dict[str, BIOSChainEntry],
) -> None:
    """OVERWRITE discards the old file by request, so it never reads it."""
    playlist = dest_dir / "mame.lpl"
    playlist.write_bytes(b"not json")
    plan = _plan(source_dir, dest_dir, bios_chain).model_copy(
        update={"conflict_strategy": ConflictStrategy.OVERWRITE}
    )
    report = run_copy(plan, data_dir=tmp_path / "data")

    assert report.status is CopyReportStatus.OK
    assert json.loads(playlist.read_text(encoding="utf-8"))["items"]


def test_cli_append_reports_the_refusal_and_exits_1(
    tmp_path: Path,
    source_dir: Path,
    dest_dir: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    playlist = dest_dir / "mame.lpl"
    playlist.write_bytes(b"not json")
    report_path = tmp_path / "filter-report.json"
    report_path.write_text(json.dumps({"winners": ["kof94"]}), encoding="utf-8")
    dat = tmp_path / "tiny.xml"
    dat.write_text(
        '<?xml version="1.0"?><mame>'
        '<machine name="kof94"><description>KoF94</description></machine>'
        "</mame>",
        encoding="utf-8",
    )
    args = build_parser().parse_args(
        [
            "copy",
            "--apply",
            "--conflict",
            "append",
            "--dat",
            str(dat),
            "--listxml",
            str(COPY_FIXTURES / "listxml_bios.xml"),
            "--filter-report",
            str(report_path),
            "--source",
            str(source_dir),
            "--dest",
            str(dest_dir),
        ]
    )

    assert run(args) == 1
    assert "playlist" in capsys.readouterr().err
    assert playlist.read_bytes() == b"not json"

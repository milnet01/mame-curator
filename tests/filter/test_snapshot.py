"""Snapshot regression: full pipeline against a 30-machine fixture."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from mame_curator.filter.config import FilterConfig
from mame_curator.filter.overrides import load_overrides
from mame_curator.filter.runner import run_filter
from mame_curator.filter.sessions import load_sessions
from mame_curator.filter.types import FilterContext
from mame_curator.parser import parse_bestgames, parse_catver, parse_dat, parse_languages
from mame_curator.parser.listxml import parse_listxml_cloneof, parse_listxml_disks
from mame_curator.parser.models import Machine

SNAPSHOT_PATH = Path(__file__).parents[1] / "snapshots" / "filter_smoke.json"


def _build_input(
    fixtures_dir: Path,
) -> tuple[dict[str, Machine], FilterContext, FilterConfig]:
    machines = parse_dat(fixtures_dir / "snapshot_dat.xml")
    cloneof = parse_listxml_cloneof(fixtures_dir / "snapshot_listxml.xml")
    chd = parse_listxml_disks(fixtures_dir / "snapshot_listxml.xml")
    catver = parse_catver(fixtures_dir / "snapshot_catver.ini")
    langs_lists = parse_languages(fixtures_dir / "snapshot_languages.ini")
    bestgames = parse_bestgames(fixtures_dir / "snapshot_bestgames.ini")
    ctx = FilterContext(
        category=catver,
        languages={k: tuple(v) for k, v in langs_lists.items()},
        cloneof_map=cloneof,
        chd_required=frozenset(chd),
        bestgames_tier=bestgames,
    )
    cfg = FilterConfig(
        drop_categories=("Casino*", "Mahjong*"),
        drop_year_before=1978,
        drop_year_after=2015,
    )
    return machines, ctx, cfg


def test_snapshot_matches(fixtures_dir: Path) -> None:
    """Re-run the full filter against the fixture; assert byte-identical to snapshot."""
    machines, ctx, cfg = _build_input(fixtures_dir)
    overrides = load_overrides(fixtures_dir / "snapshot_overrides.yaml")
    sessions = load_sessions(fixtures_dir / "snapshot_sessions.yaml")
    result = run_filter(machines, ctx, cfg, overrides, sessions)

    actual: Any = json.loads(result.model_dump_json())
    if os.environ.get("UPDATE_SNAPSHOTS") == "1":
        SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_PATH.write_text(json.dumps(actual, indent=2, sort_keys=True) + "\n")
    expected: Any = json.loads(SNAPSHOT_PATH.read_text())
    assert actual == expected, "Snapshot drift — re-run with UPDATE_SNAPSHOTS=1 if intentional."

"""Shared helpers for the test_runner*.py test files (DS05 Cluster B).

Leading-underscore filename = not a test file. Pytest discovery
skips this module; both `test_runner.py` and
`test_runner_lifecycle.py` import the `_machine` and `_plan`
factory helpers from here.
"""

from __future__ import annotations

from pathlib import Path

from mame_curator.copy.types import AppendDecision, ConflictStrategy, CopyPlan
from mame_curator.parser.listxml import BIOSChainEntry
from mame_curator.parser.models import Machine


def _machine(short: str, desc: str | None = None) -> Machine:
    return Machine(name=short, description=desc or short, runnable=True)


def _plan(
    *,
    winners: tuple[str, ...],
    machines: dict[str, Machine],
    bios_chain: dict[str, BIOSChainEntry],
    source_dir: Path,
    dest_dir: Path,
    conflict_strategy: ConflictStrategy = ConflictStrategy.CANCEL,
    append_decisions: dict[str, AppendDecision] | None = None,
    delete_existing_zips: bool = False,
    dry_run: bool = False,
) -> CopyPlan:
    return CopyPlan(
        winners=winners,
        machines=machines,
        bios_chain=bios_chain,
        source_dir=source_dir,
        dest_dir=dest_dir,
        conflict_strategy=conflict_strategy,
        append_decisions=append_decisions or {},
        delete_existing_zips=delete_existing_zips,
        dry_run=dry_run,
    )

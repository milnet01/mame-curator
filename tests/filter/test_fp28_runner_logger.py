"""FP28 B4 — `filter.runner` override-warning sites must call `logger.warning`.

The module declares ``logger = logging.getLogger(__name__)`` at
``filter/runner.py:23`` but never calls it. Three override-warning sites
(``L66`` parent-not-in-groups; ``L69`` target-not-in-DAT; ``L73-77`` multi-line
target-wrong-group) only ``warnings.append(...)`` — half the contract from
``filter/spec.md:71`` § Phase C which says "log a warning, skip the override,
and append the message to ``FilterResult.warnings``".

Post-fix adds a matching ``logger.warning(<message>)`` call at each of the
three sites alongside the existing ``warnings.append``.

Pre-fix: ``caplog.records`` is empty at WARNING level — assertions fail.
Post-fix: each test seeds exactly one override → exactly one WARNING record.

See ``docs/specs/FP28.md`` § B4.
"""

from __future__ import annotations

import logging
import re

import pytest

from mame_curator.filter.config import FilterConfig
from mame_curator.filter.overrides import Overrides
from mame_curator.filter.runner import run_filter
from mame_curator.filter.sessions import Sessions
from mame_curator.parser.models import Machine
from tests.filter.conftest import make_empty_ctx as _empty_ctx

LOGGER_NAME = "mame_curator.filter.runner"


def _make_machine(name: str) -> Machine:
    return Machine(
        name=name,
        description=name,
        year=1990,
        manufacturer_raw="Acme",
        publisher="Acme",
        developer="Acme",
        cloneof=None,
        romof=None,
        is_bios=False,
        is_device=False,
        is_mechanical=False,
        runnable=True,
        roms=(),
        biossets=(),
        driver_status=None,
        sample_of=None,
    )


def test_filter_runner_logs_parent_not_in_groups(caplog: pytest.LogCaptureFixture) -> None:
    """``runner.py:65`` branch — override key references an unknown parent."""
    caplog.set_level(logging.WARNING, logger=LOGGER_NAME)
    machines = {"foo": _make_machine("foo")}
    overrides = Overrides(entries={"ghost": "foo"})  # type: ignore[call-arg, unused-ignore]

    result = run_filter(machines, _empty_ctx(), FilterConfig(), overrides, Sessions())

    msg_pattern = re.compile(r"override key 'ghost' is not a known parent")
    records = [r for r in caplog.records if r.name == LOGGER_NAME]
    assert len(records) == 1, (
        f"FP28 B4 — expected exactly one WARNING record at {LOGGER_NAME}, "
        f"got {len(records)}: {[r.getMessage() for r in records]}"
    )
    assert msg_pattern.search(records[0].getMessage())
    # Dual-channel contract: warnings list also carries the message.
    assert any(msg_pattern.search(w) for w in result.warnings)


def test_filter_runner_logs_target_not_in_dat(caplog: pytest.LogCaptureFixture) -> None:
    """``runner.py:68`` branch — override target not present in the DAT."""
    caplog.set_level(logging.WARNING, logger=LOGGER_NAME)
    machines = {"foo": _make_machine("foo")}
    overrides = Overrides(entries={"foo": "phantom"})  # type: ignore[call-arg, unused-ignore]

    result = run_filter(machines, _empty_ctx(), FilterConfig(), overrides, Sessions())

    msg_pattern = re.compile(r"override target 'phantom' is not in the DAT")
    records = [r for r in caplog.records if r.name == LOGGER_NAME]
    assert len(records) == 1
    assert msg_pattern.search(records[0].getMessage())
    assert any(msg_pattern.search(w) for w in result.warnings)


def test_filter_runner_logs_target_wrong_group(caplog: pytest.LogCaptureFixture) -> None:
    """``runner.py:71`` branch — override target belongs to a different parent group."""
    caplog.set_level(logging.WARNING, logger=LOGGER_NAME)
    # Two separate groups; override tries to substitute across groups.
    machines = {
        "foo": _make_machine("foo"),
        "bar": _make_machine("bar"),
    }
    overrides = Overrides(entries={"foo": "bar"})  # type: ignore[call-arg, unused-ignore]

    result = run_filter(machines, _empty_ctx(), FilterConfig(), overrides, Sessions())

    msg_pattern = re.compile(r"target belongs to a different group")
    records = [r for r in caplog.records if r.name == LOGGER_NAME]
    assert len(records) == 1
    assert msg_pattern.search(records[0].getMessage())
    assert any(msg_pattern.search(w) for w in result.warnings)

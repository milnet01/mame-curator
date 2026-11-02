"""mame-curator-1145 review, Group 4: the second line, where the copy builds paths.

A name reaches `run_copy` from a DAT, a listxml or a saved filter report too,
not only through the API's check against the library.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from mame_curator.copy import (
    AppendDecision,
    AppendDecisionKind,
    ConflictStrategy,
    CopyOutcomeStatus,
    CopyPlan,
    preflight,
    run_copy,
)
from mame_curator.parser.listxml import BIOSChainEntry

_UNSAFE = ["../outside/secret", "a/../../outside/secret", "..", ".", "", "a\\b", "c:secret", "a\0b"]


def _tree(tmp_path: Path) -> tuple[Path, Path, Path]:
    source, dest = tmp_path / "deep" / "src", tmp_path / "deep" / "dest"
    source.mkdir(parents=True)
    dest.mkdir()
    outside = tmp_path / "deep" / "outside"
    outside.mkdir()
    (outside / "secret.zip").write_bytes(b"secret")
    (source / "good.zip").write_bytes(b"good")
    return source, dest, outside


def _plan(source: Path, dest: Path, *winners: str, **overrides: object) -> CopyPlan:
    fields: dict[str, object] = {
        "winners": winners,
        "machines": {},
        "bios_chain": {},
        "chd_required": frozenset(),
        "source_dir": source,
        "dest_dir": dest,
        "conflict_strategy": ConflictStrategy.OVERWRITE,
        "append_decisions": {},
    }
    return CopyPlan(**{**fields, **overrides})  # type: ignore[arg-type]  # the fields above.


@pytest.mark.parametrize("name", _UNSAFE)
def test_an_unsafe_winner_fails_alone_and_touches_nothing(tmp_path: Path, name: str) -> None:
    source, dest, outside = _tree(tmp_path)
    ticks: list[str] = []

    report = run_copy(
        _plan(source, dest, name, "good"),
        data_dir=tmp_path / "data",
        on_progress=lambda short, _done, _total: ticks.append(short),
    )

    assert [o.short_name for o in report.failed] == [name]
    assert report.failed[0].status is CopyOutcomeStatus.FAILED
    assert [o.short_name for o in report.succeeded] == ["good"]
    assert name in ticks, "a progress consumer must still count it as processed"
    assert sorted(p.name for p in dest.iterdir() if p.suffix == ".zip") == ["good.zip"]
    assert sorted(p.name for p in outside.iterdir()) == ["secret.zip"]


def test_a_winner_cannot_write_outside_the_destination(tmp_path: Path) -> None:
    """Measured before the fix: this read src/../outside and wrote dest/../outside."""
    source, dest, _outside = _tree(tmp_path)
    (source.parent / "planted.zip").write_bytes(b"planted")

    report = run_copy(_plan(source, dest, "../planted"), data_dir=tmp_path / "data")

    assert report.bytes_copied == 0
    assert [o.status for o in report.failed] == [CopyOutcomeStatus.FAILED]


def test_an_unsafe_bios_fails_alone(tmp_path: Path) -> None:
    source, dest, outside = _tree(tmp_path)
    (source / "game.zip").write_bytes(b"game")
    chain = {
        "game": BIOSChainEntry(romof="../outside/secret", is_bios=False),
        "../outside/secret": BIOSChainEntry(romof=None, is_bios=True),
    }

    report = run_copy(_plan(source, dest, "game", bios_chain=chain), data_dir=tmp_path / "data")

    assert [(o.short_name, o.role) for o in report.failed] == [("../outside/secret", "bios")]
    assert [o.short_name for o in report.succeeded] == ["game"]
    assert (outside / "secret.zip").read_bytes() == b"secret"


def test_an_unsafe_replaces_recycles_nothing_and_warns(tmp_path: Path) -> None:
    """Measured before the fix through the route: the outside file went to the bin."""
    source, dest, outside = _tree(tmp_path)
    decision = AppendDecision(
        kind=AppendDecisionKind.REPLACE_AND_RECYCLE, replaces="../outside/secret"
    )

    report = run_copy(
        _plan(
            source,
            dest,
            "good",
            conflict_strategy=ConflictStrategy.APPEND,
            append_decisions={"good": decision},
        ),
        data_dir=tmp_path / "data",
    )

    assert (outside / "secret.zip").read_bytes() == b"secret"
    assert report.recycled == ()
    assert any("../outside/secret" in w for w in report.warnings)
    assert [o.short_name for o in report.succeeded] == ["good"]


def test_preflight_does_not_look_outside_the_folders(tmp_path: Path) -> None:
    source, dest, _outside = _tree(tmp_path)
    (dest.parent / "outside" / "secret.zip").write_bytes(b"secret")

    result = preflight(_plan(source, dest, "../outside/secret"))

    assert result.missing_source == ("../outside/secret",)
    assert result.already_copied == ()


def test_preflight_leaves_an_unsafe_bios_out_of_the_size_total(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, dest, outside = _tree(tmp_path)
    (outside / "secret.zip").write_bytes(b"x" * 500)
    monkeypatch.setattr("shutil.disk_usage", lambda _p: SimpleNamespace(free=1000))
    chain = {
        "good": BIOSChainEntry(romof="../outside/secret", is_bios=False),
        "../outside/secret": BIOSChainEntry(romof=None, is_bios=True),
    }

    result = preflight(_plan(source, dest, "good", bios_chain=chain))

    assert result.free_space_gap_bytes == 1000 - len(b"good")


@pytest.mark.parametrize("name", ["pacman", "sf2ce", "3bagfull", "a_b-c.d"])
def test_ordinary_names_are_untouched(tmp_path: Path, name: str) -> None:
    source, dest, _outside = _tree(tmp_path)
    (source / f"{name}.zip").write_bytes(b"x")

    report = run_copy(_plan(source, dest, name), data_dir=tmp_path / "data")

    assert [o.short_name for o in report.succeeded] == [name]

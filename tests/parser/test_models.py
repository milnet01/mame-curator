"""Tests for the Machine model."""

import pytest
from pydantic import ValidationError

from mame_curator.parser.models import BiosSet, DriverStatus, Machine, Rom


def test_minimal_machine_constructs() -> None:
    m = Machine(name="pacman", description="Pac-Man (Midway)")
    assert m.name == "pacman"
    assert m.description == "Pac-Man (Midway)"
    assert m.year is None
    assert m.is_bios is False
    assert m.is_device is False
    assert m.is_mechanical is False
    assert m.runnable is True
    assert m.roms == ()
    assert m.biossets == ()
    assert m.driver_status is None


def test_full_machine_constructs() -> None:
    m = Machine(
        name="kinst",
        description="Killer Instinct",
        year=1994,
        manufacturer_raw="Rare / Nintendo (Midway license)",
        publisher="Rare / Nintendo",
        developer="Midway",
        cloneof=None,
        romof=None,
        is_bios=False,
        is_device=False,
        is_mechanical=False,
        runnable=True,
        roms=(Rom(name="ki.u98", size=524288, crc="65f7ea31", sha1="abc"),),
        biossets=(BiosSet(name="default", description="Default", default=True),),
        driver_status=DriverStatus.GOOD,
        sample_of=None,
    )
    assert m.driver_status is DriverStatus.GOOD
    assert m.roms[0].crc == "65f7ea31"
    assert m.biossets[0].default is True


def test_machine_is_frozen() -> None:
    m = Machine(name="pacman", description="Pac-Man")
    with pytest.raises(ValidationError):
        m.name = "other"


def test_machine_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        Machine(name="x", description="y", bogus_field=True)  # type: ignore[call-arg]


def test_driver_status_values() -> None:
    assert DriverStatus.GOOD.value == "good"
    assert DriverStatus.IMPERFECT.value == "imperfect"
    assert DriverStatus.PRELIMINARY.value == "preliminary"

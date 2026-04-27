"""Typed Pydantic models for parsed MAME data."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DriverStatus(StrEnum):
    """MAME driver emulation status."""

    GOOD = "good"
    IMPERFECT = "imperfect"
    PRELIMINARY = "preliminary"


class Rom(BaseModel):
    """A single ROM entry within a machine."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    size: int | None = Field(default=None, ge=0)
    crc: str | None = None
    sha1: str | None = None


class BiosSet(BaseModel):
    """A `<biosset>` declaration within a machine."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    description: str | None = None
    default: bool = False


class Machine(BaseModel):
    """A parsed MAME machine record."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    description: str
    year: int | None = None
    manufacturer_raw: str | None = None
    publisher: str | None = None
    developer: str | None = None
    cloneof: str | None = None
    romof: str | None = None
    is_bios: bool = False
    is_device: bool = False
    is_mechanical: bool = False
    runnable: bool = True
    roms: tuple[Rom, ...] = ()
    biossets: tuple[BiosSet, ...] = ()
    driver_status: DriverStatus | None = None
    sample_of: str | None = None

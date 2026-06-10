"""Tests for `filter/types.py` model immutability invariants.

DS01 cluster C2 — `FilterResult.dropped` was `dict[str, DroppedReason]`,
mutable in-place despite `frozen=True` on the model (Pydantic v2 freezes field
rebinding, not contained-dict state). Tests pin the post-fix shape:
`tuple[tuple[str, DroppedReason], ...]`.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from mame_curator.filter.types import DroppedReason, FilterResult


def test_filter_result_dropped_is_tuple_of_tuples() -> None:
    """The `dropped` field is a tuple of (short_name, DroppedReason) pairs."""
    result = FilterResult(
        winners=("sf2",),
        dropped=(("neogeo", DroppedReason.BIOS), ("z80", DroppedReason.DEVICE)),
        contested_groups=(),
    )
    assert isinstance(result.dropped, tuple)
    assert all(isinstance(pair, tuple) and len(pair) == 2 for pair in result.dropped)
    assert result.dropped[0] == ("neogeo", DroppedReason.BIOS)


def test_filter_result_dropped_cannot_be_mutated() -> None:
    """Tuple is immutable; attempting to assign a new dropped value raises."""
    result = FilterResult(
        winners=("sf2",),
        dropped=(("neogeo", DroppedReason.BIOS),),
        contested_groups=(),
    )
    # Pydantic v2 frozen=True raises ValidationError (type=frozen_instance)
    # on field rebinding.
    with pytest.raises(ValidationError, match=r"Instance is frozen"):
        result.dropped = (("z80", DroppedReason.DEVICE),)


def test_filter_result_dropped_supports_len() -> None:
    """`len(result.dropped)` survives the type change (CLI uses it)."""
    result = FilterResult(
        winners=("sf2",),
        dropped=(
            ("neogeo", DroppedReason.BIOS),
            ("z80", DroppedReason.DEVICE),
            ("3bagfull", DroppedReason.MECHANICAL),
        ),
        contested_groups=(),
    )
    assert len(result.dropped) == 3

r"""FP28 B1 — `_LICENSE_RE` must not mis-capture nested parentheticals.

Current pattern `r"^\s*(?P<publisher>.+?)\s*\((?P<developer>.+?)\s+license\)\s*$"`
on the input ``"Atari (JSA III) (Williams license)"`` non-greedily binds
``publisher="Atari"`` and ``developer="JSA III) (Williams"`` — the close-paren
inside ``developer`` is the bug.

Post-fix uses ``[^()]+?`` for the developer capture so nested parens fall through
to the no-match path, then the engine backtracks and re-anchors at the *last*
open-paren before ``license)``.

Pre-fix: second parametrise case fails — publisher = ``"Atari"`` (wrong).
Post-fix: publisher = ``"Atari (JSA III)"``, developer = ``"Williams"``.

See ``docs/specs/FP28.md`` § B1.
"""

from __future__ import annotations

import pytest

from mame_curator.parser.manufacturer import split_manufacturer


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # Single-license case — unchanged behaviour pre/post fix.
        ("Capcom (Sega license)", ("Capcom", "Sega")),
        # Nested-parens case — the FP28 B1 regression-lock.
        ("Atari (JSA III) (Williams license)", ("Atari (JSA III)", "Williams")),
        # Negative controls — no-license inputs preserve current semantics.
        ("Capcom", ("Capcom", "Capcom")),
        ("", (None, None)),
        (None, (None, None)),
    ],
)
def test_split_manufacturer_handles_nested_parens(
    raw: str | None, expected: tuple[str | None, str | None]
) -> None:
    assert split_manufacturer(raw) == expected

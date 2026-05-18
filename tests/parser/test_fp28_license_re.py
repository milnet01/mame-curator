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
        # FP28 B1 regression-lock: nested-parens case (the actual bug shape).
        ("Atari (JSA III) (Williams license)", ("Atari (JSA III)", "Williams")),
        # Closest-shape negative control absent from test_manufacturer.py: a
        # publisher-only string adjacent to the nested-parens grammar must
        # still resolve developer=publisher (not None).
        ("Capcom", ("Capcom", "Capcom")),
    ],
)
def test_split_manufacturer_handles_nested_parens(
    raw: str | None, expected: tuple[str | None, str | None]
) -> None:
    # FP31: stripped duplicate cases that already live verbatim in
    # tests/parser/test_manufacturer.py (the canonical home for
    # split_manufacturer parametrize coverage). The two cases above are the
    # ones that pin THIS file's FP28-specific contract.
    assert split_manufacturer(raw) == expected

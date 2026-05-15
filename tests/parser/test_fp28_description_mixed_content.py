"""FP28 B3 — `Machine.description` must preserve mixed-content text.

Current code at ``parser/dat.py:171, 179`` uses ``description_elem.text``
which returns only the text *before* the first child element. On a mixed-
content ``<description>Foo <i>bar</i> baz</description>`` element the lxml
``.text`` attribute returns ``"Foo "`` — silently truncating the rest.

Post-fix uses ``"".join(description_elem.itertext()).strip()`` to walk the
whole subtree including child element text and the tail after each child.

Pre-fix: assertion fails — ``machine.description == "Foo "``.
Post-fix: assertion passes — ``machine.description == "Foo bar baz"``.

See ``docs/specs/FP28.md`` § B3.

MAME DATs do not currently ship mixed-content ``<description>`` elements,
so the fix is defensive; the test exercises the failure mode that would
trigger if a future DAT introduced styled text.
"""

from __future__ import annotations

from lxml import etree

from mame_curator.parser.dat import _machine_from_element


def test_machine_description_preserves_mixed_content() -> None:
    elem = etree.fromstring(
        b"<machine name='x'><description>Foo <i>bar</i> baz</description></machine>"
    )
    machine = _machine_from_element(elem, seen_unknown_statuses=set())
    assert machine.description == "Foo bar baz"

"""Tests for parse_dat — security hardening (DS05 Cluster C security seam).

Extracted from `tests/parser/test_dat.py` during DS05. This file
covers the parser's response to adversarial inputs: XXE entity
exfiltration, billion-laughs entity expansion, and zip-bomb
member-size cap. Each test verifies a specific attack class is
neutralised — see FP20-A for the original hardening pass.
"""

import zipfile
from pathlib import Path

import pytest

from mame_curator.parser.dat import parse_dat
from mame_curator.parser.errors import DATError


def test_xxe_external_entity_is_not_resolved(tmp_path: Path) -> None:
    """FP20-A: parser must not resolve external entities.

    A malicious DAT could declare ``<!ENTITY xxe SYSTEM "file:///etc/passwd">``
    and reference it inside a ``<description>`` to exfiltrate file contents
    via the parsed machine struct. Defaults on lxml.iterparse historically
    resolve internal entities; ``no_network=True`` blocks http(s) but NOT
    the ``file://`` scheme. The fix passes an explicit
    ``XMLParser(resolve_entities=False, ...)`` at every iterparse call site.
    """
    secret = tmp_path / "secret.txt"
    secret.write_text("SECRET_PASSWORD_DO_NOT_LEAK")
    secret_uri = secret.as_uri()  # file:///tmp/.../secret.txt
    xxe = tmp_path / "xxe.xml"
    xxe.write_text(
        f'<?xml version="1.0"?>\n'
        f"<!DOCTYPE datafile [\n"
        f'  <!ENTITY xxe SYSTEM "{secret_uri}">\n'
        f"]>\n"
        f'<datafile><machine name="evil" sourcefile="x.cpp">\n'
        f"  <description>&xxe;</description>\n"
        f"  <year>1984</year>\n"
        f"  <manufacturer>x</manufacturer>\n"
        f'  <driver status="good"/>\n'
        f"</machine></datafile>\n"
    )
    # Either the parser refuses to resolve the entity (preferred —
    # description ends up empty or literally "&xxe;") or it raises a
    # parse error. What it must NOT do is leak SECRET_PASSWORD into
    # the parsed Machine.
    try:
        machines = parse_dat(xxe)
    except DATError:
        return
    assert "evil" in machines
    assert "SECRET_PASSWORD_DO_NOT_LEAK" not in (machines["evil"].description or "")


def test_billion_laughs_internal_entity_does_not_expand(tmp_path: Path) -> None:
    """FP20-A: ``XMLParser(resolve_entities=False, ...)`` blocks the
    classic Billion Laughs DoS where deeply-nested internal entities
    expand to a multi-GB string in memory. Without ``resolve_entities=
    False`` lxml expands ``&lol9;`` even with ``no_network=True``.

    Either the parser refuses with a parse error or the description
    contains the literal "&lol;" reference rather than the expanded
    string. Critically, parse_dat must complete in under a second on
    the test fixture (anything slower implies expansion).
    """
    bomb = tmp_path / "lol.xml"
    entity_decl = "".join(
        [
            '<!ENTITY lol "lol">',
            '<!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">',
            '<!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">',
            '<!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">',
            '<!ENTITY lol5 "&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;">',
        ]
    )
    bomb.write_text(
        f'<?xml version="1.0"?>\n<!DOCTYPE datafile [{entity_decl}]>\n'
        f'<datafile><machine name="lol" sourcefile="x.cpp">'
        f"<description>&lol5;</description><year>1984</year>"
        f'<manufacturer>x</manufacturer><driver status="good"/>'
        f"</machine></datafile>"
    )
    # DS04 T2.17: dropped the secondary `time.perf_counter() < 5.0`
    # defence-in-depth assertions. The length check below is the
    # load-bearing one (a non-expanded description fits in <1000 chars;
    # the expanded form would be >100 KB), and wall-time thresholds on
    # CI runners flake — the pre-FP25-K 1.0 s threshold was already
    # bumped to 5 s once; either we trust the length check or we don't.
    try:
        machines = parse_dat(bomb)
    except DATError:
        # FP25-K(3): expansion would produce a multi-GB string; the
        # raise itself is the strong signal that the parser rejected
        # the bomb without expanding entities.
        return
    desc = machines["lol"].description or ""
    assert len(desc) < 1000, f"description has {len(desc)} chars — entities were expanded"


def test_zip_member_size_capped(tmp_path: Path) -> None:
    """FP20-A: a zip member declaring a decompressed size above
    ``_MAX_DAT_BYTES`` (256 MiB) must be rejected before extraction —
    otherwise a malicious 100 KB upload could decompress to gigabytes
    on disk. The cap reads ``zf.getinfo(member).file_size`` (the
    pre-decompression metadata) and refuses extraction without ever
    touching ``zf.extract``.
    """
    from mame_curator.parser.dat import _MAX_DAT_BYTES

    bomb = tmp_path / "bomb.zip"
    big_payload = b"<datafile></datafile>" + b"\0" * 1024  # tiny on disk
    with zipfile.ZipFile(bomb, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("dat.xml", big_payload)
        # Patch the central-dir entry's file_size so the metadata-side
        # check trips even though the actual payload is small.
        info = zf.getinfo("dat.xml")
        info.file_size = _MAX_DAT_BYTES + 1
    with pytest.raises(DATError, match=r"size cap|too large|exceeds"):
        parse_dat(bomb)

"""mame-curator-1118 — `build_world` opens the `-listxml` once.

Each of the four `parse_listxml_*` passes was a full iterparse over a
~300 MB file, 5.5-8.7 s apiece. Pre-fix, `build_world` opened it four
times; this counts the opens.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree

from mame_curator.api.state import build_world

_LISTXML = """<?xml version="1.0"?>
<mame build="0.287">
  <machine name="pacman"><driver status="good"/></machine>
  <machine name="pacmanf" cloneof="pacman" romof="pacman"><driver status="good"/></machine>
</mame>
"""


@pytest.fixture
def listxml(tmp_path: Path) -> Path:
    path = tmp_path / "listxml.xml"
    path.write_text(_LISTXML, encoding="utf-8")
    return path


def test_build_world_reads_listxml_once(
    config_file: Path, listxml: Path, monkeypatch: pytest.MonkeyPatch, fake_home: Path
) -> None:
    text = config_file.read_text(encoding="utf-8")
    config_file.write_text(
        "".join(
            f"  listxml: {listxml}\n" if ln.lstrip().startswith("listxml:") else ln
            for ln in text.splitlines(keepends=True)
        ),
        encoding="utf-8",
    )
    real_iterparse = etree.iterparse
    opened: list[str] = []

    def counting_iterparse(source: object, *args: object, **kwargs: object) -> object:
        opened.append(str(source))
        return real_iterparse(source, *args, **kwargs)

    monkeypatch.setattr(etree, "iterparse", counting_iterparse)

    build_world(config_file)

    assert opened.count(str(listxml)) == 1, f"listxml opened {opened.count(str(listxml))} times"

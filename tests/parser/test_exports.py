"""FP27 A9 — `parse_listxml_bios_chain` + `BIOSChainEntry` exported.

Four `src/` modules import these symbols directly from
`mame_curator.parser.listxml` because they are absent from
`parser/__init__.py.__all__` and from `parser/spec.md`:

- `cli/__init__.py:50,307`
- `api/state.py:39,40,57,111`
- `copy/bios.py:9,14`
- `copy/types.py:18,177`

The project convention is to import from the package surface, not from
submodules. A9 closes the discoverability gap by adding both names to the
`mame_curator.parser` public API and to its spec doc.

Pre-fix: neither symbol is on `parser.__all__` nor in `parser/spec.md`.
Post-fix: both are present.
"""

from __future__ import annotations

from pathlib import Path

from mame_curator import parser


def _parser_spec_path() -> Path:
    """Resolve ``src/mame_curator/parser/spec.md``, guarding the ``parents[2]``
    hop with a ``pyproject.toml`` sentinel so a future move of this test file
    surfaces as a clear assertion rather than a confusing missing-file read
    (mame-curator-1055f)."""
    root = Path(__file__).resolve().parents[2]
    assert (root / "pyproject.toml").is_file(), (
        f"expected repo root at {root} — pyproject.toml sentinel missing; "
        "test_exports.py's parents[2] hop is stale"
    )
    return root / "src" / "mame_curator" / "parser" / "spec.md"


def test_parse_listxml_bios_chain_in_all() -> None:
    """`parse_listxml_bios_chain` must be part of `mame_curator.parser.__all__`."""
    assert "parse_listxml_bios_chain" in parser.__all__, (
        "mame_curator.parser.__all__ must export 'parse_listxml_bios_chain' "
        "(see `docs/specs/FP27.md` § A9)."
    )


def test_bios_chain_entry_in_all() -> None:
    """`BIOSChainEntry` must be part of `mame_curator.parser.__all__`."""
    assert "BIOSChainEntry" in parser.__all__, (
        "mame_curator.parser.__all__ must export 'BIOSChainEntry' (see `docs/specs/FP27.md` § A9)."
    )


def test_parse_listxml_bios_chain_importable_from_package() -> None:
    """The symbol must be accessible as `mame_curator.parser.parse_listxml_bios_chain`."""
    assert hasattr(parser, "parse_listxml_bios_chain"), (
        "mame_curator.parser.parse_listxml_bios_chain must be importable "
        "from the package surface (see `docs/specs/FP27.md` § A9)."
    )


def test_bios_chain_entry_importable_from_package() -> None:
    """The symbol must be accessible as `mame_curator.parser.BIOSChainEntry`."""
    assert hasattr(parser, "BIOSChainEntry"), (
        "mame_curator.parser.BIOSChainEntry must be importable from the "
        "package surface (see `docs/specs/FP27.md` § A9)."
    )


def test_parser_spec_md_documents_parse_listxml_bios_chain() -> None:
    """`parser/spec.md` must mention `parse_listxml_bios_chain` inside
    backticks.

    Substring assertion (not regex anchored to a bullet shape) survives
    later spec formatting changes (table vs list, H4-inline vs prose).
    """
    text = _parser_spec_path().read_text(encoding="utf-8")
    assert "`parse_listxml_bios_chain`" in text, (
        "parser/spec.md must document 'parse_listxml_bios_chain' inside "
        "backticks (see `docs/specs/FP27.md` § A9)."
    )


def test_parser_spec_md_documents_bios_chain_entry() -> None:
    """`parser/spec.md` must mention `BIOSChainEntry` inside backticks."""
    text = _parser_spec_path().read_text(encoding="utf-8")
    assert "`BIOSChainEntry`" in text, (
        "parser/spec.md must document 'BIOSChainEntry' inside backticks "
        "(see `docs/specs/FP27.md` § A9)."
    )

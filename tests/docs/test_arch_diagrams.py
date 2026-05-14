"""FP27 C1 + C2 — architecture diagrams in CLAUDE.md / README.md must
match the actual `src/mame_curator/` package layout.

C1: `CLAUDE.md:51` reads `api/       ← all of the above (P04 — next)`
even though P04 shipped 2026-05-01. The `(P04 — next)` annotation is two
phases stale.

C2: Both `CLAUDE.md:54-55` (help/ + setup/) and `README.md:114` (help/
only) list packages that don't exist on disk. Help content is served by
`api/routes/help.py` from a `docs/help/` directory; setup-wizard
endpoints live in `api/routes/stubs.py`.

The test parses the architecture-diagram fenced code block from each doc
and asserts every `<name>/` row corresponds to (a) a real
`src/mame_curator/<name>/__init__.py`, or (b) an explicit annotation
that excuses it (`(post-v1)`, `(filesystem-only)`), or (c) the
`frontend/` exception (README only — separate React tree).

Pre-fix: CLAUDE.md has `(P04 — next)` for shipped code + help/ + setup/
rows for non-existent packages → fails. README has help/ row for
non-existent package → fails.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_PKG = REPO_ROOT / "src" / "mame_curator"

# Excused annotations that mean "this row is not expected to back to a
# Python package in src/mame_curator/".
_EXCUSED_ANNOTATIONS = (
    "(post-v1)",
    "(filesystem-only)",
)

# Pattern for a diagram row: `<name>/<padding>← <description>` optionally
# followed by `(annotation)`. The leading `<name>/` is the package name.
# Examples that should match:
#   `parser/    ← pure, no internal deps           (P01)`
#   `api/       ← all of the above                 (P04 — next)`
#   `main.py    ← wires everything together`
_ROW_RE = re.compile(
    r"^(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)/\s+←",
)


def _extract_arch_diagram(text: str) -> list[str]:
    """Return the lines of the first fenced code block that looks like
    an architecture diagram (contains at least three `<name>/  ←` rows).

    Accepts any language tag on the opening fence (or none).
    """
    blocks: list[str] = re.findall(
        r"^```[a-zA-Z]*\n(.*?)\n```", text, flags=re.DOTALL | re.MULTILINE
    )
    for block in blocks:
        lines: list[str] = block.splitlines()
        rows = [ln for ln in lines if _ROW_RE.match(ln)]
        if len(rows) >= 3:
            return lines
    raise AssertionError(
        "no architecture-diagram fenced code block found (needs ≥3 `<name>/  ←` rows)"
    )


def _row_packages(diagram_lines: list[str]) -> list[tuple[str, str]]:
    """Return (name, full_line) pairs for every package row in the
    diagram. Excludes non-package rows like `main.py`.
    """
    out: list[tuple[str, str]] = []
    for ln in diagram_lines:
        m = _ROW_RE.match(ln)
        if m:
            out.append((m.group("name"), ln))
    return out


def _is_excused(line: str) -> bool:
    return any(tok in line for tok in _EXCUSED_ANNOTATIONS)


def test_claude_md_architecture_diagram_matches_source_tree() -> None:
    """Every package row in `CLAUDE.md`'s architecture diagram must
    correspond to a real `src/mame_curator/<name>/__init__.py` or carry
    an excused annotation.
    """
    claude_md = REPO_ROOT / "CLAUDE.md"
    text = claude_md.read_text(encoding="utf-8")
    diagram = _extract_arch_diagram(text)
    failures: list[str] = []
    for name, line in _row_packages(diagram):
        if _is_excused(line):
            continue
        pkg_init = SRC_PKG / name / "__init__.py"
        if not pkg_init.exists():
            failures.append(
                f"  CLAUDE.md row `{name}/` has no backing "
                f"{pkg_init.relative_to(REPO_ROOT)} (line: {line!r})"
            )
    assert not failures, (
        "CLAUDE.md architecture-diagram rows do not match `src/mame_curator/` "
        "package layout (see `docs/specs/FP27.md` § C1 + C2):\n" + "\n".join(failures)
    )


def test_claude_md_diagram_has_no_future_marker_for_shipped_api() -> None:
    """`CLAUDE.md`'s diagram must not annotate the `api/` row with
    `(P04 — next)` — P04 shipped on 2026-05-01.
    """
    claude_md = REPO_ROOT / "CLAUDE.md"
    text = claude_md.read_text(encoding="utf-8")
    diagram = _extract_arch_diagram(text)
    api_rows = [ln for ln in diagram if _ROW_RE.match(ln) and ln.startswith("api/")]
    assert len(api_rows) == 1, (
        f"expected exactly one `api/` row in CLAUDE.md diagram, got {len(api_rows)}: {api_rows!r}"
    )
    api_row = api_rows[0]
    assert "(P04 — next)" not in api_row, (
        f"CLAUDE.md's api/ row still carries the `(P04 — next)` "
        f"annotation though P04 shipped 2026-05-01: {api_row!r} "
        f"(see `docs/specs/FP27.md` § C1)."
    )


def test_readme_md_architecture_diagram_matches_source_tree() -> None:
    """Every package row in `README.md`'s architecture diagram must
    correspond to a real `src/mame_curator/<name>/__init__.py`, the
    `frontend/` exception, or an excused annotation. Phase-marker
    annotations (`(P01)`, `(P02)` etc.) are out of scope for this test
    — they're a README convention, not a freshness signal.
    """
    readme_md = REPO_ROOT / "README.md"
    text = readme_md.read_text(encoding="utf-8")
    diagram = _extract_arch_diagram(text)
    failures: list[str] = []
    for name, line in _row_packages(diagram):
        if _is_excused(line):
            continue
        if name == "frontend":
            # React tree at repo-root; expected exception.
            continue
        pkg_init = SRC_PKG / name / "__init__.py"
        if not pkg_init.exists():
            failures.append(
                f"  README.md row `{name}/` has no backing "
                f"{pkg_init.relative_to(REPO_ROOT)} (line: {line!r})"
            )
    assert not failures, (
        "README.md architecture-diagram rows do not match "
        "`src/mame_curator/` package layout (see `docs/specs/FP27.md` § C2):\n"
        + "\n".join(failures)
    )

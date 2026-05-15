"""DS02 F1 — CHANGELOG versioning-policy paragraph reflects v1.x reality.

The current paragraph (CHANGELOG.md lines 8-16 at the time DS02 opened)
claims:

    > **Versioning policy.** This project is pre-alpha. **All shipped
    > work stays under `[Unreleased]` until the v1.0.0 cut at P09.**

That claim was true at P00..P08. The project has since shipped v1.0.0
(at P09 close, 2026-05-04) and v1.2.0; the paragraph is stale and
misleading to a contributor reading the file today.

F1 replaces it with current truth: v1.0.0 cut at P09 happened, minor
releases now accumulate phase-closing tags between them, and the
CHANGELOG is still authoritative per-phase.

Test: assert the post-fix wording contains "v1.0.0 shipped at P09"
(or equivalent past-tense phrasing). The exact prose is finalised at
Step 4 — this test pins the substantive anchor, not the surrounding
sentence structure.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CHANGELOG = REPO_ROOT / "CHANGELOG.md"


def _versioning_paragraph(text: str) -> str:
    """Slice the versioning-policy block from the file.

    The block is a fenced `>` blockquote starting with `> **Versioning
    policy.**` and ending at the first non-blockquote line.
    """
    lines = text.splitlines()
    in_block = False
    out: list[str] = []
    for line in lines:
        if not in_block:
            if "**Versioning policy.**" in line:
                in_block = True
                out.append(line)
            continue
        if line.startswith(">") or line.strip() == "":
            out.append(line)
            if line.strip() == "" and out and out[-2].strip() != "":
                # End of blockquote — blank line after content.
                break
        else:
            break
    return "\n".join(out)


def test_versioning_paragraph_names_p09_in_past_tense() -> None:
    """Post-fix wording must mention v1.0.0 shipping (past tense) at P09."""
    text = CHANGELOG.read_text(encoding="utf-8")
    block = _versioning_paragraph(text)
    assert block, "could not locate the versioning-policy blockquote in CHANGELOG.md"
    # Pin the substantive anchor: past-tense phrasing that v1.0.0
    # already shipped at P09. The current (stale) wording uses
    # future tense ("until the v1.0.0 cut at P09"), so requiring
    # a past-tense verb anchored to v1.0.0/P09 keeps this red until
    # F1 lands its rewrite.
    # "cut" appears in BOTH the stale future-tense wording ("the v1.0.0
    # cut at P09" — noun phrase) and the post-fix past-tense option
    # ("v1.0.0 was cut at P09"). Pin against past-tense auxiliary
    # verbs / verb forms only: shipped / released / landed, or "was
    # cut" / "has shipped" style. The future-tense stale phrasing
    # uses "the … cut" (article + noun) which this regex rejects.
    past_tense_re = re.compile(
        r"v1\.0\.0[^.]*\b(shipped|released|landed|was\s+cut|has\s+(shipped|landed|released))\b[^.]*\bP09\b"
        r"|\bP09\b[^.]*\b(shipped|released|landed|was\s+cut|has\s+(shipped|landed|released))\b[^.]*v1\.0\.0",
        re.IGNORECASE | re.DOTALL,
    )
    assert past_tense_re.search(block), (
        f"versioning-policy block does not name v1.0.0 as a past-tense P09 shipment:\n{block}"
    )


def test_versioning_paragraph_drops_pre_alpha_claim() -> None:
    """Stale "pre-alpha" / "stays under [Unreleased] until v1.0.0" wording is gone."""
    text = CHANGELOG.read_text(encoding="utf-8")
    block = _versioning_paragraph(text)
    assert block, "could not locate the versioning-policy blockquote in CHANGELOG.md"
    assert "pre-alpha" not in block.lower(), (
        f"versioning-policy block still calls the project pre-alpha:\n{block}"
    )
    # "stays under `[Unreleased]` until the v1.0.0 cut" is the exact
    # phrase that needs removing; allow generous fuzz on whitespace
    # and code-quote punctuation.
    stale_re = re.compile(
        r"stays\s+under[^.]*Unreleased[^.]*until\s+the\s+v1\.0\.0\s+cut",
        re.IGNORECASE | re.DOTALL,
    )
    assert not stale_re.search(block), (
        f"stale 'stays under [Unreleased] until the v1.0.0 cut' wording remains:\n{block}"
    )

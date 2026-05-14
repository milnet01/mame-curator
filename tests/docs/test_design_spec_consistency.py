"""FP27 A6c — design-spec keyboard shortcuts match the wired post-fix set.

`docs/superpowers/specs/2026-04-27-mame-curator-design.md` advertises
nine keyboard-shortcut bullets under the `### Keyboard shortcuts`
section. `frontend/src/App.tsx:316-318` registers exactly one binding
via `useKeyboard` (`combo: 'k'` with `meta:true`). The other eight are
zombies — declared in docs, never wired.

A6 splits the resolution:

- A6a: keep `Esc` (Radix-delivered) with a credit annotation.
- A6b: wire `/` (focus library search) — adds a second useKeyboard
  binding.
- A6c: remove `?`, `g …`, `j`/`k`, `o`/`Enter`, `a`, `n` from the
  design spec; file a P14-class roadmap entry for the chord cohort.

Post-fix design-spec contract: bullets are exactly
`{⌘K/Ctrl-K, /, Esc}`. Post-fix `useKeyboard` contract: bindings are
exactly `{⌘K/Ctrl-K, /}` (Esc lives in design-spec but is Radix-
delivered).

The test locates the section by exact-string match on the H3 heading
(not by line number — line 590 will shift on future edits).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DESIGN_SPEC = REPO_ROOT / "docs" / "superpowers" / "specs" / "2026-04-27-mame-curator-design.md"
APP_TSX = REPO_ROOT / "frontend" / "src" / "App.tsx"

# Expected post-fix sets.
DESIGN_SPEC_EXPECTED = frozenset({"cmd-k", "/", "esc"})
WIRED_EXPECTED = frozenset({"cmd-k", "/"})


def _normalize(token: str) -> str:
    """Map design-spec bullet leads and useKeyboard combos to a common
    canonical form so comparison is stable across notation choices.

    Examples:
      `⌘K` / `Ctrl-K`  → 'cmd-k'
      `/`              → '/'
      `Esc`            → 'esc'
      `combo: 'k'` (meta:true)  → 'cmd-k'
    """
    t = token.strip().lower().strip("`").strip()
    if t in ("⌘k / ctrl-k", "⌘k/ctrl-k", "ctrl-k", "cmd-k", "⌘k"):
        return "cmd-k"
    if t == "/":
        return "/"
    if t in ("esc", "escape"):
        return "esc"
    return t


def _extract_design_spec_bullets() -> list[str]:
    """Parse the `### Keyboard shortcuts` section of the design spec
    and return the first inline `` `<token>` `` (the shortcut key) from
    each bullet.
    """
    text = DESIGN_SPEC.read_text(encoding="utf-8")
    # Find the section by exact heading match.
    section_start = text.find("### Keyboard shortcuts")
    assert section_start >= 0, (
        "design spec must contain a `### Keyboard shortcuts` H3 heading "
        "(see `docs/specs/FP27.md` § A6c)."
    )
    # Find the next H2/H3 heading after this one to bound the section.
    rest = text[section_start + len("### Keyboard shortcuts") :]
    next_heading = re.search(r"\n##+\s", rest)
    section_body = rest[: next_heading.start()] if next_heading else rest

    bullets: list[str] = []
    for line in section_body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        # First `` `<token>` `` in the bullet is the shortcut.
        m = re.search(r"`([^`]+)`", stripped)
        if m:
            bullets.append(m.group(1))
    return bullets


def _extract_wired_combos() -> list[str]:
    """Parse `frontend/src/App.tsx` for `combo: '<x>'` strings inside a
    `useKeyboard([...])` block.

    Substring-based, not full TS parsing — sufficient for a contract
    test on a single registration block.
    """
    text = APP_TSX.read_text(encoding="utf-8")
    # `combo: 'x'` or `combo: "x"` with optional whitespace.
    combos = re.findall(r"combo:\s*['\"]([^'\"]+)['\"]", text)
    # `meta:true` paired with `combo: 'k'` becomes cmd-k by convention.
    # We just normalize the raw combos; canonicalization handles meta.
    out: list[str] = []
    # Find each useKeyboard block + the combos inside.
    for block_match in re.finditer(r"useKeyboard\s*\(\s*\[(.*?)\]\s*\)", text, re.DOTALL):
        block = block_match.group(1)
        for combo_match in re.finditer(r"\{[^{}]*combo:\s*['\"]([^'\"]+)['\"][^{}]*\}", block):
            inner = combo_match.group(0)
            combo = combo_match.group(1)
            # If the entry has `meta:true`, treat as cmd-k variant.
            if "meta" in inner and combo.lower() == "k":
                out.append("cmd-k")
            else:
                out.append(combo)
    # If the regex matched zero blocks (e.g. unconventional formatting),
    # fall back to a global `combo:` sweep without the `meta:true` join.
    if not out:
        out = combos
    return out


@pytest.mark.xfail(
    reason="FP27 T1c — A6c implementation not yet landed; this test stays "
    "RED until the design spec is trimmed to {⌘K/Ctrl-K, /, Esc}.",
    strict=True,
)
def test_design_spec_keyboard_shortcuts_match_post_fix_set() -> None:
    """The design-spec `### Keyboard shortcuts` section must list
    exactly `{⌘K/Ctrl-K, /, Esc}` post-fix.
    """
    raw_bullets = _extract_design_spec_bullets()
    canonical = {_normalize(b) for b in raw_bullets}
    assert canonical == DESIGN_SPEC_EXPECTED, (
        f"design-spec keyboard shortcuts must be exactly "
        f"{sorted(DESIGN_SPEC_EXPECTED)}, got "
        f"{sorted(canonical)} (raw bullets: {raw_bullets!r}). "
        f"See `docs/specs/FP27.md` § A6c."
    )


@pytest.mark.xfail(
    reason="FP27 T1c — A6b implementation not yet landed; this test stays "
    "RED until App.tsx registers a `/` useKeyboard binding.",
    strict=True,
)
def test_app_tsx_use_keyboard_bindings_match_post_fix_set() -> None:
    """`frontend/src/App.tsx` must register exactly the wired set
    `{⌘K/Ctrl-K, /}` post-fix (Esc is Radix-delivered, not wired).
    """
    raw_combos = _extract_wired_combos()
    canonical = {_normalize(c) for c in raw_combos}
    assert canonical == WIRED_EXPECTED, (
        f"App.tsx useKeyboard bindings must be exactly "
        f"{sorted(WIRED_EXPECTED)}, got "
        f"{sorted(canonical)} (raw combos: {raw_combos!r}). "
        f"See `docs/specs/FP27.md` § A6b + A6c."
    )

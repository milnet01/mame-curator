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
    if t.startswith("cmd-"):
        return t  # already canonical (`cmd-k`)
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
    """Parse `frontend/src/App.tsx` for `combo: '<x>'` strings.

    For each `combo:` match, look at a ±200-char window around the
    match for `meta:\\s*true` — if present, the combo is canonicalized
    as `cmd-<key>`. Window-based pairing tolerates nested braces in
    handler arrow-function bodies that a strict object-literal regex
    can't (TS handler bodies introduce inner `{}` blocks).
    """
    text = APP_TSX.read_text(encoding="utf-8")
    out: list[str] = []
    for combo_match in re.finditer(r"combo:\s*['\"]([^'\"]+)['\"]", text):
        combo = combo_match.group(1)
        start = max(0, combo_match.start() - 200)
        end = min(len(text), combo_match.end() + 200)
        window = text[start:end]
        if re.search(r"meta:\s*true", window) and len(combo) == 1:
            out.append(f"cmd-{combo.lower()}")
        else:
            out.append(combo)
    return out


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


# ---------------------------------------------------------------------------
# FP28 E1 — INI refresh trust-model ADR + design.md § 6.7 cross-link
# ---------------------------------------------------------------------------

ADR_PATH = REPO_ROOT / "docs" / "decisions" / "0004-ini-refresh-trust-model.md"
ADR_BASENAME = "0004-ini-refresh-trust-model"


def test_ini_refresh_trust_model_adr_exists() -> None:
    """FP28 E1a — ``docs/decisions/0004-ini-refresh-trust-model.md`` must exist post-fix.

    Pre-fix: file is absent → ``ADR_PATH.is_file()`` returns False → assertion fails.
    Post-fix: ADR drafted with wizard-vs-refresh split + current trust posture
    + post-v1 hardening path; required substrings present.

    See ``docs/specs/FP28.md`` § E1.
    """
    assert ADR_PATH.is_file(), (
        f"FP28 E1a — expected ADR at {ADR_PATH} (not found). See `docs/specs/FP28.md` § E1."
    )
    body = ADR_PATH.read_text(encoding="utf-8")
    for needle in ("wizard", "refresh", "sha256"):
        assert needle in body.lower(), (
            f"FP28 E1a — ADR body must mention '{needle}' (wizard-vs-refresh "
            f"split + trust posture); see `docs/specs/FP28.md` § E1."
        )


def test_design_spec_section_6_7_cross_links_trust_model_adr() -> None:
    """FP28 E1b — design.md § 6.7 must cross-link the FP28 E1 ADR by basename.

    The locator is heading-text-anchored (not line-number) so future edits to
    earlier sections don't break the test.

    Pre-fix: § 6.7 body has no reference to ``0004-ini-refresh-trust-model``.
    Post-fix: a one-line "See ADR-0004 for the runtime refresh trust model."
    sits within § 6.7.

    See ``docs/specs/FP28.md`` § E1.
    """
    text = DESIGN_SPEC.read_text(encoding="utf-8")
    section_pattern = re.compile(
        r"^### 6\.7 `updates/`.*?(?=^### |^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = section_pattern.search(text)
    assert match is not None, (
        f"FP28 E1b — could not locate `### 6.7 \\`updates/\\`...` section in "
        f"{DESIGN_SPEC!s}; spec author may have renamed it."
    )
    section_body = match.group(0)
    assert ADR_BASENAME in section_body, (
        f"FP28 E1b — design.md § 6.7 body must cross-link {ADR_BASENAME!r}; "
        f"see `docs/specs/FP28.md` § E1."
    )

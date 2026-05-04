# MAME Curator — Audit allowlist

> **Status:** Empty until first confirmed false positive.
> **Bar for entry:** high — every entry requires written
> reasoning. Future audits re-verify the suppression is still
> warranted.
> **Scope:** project-specific.

This file is the **closed-loop memory** for `/audit` and
`/indie-review` false positives. Without it, the same false
positive gets surfaced and dismissed every audit run, burning
tokens and tempting "skip without thinking" reflexes.

The
[app-workflow skill](~/.claude/skills/app-workflow/SKILL.md)
reads this file **before** triaging audit findings, so
already-confirmed false positives are discarded without
re-evaluating.


## How entries are added

When `/audit` or `/indie-review` produces a finding F that
triage classifies as a tool false positive (verified, not just
dismissed):

1. Add an entry to this file with the rule, location,
   reasoning, date, and confirming phase.
2. Apply a tool-level suppression where the toolchain supports
   it — `# noqa: <RULE>` for ruff, `# nosec BNNN  # <reason>`
   for bandit (the project's coding-standards § 1 already
   requires the inline reason on bandit suppressions) — and
   cite this allowlist entry by number in the suppression
   comment.
3. Log the false positive inline in the active phase's
   `docs/journal/<ID>.md`.


## How entries are revoked

If a previously-allowlisted finding turns out to be a real
issue:

1. Update the entry's `Status:` to `revoked YYYY-MM-DD` with
   reasoning.
2. Remove the tool-level suppression in code.
3. Fold the finding into the next fix-pass like any actionable
   issue.

Do not delete revoked entries — the history is the value.


## Format

```markdown
## allowlist-NNN — <rule>:<location> short summary

- **Status:** active | revoked YYYY-MM-DD (<reason>)
- **Tool / rule:** e.g. ruff:S301, bandit:B410, indie-review:R-7
- **Location:** file:line, or finding signature
- **Why this is a false positive:** one paragraph. Be specific.
- **Suppression applied:** none | inline (cite syntax used)
- **Logged:** YYYY-MM-DD
- **Confirmed by phase:** P##/FP##/etc.
```


## Entries


## allowlist-001 — indie-review:`_preferred_score` substring vs fnmatch

- **Status:** active
- **Tool / rule:** indie-review (pre-P03 sweep round 3, 2026-04-27); also flaggable by readers comparing against `drop_*` rules.
- **Location:** `src/mame_curator/filter/picker.py:61-67` (`_preferred_score`).
- **Why this is a false positive:** the picker's `_preferred_score`
  intentionally uses substring (`patterns in name.lower()`) rather than
  `fnmatch`. The project's filter spec pins this as an intentional
  asymmetry against `drop_*` rules (which do use `fnmatch`): preferred
  scoring is a soft, descriptive boost ("does the name *contain* the
  preferred token") whereas drop predicates are strict pattern matches
  ("does the name match this glob"). The intent comment lives at
  `picker.py:64-65`. Future audits should pre-discard this finding.
- **Suppression applied:** none (no inline marker; this allowlist entry
  IS the suppression mechanism for design-intent false positives).
- **Logged:** 2026-05-01
- **Confirmed by phase:** DS01.


## allowlist-002 — eslint `react-hooks/incompatible-library` on `useVirtualizer`

- **Status:** active
- **Tool / rule:** eslint `react-hooks/incompatible-library` (FP11 closing /audit, 2026-05-02).
- **Location:** `frontend/src/components/library/LibraryGrid.tsx:35` (`useVirtualizer({ ... })`).
- **Why this is a false positive:** the lint rule warns that `@tanstack/react-virtual`'s `useVirtualizer` returns functions that cannot be safely memoized by the React Compiler. This is documented and intentional behaviour of the library — every grid + list virtualizer has the same shape (the returned `getVirtualItems()` is intentionally non-stable so consumers re-render on scroll). The warning is a generic library-compat advisory, not a project-level defect; the spec mandates `@tanstack/react-virtual` (P06.md § Toolchain).
- **Suppression applied:** none — the rule emits only a `warning`, not an `error`, and is correct to surface as a project-onboarding hint. Future contributors who pipe values from the virtualizer through a `useMemo`-d child should heed the warning; the audit-fold check should pre-discard it.
- **Logged:** 2026-05-02
- **Confirmed by phase:** FP11.


## allowlist-003 — eslint `react-refresh/only-export-components` on shadcn-generated UI primitives

- **Status:** active
- **Tool / rule:** eslint `react-refresh/only-export-components` (FP11 closing /audit, 2026-05-02).
- **Location:** `frontend/src/components/ui/button.tsx:64`, `frontend/src/components/ui/tabs.tsx:89`.
- **Why this is a false positive:** these files are generated verbatim by `npx shadcn add` and ship with both the React component AND a sibling `cva()` variants helper or sub-component constant. The Fast-Refresh-only-components rule fires because of the non-component co-export. The project does not author these files — they are vendored as-is per shadcn's distribution model — so refactoring them to satisfy the lint rule diverges from the upstream registry and breaks the next `shadcn add`'s diff. Project-authored files MUST follow the rule; shadcn-generated files in `src/components/ui/` are exempt by virtue of being vendored.
- **Suppression applied:** none — the lint rule's noise on vendored output is the cost of using shadcn; this allowlist entry IS the suppression mechanism.
- **Logged:** 2026-05-02
- **Confirmed by phase:** FP11.


## allowlist-004 — semgrep `dangerouslySetInnerHTML` on FP16 § D DOMPurify-sanitized HelpPage render

- **Status:** active
- **Tool / rule:** semgrep `dangerouslySetInnerHTML from non-constant definition` (ants-audit v0.7.77, 2026-05-04).
- **Location:** `frontend/src/pages/HelpPage.tsx:72`.
- **Why this is a false positive:** the value passed to `dangerouslySetInnerHTML` is `sanitizedHtml`, defined two lines above as `useMemo(() => DOMPurify.sanitize(topicHtml), [topicHtml])`. FP16 § D added DOMPurify@3.4 specifically to close the FP11 § H4 security debt this rule re-flags; tests cover `<script>` strip and `javascript:` URL strip (`HelpPage.test.tsx`). Semgrep's structural pattern can't see through the useMemo + DOMPurify chain. Migrating to react-markdown would also clear the rule but adds dependency churn for the same security guarantee.
- **Suppression applied:** none — the runtime DOMPurify call IS the suppression. This allowlist entry documents that the project's mitigation is in place.
- **Logged:** 2026-05-04
- **Confirmed by phase:** FP19 audit-triage.


## allowlist-005 — grep "Weak Cryptography" on `sha1` field used as MAME ROM identifier

- **Status:** active
- **Tool / rule:** generic grep "weak cryptography" pattern (ants-audit v0.7.77, 2026-05-04).
- **Location:** `src/mame_curator/parser/models.py:26` (`sha1: str | None`), `frontend/src/api/types.ts:81/89` (mirroring schema).
- **Why this is a false positive:** the `sha1` field carries the canonical SHA-1 hash MAME embeds in every DAT entry to identify ROM dumps. Every MAME-ecosystem tool — ClrMamePro, RomVault, Pleasuredome DATs, libretro-thumbnails URL keys — uses SHA-1 the same way. It is **not** used for authentication, password hashing, signing, or any security boundary; it's a content-hash for ROM-set verification. Switching to SHA-256 would break interop with the entire ecosystem since DATs ship SHA-1.
- **Suppression applied:** none — the field name `sha1` is the file-format contract; renaming it would break parsing.
- **Logged:** 2026-05-04
- **Confirmed by phase:** FP19 audit-triage.


## allowlist-006 — grep "Debug / Temp Code (print)" in `tools/check_api_types_sync.py`

- **Status:** active
- **Tool / rule:** generic grep "Debug / Temp Code" — print() statement detection (ants-audit v0.7.77, 2026-05-04).
- **Location:** `tools/check_api_types_sync.py:281, 288, 290`.
- **Why this is a false positive:** the project rule "print() is forbidden outside cli/" scopes RUNTIME code (where `print` bypasses the structured logging layer). `tools/` is a developer-tooling directory whose scripts are CLI-shaped utilities run from the terminal — same role as `cli/`, just lives at a separate path because it's not part of the shipped wheel. `tools/check_api_types_sync.py` is the CI-time API-types-drift gate; its prints go to stdout (success line) and stderr (per-finding line via `file=sys.stderr`) by design. The script's role IS to print to humans.
- **Suppression applied:** none — this allowlist entry IS the suppression. If `tools/` ever houses runtime code, the entry should be revoked.
- **Logged:** 2026-05-04
- **Confirmed by phase:** FP19 audit-triage.


## allowlist-007 — grep "Test-Health (skipped)" on `pytest.mark.skipif sys.platform == "win32"`

- **Status:** active
- **Tool / rule:** generic grep "Test-Health (skipped / disabled / only)" (ants-audit v0.7.77, 2026-05-04).
- **Location:** `tests/api/test_fp09_fixes.py:284`.
- **Why this is a false positive:** the skip is a documented cross-platform conditional — Windows doesn't support `fsync(dir_fd)`, and `_atomic.atomic_write_bytes` short-circuits the parent-dir fsync on `OSError` for that exact reason. The test verifies the file fsync count remains ≥1 on POSIX where the dir fsync DOES work; running it on Windows would assert against a code path that doesn't exist there. The `reason=` argument cites the constraint directly. This is the correct shape for a platform-conditional regression test.
- **Suppression applied:** none — `pytest.mark.skipif(...)` with a `reason=` is the canonical mechanism the audit rule should respect.
- **Logged:** 2026-05-04
- **Confirmed by phase:** FP19 audit-triage.


## What does NOT belong here

- **Findings that are real but blocked by a missing feature.**
  Those go in `docs/known-issues.md`.
- **Findings the user wants to defer.** No deferral disposition
  exists outside of "blocked by dependency" — every actionable
  finding becomes a fix-pass.
- **Findings the user accepts as a permanent trade-off.**
  Those become an ADR in `docs/decisions/`.

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


## What does NOT belong here

- **Findings that are real but blocked by a missing feature.**
  Those go in `docs/known-issues.md`.
- **Findings the user wants to defer.** No deferral disposition
  exists outside of "blocked by dependency" — every actionable
  finding becomes a fix-pass.
- **Findings the user accepts as a permanent trade-off.**
  Those become an ADR in `docs/decisions/`.

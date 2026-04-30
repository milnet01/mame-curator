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

(none yet — numbered sequentially as added; numbers never
reused, including for revoked entries)


## What does NOT belong here

- **Findings that are real but blocked by a missing feature.**
  Those go in `docs/known-issues.md`.
- **Findings the user wants to defer.** No deferral disposition
  exists outside of "blocked by dependency" — every actionable
  finding becomes a fix-pass.
- **Findings the user accepts as a permanent trade-off.**
  Those become an ADR in `docs/decisions/`.

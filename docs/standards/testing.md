<!-- ants-test-standards: 1 (redirect) -->
# Testing Standards — MAME Curator

This file is a **redirect pointer** for the
[`app-workflow` skill](~/.claude/skills/app-workflow/SKILL.md).
The canonical rules live in the consolidated
[`coding-standards.md`](coding-standards.md), §§ 6-7.

## Sections this slot covers

| `coding-standards.md` § | Topic |
|-------------------------|-------|
| §6 | Testing — TDD policy, coverage targets per module (parser ≥90%, filter ≥95%, copy ≥85%, api ≥80%, frontend ≥70%, overall ≥85%), test types (unit / integration / API smoke / E2E), property tests for the rule chain, no live-network tests, snapshot tests for curated output |
| §7 | Specs and feature audits — every feature ships `spec.md` next to its code; spec is the audit surface; tests enforce every clause; spec template |

## TDD reminder (most-load-bearing)

From §6: **TDD is the default for non-trivial logic.** Write a
failing test, write the minimum code to pass, refactor.

From §7: **No feature merges without its `spec.md`.** Existing
specs at `src/mame_curator/{cli,parser,filter}/spec.md`;
upcoming P03+ phases each add one for their module.

## Governs

ROADMAP bullets with `Kind: test`, plus the regression-test
follow-through for `fix`, `audit-fix`, and `review-fix`.

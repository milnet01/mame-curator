<!-- ants-coding-standards: 1 (redirect) -->
# Coding Standards — MAME Curator

This file is a **redirect pointer** for the
[`app-workflow` skill](~/.claude/skills/app-workflow/SKILL.md).
The canonical rules live in the consolidated
[`coding-standards.md`](coding-standards.md), §§ 0-5, 9-11, 13-15.

Read the consolidated file directly — its rule precedence
(§15: lower-numbered section wins) depends on its single-file
ordering and cannot be reproduced across separate files. The
slot files exist so the workflow skill's auto-loaders find
each governance domain at its expected path.

## Sections this slot covers

When the workflow skill or a subagent loads `coding.md`, it
should read these sections of `coding-standards.md`:

| `coding-standards.md` § | Topic |
|-------------------------|-------|
| §0 | Guiding principles (correctness, shortest correct, reuse, no workarounds, six-month test) |
| §1 | Security (every rule) |
| §2 | Project structure & file size (300/500 line caps, function size) |
| §3 | Python language & style (3.12+, type hints, mypy strict, no globals) |
| §4 | Frontend (React 19 + Tailwind v4 + shadcn/ui, accessibility) |
| §5 | Comments and documentation (default no comments) |
| §9 | Errors, logging, observability (actionable messages, typed exceptions) |
| §10 | Performance (profile first, streaming, lazy-load) |
| §11 | Code ordering & flow (layer order, no cycles) |
| §13 | Frontend-specific quality |
| §14 | Things to NOT do |
| §15 | Conflict precedence rule |

## Governs

ROADMAP bullets with `Kind: implement`, `fix`, `refactor`,
`audit-fix`, or `review-fix`.

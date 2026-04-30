<!-- ants-doc-standards: 1 (redirect) -->
# Documentation Standards — MAME Curator

This file is a **redirect pointer** for the
[`app-workflow` skill](~/.claude/skills/app-workflow/SKILL.md).
The canonical rules live in the consolidated
[`coding-standards.md`](coding-standards.md), §§ 5 and 7, plus
the dedicated [`roadmap-format.md`](roadmap-format.md) sub-spec
for `ROADMAP.md` and `CHANGELOG.md` authoring.

## Sections this slot covers

| `coding-standards.md` § | Topic |
|-------------------------|-------|
| §5 | Comments and documentation — default no comments; module docstrings required; public-function docstrings when non-obvious preconditions / side effects / API layer; no multi-paragraph docstrings; TODO/FIXME format |
| §7 | Specs and feature audits — every feature ships `spec.md`; spec template |

## Project-specific layout

| Doc | Purpose |
|-----|---------|
| `README.md` | Project front page; install + quickstart |
| `CLAUDE.md` | Claude Code session instructions; resumption flow |
| `CHANGELOG.md` | Keep-a-Changelog format; `[Unreleased]` always at top |
| `ROADMAP.md` | Queue summary; points to long-form phase plan |
| `docs/superpowers/specs/2026-04-27-roadmap.md` | Long-form authoritative phase plan (Phase 0–9) |
| `docs/superpowers/specs/2026-04-27-mame-curator-design.md` | Long-form design spec (architecture, data shapes, routes) |
| `docs/standards/coding-standards.md` | All enforceable rules, single ordered document |
| `docs/decisions/<NNNN>-<slug>.md` | ADRs for non-obvious choices |
| `docs/journal/<P##>.md` | Per-phase journal entry — what shipped, what was learned |
| `docs/glossary.md` | Domain + workflow vocabulary |
| `docs/known-issues.md` | Findings deferred until a named dependency lands |
| `docs/audit-allowlist.md` | Closed-loop memory for confirmed false positives |
| `docs/ideas.md` | Mid-flight user-proposed ideas, pending placement decision |
| `docs/specs/<ID>.md` | Per-roadmap-item spec (lazy — written at Step 1 of the per-item loop) |
| `src/mame_curator/<module>/spec.md` | Per-module feature contract; the audit surface for that module |

## Governs

ROADMAP bullets with `Kind: doc` or `doc-fix`.

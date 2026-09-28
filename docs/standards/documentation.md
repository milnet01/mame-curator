<!-- ants-doc-standards: 1 (redirect) -->
<!-- OWNED-HERE documentation.md — slot pointer into this project's own coding-standards.md, read instead of the global documentation.md; decided 2026-09-27 (mame-curator-1113) -->
# Documentation Standards — MAME Curator

This file is a **redirect pointer**, read in place of the global
standard of the same name (see the OWNED-HERE marker above).
The canonical rules live in the consolidated
[`coding-standards.md`](coding-standards.md), §§ 5 and 7.
`ROADMAP.md` and `CHANGELOG.md` follow the global
`~/.claude/standards/roadmap-format.md`, read in place.

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
| `docs/plans/phase-plan.md` | Long-form authoritative phase plan (Phase 0–9) |
| `docs/design.md` | Long-form design spec (architecture, data shapes, routes) |
| `docs/standards/coding-standards.md` | All enforceable rules, single ordered document |
| `docs/decisions/<NNNN>-<slug>.md` | ADRs for non-obvious choices |
| `docs/journal/<P##>.md` | Per-phase journal entry — what shipped, what was learned |
| `docs/glossary.md` | Domain + workflow vocabulary |
| `docs/known-issues.md` | Findings deferred until a named dependency lands |
| `docs/audit-allowlist.md` | Closed-loop memory for confirmed false positives |
| `docs/ideas.md` | Mid-flight user-proposed ideas, pending placement decision |
| `docs/specs/<ID>-<topic>.md` | Per-roadmap-item spec (lazy — written at Step 1 of the per-item loop). Format: the global `~/.claude/standards/spec-format.md` plus [`spec-format-overrides.md`](spec-format-overrides.md). |
| `docs/plans/<ID>-<topic>.md` | Build steps for that item. `phase-plan.md` is the pre-existing long-form Phase 0–9 plan and has no single id. |
| `src/mame_curator/<module>/spec.md` | Per-module feature contract; the audit surface for that module |

## Governs

ROADMAP bullets with `Kind: doc` or `doc-fix`.

<!-- ants-commit-standards: 1 (redirect) -->
# Commit Standards — MAME Curator

This file is a **redirect pointer** for the
[`app-workflow` skill](~/.claude/skills/app-workflow/SKILL.md).
The canonical rules live in the consolidated
[`coding-standards.md`](coding-standards.md), § 12.

## Sections this slot covers

| `coding-standards.md` § | Topic |
|-------------------------|-------|
| §12 | Git, commits, and CI — Conventional Commits, semver, branches (`main` always green), CI matrix (lint / types / test / security), pre-commit hooks, no `--no-verify`, releases gate on green CI |

## Project-specific note on commit-subject ID prefix

The App-Build standard `commits.md` § 1.1 mandates
`<ID>: <description>` subjects (e.g. `MC-1042: implement live
search`). MAME Curator currently uses **Conventional Commits**
(`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`,
`perf:`, `ci:`) — see git log for examples like
`feat(filter): phase A drop predicates with one test per rule`.

This is a deliberate deviation: the project has 100+ existing
commits in Conventional Commits format, and per
`coding-standards.md` § 12 the convention stays. New work uses
Conventional Commits. When the App-Build phase ID is relevant
(closing a phase, citing a fix-pass), include it in the body
or scope. Real examples from `git log`:

- Phase-shipping commits: scope identifies the module, subject
  names the phase explicitly:
  `feat(filter): run_filter orchestrator with overrides and session-slice`
  `feat(parser): parse_listxml_cloneof for parent/clone reconstruction`
- Phase-closing landmarks: a `docs(roadmap)` commit ticking the
  acceptance criteria — the actual close marker:
  `docs(roadmap): tick Phase 2 acceptance — pass-3 Tier 1 findings closed`
- Fix-pass commits: cite the pass and tier in the subject:
  `fix(filter): pass-3 Tier 1 — wire drop_bios_devices_mechanical config field`
  `fix(filter): pass-3 C1 — picker uses functools.cmp_to_key per spec line 55`
- Roadmap-item commits when stable IDs are assigned (`mame-curator-NNNN`):
  cite in the body trailer: `Refs: mame-curator-1042`

Per-bullet stable IDs from `.roadmap-counter` are assigned
**lazily** (only when an item really needs cross-referenced
identity — typically multi-commit features or fix-passes). New
P##/FP##/DS##/DOC## phase IDs use the convention from
`docs/standards/roadmap-format.md`.

## Governs

Every commit, plus release-orchestration work
(`Kind: chore` / `release`).

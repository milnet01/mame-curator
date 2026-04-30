# Project Standards — MAME Curator

This project's enforceable rules live in **one consolidated
document**: [`coding-standards.md`](coding-standards.md). It
covers everything the four-file App-Build slot pattern usually
splits into: code style, security, project structure, testing,
spec format, deps, errors, performance, code ordering, git
conventions, frontend quality, anti-patterns, and the conflict-
precedence rule (§15).

The slot files in this folder
(`coding.md`, `testing.md`, `commits.md`, `documentation.md`,
`roadmap-format.md`) are **redirect pointers** to the relevant
sections of the consolidated document — they exist so the
[`app-workflow` skill](~/.claude/skills/app-workflow/SKILL.md)
auto-loaders find each governance domain at its expected path,
without fragmenting the rules.

## Why one consolidated file

`coding-standards.md` § 15 says: "When two standards in this
document appear to conflict, the one earlier in this document
wins (lower-numbered section is more fundamental)." That
precedence rule is **load-bearing** for resolving real-world
conflicts (e.g. a security rule beats a performance rule). It
only works if the rules live in one ordered file. Splitting
them across four files would break the precedence ordering.

The slot files preserve App-Build's automation-friendly layout
without breaking that ordering.

## Slot-file index

| Slot file | Redirects to (sections in `coding-standards.md`) | Governs |
|-----------|--------------------------------------------------|---------|
| [`coding.md`](coding.md) | §0 Principles, §1 Security, §2 Project structure, §3 Python, §4 Frontend, §5 Comments, §9 Errors, §10 Performance, §11 Ordering, §13 Frontend quality, §14 Anti-patterns | `Kind: implement / fix / refactor / audit-fix / review-fix` |
| [`testing.md`](testing.md) | §6 Testing, §7 Specs and feature audits | `Kind: test`; regression-test follow-through for fixes |
| [`commits.md`](commits.md) | §12 Git, commits, and CI | Every commit |
| [`documentation.md`](documentation.md) | §5 Comments and documentation, §7 Specs | `Kind: doc / doc-fix` |
| [`roadmap-format.md`](roadmap-format.md) | App-Build's standard `roadmap-format.md` v1, copied verbatim | `ROADMAP.md` and `CHANGELOG.md` authoring |

## Editing rules

- **Edit `coding-standards.md`**, not the slot files. The slots
  are pointers; editing them creates drift.
- **Exception:** `roadmap-format.md` is shipped as a verbatim
  copy of the App-Build template (the format spec is
  cross-project shared, not MAME-Curator-specific). Edits to
  it should track upstream template revisions.
- **Adding a new section to `coding-standards.md`?** If it falls
  under a new governance domain (e.g. localisation), update the
  slot index above so the relevant slot file's redirect covers
  it.

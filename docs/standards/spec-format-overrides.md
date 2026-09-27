# Spec-format overrides — MAME Curator

Deltas from the global spec standard, `~/.claude/standards/spec-format.md`,
read in place. Readers take the global file plus this one; where the two
differ, this file wins for work in this repo. New specs and plans start from
the global skeletons in `~/.claude/standards/skeletons/`.

Until 2026-09-27 this repo carried a full v1 copy of the standard with these
deltas at its foot. mame-curator-1113 extracted them here and deleted the
copy. The numbering is kept so older references stay stable.

**O1 — retired 2026-09-26.** It exempted sixteen legacy specs named
bare `<ID>.md`. mame-curator-1092 renamed them to `<ID>-<topic>.md`, so
§2 now holds for every file in `docs/specs/`.

**O2 — phase ids, not `<PREFIX>-NNNN`, on the older specs.** This project
predates the counter-allocated id scheme: its specs and journals key on
phase ids (`P##`), fix-passes (`FP##`) and doc sweeps (`DS##`), while the
roadmap allocates `mame-curator-NNNN`. Both are stable ids and both link a
spec to its item; §2 should be read as "the id the roadmap bullet carries".

**O3 — commits do not use the `<ID>: <description>` subject.** This project
uses Conventional Commits and cites the id in the scope or body; see
`docs/standards/commits.md`. Where §6 or the skeleton implies the
App-Build subject form, the project standard wins.

**O4 — the co-located module contract is NOT governed by this standard.**
`src/mame_curator/<module>/spec.md` is the per-module audit surface owned
by `coding-standards.md` §7 — one per shipped module, enforced by its test
file, and required for a feature to merge. It has a different shape and a
different lifecycle from a `docs/specs/` item contract. A fix-pass
(`FP##` / `DS##`) corrects code against an existing module spec and needs
no `docs/specs/` entry of its own, though the larger multi-tier ones
(FP05, FP27, FP28, DS01–DS05) have carried one and their journals credit it
with catching drift before implementation.

## What checks this

| Override | What catches a breach |
|----------|----------------------|
| O2 | **nothing mechanical** — a cold reader |
| O3 | **nothing mechanical** — commit subjects are not linted |
| O4 | `tests/` enforces each module `spec.md` clause-by-clause; that is the check `coding-standards.md` §7 refers to |

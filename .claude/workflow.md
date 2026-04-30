# MAME Curator — Workflow state

## §1. Status header

| Field | Value |
|-------|-------|
| **Project phase** | P03 — Copy, BIOS resolution, RetroArch playlist (next) |
| **Active item ID** | (none — P02 closed; P03 not yet started) |
| **Active step** | (resets to all ⬜ when P03 becomes active) |
| **Blocked on** | — |
| **Last update** | 2026-04-30 (App-Build alignment) |
| **Next gate** | User says "let's start P03" (or equivalent) |
| **Convergence checkpoint** | 5 (pause and check in with user after this many fix-passes in a row) |
| **Debt-sweep phase threshold** | 5 (auto-prompt for `/debt-sweep` after this many phases without one) |
| **Last debt sweep** | (none yet) |
| **Repo visibility** | PUBLIC (cached 2026-04-30 via `gh repo view --json visibility`) |

### Step progress

While an item is active, Claude marks the current step 🚧;
completed steps flip to ✅. Resets to all ⬜ when a new item
becomes active.

1. ⬜ Verify spec (research first if non-trivial)
2. ⬜ Verify dependencies on the roadmap DAG
3. ⬜ Write failing tests
4. ⬜ Implement until tests pass
5. ⬜ Run `/audit` (read `docs/audit-allowlist.md` first)
6. ⬜ Run `/indie-review` (same allowlist read)
7. ⬜ Fold actionable findings → new FP## roadmap item
8. ⬜ Update CHANGELOG / ROADMAP / journal
9. ⬜ Commit, tag `<ID>-complete`, ask user about push

### Active item details

(filled in once P03 becomes active)

```
Item: P03 — Copy, BIOS resolution, RetroArch playlist
Spec: src/mame_curator/copy/spec.md (to be written at Step 1)
Branch: main (no feature branch yet — solo development)
Sub-findings: (none)
Tests: (none yet — Step 3 writes them)
```

### Phase history (App-Build mapping)

The project predates App-Build conventions. Existing phases map
1:1 to App-Build P## IDs:

| App-Build ID | Original label | Status | Theme |
|--------------|---------------|--------|-------|
| P00 | Phase 0 | ✅ closed 2026-04-27 | Scaffold + tooling + CI |
| P01 | Phase 1 | ✅ closed 2026-04-27 | DAT + INI parsers (`parser/`) |
| P02 | Phase 2 | ✅ closed 2026-04-27 | Filter rule chain (`filter/`) |
| P03 | Phase 3 | 📋 next | Copy + BIOS + `.lpl` (`copy/`) |
| P04 | Phase 4 | 📋 | HTTP API (`api/`) |
| P05 | Phase 5 | 📋 | Media subsystem (`media/`) |
| P06 | Phase 6 | 📋 | Frontend MVP |
| P07 | Phase 7 | 📋 | Self-update + help (`updates/`, `help/`) |
| P08 | Phase 8 | 📋 | Setup wizard (`setup/`) |
| P09 | Phase 9 | 📋 | Polish + v1.0.0 release |

The detailed per-phase contract for every phase still lives at
`docs/superpowers/specs/2026-04-27-roadmap.md` — that file is the
long-form authoritative phase plan. `ROADMAP.md` at the root is
the queue summary.

## §2. Workflow rules

The canonical rules — phases A–D, the per-phase 9-step loop,
ID scheme, triage table, fold-into-roadmap pattern,
false-positive learning loop, drift handling, Definition of
Done — live in
`~/.claude/skills/app-workflow/SKILL.md`.
The skill auto-loads when this file is present in the
project, so reading SKILL.md is the way to access the rules
in any session.

**Hard rule kept inline (most-load-bearing):** never silently
drift. If code being written diverges from the spec, stop and
surface. Either the spec was wrong (update spec → re-audit
affected sections → resume) or the code was wrong (fix code,
no spec change). Never both papered-over.

To refresh this file from the (upgraded) skill template, copy
`~/.claude/skills/app-workflow/templates/.claude/workflow.md`
over this file — preserve §1 (status header) and §3 (session
journal); §2 is the only part that changes.

## §3. Session journal

Append-only. Newest at the top.

### 2026-04-30 — App-Build alignment

Project retrofitted to align with the Ants App-Build workflow.
Phase 0–2 (already shipped) mapped to P00–P02. Added the
state-tracking surface (`.claude/workflow.md`,
`.claude/settings.json`), the four-standards slot files at
`docs/standards/{coding,testing,commits,documentation,roadmap-format}.md`
(redirecting to the consolidated `coding-standards.md` which
remains the canonical document), `ROADMAP.md` at root,
`docs/decisions/` with three retroactive ADRs (`0001-record-architecture-decisions`,
`0002-cloneof-from-listxml`, `0003-listxml-tiered-acquisition`),
`docs/journal/{P00,P01,P02}.md` capturing what shipped in each,
and the supporting docs (`glossary`, `known-issues`,
`audit-allowlist`, `ideas`).

Existing per-module specs (`src/mame_curator/{cli,parser,filter}/spec.md`)
remain the per-feature audit surface — they already meet
App-Build's spec-as-contract requirement.

`docs/superpowers/specs/2026-04-27-{roadmap,mame-curator-design}.md`
remain the long-form authoritative phase plan and design spec
respectively; the new `ROADMAP.md` at root is the queue summary
that points to them.

Next: P03 — `copy/` spec, tests, implementation per the per-phase
9-step loop.

### 2026-04-27 — Phase 2 closed

Pass-3 indie-review surfaced two CRITICAL spec violations
(picker not using `cmp_to_key`, CLI dispatch not using
`set_defaults(func=)`) and one HIGH zombie field
(`drop_bios_devices_mechanical` declared but never honoured).
All three closed; 158 tests pass, filter coverage 96%+.
Tier 2/3 findings logged in CHANGELOG `[Unreleased]` per the
project's CHANGELOG-as-sweep-log convention.

### 2026-04-27 — Phase 1 closed

DAT + 5 INI parsers + listxml CHD detector + cloneof map +
manufacturer split. CLI smoke `mame-curator parse` ships.

### 2026-04-27 — Phase 0 closed

`uv` + ruff + mypy + pytest + bandit configured; pre-commit
hooks installed; CI workflow committed; coverage gate at 85%
enforced.

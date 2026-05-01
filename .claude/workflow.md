# MAME Curator — Workflow state

## §1. Status header

| Field | Value |
|-------|-------|
| **Project phase** | P04 — HTTP API (next; planned) |
| **Active item ID** | (none — FP04 closed 2026-05-01, tag `FP04-complete` pushed) |
| **Active step** | (resets to all ⬜ when P04 becomes active) |
| **Blocked on** | — |
| **Last update** | 2026-05-01 (FP04 closed; parser hardening sweep — 6 OSError gaps + fd-leak window in `parser/dat.py` + `parser/listxml.py`; all queued fix-passes done; P04 next) |
| **Next gate** | User says "let's start P04" (or equivalent) |
| **Convergence checkpoint** | 5 (pause and check in with user after this many fix-passes in a row) |
| **Debt-sweep phase threshold** | 5 (auto-prompt for `/debt-sweep` after this many phases without one) |
| **Last debt sweep** | 2026-05-01 (scope `P02-complete..HEAD`; 4 rounds of cold-eyes spec review converged on 20 actionable sub-bullets — C9 retained as footnoted stale entry, D3 added during review; folded into DS01) |
| **Repo visibility** | PUBLIC (cached 2026-04-30 via `gh repo view --json visibility`) |

### Step progress

While an item is active, Claude marks the current step 🚧;
completed steps flip to ✅. Resets to all ⬜ when a new item
becomes active.

All steps reset to ⬜ until P04 becomes active.

1. ⬜ Verify spec — write `docs/specs/P04.md` (P## items get fresh specs; FP##/DS## items don't, per the specs-for-features rule)
2. ⬜ Verify dependencies on the roadmap DAG
3. ⬜ Write failing tests
4. ⬜ Implement until tests pass
5. ⬜ Run `/audit`
6. ⬜ Run `/indie-review`
7. ⬜ Fold actionable findings → new FP## roadmap item
8. ⬜ Update CHANGELOG / ROADMAP / journal
9. ⬜ Commit, tag `<ID>-complete`, ask user about push

### Active item details

(none — between phases. Five-fix-pass run DS01→FP05→FP06→FP07→FP08→FP04 closed all queued review-fix work; P04 is the next planned phase.)

### Phase history (App-Build mapping)

The project predates App-Build conventions. Existing phases map
1:1 to App-Build P## IDs:

Closure dates below are **commit-author dates** (when the work
shipped); `<ID>-complete` annotated tags are dated 2026-04-30
because the App-Build `<ID>-complete` tag convention was adopted
*at* the alignment commit and applied retroactively. P00 and P01
shared a single combined initial commit (`56449c6`) — there is no
separate "P01 closing commit"; the tag boundary between them is
nominal. Both tags point at `56449c6`.

| App-Build ID | Original label | Status | Shipped | Tagged | Theme |
|--------------|---------------|--------|---------|--------|-------|
| P00 | Phase 0 | ✅ | 2026-04-27 | 2026-04-30 (retro) | Scaffold + tooling + CI (combined ship with P01) |
| P01 | Phase 1 | ✅ | 2026-04-27 | 2026-04-30 (retro) | DAT + INI parsers (`parser/`) (combined ship with P00) |
| P02 | Phase 2 | ✅ | 2026-04-27 | 2026-04-30 (retro) | Filter rule chain (`filter/`) |
| DOC01 | — | ✅ | 2026-04-30 | 2026-04-30 | Documentation audit fold-in (Phase D) — 4 review rounds, 30 findings closed |
| P03 | Phase 3 | ✅ | 2026-04-30 | 2026-04-30 | Copy + BIOS + `.lpl` (`copy/`) |
| FP01 | — | ✅ | 2026-04-30 | 2026-04-30 | P03 indie-review fold-in (round-1 + round-2) |
| FP02 | — | ✅ | 2026-04-30 | 2026-04-30 | FP01 round-2 fold-in (9 items) + FP02 round-2 spec drift |
| DS01 | — | ✅ | 2026-05-01 | 2026-05-01 | Pre-P04 debt-sweep fold-in (20 actionable + 2 round-2 R1/R2; cold-eyes review pattern adopted at Step 1) |
| FP05 | — | ✅ | 2026-05-01 | 2026-05-01 | DS01 closing-review fold-in (20 actionable + R1-R6 round-2; B1+B4 reclassified after empirical investigation) |
| FP06 | — | ✅ | 2026-05-01 | 2026-05-01 | FP05 closing-review fold-in (7 findings: A1 purge_recycle OSError, B1-B3 sessions hardening, R1-R3 closing-review drift) |
| FP07 | — | ✅ | 2026-05-01 | 2026-05-01 | `cli/` + typed-error path-quoting sweep (5+1 sites; fix base classes once, covers ~10 raise sites) |
| FP08 | — | ✅ | 2026-05-01 | 2026-05-01 | `runner.py` warning path-quoting (1+1 sites; one-round cold-eyes converge) |
| FP04 | — | ✅ | 2026-05-01 | 2026-05-01 | Parser hardening sweep (6 sites: OSError gaps in `dat.py` + `listxml.py` + fd-leak window in `_resolve_xml`) |
| P04 | Phase 4 | 📋 | — | — | HTTP API (`api/`) |
| P05 | Phase 5 | 📋 | — | — | Media subsystem (`media/`) |
| P06 | Phase 6 | 📋 | — | — | Frontend MVP |
| P07 | Phase 7 | 📋 | — | — | Self-update + help (`updates/`, `help/`) |
| P08 | Phase 8 | 📋 | — | — | Setup wizard (`setup/`) |
| P09 | Phase 9 | 📋 | — | — | Polish + v1.0.0 release |

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

### 2026-05-01 — DS01 closed

DS01 (pre-P04 debt-sweep fold-in) closed: 20 actionable sub-bullets across 4 clusters (A: 5 copy/ spec+code drift; B: 4 test gaps; C: 8 filter+cli hardening; D: 3 record/allowlist) + 2 round-2 fix-pass-internal R1/R2 (filter/spec.md tuple-shape update; CLI atomic-write try/finally cleanup) closed inside DS01 per the FP02 precedent. 260 tests pass; coverage 94.67%; all five gates green.

**Major workflow addition**: cold-eyes spec review at Step 1, looped until clean. Round 1 → 4 substantive findings (C9 fully false; C2 read-sites incomplete; A1 third site missed; FP04 needed). Round 4 → 2 (count drift 22→20; FP## allocation deferred). Round 5 → clean. Saved as `feedback_cold_eyes_spec_review_at_step_1.md` for future projects. Without these rounds the implementation would have shipped a partly-fictional plan (C9 was a no-op finding; the count was wrong).

**Closing /audit + /indie-review**: tools clean; indie-review across 3 lanes returned 14+ findings in surrounding code → folded into FP05 (recycle_partial unimplemented, empty-string active footgun, MemoryError swallow narrowing, FilterContext mutability parallel to C2, BIOSResolutionWarning one-arm Literal, pause/cancel race window, TOCTOU stat/read, _cmd_copy asymmetry, etc.). DS01-internal drift (filter/spec.md not updated by C2; CLI atomic-write missed try/finally) closed in same fix-pass per FP02 precedent.

**Lesson saved**: every fix-pass's closing review on its own patches surfaces patch-introduced drift, not just leftover round-1 findings. FP02 caught FP02-shipped Tier-2 spec drift; DS01 caught DS01-shipped R1/R2 drift. Pattern holds; closing review is non-skippable.

**FP05 opened** with 14+ findings, **FP04 still queued** (parser hardening — 2 items deferred from DS01 cold-eyes review). Numerically FP04 < FP05 but FP05 has Tier-1 bugs and runs first in the queue. Numbers reflect creation-order; queue-position reflects priority.

### 2026-04-30 — FP02 closed

FP02 closed all 9 round-2 deferrals from FP01: 3 Tier-2 (`OverwriteRecord.parent` dropped; `AppendDecision` widened from `StrEnum` to a Pydantic model with `kind` + `replaces` so multi-conflict sessions steer to the right entry; recycle dirname keyed on `session_id` so cross-session same-second collisions are impossible) + 6 Tier-3 (spec typo `mid-copy3`; `_chd_missing` helper; `functools.partial` over `make_cb`; playlist filter to `SUCCEEDED` + `SKIPPED_IDEMPOTENT`; KI test extended to `progress=cb` branch; recycle 3+ collision test). 9 new tests in `tests/copy/test_fp02_fixes.py`; 241 tests pass project-wide; coverage 94.79%.

Closing `/audit` + `/indie-review` on the FP02 patches surfaced FP02's own spec drift: duplicate `AppendDecision` definition in `copy/spec.md` § CopyPlan; stale `recycle_file` docstring (`<timestamp>`); `test_recyclebin.py` docstring also stale; missing note about duplicate `replaces` being undefined behaviour. All folded into FP02 (DOC01 round-2 precedent — round-2 in same fix-pass when findings are spec-drift caused by the patches themselves). Pre-existing `except Exception` without `logger.exception()` deferred to a future debt-sweep, not in FP02 scope.

Lesson saved: every fix-pass needs a closing review on its own patches, not just on surrounding code. FP01 round-2 caught FP01-shipped Tier-2; FP02 closing review caught FP02-introduced spec drift. Both were caught by /audit + /indie-review running on the latest patches; the iteration converges quickly when the round-2 findings are documentation-only.

Architecture note: FP02 #2 (`AppendDecision.replaces`) compounds the FP01 #4 caller-side architecture. Runner is now strictly a "trusts the caller" layer — no heuristics, no `cloneof_map` reach-around. The CLI / API layer (P04+) is the natural home for cloneof-aware decision logic.

### 2026-04-30 — P03 + FP01 closed

P03 (`copy/` module) shipped: BIOS chain resolution, atomic copy primitive, RetroArch v6+ JSON playlist writer, project-internal recycle bin (no `send2trash` dep), pause/resume/cancel `CopyController`, `data/activity.jsonl` append-only log with discriminated-union event schema, `CopyReport` Pydantic model, CLI `mame-curator copy --dry-run / --apply / --purge-recycle`. 74 tests in `tests/copy/`, copy/ aggregate ~89%, project-wide 92.95%. All five CI gates green.

FP01 closed paired: indie-review on freshly-shipped P03 surfaced 6 Tier-1 real bugs that `/audit` missed (signature drift, `KeyboardInterrupt` cleanup, `OverwriteRecord` allocated-but-never-appended, `PlaylistError` design contradiction, broken recycle collision logic, `read_lpl` legacy claim without code). Round-1 closed all 6 Tier-1 + most Tier-2/3. Round-2 surfaced 5 fresh Tier-2 + 4 Tier-3; user-data-risk (B-T2-3 corrupt-playlist silent overwrite) closed in FP01; 15 remaining items deferred to FP02. Per App-Build's "every finding tracked" hard rule, deferred items live in ROADMAP § FP02.

Notable lesson: `/audit` and `/indie-review` are complementary. Auto tools catch the grammar; indie-review catches semantics. Both necessary; neither sufficient. Saved as a reference for future phase closes.

### 2026-04-30 — DOC01 closed (Phase D documentation audit)

Five-lane cold-eyes documentation review (standards consistency / workflow integration / spec ↔ architecture alignment / phase-history accuracy / discoverability). Four review rounds total: round 1 surfaced 27 findings (3 Tier-1 / 17 Tier-2 / 7 Tier-3), round 2 added 13 follow-on (2/7/4) catching round-1 patches that didn't propagate to sibling files, round 3 added 7 (1/3/3), round 4 came back clean across all touched lanes. 30+ documents updated; CLAUDE.md trimmed 232 → 102 lines via reflow + redundancy cull (per user feedback re: long lines in context-loaded docs — saved as feedback memory). All Tier-1 / Tier-2 / Tier-3 findings closed; allowlist remains empty (no false positives surfaced). Journal: `docs/journal/DOC01.md`.

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

<!-- ants-roadmap-format: 1 -->
# MAME Curator — Roadmap

> **Current version:** 0.0.0 (pre-alpha). See [CHANGELOG.md](CHANGELOG.md)
> for what's shipped; this file covers what's **planned**.
>
> **Format:** v1 — see
> [docs/standards/roadmap-format.md](docs/standards/roadmap-format.md).
>
> **Long-form authoritative phase plan:**
> [`docs/superpowers/specs/2026-04-27-roadmap.md`](docs/superpowers/specs/2026-04-27-roadmap.md)
> carries every phase's pre-conditions, tests-to-write-first list,
> ordered implementation steps, acceptance criteria, and out-of-scope
> list. **Read it before starting any phase.** This file is the
> **queue summary** that bridges App-Build's per-phase loop to that
> long-form plan.
>
> Stable per-bullet IDs (`mame-curator-NNNN`) are assigned **lazily**
> via `.roadmap-counter` — only for items that need cross-referenced
> identity (multi-commit features, fix-passes). Phase IDs (`P##`,
> `FP##`, `DS##`, `DOC##`) categorise blocks.

**Legend** (per `docs/standards/roadmap-format.md § 3.3`)

- ✅ Done (shipped)
- 🚧 In progress (being tackled now)
- 📋 Planned (next up)
- 💭 Considered (research phase; scope or feasibility uncertain)

**Themes** (per `docs/standards/roadmap-format.md § 3.4`)

- 🎨 Features · ⚡ Performance · 🔌 Plugins · 🖥 Platform
- 🔒 Security · 🧰 Dev experience · 📚 Documentation
- 📦 Packaging · 🐛 Bug fixes · 🔍 Findings fold-in
- 🧹 Cleanup / debt

---

## P00 — Scaffold and tooling (shipped 2026-04-27)

**Theme:** `uv` + ruff + mypy + pytest + bandit + pre-commit + CI
matrix. Coverage gate at 85% enforced.

### 🧰 Dev experience

- ✅ **P00 — scaffold + tooling baseline.** All five CI gates green
  on empty test suite. See `docs/journal/P00.md`.
  Kind: chore.
  Lanes: build, ci.

---

## P01 — DAT + INI parsers (shipped 2026-04-27)

**Theme:** pure-Python parser turning the user's DAT XML and the
five `.ini` reference files into typed in-memory data; CLI smoke
prints summary stats.

### 🎨 Features

- ✅ **P01 — `parser/` module shipped.** `parse_dat()` (lxml.iterparse
  on `.xml` / `.zip`), `parse_catver()`, `parse_languages()`,
  `parse_bestgames()`, `parse_mature()`, `parse_series()`,
  `parse_listxml_disks()`, `split_manufacturer()`. Coverage 90%+;
  `mame-curator parse` CLI smoke ships. See `docs/journal/P01.md`.
  Kind: implement.
  Lanes: parser, tests.

---

## P02 — Filter rule chain (shipped 2026-04-27)

**Theme:** deterministic curated set from parsed data — drop +
pick + override + session-slice rule chain, with a JSON report
CLI subcommand.

### 🎨 Features

- ✅ **P02 — `filter/` module shipped.** Phase A drops, Phase B
  tiebreakers (region, revision, tier, language, preferred boosts),
  Phase C overrides, Phase D session focus. `cmp_to_key` picker per
  spec line 55; `set_defaults(func=...)` CLI dispatch.
  Coverage 96%+; 158 tests; snapshot test on hand-picked 30-machine
  fixture; hypothesis property tests for determinism + idempotency.
  See `docs/journal/P02.md`.
  Kind: implement.
  Lanes: filter, parser, cli, tests.

### 🔍 Indie-review pass-3 fold-in (2026-04-27)

Tier 1 closed before P03 (the three sub-bullets below); Tier 2 / 3
findings tracked in CHANGELOG `[Unreleased]` per the project's
CHANGELOG-as-sweep-log convention.

- ✅ **CRITICAL — picker uses `functools.cmp_to_key`.** Was using a
  score-tuple + `max()` that made `sf2ce` win over `sf2` on alpha
  fallback. Fix pinned by
  `test_alphabetical_fallback_spec_lower_wins_with_prefix_collision`.
  Kind: review-fix. Source: indie-review-2026-04-27.
- ✅ **CRITICAL — CLI dispatch via `set_defaults(func=)`.**
  `cli/spec.md` updated to record migration as current contract.
  Kind: review-fix. Source: indie-review-2026-04-27.
- ✅ **HIGH — `drop_bios_devices_mechanical` config field wired.**
  Was zombie. Now honoured by Phase A predicates 1-3 with
  early-return when False. `filter/spec.md` updated.
  Kind: review-fix. Source: indie-review-2026-04-27.

---

## DOC01 — Phase D documentation audit fold-in (closed 2026-04-30)

**Theme:** five-lane cold-eyes documentation review (standards consistency / workflow integration / spec ↔ architecture alignment / phase-history accuracy / discoverability + onboarding). Round 1 batched 3 Tier-1 + 17 Tier-2 + 7 Tier-3 actionable findings (after deduplicating cross-lane overlaps and one Tier-1 demoted to Tier-3 on re-read). Round 2 surfaced 2 Tier-1 + 7 Tier-2 + 4 Tier-3 follow-on findings (mostly round-1 patches that did not propagate fully to sibling files). Fold-into-roadmap pattern per the [app-workflow skill](~/.claude/skills/app-workflow/SKILL.md). Closes when one re-review pass returns zero actionable findings.

### 🔍 Findings fold-in

#### Tier 1 — blockers

- ✅ **Long-form roadmap acceptance checkboxes for shipped
  phases left unticked.** Phase 0 (lines 72-80) and Phase 1
  (lines 129-133) of `docs/superpowers/specs/2026-04-27-roadmap.md`
  show every `[ ]` despite both phases shipping; Phase 2 is
  already ticked (the pattern). Tick all boxes citing the
  journal entries; reword Phase 0's mypy-vs-Ty box to match
  what actually shipped (`coding-standards.md` § 8 documents
  the Ty deferral).
  Kind: doc-fix.
  Lanes: docs.
  Source: indie-review-2026-04-30 lane 3.
- ✅ **Journal closing-commit citations are fabricated.** All
  three of `docs/journal/{P00,P01,P02}.md` cite commit subjects
  that do not exist in `git log`. P00 + P01 actually shipped
  in a single combined commit `56449c6 chore(scaffold):
  phase-0 tooling and CI baseline + phase-1 parser`. P02's
  closing landmark is `ee80a55 docs(roadmap): tick Phase 2
  acceptance — pass-3 Tier 1 findings closed`. Replace with
  real subjects + 7-char SHA prefixes; acknowledge P00 + P01
  shared a commit.
  Kind: doc-fix.
  Lanes: docs.
  Source: indie-review-2026-04-30 lane 4.
- ✅ **README front page misrepresents project status.**
  "What works today" table shows `2 — Filter` as `🔜 next`,
  but P02 shipped 2026-04-27. Flip P02 to `✅ done` with the
  filter-pipeline summary; advance the next-up indicator to
  `3 — Copy`.
  Kind: doc-fix.
  Lanes: docs, onboarding.
  Source: indie-review-2026-04-30 lane 5.

#### Tier 2 — should-fix

- ✅ **Standards slot `coding.md` omits §8 Dependencies and
  tooling.** No slot file claims §8, breaking the README slot
  index's coverage promise. Add §8 to the `coding.md` redirect
  table and to `docs/standards/README.md` slot index.
  Kind: doc-fix. Lanes: docs.
- ✅ **`docs/standards/roadmap-format.md` numbering jumps to
  §3 with no §1/§2.** File header also calls itself "verbatim"
  while body uses MAME-Curator-customised examples. Reword to
  "structure verbatim, examples customised" and add a one-line
  note about the upstream §§1-2.
  Kind: doc-fix. Lanes: docs.
- ✅ **Workflow.md phase-history closure dates are commit-author
  dates (2026-04-27); `<ID>-complete` tags are dated
  2026-04-30.** Clarify "shipped 2026-04-27, retroactively
  tagged 2026-04-30 at App-Build alignment commit."
  Kind: doc-fix. Lanes: docs.
- ✅ **CHANGELOG `[Unreleased]` policy unstated.** Project has
  shipped P00–P02 work but never tagged a `v0.0.X` release;
  current state is consistent with "stay on `[Unreleased]`
  until v1.0.0 (P09)" — but that policy isn't documented.
  Add an explanatory note at the top of `CHANGELOG.md`.
  Kind: doc-fix. Lanes: docs.
- ✅ **`filter/spec.md` says `winners: list[str]` and
  `contested_groups: list[ContestedGroup]`.** Code declares
  both as `tuple[...]` (frozen-by-default convention). Update
  the spec to match.
  Kind: doc-fix. Lanes: docs, filter.
- ✅ **`filter/spec.md` advertises `apply_overrides()` and
  `apply_session()` as standalone callables.** Both are
  inlined into `run_filter` (`apply_session` exists as
  `_apply_session`, private). Reword to describe Phase C / D
  as internal phases of `run_filter`.
  Kind: doc-fix. Lanes: docs, filter.
- ✅ **`filter/spec.md` Phase A rule 5 parenthetical claims
  "bound to Mature* category fallback".** No fallback exists
  in `_mature` (`drops.py:52`). Drop the parenthetical.
  Kind: doc-fix. Lanes: docs, filter.
- ✅ **`pick_winner` exported from `filter/__init__.py` but
  not in `filter/spec.md`'s public API surface.** Add it to
  Phase B (alongside `explain_pick`).
  Kind: doc-fix. Lanes: docs, filter.
- ✅ **`parser/spec.md` cross-reference says §6.7 update
  channel for listxml acquisition.** §6.7 is `updates/`; the
  acquisition flow is at design §6.1. Fix the reference.
  Kind: doc-fix. Lanes: docs, parser.
- ✅ **`cli/spec.md` subcommand inventory shows `filter` as
  `planned`.** P02 shipped; flip to `shipped`.
  Kind: doc-fix. Lanes: docs, cli.
- ✅ **P00 journal omits `CHANGELOG.md` skeleton and example
  yaml configs from "What shipped".** The combined initial
  commit landed those too. Add bullets.
  Kind: doc-fix. Lanes: docs.
- ✅ **P00 journal has no Spec line in the header (P01/P02
  both have one).** Add `**Spec:** none (scaffold phase has
  no module spec)` for template consistency.
  Kind: doc-fix. Lanes: docs.
- ✅ **`docs/glossary.md` missing entry for "non-merged ROM
  set".** Term appears in README × 2 and in parser/design
  specs as a hard requirement. Add an entry explaining the
  three MAME ship styles (merged / split / non-merged) and
  why this project requires non-merged.
  Kind: doc-fix. Lanes: docs, onboarding.
- ✅ **README has no link path to authoritative docs.**
  Coding-standards, ROADMAP, CHANGELOG, glossary, ADRs are
  unreachable from the front page. Add a "Project docs" /
  "Contributing" section.
  Kind: doc-fix. Lanes: docs, onboarding.
- ✅ **README does not mention the project's Conventional
  Commits format.** First-time PR authors will guess wrong.
  One-line addition under Contributing.
  Kind: doc-fix. Lanes: docs, onboarding.
- ✅ **README "Project structure" section is a one-line stub
  pointing at design § 11.** Inline the parser → filter →
  copy → … layer diagram from CLAUDE.md so newcomers get the
  mental model on the front page.
  Kind: doc-fix. Lanes: docs, onboarding.
- ✅ **`README.md:45` shows `git clone <repo>` placeholder.**
  Replace with the real public URL.
  Kind: doc-fix. Lanes: docs, onboarding.

#### Tier 3 — nits

- ✅ **`coding-standards.md` §15 precedence rule is silent
  about §16 Amendments.** Add a one-line scope note ("applies
  to coding rules §§1-14; §16 governs how this document
  itself changes").
  Kind: doc-fix. Lanes: docs.
- ✅ **`commits.md` example "phase A drop predicates" doesn't
  match git log convention** (real commits use `phase-2 / P02`).
  Replace with a real example.
  Kind: doc-fix. Lanes: docs.
- ✅ **CLAUDE.md filter CLI smoke example silently drops the
  optional `--mature` flag.** Add a `# --mature optional`
  comment to the block.
  Kind: doc-fix. Lanes: docs.
- ✅ **CLAUDE.md is silent on PR-vs-direct-push policy for
  feature work.** Direct-push is the established habit;
  state it explicitly.
  Kind: doc-fix. Lanes: docs.
- ✅ **Design spec §12 Phase 4 mentions filesystem-browser
  routes "for the wizard's Browse buttons".** The wizard is
  Phase 8; add `(consumed by the Phase 8 wizard)` parenthetical.
  Kind: doc-fix. Lanes: docs.
- ✅ **P02 journal truncates fix-commit subjects.** Quote
  full subjects so `git log --grep` finds them.
  Kind: doc-fix. Lanes: docs.
- ✅ **Closing-commit citations in journals lack 7-char SHA
  prefixes for grep-ability.** Add them.
  Kind: doc-fix. Lanes: docs.

### 🔍 Round-2 follow-on findings (2026-04-30)

Round-2 cold-eyes review revealed that round-1 patches were
applied to spec files but not propagated to the long-form roadmap
or to a few cross-document references. All landed in this same
DOC01 fix-pass before close.

#### Tier 1 — blockers

- ✅ **`.claude/workflow.md` § Phase history table malformed.**
  P03–P09 rows have 4 columns vs the 6-column header (introduced
  by the round-1 "Shipped / Tagged" split). Fix by adding `| — |
  — |` placeholders to those rows so each renders correctly.
  Kind: doc-fix. Lanes: docs.
- ✅ **DOC01 finding-count drift between prose and bullets.**
  Round-1 prose advertised "5 Tier-1, 17 Tier-2, 12 Tier-3" but
  the actual sub-bullets are 3/17/7 (after deduplication and
  re-read demotion). Reword the DOC01 prose AND the CHANGELOG
  highlight to the actual count and explain the dedupe rule.
  Kind: doc-fix. Lanes: docs.

#### Tier 2 — should-fix

- ✅ **Long-form roadmap Phase 2 step 7 still describes
  `apply_overrides(decisions, overrides_yaml) -> decisions` as a
  public callable.** Round-1 patched `filter/spec.md` to describe
  Phase C as an internal phase of `run_filter`; the long-form
  roadmap missed the same patch. Reword step 7 in
  `docs/superpowers/specs/2026-04-27-roadmap.md`.
  Kind: doc-fix. Lanes: docs, filter.
- ✅ **Long-form roadmap Phase 2 step 8 still says `winners:
  list[str]` and `contested_groups: list[ContestedGroup]`.**
  Round-1 patched the per-module spec to `tuple[..., ...]`;
  long-form roadmap missed the same patch. Update; add the
  `warnings: tuple[str, ...]` field.
  Kind: doc-fix. Lanes: docs, filter.
- ✅ **`filter/spec.md` `pick_winner` signature wrong in the
  Public-API block** (round-1's own addition). Spec shows
  `(candidates, ctx, config) -> Machine | None`; code is
  `(candidates, parent, ctx, cfg) -> Machine` (4 args; never
  returns None — empty groups filtered before the call). Update.
  Kind: doc-fix. Lanes: docs, filter.
- ✅ **`filter/spec.md` `explain_pick` signature wrong.** Spec
  shows `(group, config) -> list[TiebreakerHit]`; code is
  `(candidates, parent, ctx, cfg) -> tuple[TiebreakerHit, ...]`.
  Update.
  Kind: doc-fix. Lanes: docs, filter.
- ✅ **`filter/spec.md` "session-excluded winner remains a winner
  in the underlying `FilterResult`" promises a data shape that
  doesn't exist.** `FilterResult.winners` is the post-session-slice
  set; there is no separate "underlying winners" field. Reword.
  Kind: doc-fix. Lanes: docs, filter.
- ✅ **README and CLAUDE.md layer-diagram order disagree.** README
  orders `parser → filter → copy → media → api → updates → help →
  setup`; CLAUDE.md orders `parser → filter → media → copy →
  updates → help → api → setup`. Pick one canonical order
  (README's groups by phase number, more onboarding-friendly) and
  align both.
  Kind: doc-fix. Lanes: docs, onboarding.
- ✅ **Glossary missing `DOC##` entry.** Workflow ID family has
  `FP##` and `DS##` defined; `DOC##` was introduced this pass and
  is now used in 3 docs without a definition.
  Kind: doc-fix. Lanes: docs, onboarding.

#### Tier 3 — nits

- ✅ **`docs/standards/README.md` `coding.md` slot row omits §15.**
  Round-1 added §8 to that row but `coding.md`'s own redirect line
  and table both list §15. Add §15 to the README slot row for
  parity.
  Kind: doc-fix. Lanes: docs.
- ✅ **"Phase D" terminology collides** between App-Build's Phase D
  (documentation audit; used in DOC01 title) and the filter
  pipeline's Phase D (session-slice; used throughout `filter/`
  spec and CHANGELOG). Add a glossary disambiguation.
  Kind: doc-fix. Lanes: docs, onboarding.
- ✅ **Glossary missing `App-Build alignment commit` entry.**
  Term appears in `.claude/workflow.md` § 3 journal and ROADMAP
  Tier-2 fix bullet; needs a one-liner.
  Kind: doc-fix. Lanes: docs, onboarding.
- ✅ **README "Project docs" section omits housekeeping doc
  pointers** (`docs/known-issues.md`, `docs/ideas.md`,
  `docs/audit-allowlist.md`). Add a single bullet.
  Kind: doc-fix. Lanes: docs, onboarding.

Dependencies: P02 ✅.
Convergence-checkpoint counts this as fix-pass #1 since the last
clean review (rounds 1–2 within the same fix-pass; convergence
threshold not reached).

---

## P03 — Copy + BIOS resolution + RetroArch playlist (shipped 2026-04-30)

**Theme:** given a winner list from P02, copy each winner's `.zip`
plus all transitively-required BIOS `.zip`s to the destination,
write a RetroArch `mame.lpl` playlist, and emit a copy report.

**Long-form contract:**
[`docs/superpowers/specs/2026-04-27-roadmap.md` § Phase 3](docs/superpowers/specs/2026-04-27-roadmap.md).

### 🎨 Features

- ✅ **P03 — `copy/` module.** Implements: BIOS chain resolution
  (transitive `romof` + `<biosset>` walk, dedup), atomic copy
  (`.tmp` + `os.replace`, `shutil.copy2` mtime preservation), `.lpl`
  RetroArch v6+ JSON writer, playlist conflict resolution
  (append vs overwrite, per-game version replace, recycle-bin),
  pause/resume/cancel semantics, activity-log append, copy report.
  Two file schemas to pin in `copy/spec.md`: `data/activity.jsonl`
  event format, `CopyReport` Pydantic model.
  CLI: `mame-curator copy --dry-run` and `--apply`.
  Coverage target: ≥85%.
  Kind: implement.
  Lanes: copy, tests.
  Dependencies: P02 ✅.

---

## FP01 — P03 indie-review fold-in (closed 2026-04-30)

**Theme:** indie-review pass on the freshly-shipped P03 surfaced 6 Tier-1 spec/code drift + atomicity bugs that the standard `/audit` tools missed, plus 10 Tier-2 + 7 Tier-3. Folded per the "every audit finding is tracked" hard rule. P03 stays open until FP01 closes.

### What closed in FP01

- ✅ All 6 Tier-1 fixed: `copy_one` signature drift (spec widened), `KeyboardInterrupt` cleanup (try/finally), `OverwriteRecord` populated in REPLACE / REPLACE_AND_RECYCLE branches, append-decision design (caller-side conflict detection — spec updated, runner trusts presence-in-`append_decisions`), recycle collision logic (clean counter loop), `read_lpl` scope narrowed to v1.5+ JSON.
- ✅ Tier-2 closed: six `# type: ignore[arg-type]` removed by typing work-list as `Literal["winner","bios"]`; FAILED-branch + PARTIAL_FAILURE coverage; OVERWRITE + `delete_existing_zips` coverage; round-2 follow-on — corrupt-playlist surfaces warning instead of silent-overwrite (B-T2-3 user-data risk); plain `REPLACE` (no recycle) test added.
- ✅ Tier-3 closed: `errors.py` `__str__` test; `playlist.py` PlaylistError branch tests; `recycle_file` missing-source test.
- ⏭️ **Deferred to FP02** (round-2 indie-review surfaced fresh-eyes findings): `OverwriteRecord.parent` cosmetic rename; multi-conflict replaced-short heuristic; cross-session recycle dirname collision; spec typo `mid-copy3`; `_finalize` chd_missing duplication; `make_cb` → `functools.partial` refactor; SKIPPED_MISSING_SOURCE accidentally entering `mame.lpl`; chunked-path failure test; cancel-keeps-partial test strengthening; recycle same-name 3+ collision test; `self_reference` warning enum arm; `wait_if_paused` race comment; O_APPEND 4 KiB comment; hypothesis property tests; `session_id` ULID claim narrowed; `data/copy-history` persistence dropped; macOS/Windows path separator known-issue; `source_dir` fixture scope; `test_lpl_no_bom` strengthening.

74 tests pass; copy/ aggregate ~89% coverage; mypy strict + ruff + bandit + pre-commit all green.

Dependencies: P03 ✅.

---

## FP02 — FP01 round-2 fold-in (closed 2026-04-30)

**Theme:** FP01 round-2 indie-review surfaced 3 fresh-eyes Tier-2 + 6 Tier-3 findings on the surrounding `copy/` code (not regressions on FP01 fixes themselves). Closing `/audit` + `/indie-review` on the FP02 patches surfaced spec drift introduced by FP02 itself (duplicate `AppendDecision` in `copy/spec.md`; stale `recycle_file` docstring); folded into the same fix-pass per the DOC01 round-2 precedent.

### What closed in FP02

- ✅ **`OverwriteRecord.parent` dropped.** Field always equalled `old_short` (the runner has no `cloneof_map` to compute the actual parent — FP01 #4 design contract). Removed from the model; runner instantiation updated; types.py docstring captures the rationale. Kind: review-fix. Lanes: copy.
- ✅ **`AppendDecision` widened to a Pydantic model.** Was a `StrEnum`; is now `BaseModel(kind: AppendDecisionKind, replaces: str | None)` so multi-conflict sessions steer to the right existing entry. Pre-FP02 heuristic ("first existing-but-not-winner") would have recycled the wrong file with two simultaneous REPLACE_AND_RECYCLE decisions. Caller now specifies `replaces` explicitly. Spec § "Playlist conflict resolution" updated; spec also notes that duplicate `replaces` across decisions is undefined behaviour (caller responsibility). Kind: review-fix. Lanes: copy.
- ✅ **Recycle dirname keyed on `session_id`.** Layout changed from `data/recycle/<ISO-timestamp>/` to `data/recycle/<session_id>/`; two sessions recycling within the same second can no longer collide. Same-session same-name collisions still walk a `-1`, `-2`, ... counter loop (covered by test_recycle_three_same_name_same_session_collisions). Kind: review-fix. Lanes: copy.
- ✅ **Spec typo `mid-copy3` → `mid-copy`** (`copy/spec.md` step 6 of Atomic copy primitive). Kind: doc-fix.
- ✅ **`_chd_missing(plan)` helper extracted.** Was duplicated across `run_copy` and `_finalize`. Single canonical computation. Kind: refactor.
- ✅ **`functools.partial` over `make_cb` closure factory** for per-file progress callbacks. Kind: refactor.
- ✅ **Playlist entries filtered to `SUCCEEDED` + `SKIPPED_IDEMPOTENT`.** Pre-FP02 the builder included `SKIPPED_MISSING_SOURCE` outcomes (winners whose source was missing — `dst` never written) and `SKIPPED_EXISTING_VERSION` (KEEP_EXISTING — `dst` never written; existing entry covers it). Both produced `mame.lpl` entries pointing at non-existent files. New "Which winners become entries" subsection in `copy/spec.md` documents the contract. Kind: review-fix.
- ✅ **`KeyboardInterrupt` cleanup test extended to `progress=cb` branch.** The pre-FP02 test only exercised the `progress=None` (shutil.copy2) path; the chunked-progress branch was untested. Both share the try/finally, but the test was the only signal. Kind: test.
- ✅ **Recycle 3+ same-name same-session collision test added.** Pre-FP02 the test only iterated counter=1; the new test forces counter=2 to exercise the loop bound. Kind: test.

### Round-2 findings (closed in same FP02)

- ✅ **Spec self-contradiction: duplicate `AppendDecision` definition.** `copy/spec.md` § CopyPlan still had the pre-FP02 `StrEnum` definition while the upstream § "Playlist conflict resolution" had the new model. Removed the duplicate; CopyPlan section now references the upstream definition. Kind: doc-fix. Source: indie-review-2026-04-30 round-2.
- ✅ **`recycle_file` spec docstring still said `<timestamp>`.** Updated to `<session_id>`; signature updated to match the actual `*, reason, session_id, recycle_root` keyword-only marker. Kind: doc-fix. Source: audit-2026-04-30 / indie-review-2026-04-30 round-2.
- ✅ **`test_recyclebin.py:13` docstring still mentioned `<ISO-timestamp>`.** Updated to `<session_id>`. Kind: doc-fix.
- ✅ **Duplicate `replaces` in `append_decisions` — caller-responsibility note added** to spec (spec.md § CopyPlan).

9 new tests in `tests/copy/test_fp02_fixes.py`; 241 tests pass project-wide; coverage 94.79% (gate 85%); mypy strict + ruff + bandit + pre-commit all green.

Dependencies: P03 ✅, FP01 ✅.

---

## DS01 — Pre-P04 debt sweep fold-in (closed 2026-05-01)

**Theme:** `/debt-sweep` 2026-05-01 surfaced findings across `P02-complete..HEAD` (DOC01 + P03 + FP01 + FP02 + 179325a); four rounds of cold-eyes spec review converged on **20 actionable sub-bullets** (C9 retained as a footnoted stale entry — `--help` strings were already present at HEAD; D3 added during review to prune two stale `[Unreleased]` Tier-3 entries that shipped silently in DOC01/P03). Captures the FP01 stragglers that did not actually close in FP02, the pre-P03 sweep `[Unreleased]` Tier-2/3 hardening items (deferred "until Tier 1 ships" — Tier 1 has shipped), the pre-existing `runner.py:258` swallow that FP02 deferred forward, and record drift on commit `179325a`. One clean fix-pass before P04 opens, so the API surface lands on a debt-free foundation. **Prefix is `DS##`** (debt-sweep) per the App-Build ID scheme — sourced from `/debt-sweep`, even though many sub-bullets are recovered FP-shaped findings.

**Long-form contract:** [`docs/specs/DS01.md`](docs/specs/DS01.md).

### 🔍 Findings fold-in

#### Cluster A — `copy/` spec drift (record-keeping liars)

- ✅ **A1 — drop `data/copy-history/<id>/report.json` persistence claim** from `copy/spec.md:12, 341`. No code writes this path; CHANGELOG `[Unreleased]` FP01 already credits the drop as shipped. Kind: doc-fix. Lanes: docs, copy.
- ✅ **A2 — narrow `session_id` ULID claim** in `copy/spec.md:303, 369`. Actual generator at `runner.py:45` is `strftime + token_hex(4)`, not a Crockford-base32 ULID. Kind: doc-fix. Lanes: docs, copy.
- ✅ **A3 — drop unused `self_reference` enum arm** from `copy/types.py:78`. Decision: drop (no constructor in `src/`); if a real case surfaces later, add the arm with the test that motivates it. Kind: refactor. Lanes: copy.
- ✅ **A4 — `wait_if_paused` race-safety comment** at `copy/controller.py:72-74`. One-line note: `Event.set()` atomicity is why the unlocked wait is safe. Kind: review-fix. Lanes: copy.
- ✅ **A5 — `logger.exception()` on bare `except Exception` at `copy/runner.py:258`.** Traceback is currently swallowed; only `str(exc)` makes it into `CopyOutcome.error`. FP02's closing review explicitly deferred this to "a future debt-sweep" (`docs/journal/FP02.md:137-141`). Kind: review-fix. Lanes: copy.

#### Cluster B — Test gaps (FP01-deferred)

- ✅ **B1 — Hypothesis property tests for `resolve_bios_dependencies`.** Idempotence, subset closure, no self-loops, order independence. Kind: test. Lanes: copy, tests.
- ✅ **B2 — `test_cancel_with_keep_partial` strengthened to mid-session cancel.** Current test only exercises cancel-before-start. Kind: test. Lanes: copy, tests.
- ✅ **B3 — `test_lpl_no_bom` strengthened to UTF-8 round-trip.** Currently a single negative assertion. Kind: test. Lanes: copy, tests.
- ✅ **B4 — `source_dir` fixture scope review** (`tests/copy/conftest.py:62`). Widen to `module` if no test mutates; otherwise document the function-scope as deliberate. Kind: test. Lanes: copy, tests.

#### Cluster C — `filter/` + `cli/` hardening (pre-P03 sweep `[Unreleased]`)

- ✅ **C1 — `Sessions(active=...)` `model_validator(mode="after")`** in `filter/sessions.py`. Programmatic construction currently bypasses validation. Kind: review-fix. Lanes: filter.
- ✅ **C2 — `FilterResult.dropped` to `tuple[tuple[str, DroppedReason], ...]`** in `filter/types.py:57`. Mutable `dict` despite `frozen=True`; all peers are tuples. Kind: refactor. Lanes: filter.
- ✅ **C3 — YAML alias-bomb cap (1 MB)** in `filter/overrides.py:31`, `filter/sessions.py:59`. Future-proofs P07 preset downloads. Kind: review-fix. Lanes: filter.
- ✅ **C4 — explicit `None` checks** replace `raw.get("sessions") or {}` and `body or {}` in `filter/sessions.py:65, 71`. Kind: review-fix. Lanes: filter.
- ✅ **C5 — wrap `read_text` in `try/except OSError`** in `filter/overrides.py:28-31`, `filter/sessions.py:56-59`. TOCTOU between `.exists()` and `.read_text()`. Kind: review-fix. Lanes: filter.
- ✅ **C6 — `_cmd_filter` wraps `OSError`** from `--catver`/`--listxml`/`--dat`/`--languages`/`--bestgames` pointing at a directory or unreadable file. `cli/spec.md` § "Errors the CLI catches but never raises." Kind: review-fix. Lanes: cli.
- ✅ **C7 — atomic report write** (`cli/__init__.py` `_cmd_filter`). Tmp + `Path.replace`. P03's `copy/` consumes this report. Kind: review-fix. Lanes: cli.
- ✅ **C8 — replace sentinel-path antipattern** in `cli/__init__.py` `_cmd_filter` with direct empty `Overrides()` / `Sessions()` construction. Kind: refactor. Lanes: cli.
- ~~**C9 — `help=` strings** on argparse args in `cli/__init__.py:48-54`.~~ **Removed 2026-05-01 — finding was stale; all flags already have `help=` strings at HEAD (verified during DS01 cold-eyes review). Replaced by D3.** Kind: doc-fix (closed-as-stale).

#### Cluster D — Allowlist + record

- ✅ **D1 — add `_preferred_score` substring-vs-fnmatch** to `docs/audit-allowlist.md`. Spec already documents the intent; audits should pre-discard. Kind: doc-fix. Lanes: docs.
- ✅ **D2 — credit `179325a` in CHANGELOG.** Cross-platform path fix landed after FP02 closed; commit is uncredited. Closes the FP01 macOS/Windows-path deferral on the record. Kind: doc-fix. Lanes: docs.
- ✅ **D3 — prune stale `[Unreleased]` Tier-3 entries** at `CHANGELOG.md` lines ~134-137 (CLI module docstring `copy`-as-shipped misclaim; `--catver` etc. lacking `help=`). Both shipped silently in DOC01/P03 work. Strikethrough + dated footnote per the spec. Kind: doc-fix. Lanes: docs.

### Out of scope (deferred to FP04)

- `parser/dat.py` `_resolve_xml` `OSError` non-catch + theoretical fd-leak. Originally surfaced in pre-P03 indie-review sweep (CHANGELOG `[Unreleased]` Tier-2 lines ~115-124). Tracked as FP04 below — not as CHANGELOG-only prose.

Dependencies: P03 ✅, FP01 ✅, FP02 ✅.

---

## FP05 — DS01 closing-review fold-in (closed 2026-05-01)

**Theme:** the closing `/audit` + `/indie-review` pass on DS01's patches surfaced 14+ findings in the surrounding `copy/`, `filter/`, `cli/` code (not introduced by DS01 itself — DS01-introduced drift was closed inside DS01 as Cluster R per the FP02 precedent). Findings batched into one fix-pass per the App-Build "every audit finding is tracked" rule. **Source:** `/indie-review` 2026-05-01, three lanes: copy/, filter/, cli/.

**Long-form contract:** to be written at Step 1 of FP05's loop (`docs/specs/FP05.md`), per the App-Build "specs just-in-time" anti-pattern guard.

### 🔍 Findings fold-in

#### Tier 1 — real bugs (close-this-week)

- ✅ **A1 — `recycle_partial=True` cancellation specced but unimplemented.** `copy/spec.md:288-289` contracts: cancel with `recycle_partial=True` recycles every successfully-copied file from the current session and emits one `copy_aborted` activity event with `details.recycled_count = N`. `copy/runner.py:305` reads `cancelled_mid = ctl.should_cancel()` and skips the playlist write but never inspects `controller.recycle_partial` and never recycles `succeeded` outcomes. `_recycle_partial` flag at `controller.py:33-45,64-68` is write-only state from the runner's POV. Silent contract violation. Kind: review-fix. Lanes: copy. Source: indie-review-2026-05-01 lane copy M2.
- ✅ **A2 — empty-string `active` footgun in `Sessions._active_must_reference_a_defined_session`.** `Sessions(active="", sessions={"": Session(...)})` succeeds — empty-string keys are valid Python dict keys, the validator's membership test passes, and `_apply_session` (`runner.py:100`) silently activates the empty-name session. Reject `active == ""` and reject empty session keys at `from_raw` / `load_sessions` time. Kind: review-fix. Lanes: filter. Source: indie-review-2026-05-01 lane filter H2.
- ✅ **A3 — bare `except Exception` at `copy/runner.py:258` is wider than spec.** Catches `MemoryError` (which derives from `Exception`, not `BaseException`) and continues the loop after OOM — exactly wrong. Spec § Errors lists `CopyExecutionError` as the failure mode. Narrow to `except (OSError, CopyExecutionError)`. Kind: review-fix. Lanes: copy. Source: indie-review-2026-05-01 lane copy M3.

#### Tier 2 — hardening sweep

- ✅ **B1 — `BIOSResolutionWarning.kind` is now a one-arm `Literal["missing_from_listxml"]`** after DS01 A3 dropped `self_reference`. Either restore a real second variant (e.g. winner whose chain transitively reaches a name absent from `bios_chain`) or collapse `BIOSResolutionWarning` to `name: str` and let `kind` come back when a second variant is genuinely needed. Kind: refactor. Lanes: copy. Source: indie-review-2026-05-01 lane copy H1.
- ✅ **B2 — cycle-safety claim in `copy/spec.md:54` doesn't match `copy/bios.py:22-44`.** Spec says cycles broken by `seen` plus `entry.romof != name` self-reference guard. Code: `seen` is checked at pop time (not enqueue), and the self-reference guard is absent (line 41 only checks `if entry.romof:`). Functionally correct; contractually drifted. Tighten spec wording or restore the guard. Kind: doc-fix or refactor. Lanes: copy. Source: indie-review-2026-05-01 lane copy H2.
- ✅ **B3 — `BIOSResolutionError` is a zombie** (`copy/errors.py:30`, exported in `__init__.py:10,47`, no `raise` site). Either delete the class + export + spec line, or actually raise it on a real failure mode (e.g. malformed transitive chain). Kind: refactor. Lanes: copy. Source: indie-review-2026-05-01 lane copy M1.
- ✅ **B4 — pause/cancel race window in `CopyController.pause()`.** `pause()` clears the resume event under the lock; `cancel()` sets it under the lock; but a `cancel()` that runs *between* `pause()`'s release and the next `wait_if_paused()` enqueue can leave the event cleared with `_cancel_flag=True`, never waking. Close: re-check `_cancel_flag` immediately after `_resume_event.clear()` in `pause()`, set the event back if cancel won. Kind: review-fix. Lanes: copy. Source: indie-review-2026-05-01 lane copy M4.
- ✅ **B5 — TOCTOU between `path.stat()` and `path.read_text()`** in `filter/sessions.py:67-86` and `filter/overrides.py:30-49`. Open-then-stat-then-read via `path.open("rb")` + `os.fstat(f.fileno())` + `f.read()` closes the swap window. Threat is theoretical for self-authored configs but escalates with P07's preset downloads. Kind: review-fix. Lanes: filter. Source: indie-review-2026-05-01 lane filter M2.
- ✅ **B6 — `FilterContext` has the same `frozen=True`-but-mutable-dict problem C2 fixed for `FilterResult`.** `category: dict[str, str]`, `languages: dict[str, tuple[str, ...]]`, `cloneof_map: dict[str, str]`, `bestgames_tier: dict[str, str]` — all in-place-mutable on a frozen-claim model. Hot-path so the perf consideration matters; pragmatic fix is documenting owner-mutable-but-treated-read-only or migrating to `MappingProxyType`. Kind: refactor. Lanes: filter. Source: indie-review-2026-05-01 lane filter M3.
- ✅ **B7 — `Session.from_raw` validation should be a `Session.model_validator(mode="after")`** matching the C1 pattern for `Sessions.active`. Currently `Session(include_year_range=(1995, 1990))` succeeds programmatically — exact same bug class C1 closed for `Sessions`. Kind: review-fix. Lanes: filter. Source: indie-review-2026-05-01 lane filter M4.
- ✅ **B8 — `_cmd_filter` C6 OSError catch comment overstates the threat surface.** Loaders already wrap `OSError` into typed errors; the residual surface is narrow (TOCTOU between `.exists()` and read). Reword the inline comment to "Defense-in-depth: loaders wrap OSError into typed errors, but a TOCTOU between `.exists()` and read can still surface bare OSError" so a future reader doesn't hunt for a non-existent escape path. Kind: doc-fix. Lanes: cli. Source: indie-review-2026-05-01 lane cli H1.
- ✅ **B9 — `_cmd_copy` lacks C6-equivalent OSError wrap.** DS01 explicitly out-of-scoped this; the asymmetry is itself a six-month-test smell. Add the same `except OSError` clause, or document why `_cmd_copy`'s parser-only inputs make it unnecessary. Kind: review-fix. Lanes: cli. Source: indie-review-2026-05-01 lane cli M3.
- ✅ **B10 — exit code for `CopyReportStatus.CANCELLED` collides with runtime-error 1.** A user-initiated SIGINT cancel returns exit 1, same as a corrupt DAT — UX wart per `cli/spec.md` § "Exit codes." Pin a distinct exit code (130 for SIGINT-cancel, e.g.) or document explicitly. Kind: review-fix. Lanes: cli. Source: indie-review-2026-05-01 lane cli M4.

#### Tier 3 — structural / nits

- ✅ **C1 — extract `_read_yaml_text` helper.** Currently duplicated across `filter/sessions.py` and `filter/overrides.py`. Two divergent inline copies of a size-cap + OSError-wrap idiom risks skew (someone bumps the cap in one file, forgets the other). Extract to `filter/_io.py` with `exc_cls` parameter. Kind: refactor. Lanes: filter. Source: indie-review-2026-05-01 lane filter M1.
- ✅ **C2 — extract `atomic_write_text` helper now that DS01 R2 forced divergence from `executor.py`.** The CLI's atomic-write is now near-identical to `executor.py:60-79` (try/finally cleanup of `.tmp`). Two correct copies that have to handle the same cleanup is the threshold where Rule of Three flips. Use `tempfile.NamedTemporaryFile` for a unique tmp name to defend against concurrent invocations and stale `.tmp` from prior crashes. Kind: refactor. Lanes: cli, copy. Source: indie-review-2026-05-01 lane cli H2 follow-up.
- ✅ **C3 — `os.replace` cross-filesystem hazard.** If `args.out` resolves through a symlink across mounts, `os.replace` raises `OSError(EXDEV)`. Theoretical risk. Document or accept. Kind: review-fix. Lanes: cli. Source: indie-review-2026-05-01 lane cli M2.

Plus 8-10 minor LOW findings (unit drift in error messages, `with_suffix` corner cases, redundant validation paths, etc.) — folded into FP05 spec at Step 1 with full file:line citations.

Dependencies: DS01 ✅. Tracked here as 📋 (planned); spec written at Step 1 of FP05's own 9-step loop.

---

## FP06 — FP05 closing-review fold-in (planned)

**Theme:** the closing `/audit` + `/indie-review` pass on FP05's patches surfaced 4 actionable findings in surrounding code (cli/, _atomic.py, filter/sessions.py). FP05-introduced drift (6 items) closed inside FP05 as Cluster R. Sourced from `/indie-review` 2026-05-01.

**Long-form contract:** to be written at Step 1 of FP06's loop (`docs/specs/FP06.md`).

### 🔍 Findings to fold

- 📋 **A1 — `purge_recycle()` OSError leak in `_cmd_copy`.** The `--purge-recycle` short-circuit at `cli/__init__.py:209-212` calls `purge_recycle()` *before* the FP05 B9 `except OSError` block. A user with unreadable recycle directory gets a Python traceback. Wrap or surface via typed `CopyError`. Kind: review-fix. Lanes: cli, copy. Source: indie-review-2026-05-01 lane cli H1.
- 📋 **B1 — verify SessionsError-via-ValidationError shape with explicit test.** `Sessions._active_must_reference_a_defined_session` raises `SessionsError` from a Pydantic `model_validator(mode="after")`. Pydantic v2 wraps ValueError/AssertionError in ValidationError but tolerates other exceptions; the loader's `try/except ValidationError → SessionsError` wrap may not cover this path consistently. 5-line regression test, no code change. Kind: test. Lanes: filter, tests. Source: indie-review-2026-05-01 lane filter M3.
- 📋 **B2 — validator-raise-style asymmetry.** `Session._validate_session` raises `ValueError`; `Sessions._active_must_reference_a_defined_session` raises `SessionsError`. Pick one convention. Both work but the six-month test fails. Kind: refactor. Lanes: filter. Source: indie-review-2026-05-01 lane filter M4.
- 📋 **B3 — error-message path quoting.** `read_capped_text` uses `f"failed to read {path}: {exc}"`; a path with newlines or control chars breaks the single-line error contract. Use `repr(path)`. Kind: review-fix. Lanes: filter. Source: indie-review-2026-05-01 lane filter M2.

Dependencies: FP05 ✅. (FP04 — parser hardening — unchanged.)

---

## FP04 — Parser hardening sweep (planned)

**Theme:** items deferred from DS01 cold-eyes review (2026-05-01). Scope is `parser/dat.py` only. Opens after DS01 closes. May absorb new parser findings if `/audit` or `/indie-review` surfaces them during DS01's closing review.

**Source:** pre-P03 indie-review sweep 2026-04-27 (CHANGELOG `[Unreleased]` Tier-2 entries at lines ~115-124, originally tagged "deferred until Tier 1 ships"). DS01 explicitly leaves these out of scope to keep its audit surface coherent on `copy/` + `filter/` + `cli/`.

### 🔍 Findings to fold

- 📋 **`_resolve_xml` `OSError` non-catch** (`parser/dat.py:48-50`). Doesn't catch `OSError` from `zipfile.ZipFile(...)` (perm-denied, EIO, broken symlink). `parser/spec.md` line 138 says every CLI-visible error path stays inside `ParserError`. Kind: review-fix. Lanes: parser.
- 📋 **`_resolve_xml` fd-leak window** (`parser/dat.py:49-56`). `zip_ctx = zipfile.ZipFile(path)` binds before the `with` block, so a future `__enter__` failure leaks the fd. Theoretical (CPython `__enter__` is `return self`) but the idiomatic fix is one-line: move `ZipFile(path)` inside the `with` and the `try` around it. Kind: review-fix. Lanes: parser.

Dependencies: DS01 (sequenced for cognitive coherence — surfaces don't overlap (`parser/dat.py` only) so technically parallelisable, but the project's per-phase loop is single-active-item by convention; running FP04 after DS01 closes keeps the convention intact).

---

## P04 — HTTP API (planned)

**Theme:** FastAPI server exposing P01-P03 over HTTP + SSE for
copy progress.

**Long-form contract:**
[`docs/superpowers/specs/2026-04-27-roadmap.md` § Phase 4](docs/superpowers/specs/2026-04-27-roadmap.md).

### 🎨 Features

- 📋 **P04 — `api/` module.** All routes from design spec § 6.5;
  Pydantic schemas; SSE for copy progress; sandboxed `/api/fs/*`
  browser routes. Coverage target: ≥80%.
  Kind: implement.
  Lanes: api, tests.
  Dependencies: P03.

---

## P05 — Media subsystem (planned)

**Theme:** libretro-thumbnails URL builder + lazy fetch + sha256-
keyed disk cache through the API proxy.

**Long-form contract:**
[`docs/superpowers/specs/2026-04-27-roadmap.md` § Phase 5](docs/superpowers/specs/2026-04-27-roadmap.md).

### 🎨 Features

- 📋 **P05 — `media/` module.** URL escape rules
  (`&*/:\<>?\|"` → `_`); `urls_for(machine)`; async
  `fetch_with_cache(url, cache_dir)`; cache key = `sha256(url)`.
  Coverage target: ≥90%.
  Kind: implement.
  Lanes: media, api, tests.
  Dependencies: P04.

---

## P06 — Frontend MVP (planned)

**Theme:** Vite + React 19 + Tailwind v4 + shadcn/ui browser UI
with virtualized grid, alternatives drawer, copy modal with SSE,
multiple themes/layouts, Cmd-K palette.

**Long-form contract:**
[`docs/superpowers/specs/2026-04-27-roadmap.md` § Phase 6](docs/superpowers/specs/2026-04-27-roadmap.md).

### 🎨 Features

- 📋 **P06 — frontend MVP.** All component tests + one Playwright
  E2E. `Switch` for binary preferences (not `Checkbox`).
  `AlertDialog` on every destructive action. Coverage target: ≥70%.
  Kind: implement.
  Lanes: frontend, tests.
  Dependencies: P05.

---

## P07 — Self-update + in-app help (planned)

**Theme:** in-app updates (git-pull / release-download with
snapshot+rollback), INI refresh with diff preview, bundled
markdown help searchable via Cmd-K. Introduces the shared
`downloads.py` primitive that P08 reuses.

**Long-form contract:**
[`docs/superpowers/specs/2026-04-27-roadmap.md` § Phase 7](docs/superpowers/specs/2026-04-27-roadmap.md).

### 🎨 Features

- 📋 **P07 — `updates/` + `help/` modules.** `downloads.py`
  primitive (sha256-pinned, exponential retry, atomic writes,
  manual-fallback hook); app self-update + rollback;
  INI refresh with diff preview; bundled help server.
  Coverage targets: updates ≥85%, help ≥90%.
  Kind: implement.
  Lanes: updates, help, downloads, frontend, tests.
  Dependencies: P06.

---

## P08 — Setup wizard (planned)

**Theme:** `git clone && ./run.sh` → curated grid via in-browser
wizard, no manual config. Reuses P07's `downloads.py`. Two-flow
reference-data acquisition (INIs checksum-pinned; `-listxml`
tiered).

**Long-form contract:**
[`docs/superpowers/specs/2026-04-27-roadmap.md` § Phase 8](docs/superpowers/specs/2026-04-27-roadmap.md).
**Two-flow `-listxml` acquisition:**
[ADR-0003](docs/decisions/0003-listxml-tiered-acquisition.md).

### 🎨 Features

- 📋 **P08 — `setup/` module.** `run.sh` / `run.bat` Stage 1;
  Stage 2 in-browser wizard with `FileBrowser`. Resumable across
  reboots. Coverage target: ≥85%.
  Kind: implement.
  Lanes: setup, frontend, tests.
  Dependencies: P07.

---

## P09 — Polish + v1.0.0 (planned)

**Theme:** finishing work — README hero shot, screenshots,
CONTRIBUTING, final UAT, tag `v1.0.0`, GitHub publish.

### 📚 Documentation

- 📋 **P09 — v1.0.0 release.** README quickstart that a
  non-technical user can follow; 4-6 screenshots from a working
  install; CHANGELOG bootstrapped with v1.0.0 entry summarising
  every phase; release workflow validated; tag + push.
  Kind: release.
  Lanes: docs, packaging, ci.
  Dependencies: P08.

---

## Future enhancements (post-v1.0.0)

Captured in
[`docs/superpowers/specs/2026-04-27-roadmap.md` § "Future
enhancements"](docs/superpowers/specs/2026-04-27-roadmap.md):
software-list routing, EmulationStation `gamelist.xml` exporter,
LaunchBox interop, DAT-version-upgrade workflow, cloud sync of
`overrides.yaml` / `sessions.yaml`, multi-user mode, i18n,
themes from more arcade classics. **Deliberately deferred** to
keep v1.0.0 shippable; not part of the v1 plan.

---

## How to add an item

1. Allocate the next ID (only if cross-referenced identity is
   needed):
   ```bash
   echo $(($(cat .roadmap-counter) + 1)) > .roadmap-counter
   printf "mame-curator-%04d\n" $(cat .roadmap-counter)
   ```
2. Insert at the position where it should be tackled (not blindly
   at the end).
3. Set the status emoji (📋 Planned, 💭 Considered).
4. Add `Kind:`, `Lanes:`, optionally `Source:` and `Dependencies:`.

See `docs/standards/roadmap-format.md § 3.5` for the full bullet
contract.

## How findings get folded

After every `/audit` + `/indie-review` (and `/debt-sweep`):

```
Phase closes
  → Run /audit + /indie-review (parallel)
  → Triage findings
  → If clean: phase fully closed.
  → If actionable: batch into one new fix-pass FP## (next-up),
    add [Unreleased] entry, run that fix-pass through the
    9-step loop; its own closing audits may produce another.
```

See `docs/standards/roadmap-format.md § 3.6` and the
[app-workflow skill](~/.claude/skills/app-workflow/SKILL.md)
for the full pattern.

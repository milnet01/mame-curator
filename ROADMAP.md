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

**Long-form contract:** [`docs/specs/FP05.md`](docs/specs/FP05.md) (signed off 2026-05-01 after 3-round cold-eyes review; closed 2026-05-01).

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

**275 tests pass project-wide; coverage 94.67%; all five gates green.**

Dependencies: DS01 ✅.

---

## FP06 — FP05 closing-review fold-in (closed 2026-05-01)

**Theme:** the closing `/audit` + `/indie-review` pass on FP05's patches surfaced 4 actionable findings in surrounding code (`cli/__init__.py`, `filter/sessions.py`, `filter/_io.py`, `filter/overrides.py`) plus 3 cleanups folded as Cluster R (R1 docstring fix, R2 missed name-quoting site at `sessions.py:81` caught by closing review, R3 B1b assertion hardening). FP05-introduced drift (6 items) closed inside FP05 itself per the FP02 / DS01 precedent. **Total: 7 actionable items.**

**Long-form contract:** [`docs/specs/FP06.md`](docs/specs/FP06.md) (signed off 2026-05-01 after 4-round cold-eyes review; closed 2026-05-01).

### 🔍 Findings fold-in

#### Tier 1 — real bug (1)

- ✅ **A1 — `purge_recycle()` OSError leak in `_cmd_copy`.** Wrapped `if args.purge_recycle:` short-circuit in `try/except OSError` at `cli/__init__.py:215-225`; surfaces clean `error:` line + exit 1 instead of traceback. Kind: review-fix. Lanes: cli, copy.

#### Tier 2 — hardening (3)

- ✅ **B1 — Lock-in tests for `Sessions` exception-shape contract.** Two tests in `tests/filter/test_sessions.py`: direct construction → `ValidationError` (verified via `errors()[0]['ctx']['error']` shape); loader path → `SessionsError` with path-prefixed message. Kind: test. Lanes: filter, tests.
- ✅ **B2 — Unify validator-raise convention.** `Sessions._active_must_reference_a_defined_session` now raises `ValueError` (was `SessionsError`); Pydantic wraps; loader's `except ValidationError → SessionsError(f"{path!r}: ...")` rewrap fires. Direct callers see `ValidationError` (a `ValueError` subclass in v2.x), matching `Session._validate_session`. Kind: review-fix. Lanes: filter.
- ✅ **B3 — Quote user-controlled strings via `repr`.** Applied `f"{path!r}"` and `f"{name!r}"` at 13 sites total (10 path + 3 name, post-R2): `_io.py:32, 35, 40`; `sessions.py:50, 81, 86, 93, 107, 119, 138, 150`; `overrides.py:35, 41, 45`. Defends single-line error contract against control-byte spoofing. Kind: review-fix. Lanes: filter.

#### Cluster R — fix-pass-internal drift (3)

- ✅ **R1 — Fix misleading `__cause__` docstring + add sibling note.** `sessions.py:27-30` updated to point at `errors()[0]['ctx']['error']` (Pydantic v2 leaves `__cause__=None`); parallel comment block above `_active_must_reference_a_defined_session` documents the same wrap behaviour for B2's now-`ValueError`-raising path. Kind: doc-fix. Lanes: filter.
- ✅ **R2 — `sessions.py:81` `self.active` quoting (B3 scope error).** Closing `/indie-review` flagged that B3 audit catalogued 2 name-quoting sites (`sessions.py:50, 125`) but missed `sessions.py:81` where `self.active` (from YAML) interpolates raw. Reproduced literal-LF leak through `ValidationError.__str__`; folded inline as Cluster R per FP02 / DS01 / FP05 precedent for fix-pass-internal scope errors. New test `test_active_with_control_char_quoted_in_error` pins. Kind: review-fix. Lanes: filter.
- ✅ **R3 — B1b assertion hardening against path-form fragility.** Closing-review M1 flagged the original `assert repr(f) in msg or repr(str(f)) in msg` would pass both pre-fix and post-fix on a clean fixture path. Strengthened to fixture path with literal LF + strict "no LF in head" assertion that survives a future "I'll just simplify the f-string" refactor. Kind: test. Lanes: filter, tests.

### Out of scope (deferred to FP07)

- `cli/__init__.py:139, 187, 200, 225, 233, 240, 260` and `copy/recyclebin.py` path-quoting (different module surface; deliberately scoped FP06 to `filter/`'s loaders).

**284 tests pass project-wide; coverage 94.63%; all five gates green.**

Dependencies: FP05 ✅.

---

## FP07 — `cli/` + typed-error path-quoting sweep (closed 2026-05-01)

**Theme:** complete the path-quoting sweep that FP06 scoped to `filter/`. Five surgical edits land the contract uniformly across `cli/`, `copy/`, and `parser/` error rendering. Strategy: fix the typed-error base classes (`copy/errors.py:26` `__str__`, `parser/errors.py:14` `__init__`) at the rendering site rather than every per-raise-site f-string — single point of change covers ~10 raise sites between `recyclebin.py`, `playlist.py`, `executor.py`, `parser/dat.py`, `parser/listxml.py`, `parser/ini.py`. Three CLI sites (`cli/__init__.py:139, 200, 249`) cover the bare `args.*` interpolations.

**Long-form contract:** [`docs/specs/FP07.md`](docs/specs/FP07.md) (signed off 2026-05-01 after 2-round cold-eyes review).

### 🔍 Findings fold-in

#### Tier 1 — closing FP06's deferred surface (5)

- ✅ **A1 — `cli/__init__.py:139` `_cmd_parse` `failed to parse` error.** `args.dat!r` quoting. Kind: review-fix. Lanes: cli.
- ✅ **A2 — `cli/__init__.py:200` `_cmd_filter` atomic-write OSError.** `args.out!r`. Kind: review-fix. Lanes: cli.
- ✅ **A3 — `cli/__init__.py:249` `_cmd_copy` filter-report load failure.** `args.filter_report!r`. Kind: review-fix. Lanes: cli.
- ✅ **A4 — `copy/errors.py:26` `CopyError.__str__` `(path=...)` rendering.** Single rendering site for every CopyError subclass — `RecycleError`, `PlaylistError`, `CopyExecutionError`, `PreflightError` all inherit. `f"{base} (path={self.path!r})"`. Kind: review-fix. Lanes: copy.
- ✅ **A5 — `parser/errors.py:14` `ParserError.__init__` `(path=...)` interpolation.** Single message-construction site for every ParserError subclass — `DATError`, `INIError`, `ListxmlError`. `f"{message} (path={path!r})" if path else message`. Kind: review-fix. Lanes: parser.

#### Cluster R — closing-review drift (1)

- ✅ **R1 — Tighten CLI test assertions.** Closing `/indie-review` M1 flagged that `assert "\n" not in err.rstrip("\n")` only strips trailing LFs; future multi-line `{exc}` would false-positive. Narrowed all three CLI tests to `assert "evil\nname.<ext>" not in err` (literal-LF form of the path). Pure test hardening; no production-code change. Kind: test. Lanes: tests.

**293 tests pass project-wide; coverage 94.93%; all five gates green.**

Dependencies: FP06 ✅.

---

## FP08 — FP07 closing-review fold-in (closed 2026-05-01)

**Theme:** FP07 closing `/indie-review` surfaced 1 actionable finding on surrounding code (M2). FP08's own closing review caught one Cluster R drift (R1: scope error in the initial audit's grep pattern — list-comp form of warnings emit at `runner.py:92` was missed). Total: 2 actionable items, 1 source line each.

**Long-form contract:** [`docs/specs/FP08.md`](docs/specs/FP08.md) (signed off 2026-05-01 after 1-round cold-eyes review).

### 🔍 Findings fold-in

#### Tier 1 — single site (1)

- ✅ **A1 — `copy/runner.py:233` recycle-failure warning quoting.** `warnings.append(f"recycle of {old_zip.name!r} failed: {exc}")`. `old_zip.name` flows from `AppendDecision.replaces` (DAT machine short-name; user-data path). Same threat model as FP06 B3 / FP07 A4. Kind: review-fix. Lanes: copy.

#### Cluster R — closing-review drift (1)

- ✅ **R1 — `copy/runner.py:92` BIOS-warning list-comp quoting (scope error).** FP08's initial audit grepped `warnings.append(f"...")` and missed the list-comprehension form `warnings: list[str] = [f"{w.name}: {w.kind}" for w in bios_warnings]`. Same value-flow class as A1; same fix shape. Folded inline as Cluster R per FP06 R2 precedent. Kind: review-fix. Lanes: copy.

**Audit-pattern lesson** (logged for future fix-passes): grep for `warnings: list[str]\s*=` and `warnings.append` *both*; or trace value-flow into `CopyReport.warnings` to find every emit-site.

**295 tests pass project-wide; coverage 95.03%; all five gates green.**

Dependencies: FP07 ✅.

---

## FP04 — Parser hardening sweep (closed 2026-05-01)

**Theme:** plumbed `OSError` into the typed-error contract at every CLI-visible parser exception path; eliminated the theoretical fd-leak window in `_resolve_xml`. Originally scoped to `parser/dat.py` only (2 deferred items from DS01); FP04's surface audit found 4 sibling sites in `listxml.py` + `_stream_machines` with the same threat model and fix shape — folded in.

### 🔍 Findings fold-in

- ✅ **A1 — `_resolve_xml` `OSError` catch.** `zipfile.ZipFile(path)` raising `PermissionError` / `IsADirectoryError` / file-disappeared race is now wrapped as `DATError(f"failed to open DAT zip: {exc}")`. Kind: review-fix. Lanes: parser.
- ✅ **A2 — `_resolve_xml` fd-binding tightening.** Replaced `zip_ctx = ZipFile(path); with zip_ctx as zf:` with a split open-then-`try/finally` pattern; `zf.close()` is now bound at the next bytecode boundary, eliminating the theoretical leak window. Kind: review-fix. Lanes: parser.
- ✅ **A3 — `_stream_machines` iterparse `OSError` catch.** `etree.iterparse` raising OSError mid-iteration (file-disappeared race, EIO during read) → `DATError(f"failed to read DAT XML: {exc}")`. Kind: review-fix. Lanes: parser.
- ✅ **A4-A6 — three `parse_listxml_*` iterparse `OSError` catches.** Same shape as A3, applied to `parse_listxml_disks`, `parse_listxml_cloneof`, `parse_listxml_bios_chain`. → `ListxmlError(f"failed to read listxml: {exc}")`. Kind: review-fix. Lanes: parser.

Dependencies: FP08 ✅. 5 regression tests added; 300 tests pass; coverage 95.11%; all five gates green. No `docs/specs/FP04.md` per the "specs are for features, not fixes" rule. See [`docs/journal/FP04.md`](docs/journal/FP04.md).

---

## P04 — HTTP API (shipped 2026-05-01)

**Theme:** FastAPI server exposing P01-P03 over HTTP + SSE for
copy progress.

**Long-form contract:**
[`docs/superpowers/specs/2026-04-27-roadmap.md` § Phase 4](docs/superpowers/specs/2026-04-27-roadmap.md).

### 🎨 Features

- ✅ **P04 — `api/` module.** All routes from design spec § 6.5;
  Pydantic schemas; SSE for copy progress; sandboxed `/api/fs/*`
  browser routes. Coverage target: ≥80% (achieved ~86%).
  Shipped 2026-05-01 across one P04 commit + FP09 fix-pass.
  Kind: implement.
  Lanes: api, tests.
  Dependencies: P03 ✅.

---

## FP09 — P04 indie-review fold-in (closed 2026-05-01)

**Theme:** the closing `/audit` + `/indie-review` pass on P04's
ship surfaced 13 actionable findings in the just-shipped `api/`
surface. `/audit` clean across ruff / mypy / bandit / gitleaks /
semgrep (p/security-audit + p/python + p/fastapi) + 9 project-
specific grep gates; all 13 actionable items came from
`/indie-review` against the cold-eyes brief.

### 🔍 Findings fold-in

- ✅ **FP09** [mame-curator-1001] **Fix-pass after P04 (HTTP API).**
  Lanes: api, cli, tests, docs.
  - **A1** (Tier 1) — `{exc}` interpolated without `repr()` at
    `state.py:75`, `state.py:77` (`yaml.YAMLError`, `ConfigError`),
    `routes/fs.py:59` (`OSError`), `routes/media.py:42`
    (`httpx.HTTPError`), and `jobs.py:_on_worker_error` (`Exception`
    str). Multi-line exception messages break the FP06–FP08 single-
    line `detail` invariant — re-validate with a `\n`-bearing
    `OSError` synthesized via monkeypatch. Wrap each `{exc}` site
    with `f"{exc!r}"` or build the detail without exception text.
  - **A2** (Tier 1) — R27 (`GET /api/copy/history/{job_id}/report`)
    returns `json.loads(...)` raw dict at `routes/copy.py:155-158`;
    spec demands `response_model=CopyReport`. Wire through
    `CopyReport.model_validate_json(path.read_text(...))`; on
    `ValidationError` raise a typed `JobReportCorruptError(502)`.
  - **A3** (Tier 1) — R19 (`POST /api/config/import`) accepts
    sessions whose names violate `_SESSION_NAME_RE` (R11's regex);
    a malicious bundle could write a session named `_deactivate`
    that then collides with the static R13b control route
    semantically. Re-apply the regex per session-name on import,
    raising `SessionNameInvalidError` consistent with R11.
  - **B1** (Tier 2) — Config export uses `model_dump(mode="json",
    exclude_defaults=True)` per session value at
    `routes/config.py:170-176`; import re-validates without
    re-populating defaults. L09 (`test_config_export_import_round_
    trip`) currently passes because the mini fixture has no
    populated-but-default Session fields; widen the test to a
    Session whose `include_year_range` equals the default and
    confirm round-trip survives, OR drop `exclude_defaults=True`.
  - **B2** (Tier 2) — `state.py:106-113` calls
    `parse_listxml_cloneof`, `parse_listxml_bios_chain`, and
    `parse_listxml_disks` sequentially (three `lxml.iterparse`
    streams over the same ~370 MB file). Combine into one streamed
    pass that yields all three outputs (preferred — one
    `parser/listxml.py` helper that accepts a callback per concern),
    OR document the deviation in `state.py` with the trade-off
    rationale and the realistic-listxml startup-time budget.
  - **B3** (Tier 2) — `Job.history` at `jobs.py:67` is an unbounded
    list; a 10k-file copy at ~50 ticks/file × ~80 bytes/event ≈
    40 MB resident. Cap with a `collections.deque(maxlen=N)` (N
    sized for one full job's events plus safety margin), OR
    document the unbounded growth in `jobs.py` with a note that
    history retention only matters for active subscribers.
  - **B4** (Tier 2) — `routes/media.py:39-41` opens a fresh
    `httpx.AsyncClient` per request; rendering 50 thumbnails
    triggers 50 TLS handshakes against `raw.githubusercontent.com`.
    Stash a single `httpx.AsyncClient` on `app.state.media_client`
    in lifespan startup, close in shutdown; reuse from R39.
    P05's caching layer can swap in transparently.
  - **B5** (Tier 2) — `JobManager.{pause,resume,abort}` call
    `await asyncio.sleep(0.05)` to wait for the controller flag
    to take effect; spec line 338 says "wait up to 250 ms".
    Pick one: either lengthen the sleep to 250 ms (matches spec)
    or update spec to 50 ms (matches impl, faster API response).
  - **B6** (Tier 2) — `state.py:replace_world` always recomputes
    `allowed_roots = compose_allowlist(new_config)`, even when
    `config` was not passed (notes-only / sessions-only swaps).
    Conditional: `allowed_roots = compose_allowlist(new_config)
    if config is not None else base.allowed_roots`. Lets the
    P01 property test ("no-op PATCH preserves identity") finally
    flip from xfail to xpass.
  - **B7** (Tier 2) — `routes/fs.py:fs_list` parent-resolution at
    lines 62-69 has a dead `parent = None; break` branch; simplify
    to `is_root = any(...); parent = ... if not is_root else None`.
    Also: when `requested.parent` is outside the allowlist, the
    current code returns it anyway and the next click 403s — either
    filter `parent` against the allowlist or document the click-
    then-403 pattern as intended.
  - **B8** (Tier 2) — `routes/help.py:_help_dir()` at line 26 uses
    `Path(__file__).resolve().parents[3].parent / "docs" / "help"`
    which evaluates to one directory above the repo root. Either
    the arithmetic is `parents[3]` (without the trailing `.parent`)
    for repo-root, or `parents[2]` for package-root. The env-var
    override saves tests but the production default points at the
    wrong directory. P07 will need `importlib.resources` for
    installed-wheel discovery; for P04 just fix the arithmetic so
    the empty-directory fallback (spec line 763) is genuinely
    empty rather than wrongly-pointed.
  - **B9** (Tier 2) — `_atomic.atomic_write_bytes` at
    `_atomic.py:24-49` does not `os.fsync` the parent directory
    after the rename; spec § Atomic-write protocol step 4 demands
    parent-dir fsync for power-loss durability. Add the parent-
    dir fsync (best-effort `contextlib.suppress(OSError)` pattern
    consistent with the existing file fsync). Same change to
    `atomic_write_text` for symmetry.
  - **C1** (Cluster R — test only) — Loop-capture race test for
    JobManager: assert that an SSE subscriber connecting AFTER
    `start()` returns observably sees the `job_started` event via
    history replay, not just live events. The cold-eyes reviewer
    flagged this as "looks correct on close read; explicit test
    missing." Pin the subscribe-after-start contract.
  - **C2** (Cluster R — comment) — `routes/media.py:38` URL
    builder uses `quote(machine.description)` which doesn't
    handle `:` (libretro-thumbnails uses `:` literally). Spec
    line 781 explicitly defers this to P05; add a one-line
    `# P04 minimal proxy — P05 swaps in proper escape rules`
    comment so future readers don't "fix" it ahead of P05.
  - **C3** (Cluster R — spec clarification) — R20 (`POST
    /api/copy/dry-run`) is silent on whether existing-playlist
    conflict surfaces (spec § Routes table just says "preflight
    + simulated plan; no job created"). Current implementation
    surfaces it via `pre.existing_playlist` in the `summary`
    field. Document the contract in the per-module spec at FP09
    close.

  Kind: review-fix.
  Source: indie-review-2026-05-01.
  Dependencies: P04.

---

## P05 — Media subsystem (closed 2026-05-02)

**Theme:** libretro-thumbnails URL builder + lazy fetch + sha256-
keyed disk cache through the API proxy.

**Long-form contract:**
[`docs/superpowers/specs/2026-04-27-roadmap.md` § Phase 5](docs/superpowers/specs/2026-04-27-roadmap.md).

### 🎨 Features

- ✅ **P05 — `media/` module.** URL escape rules
  (`&*/:\<>?\|"` → `_`); `urls_for(machine)`; async
  `fetch_with_cache(url, cache_dir)`; cache key = `sha256(url)`.
  Coverage target: ≥90%. Implementation shipped 2026-05-02
  (commit `44e33ef`); FP10 closing fix-pass folded in
  (commit `c4b91d4`). 423 tests pass; coverage 89.12%;
  `media/cache.py` 100%.
  Kind: implement.
  Lanes: media, api, tests.
  Dependencies: P04.

---

## FP10 — P05 indie-review fold-in (closed 2026-05-02)

**Theme:** the closing `/audit` + `/indie-review` pass on P05's
ship surfaced 5 actionable findings in `media/` + the R39 wiring.
`/audit` clean across ruff / bandit / gitleaks; all 5 actionable
items came from `/indie-review` against the cold-eyes brief.

### 🔍 Findings fold-in

- ✅ **FP10** [mame-curator-1002] **Fix-pass after P05 (media subsystem).**
  Lanes: media, api, tests.
  - **A1** (Tier 1) — `httpx.AsyncClient(timeout=10.0)` at
    `api/app.py:43` is missing `follow_redirects=True`. httpx
    defaults to `False`; any libretro 301/302 (rare today, but
    possible if upstream switches CDN or rename-redirects a thumb)
    surfaces as `MediaFetchError("upstream 301 ...")` → 502 to
    client. Add `follow_redirects=True` (one-line); regression
    test via `respx` returning 301 → final 200 must transit.
  - **A2** (Tier 2) — Empty 200 body silently caches as a zero-byte
    file at `media/cache.py:68-70`. `raw.githubusercontent.com`
    rate-limit interstitials and CDN edge cases occasionally
    return `200 + Content-Length: 0`. Subsequent requests hit the
    poisoned cache forever. Three-line guard:
    `if resp.status_code == 200 and not resp.content:
        raise MediaFetchError(f"empty body for {url!r}")`.
    Test via `respx` returning `httpx.Response(200, content=b"")`.
  - **A3** (Tier 3) — `routes/media.py:50` double-wraps the error
    detail: `MediaUpstreamError(f"upstream error: {exc!r}")` over
    a `MediaFetchError("upstream 500 for 'https://…'")` produces
    the user-facing message `upstream error: MediaFetchError("upstream
    500 for 'https://…'")`. Drop the prefix: `MediaUpstreamError(str(exc))`
    or `MediaUpstreamError(f"{exc}")` — chain `from exc` already
    preserves the typed cause for logs.
  - **A4** (Tier 3) — `media/cache.py:60-71` `path.exists()` race
    is benign today (`atomic_write_bytes` keeps the rename target
    intact across concurrent writes; POSIX read-after-rename is
    safe), but a future "verify checksum" or "delete corrupt
    entry" path would reintroduce TOCTOU. One-line comment next
    to the existence check naming the assumption ("cache writes
    are append-only via atomic_write_bytes; reads after a rename
    return the new inode's bytes — POSIX-safe").
  - **A5** (Tier 3) — `media/cache.py:65` interpolates both `{url!r}`
    and `{exc!r}` into the network-error message; the chained
    `__cause__` already carries the typed detail. Drop the second
    `!r`: `f"network error for {url!r}: {exc}"`.

  Kind: review-fix.
  Source: indie-review-2026-05-02.
  Dependencies: P05.

---

## P06 — Frontend MVP (closed 2026-05-02)

**Theme:** Vite + React 19 + Tailwind v4 + shadcn/ui browser UI
with virtualized grid, alternatives drawer, copy modal with SSE,
multiple themes/layouts, Cmd-K palette.

**Long-form contract:**
[`docs/superpowers/specs/2026-04-27-roadmap.md` § Phase 6](docs/superpowers/specs/2026-04-27-roadmap.md).
**Per-phase spec:** [`docs/specs/P06.md`](docs/specs/P06.md).

### 🎨 Features

- ✅ **P06** [mame-curator-1003-prereq] **Frontend MVP.** All 18 spec
  impl-steps shipped (scaffold + Tailwind v4 + 6 themes + 16 shadcn
  primitives + api/types.ts + check_api_types_sync.py CI gate +
  strings.ts + SPA static mount + 19 components/pages under TDD +
  ErrorBoundary + useKeyboard + App.tsx wiring + production build +
  Playwright smoke + frontend/dist/ committed). Closing /audit +
  /indie-review surfaced ~40 actionable findings → folded into FP11
  (closed 2026-05-02). 428 backend tests + 85 frontend tests + 1
  Playwright smoke pass; coverage 89.14% backend, ≥70% frontend gate.
  See `docs/journal/P06.md`.
  Kind: implement.
  Lanes: frontend, tests.
  Dependencies: P05.

---

## FP11 — P06 closing-review fold-in (closed 2026-05-02)

**Theme:** P06's closing /audit (eslint, tsc, gitleaks, trivy,
semgrep, check_api_types_sync) returned 8 ESLint findings (2
allowlisted as vendored / library-by-design; 6 actionable) +
1 semgrep finding (corroborates indie-review HelpPage XSS); all
other tools clean. /indie-review across 6 lanes (api-bridge,
library-components, alternatives-trio, pages, layout-+-hooks-+-app,
backend-static-mount, test-infra) returned ~40 actionable findings
spanning critical bugs, spec contract gaps, drift-gate hardening,
component lifecycle/quality, strings catalogue completeness,
standards/lint cleanups, zod ↔ pydantic mirroring, accessibility,
and test-infra polish.

### 🔍 Findings fold-in

- ✅ **FP11** [mame-curator-1003] **Fix-pass after P06 (frontend MVP).**
  All 10 clusters (A-J, ~40 actionable findings) closed across ~25
  commits since the P06 final ship at `e569214`. Notable post-A2
  follow-up: the `_SPAStaticFiles` carve-out needed Windows backslash
  normalisation (commit `8918cb5`) when CI surfaced two
  Windows-only test failures — Linux-runnable property test added
  to guard the regression.
  Lanes: frontend, api, tools, tests.

  **Cluster A — Critical bugs (4):**
  - **A1** — `App.tsx:63-64` palette nav uses
    `window.location.pathname = value.slice(4)` — hard reload, blows
    away QueryCache + React state on every Cmd-K nav. Replace with
    `useNavigate()` from react-router.
  - **A2** — `api/app.py:_SPAStaticFiles.get_response` falls back to
    `index.html` for ANY 404, including `/api/typo` and
    `/assets/missing.js`. Empirical: undefined `/api/*` returns SPA
    HTML (200) instead of a typed 404 envelope; missing assets
    cascade to `index.html` + browser parses HTML as JS → opaque
    SPA boot failure. Add prefix carve-outs for `api/`, `media/`,
    `assets/`.
  - **A3** — `CopyModal.tsx:137-144` abort flow offers only "Move
    to recycle bin"; spec / design §9 demand both keep AND recycle
    paths. `strings.copy.abortKeepFiles` + `abortRecycleFiles`
    already catalogued. Replace single ConfirmationDialog with a
    two-action prompt.
  - **A4** — `LibraryGrid.tsx:31-33,87` virtualization counts rows
    via constant `LAYOUT_GEOMETRY.columns` while the CSS uses
    `grid-cols-[repeat(auto-fill,minmax(...,1fr))]` — the two
    column counts decouple, so wide viewports clip cards inside
    280px slots and narrow viewports leave huge gaps. Replace
    auto-fill with explicit `repeat(${columns}, 1fr)` keyed off
    geometry; thread `cards_per_row_hint`.

  **Cluster B — Spec contract gaps (12):**
  - **B1** — `strings.ts` error-code map has 3 dead codes
    (`parent_not_found`, `winner_must_be_in_family`,
    `path_outside_allowed_roots`) never raised by backend; backend's
    actual `fs_sandboxed` has no friendly message. Reconcile with
    `mame_curator/api/errors.py`. Add a one-line CI assert that
    every `ApiException.code` ClassVar has a `strings.errors.byCode`
    entry.
  - **B2** — `LibraryPage.tsx:49,51` `config.data!.ui` non-null
    assertion crashes if user clicks Layout/Theme switcher before
    config GET resolves. Gate handlers on `config.isSuccess` or
    early-return.
  - **B3** — `SettingsPage.tsx:29` missing `snapshots` and `about`
    tabs (spec § 193 demands all 9). `updates` tab missing R36
    read-only banner (`strings.settings.banners.updateAvailable` /
    `setupReady` are catalogued but unused). `onSnapshotRestore`
    prop unused. Wire all three.
  - **B4** — `ActivityPage` URL state contract violated. Spec § 191:
    "Pagination via `?page=N&page_size=50` query params; URL state
    survives reload." Currently `App.tsx:96-97` hardcodes `page=1` /
    `pageSize=50` and stubs `onPageChange={() => {}}`. Wire via
    `useSearchParams()`.
  - **B5** — `AlternativesDrawer.tsx:41-44` `length === 1` renders
    "No alternatives — this is the only version" (description) AND
    iterates the one-element array showing the winner row; message
    contradicts content. Fix branching.
  - **B6** — `AlternativesDrawer` doesn't render boxart. Spec /
    design §8.521-523 demand "side-by-side strip of parent + clones
    with media". Add `<img src="/media/{name}/boxart">` per row.
  - **B7** — `CmdKPalette.tsx:67` `keywords={[item.label]}` passes
    only the label; typing the visible `hint` returns no match. Pass
    `keywords=[item.label, item.hint, sectionTitle].filter(Boolean)`,
    set `value={item.id}` instead of routing-shaped value.
  - **B8** — `App.tsx:82-141` Sessions / Activity / Stats / Settings
    / Help routes wired with hardcoded empty data + `() => {}`
    handlers. Spec § "Tests to write first" requires Sessions list /
    create / activate / deactivate to actually function. Build
    `useSessions` / `useActivity` / `useStats` / `useHelp` hooks
    (spec module layout lists them) and wire real container pages.
  - **B9** — `App.tsx:124` `<SettingsPage onPatch={() => {}}>` —
    config patches don't persist. Wire `useConfigPatch` (already
    exists in `hooks/useConfig.ts:12`).
  - **B10** — `App.tsx:155` Sonner Toaster reads from `next-themes`
    provider that's never mounted. Either drop `next-themes` and
    pass `theme={config.data?.ui.theme}` directly, or mount
    `<NextThemesProvider attribute="data-theme">`.
  - **B11** — `LibraryGrid.tsx:11-13` `groupKey` declared, never
    used; `cards_per_row_hint` from `useConfig` not threaded
    through (spec § 210 binding). Either implement grouped layout
    sectioning or document as deferred + drop the prop.
  - **B12** — `App.tsx:73` ErrorBoundary at single nesting depth.
    Spec impl-step 13 + `ErrorBoundary.tsx:17-25` docstring both
    mandate three levels: route, drawer, modal. Wrap each
    `<Route element={...}>` and the CmdKPalette+Toaster siblings.

  **Cluster C — Drift-gate hardening (4):**
  - **C1** — `tools/check_api_types_sync.py:97-100` `_INTERFACE_RE`
    body class `[^}]*` truncates at first `}` — nested object
    literals (`bar: { x: number }`) silently drop fields after the
    first `}`. Replace regex with brace-balanced scan, OR fail-loud
    on detection of `{`/`}` inside the body and require named
    interfaces. Same finding from L1-H1 + L6-F4 (≥2 lanes).
  - **C2** — `tools/check_api_types_sync.py:80-86` `_inherits_basemodel`
    matches any `*.BaseModel` attribute access (e.g.
    `pydantic_settings.BaseModel`) instead of `pydantic.BaseModel`
    only. Tighten or drop the attribute-access branch (no Pydantic
    model in this codebase uses `pydantic.BaseModel`).
  - **C3** — `tools/check_api_types_sync.py:156-166` duplicate-class
    handling silently warns + skips; should fail loud. The drift
    gate's reason for existing is to catch accuracy lapses; an
    internal lapse must fail the gate, not log to stderr.
  - **C4** — `client.ts:97-99` `apiRequest` returns `parse(schema,
    null)` on 204 but no zod schema in `types.ts` accepts `null`.
    R09 / R12 / R13b DELETE consumers will throw on first wire-up.
    Add explicit void path or require callers to pass `z.null()`.

  **Cluster D — Component lifecycle / quality (10):**
  - **D1** — `NotesEditor.tsx:19-22` `setDraft(initial)` + ref
    mutation inside `useEffect` triggers ESLint
    `react-hooks/set-state-in-effect`. Restructure to a derived-state
    pattern or per-game `key` prop on the editor.
  - **D2** — `NotesEditor.tsx:24-34` save-error state stuck across
    blurs (next blur with `draft === lastSaved.current` early-returns
    leaving error indicator); stale "Saved" can flash against new
    game on rapid game-switch mid-save. Add generation token (ref) +
    role="alert" on error.
  - **D3** — `ThemeSwitcher.tsx:35-44` `applyTheme` exported (breaks
    Fast Refresh per ESLint) AND mutates `<html data-theme>` from
    handler — races with `ThemeProvider.tsx:11-15` `useEffect`.
    Strip the handler-side `applyTheme` call; let provider be the
    single writer; move `applyTheme` to a separate utility module.
  - **D4** — `GameCard.tsx:42-52` div-as-button: `<Card role="button"
    tabIndex={0}>` loses native button semantics. Wrap in
    `<button type="button" className="contents">` for native focus
    + activation behaviour.
  - **D5** — `GameCard.tsx:21-27` badges use emoji as functional UI
    (`'🔀'`, `'✏️'`, `'💿'`, `'⚠️'`, `'📝'`). Coding-standards § 4 line 73:
    "No emojis as functional UI (decorative only); use proper icons
    (`lucide-react`)." Replace with `GitBranch` / `Pencil` / `Disc` /
    `AlertTriangle` / `StickyNote`.
  - **D6** — `FiltersSidebar.tsx:115-117` year-range slider bounds
    hard-coded `min={1975}` / `max={2025}`. Pull from `useStats()`
    `by_decade` or compute from cards.
  - **D7** — `FiltersSidebar.tsx:54-67` debounce useEffect both
    clears `debounceRef.current` inside the effect AND in the
    cleanup; collapse to the canonical
    `setTimeout` + `return () => clearTimeout(id)` shape. Latent
    no-op redundant dispatch on rapid flux.
  - **D8** — `CopyModal.tsx:118-133` UI traps user in `terminating`
    / `finished` / `aborted` states (Pause shown disabled, Cancel
    still active firing abort against terminal job, no Done/Close
    affordance). Collapse the action row into a state machine.
  - **D9** — `CopyModal.tsx:78-81` warning list `<li key={i}>` —
    array index as React key, but `slice(-3)` shifts positions
    on each new SSE event. Use payload-id-based key.
  - **D10** — `ConfirmationDialog.tsx:22` `FORBIDDEN_LABELS` set
    is haphazard (3 casings of OK, only one of Yes; missing
    common alternates "Continue", "Proceed", "Done", "Submit",
    "Yes, continue"). Normalise via `.toLowerCase()` and add.

  **Cluster E — strings.ts catalogue completeness (sweep):**
  - **E1** — Hoist all inlined English from `FiltersSidebar`
    (4 switch labels + 7 misc strings), `LayoutSwitcher`
    (4 layout labels), `ThemeSwitcher` (6 theme labels),
    `DryRunModal` ("Cancel" + duplicated section labels),
    `SessionsPage` (4 metadata labels + 2 aria-labels),
    `ActivityPage` (timestamp coercion comment),
    `SettingsPage` (~14 switch labels + 3 help paragraphs +
    "Cache:" etc.), `AlternativesDrawer` (3 dynamic strings:
    family-summary, button aria-selected/use), `WhyPickedPanel`
    (2 strings), `NotesEditor` ("Notes" label),
    `ConfirmationDialog` ("Cancel"), `ErrorBoundary` ("Try again").
    Add namespaces to `strings.ts` as needed.

  **Cluster F — Standards / lint cleanups (4):**
  - **F1** — `tsconfig.app.json` missing `"strict": true`
    (coding-standards § 4 line 65 hard requirement). Add and clean
    up any latent null-handling errors that surface.
  - **F2** — `HelpPage.tsx:52` bogus `// eslint-disable-next-line
    react/no-danger` — the rule isn't configured (eslint emits
    "Definition for rule 'react/no-danger' was not found"). Drop
    the comment.
  - **F3** — `ErrorBoundary.tsx:43` unused
    `eslint-disable no-console` directive — ruleset doesn't flag
    `console.error` here. Drop.
  - **F4** — `LibraryPage.tsx:59` `_name` parameter declared but
    unused. Either use it (sessions save callback) or drop
    `(_name)` to `()`.

  **Cluster G — zod ↔ pydantic mirroring (4):**
  - **G1** — `types.ts:74-77` mirror of `Rom.size: int | None =
    Field(default=None, ge=0)` is `z.number().int().nullable()` —
    `ge=0` not mirrored. Add `.nonnegative()`. Sweep for other
    `Field(...)` constraints.
  - **G2** — `types.ts:24` `z.iso.datetime()` rejects naive
    datetimes and offset suffixes — fragile to backend datetime
    drift (today every emitter passes `tz=UTC` so works, but
    one missed `tz=UTC` breaks the FE). Use
    `z.iso.datetime({ offset: true, local: true })`.
  - **G3** — `mame_curator/api/schemas.py:221` `SessionUpsertRequest`
    is the only schema NOT `frozen=True` — drift from rest of
    `schemas.py`. Either flip or comment why request bodies opt
    out.
  - **G4** — `client.ts:39-47, 116-126` `parse<T>` discards zod
    `result.error.issues[]` instead of mapping into
    `FieldError[]`. Same pattern in network-error path collapses
    `status: 0` across two distinct failure modes (no network vs
    bad body). Translate issues; use `-1` sentinel for
    never-reached-the-wire.

  **Cluster H — Acceptance + accessibility (8):**
  - **H1** — `index.css:189` references `'Inter'` but no
    `@font-face` rule loads it; spec § 305 forbids remote
    stylesheets. Either add `@fontsource/inter` + `@import`, or
    drop `'Inter'` from the stack.
  - **H2** — `package.json:7` `engines.node: ">=20.0.0"` weaker
    than spec § 285 ("Determinism across Node patch versions
    is not guaranteed; the CI gate runs npm ci on the pinned
    version"). Pin `"20.x"` exactly.
  - **H3** — `index.css` `[data-theme="pacman"]` accent /
    accent-foreground contrast ratio ≈ 4.0:1 — borderline AA-text.
    Either bump `--accent-foreground` to oklch(1 0 0) or darken
    `--accent` to L=0.45.
  - **H4** — `HelpPage.tsx:53` `dangerouslySetInnerHTML` from
    R38 — backend trust boundary today, but the lane brief
    flagged the future risk if help content ever sources from
    upstream. Add `// FIXME(security, 2026-05-02): replace with
    sanitized renderer when help content sources from outside
    `data/help/``. Optional: add DOMPurify (~14 kB gzipped).
    (Corroborated by semgrep `react-dangerouslysetinnerhtml`.)
  - **H5** — `HelpPage.tsx:38-41` selected-topic state visible
    only as `bg-muted font-semibold`; screen readers get no
    signal. Add `aria-current="page"` to the selected button.
    Plus: add a "Loading topic…" skeleton when `topicHtml === ''`
    but a `selectedSlug` is set (currently renders an empty
    `<article>`).
  - **H6** — `StatsPage.tsx` `<section>` has no
    `aria-labelledby` link to the `<h2>`. WCAG 2.2 AA wants the
    link; add `id` to `<h2>` and `aria-labelledby` to `<section>`.
  - **H7** — `ActivityPage.tsx:43` timestamps render as plain
    text inside a `<span>`. Wrap in `<time dateTime={...}>` for
    semantic accessibility.
  - **H8** — `SessionsPage.tsx:70,78`
    `aria-label={`Activate ${name}`}` / `Delete ${name}` are
    English strings. Move to
    `strings.sessions.actions.activateAriaLabel(name)` etc.
    (Subset of E1; called out separately because it's
    AT-affecting.)

  **Cluster I — Test infrastructure (3):**
  - **I1** — `frontend/src/test/handlers.ts:5-7` mocks `/api/health`
    which doesn't exist on the backend AND isn't called from
    frontend code. Either drop the handler (preferred) or wire
    a real `/api/health` route on the backend.
  - **I2** — `frontend/vitest.config.ts:17` `exclude:
    ['node_modules/**', 'dist/**', 'e2e/**']` replaces Vitest's
    default exclude (which adds e.g. `**/.idea/**`,
    `**/{karma,…}.config.*`). Spread `configDefaults.exclude`
    and add `'e2e/**'`.
  - **I3** — `frontend/playwright.config.ts:33,39`
    `reuseExistingServer: !process.env.CI` on the backend can
    silently reuse a dev backend running against real config
    (not the fixture YAML) on a developer's machine. Either set
    `false` for the backend specifically, or assert the fixture's
    `paths.source_dat` at globalSetup.

  **Cluster J — Spec sync (drift mid-implementation):**
  - **J1** — `docs/specs/P06.md:101-122` toolchain table version
    pins were "latest stable as of 2026-05-02" but `npm create
    vite@latest` resolves to newer minor versions: Vite ^6 →
    ^8.0.10, TypeScript ~5.6 → ~6.0.2, framer-motion ^11 →
    ^12, zod ^3 → ^4, lucide-react ^0.4xx → ^1.x, eslint
    9 → ^10. Sync the table to actual installed versions.
  - **J2** — `docs/specs/P06.md` § "Static-file serving" claim
    that `html=True` falls back for `/<anything>` is wrong —
    vanilla StaticFiles only redirects on directory hits. The
    `_SPAStaticFiles` subclass corrects this. Spec needs a
    one-line update.
  - **J3** — `docs/specs/P06.md` § "Static-file serving"
    `parents[2]` should be `parents[3]` (relative to
    `src/mame_curator/api/app.py`).
  - **J4** — `docs/specs/P06.md:161` lists
    `parent_not_found` / `winner_must_be_in_family` /
    `path_outside_allowed_roots` as codes the UI must handle
    distinctly, but backend issues none of these (uses
    `override_not_found` / no validator / `fs_sandboxed`
    respectively). Spec must reconcile (see B1).

  Source: P06 closing /audit + /indie-review (6 lanes), 2026-05-02.
  Dependencies: P06 (closed at the same SHA as FP11).
  See `docs/journal/FP11.md`.

---

## FP12 — Settings page list editors + path picker (planned)

**Theme:** P06's spec § "Out of scope" line 511 declared "all
Settings-page controls are built here," but FP11 only closed the
~11 binary toggles + theme/layout pickers — every list-shaped or
free-text field still needs hand-editing of `config.yaml`. FP12
closes that gap with two reusable UI primitives (`<ChipListEditor>`
+ `<DragReorderList>`) plus the long-deferred `<FsBrowser>` path
picker (R29-R34 backend already shipped in P04).

`UiConfig.cards_per_row_hint` is **not** in scope here — spec § 210
explicitly defers it to P07+. The `default_sort` dropdown is in
scope (a thin select control, no primitive needed).

### 🎨 Features

- 📋 **FP12** [mame-curator-1004] **Settings-page expansion: list editors + path picker.**
  Lanes: frontend, tests.
  - **A — Chip list editor primitive.** `<ChipListEditor value={string[]}
    onChange={(next) => …} placeholder="Add genre…">`. Used by 7 fields:
    `filters.drop_{categories,genres,publishers,developers}` (4) +
    `picker.preferred_{genres,publishers,developers}` (3). Free-text add
    via Enter; chip click removes; supports paste-comma-separated for
    bulk import. Coverage: ≥80%.
  - **B — Drag-reorder list primitive.** `<DragReorderList items={…}
    onChange={(next) => …}>`. Used by `picker.region_priority` (one
    field). Keyboard accessible: ArrowUp/ArrowDown to reorder when
    focused. Pointer-drag via dnd-kit (no new top-level dep).
  - **C — Number-input pair for year range.**
    `filters.drop_year_before` + `drop_year_after` (both `int | null`).
    Use shadcn `<Input type="number">`; null state via a "no limit"
    toggle next to the field. Min/max bounds: 1971..currentYear.
  - **D — `default_sort` dropdown.** `<Select>` over the four
    `'name' | 'year' | 'manufacturer' | 'rating'` literals. UI tab.
  - **E — `updates.channel` dropdown.** `<Select>` over
    `'stable' | 'dev'`. Updates tab.
  - **F — Editable `media.cache_dir`.** ✅ shipped 2026-05-04 —
    Media tab gets an `<Input>` (controlled via local draft;
    patches `onPatch({media:{...,cache_dir}})` on blur when the
    value changes) plus a "Browse…" button that mounts
    `<FsBrowser>` directory mode. Pick → updates draft + patches.
    `FsBrowser` is conditionally mounted (`{open && <FsBrowser />}`)
    so its `useFs*` hooks don't fire until the user actually
    clicks Browse — keeps existing pure-prop SettingsPage tests
    free of MSW handlers. 2 SettingsPage integration tests.
  - **G — `<FsBrowser>` path picker.** ✅ shipped 2026-05-04 —
    self-contained modal owning its own `useFs*` hooks (no
    pure-prop seam — single import via `<FsBrowser open
    onOpenChange onPick mode initialPath />`). Quick-jump buttons
    for Home (R30) + drive roots (R31) + allowed roots (R32).
    `path` derived from a `userPath` state + `home.data` fallback
    so the default-on-async-load path doesn't need a setState-in-
    effect. Listing 403 with `fs_sandboxed` surfaces a
    `ConfirmationDialog` whose action label is the design §8
    concrete form `"Grant access to <path>"`; on confirm we POST
    R33 and react-query auto-refetches the listing. Mode prop:
    `'directory'` (default) hides files; `'file'` shows files and
    clicking one fires onPick. 10 MSW-backed unit tests at
    `frontend/src/components/settings/__tests__/FsBrowser.test.tsx`
    cover open/closed, list/navigate/up, pick directory + file,
    cancel, grant prompt + grant POST. Will be consumed by F + H.
    Used by:
      - `paths.{source_roms,source_dat,dest_roms,retroarch_playlist}`
        edit-in-place from the Settings → Paths tab (was read-only
        in FP11; spec § 304 demanded `<FsBrowser>` here).
      - `paths.{catver,languages,bestgames,mature,series,listxml}`
        reference-INI overrides (P08 wizard fills these initially;
        Settings can edit afterwards).
      - `media.cache_dir` (F above).
  - **H — Settings → Paths now in-place editable.** ✅ shipped
    2026-05-04 — `PathRow` helper (`<Label>` + `<Input>` + Browse
    button → `<FsBrowser>`) renders 4 rows: `source_roms`,
    `dest_roms`, `source_dat` (`mode='file'`), `retroarch_playlist`
    (`mode='file'`). Inputs hold a local draft and patch on blur
    when the value changed. DAT swap surfaces a destructive
    `ConfirmationDialog` (action label `"Swap DAT to <path>"`)
    rather than patching immediately — switching the DAT replaces
    every machine in the library and is expensive
    (`replace_world` rebuilds the whole world state). 5
    SettingsPage integration tests cover render / patch-on-blur /
    confirm-required / confirm-accept / confirm-cancel.
  - **I — Settings → Snapshots tab implementation.** ✅ shipped
    2026-05-04 — `SnapshotsTab` primitive with loading / error /
    empty / list states; per-row "Restore" opens
    `ConfirmationDialog` whose action label is the design §8
    concrete form `"Restore N files"` (not generic "OK").
    `useSnapshots` + `useSnapshotRestore` hooks live in
    `useConfig.ts`; `App.tsx` extracts `SettingsRoute` per the
    FP11 § B8 container pattern, owning all four config-related
    queries. `useConfigPatch.onSuccess` invalidates the snapshots
    query so a fresh PATCH surfaces the new entry on next read.
    8 unit tests + 2 SettingsPage integration tests; 133 frontend
    tests total.
  - **J — Settings → Backup tab (Export / Import).** ✅ shipped
    2026-05-04 — `BackupTab` primitive (Export button +
    file-picker Import + ConfirmationDialog whose action label is
    the design §8 concrete form `"Replace settings from <file>"`)
    plus a Phase-8 forward-link line. R18 / R19 are both JSON
    POSTs (the roadmap's "R19 multipart" hint was stale — the
    backend at `config.py:170 + 186` takes / returns
    `ConfigExportBundle`). `useConfigExport` + `useConfigImport`
    hooks live in `useConfig.ts`; `SettingsRoute` does the
    download dance (Blob → `<a download>` → revoke) and the
    upload parse step (`File.text()` → `JSON.parse` → mutate).
    8 unit tests + 1 SettingsPage integration test; 142 frontend
    tests total.

  Source: spec § "Out of scope" line 511 + FP11 § J spec sync;
  filed 2026-05-02 from user follow-up after FP11's closing
  /audit highlighted the list-editor gap.
  Dependencies: FP11 (still 🚧).

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
  Coverage targets: updates ≥85%, help ≥90`.
  **Settings expansion:** `UiConfig.cards_per_row_hint` UI control
  (`'auto' | 4 | 5 | 6 | 8` selector) lands here per `docs/specs/
  P06.md:210` ("YAML-only in P06; the Phase-7+ Settings expansion
  adds a UI affordance"). Implements as a `<Select>` next to the
  layout switcher in Settings → UI tab.
  Kind: implement.
  Lanes: updates, help, downloads, frontend, tests.
  Dependencies: P06, FP11, FP12.

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

## P10 — Media coverage expansion (planned, post-v1)

**Theme:** raise box-art / snapshot / marquee coverage by
fanning out to multiple metadata sources beyond the libretro-
thumbnails set shipped in P05. The current single-source
fallback misses progettoSnaps-only games, recent additions,
and most Japanese-text obscurities.

Default placement is **post-v1.0.0** — none of these blocks
release. The smallest sub-bullet (P10 § A — progettoSnaps as a
second URL source, no auth, same shape as libretro-thumbnails)
could be promoted ahead of P07 if the user wants more art
coverage in the v1 cut; it's a one-day surface change to
`media/urls.py` plus a new fixture pack.

### 🎨 Features

- 📋 **P10** [mame-curator-1005] **Media coverage expansion.**
  Lanes: media, frontend, tests.
  - **A — progettoSnaps fallback URL source.** Add
    `https://www.progettosnaps.net/snap/<shortname>.png` (and
    sibling marquees / titles / cabinets / flyers) to
    `media/urls.py` as a secondary builder. Cache contract is
    identical to P05 (sha256-keyed, lazy-fetch). Wire into
    `MediaUrls` so the resolver tries libretro first, falls
    back to progettoSnaps on 404. **Yield estimate:** closes
    60–70% of the missing-art gap. **Effort:** ~1 day.
  - **B — ArcadeDB (arcadeitalia.net) JSON API.** REST endpoint
    `service_scraper.php?ajax=query_mame&game_name=<shortname>`
    returns title / year / manufacturer + screenshot / marquee
    / flyer URLs. Highest-quality images of the bunch but
    rate-limited; needs a polite client (per-host backoff,
    `User-Agent` set, ≤1 req/s). Folds into the same lazy-fetch
    cache. **Effort:** ~2 days incl. polite-client primitive.
  - **C — Wikipedia / MediaWiki API for prose blurbs.** Not
    primarily for images — the goal is one or two sentences of
    flavor text on the alternatives drawer's `WhyPickedPanel`.
    Where Wikipedia hosts a licensed image (rare for arcade
    games), opportunistically pull it. **Effort:** ~1 day.
  - **D — Mobygames API (port-cover fallback).** Console ports
    of arcade titles often have higher-resolution box art than
    the arcade originals. Mobygames has an API key; we'd need
    to handle quota and credit attribution per their TOS.
    Lower priority than A/B. **Effort:** ~2 days incl. auth.
  - **E — EmuMovies (deferred).** Best video coverage, but
    requires a paid login + bandwidth subscription per their
    TOS — outside scope for an MIT-licensed open-source
    project. Capture as "considered, declined" unless a user
    requests it explicitly with their own credentials. No
    immediate work.
  - **F — Settings: per-source enable/disable.** New
    `media.sources` array in `AppConfig` with the source IDs
    above; Settings → Media tab gets a checkbox group. Lets
    users opt out of slow / rate-limited sources (e.g. for
    offline use). **Effort:** ~0.5 day after A+B land.

  Source: user follow-up question 2026-05-04 mid-FP12 ("Are
  there additional sites that game metadata can be scraped
  from? There are quite a lot of games without graphics").
  Captured + recommended placement post-v1; user accepted the
  same day.
  Kind: implement.
  Dependencies: P05 (media subsystem must exist), FP10
  (closed). No dependency on FP12 / P07 / P08 / P09.

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

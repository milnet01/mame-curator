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

## FP12 — Settings page list editors + path picker (closed 2026-05-04)

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

- ✅ **FP12** [mame-curator-1004] **Settings-page expansion: list editors + path picker.**
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

## FP13 — FP12 closing-review fold-in (closed 2026-05-04)

**Theme:** FP12's closing `/audit` (ruff / ruff format / mypy /
bandit / eslint / gitleaks / trivy / semgrep) was clean across
the FP12 surface; the 3-lane `/indie-review` (primitives /
FsBrowser / SettingsPage wiring) returned **22 actionable
findings + 1 deferred false positive**, batched into 5 thematic
clusters. Cross-cutting theme flagged by 2 of 3 lanes: silent
react-query mutation errors — `useFsGrantRoot`, `useConfigPatch`,
and `useSnapshotRestore` all fire-and-forget without `onError`,
so a 422/404/500 from the API is invisible to the user.

False positive deferred (not folded here): semgrep flagged
`dangerouslySetInnerHTML` on `frontend/src/pages/HelpPage.tsx:67`
— out of FP12 scope (P06/FP11 surface). Folded into the next
debt-sweep, not allowlisted (the rule is real; the trust-boundary
mitigation is an FP11 § H4 `FIXME(security)` comment that the
debt-sweep should resolve).

### 🎨 Features

- ✅ **FP13** [mame-curator-1006] **FP12 closing-review fold-in.**
  Lanes: frontend, tests.
  - **A — Mutation observability (cross-cutting).**
    - A1: `useConfigPatch.onError` → toast.error via `strings.errors.byCode`. Patch failures invisible today.
    - A2: `useSnapshotRestore.onError` → toast.error. `snapshot_not_found` 404 invisible today.
    - A3: `useFsGrantRoot.onError` → inline error in `<FsBrowser>` modal + `disabled={grant.isPending}` on the AlertDialogAction.
    - A4: PATCH `restart_required: true` → banner in Settings page when set; today the flag is dropped on the floor (reachable via Import once a different `server.port` lands).
  - **B — Destructive-confirm correctness.**
    - B1: `BackupTab` Import — pre-confirm structural validation via `ConfigExportBundleSchema.safeParse(parsed)` before showing the "Replace settings from <file>" dialog; surface zod issues with actionable copy.
    - B2: DAT-swap cancel — `key={config.paths.source_dat}` on the source_dat `<PathRow>` so Cancel re-mounts the input and `draft` re-seeds from `value`. Today Cancel closes the confirm dialog but leaves the rejected path string in the input.
    - B3: `BackupTab` Import — file-size pre-check (≤5MB cap) before `await file.text()`; surface `backupImportTooLarge`. Prevents 100MB+ paste freezing the tab on the main thread.
  - **C — FsBrowser correctness + UX.**
    - C1: `useFsListing` query-key collision when `path === null`. Today the disabled query and a hypothetical `path=''` listing share `['fs','list','']`. Branch on null instead of `path ?? ''`.
    - C2: Sandbox confirm cancel-path lockout — when the user cancels the grant prompt and `home.data` hasn't loaded, the listing stays 403 and the dialog immediately re-opens (no exit). Close `<FsBrowser>` entirely on cancel or revert to last-known-good path.
    - C3: `mode='file'` "Use this directory" footer button — hide when `mode !== 'directory'` instead of leaving a permanently-disabled button with the wrong label.
    - C4: Quick-jump dedupe — drive roots that already appear in `allowed.data.roots` render twice today (cosmetic).
    - C5: goUp disabled at allowlist root — add `title="Already at the top of the allowed area"` so disabled state is discoverable.
    - C6: `useFsGrantRoot.onSuccess` — also `qc.invalidateQueries({ queryKey: ['fs','list'] })` so freshly-granted directories refetch in any other open FsBrowser instance.
    - C7: `useFsHome` error fallback — surface inline "could not detect home directory; pick a drive root to continue" instead of silent empty path bar.
  - **D — Accessibility (WCAG 2.2).**
    - D1: `ChipListEditor` — split chip text from the remove button (`<span>{item}</span><button aria-label={`Remove ${item}`}>×</button>`) so AT announces chip content separately from the affordance.
    - D2: `DragReorderList` — `aria-live="polite"` region announcing "Moved <item> to position N of M" after each ArrowUp/ArrowDown / button-click. Currently silent to AT.
    - D3: `DragReorderList` — adopt the FP12 § Step 1 research contract's `role="listbox"` + `aria-activedescendant` pattern OR add an inline comment justifying the simpler `role="list"` since user elected arrow-button reorder over dnd-kit (Karpathy push-back).
    - D4: SettingsPage Browse-button `aria-label` template literal at line 118 → `strings.settings.fsBrowseAriaLabel(label)` per coding-standards §4.
  - **E — Standards compliance + minor hardening.**
    - E1: `SettingsPage.tsx` 551 lines vs `coding-standards.md §2` hard-cap 350. Extract `FiltersTab` / `PickerTab` / `UpdatesTab` / `MediaTab` per the existing `SnapshotsTab`/`BackupTab` shape; SettingsPage becomes a thin tab dispatcher under 200 lines.
    - E2: `YearRangeEditor` — `Number(raw)` NaN guard + `min..max` clamp at trust boundary (paste of `"abc"` or `"1850"` currently produces `NaN`/out-of-range that flows to the patch as `null` or rejected).
    - E3: Export filename — `.toISOString().slice(0, 19).replace(/[:T]/g, '-')` drops the millisecond noise (`2026-05-04T13-22-09-455Z` → `2026-05-04-13-22-09`).
    - E4: `DragReorderList` — `key={`${item}-${index}`}` OR document item-uniqueness precondition (today depends on caller dedup).
    - E5: `useFsListing` — gate URL build behind `path !== null` instead of `path ?? ''` so the disabled query doesn't construct a misleading URL.
    - E6: `BackupTab` Import — surface `FieldError[]` from server response inline rather than only the generic error string.

  Source: FP12 closing `/audit` (clean across the FP12 surface)
  + 3-lane `/indie-review` (primitives, FsBrowser, SettingsPage
  wiring); filed 2026-05-04. All 22 findings came from the
  cold-eyes multi-agent review — static analysis surfaced zero
  on this lane.
  Dependencies: FP12 (still 🚧).

---

## FP24 — P15 closing-review fold-in (closed 2026-05-08)

**Theme:** P15's closing `/audit` (semgrep + gitleaks + eslint + trivy on top of CI-clean ruff/mypy/bandit) returned 4 actionable lint findings; the 8-lane `/indie-review` (backend + cart hook + SSE hooks + discovery surface + selection surface + LibraryPage + AppShell + types/e2e) added 30+ cross-cutting and per-lane findings. P15's `/close-phase` cannot close until these are folded. Findings batched into three tiers; all share a single `FP24` ID per the FP19/FP12 closing-review precedent. **All Tier 1, Tier 2, and Tier 3 closed across 13 commits 2026-05-08.**

### 🐛 Bug fixes

- ✅ **FP24** [mame-curator-1025] **P15 closing-review fold-in.**
  Lanes: api, frontend, e2e, docs.

  **Tier 1 — Critical / ship-this-week:**
  - **A — `JobEvent.payload` key mismatch** (`useCopySession.ts:75-76`). Backend emits `total_files` / `total_bytes` (verify against `api/jobs.py:207-214`); frontend reads `files_total` / `bytes_total`. Progress bar pinned at 0/0 every copy job. One-line fix per key, but verify the actual payload shape before patching.
  - **B — CartBar GB shows filter-result total, not cart total** (`pages/LibraryPage.tsx:325`). `totalSizeBytes={games.data?.total_bytes ?? 0}` — that's the FILTERED LIBRARY's bytes, not the cart's. Misleads users about copy size. Fix path: relabel as "filtered library" OR remove the GB figure until per-cart-item byte sum is available (requires `useCart.totalBytes` implementation OR a server-side `/api/copy/dry-run`-derived size).
  - **C — AppShell Cart NavLink broken** (`components/layout/AppShell.tsx:71-84`). `to="/"` shadows the Library NavLink — both highlight active simultaneously, click re-navigates to `/` with no panel toggle. Fix: convert to `<button onClick={...}>` that triggers `setCartExpanded(true)` (lift cart-expanded state to App.tsx alongside the cart hoist), OR add a dedicated `/cart` route.
  - **D — `OnboardingBanner.tsx:25` `setState`-in-effect** (eslint `react-hooks/set-state-in-effect`, hard error). The `useEffect` on `cartHasItems` calls `setDismissed(true)`. Fix: derive visibility from `!dismissed && !cartHasItems`, write to localStorage in the same effect WITHOUT `setDismissed`, OR move the persistent-dismiss callback to `LibraryPage` to fire on first cart.add.
  - **E — `GameCard.tsx:60-79` nested `<button>` inside `<button>`** (invalid HTML5). Outer button-with-`className="contents"` wraps the `+Add` inner button; `e.stopPropagation()` makes it work in most browsers but AT behavior is undefined. Fix: replace outer with `<div role="button" tabIndex={0} onKeyDown={...}>` so the `+Add` stays a native button.
  - **F — `ValidateRequest.short_names` unbounded** (`api/schemas.py:164-167`). User-controlled list with no length cap. Fix: `Field(max_length=10_000)` on `short_names` + per-item `Annotated[str, Field(max_length=64)]`.
  - **G — `useCart` localStorage unavailability silent** (`hooks/useCart.ts:54-63`). Spec § 8 risk 3 mandates a one-time toast. The `storageBroken` ref is set in the catch block but never surfaced. Fix: return `isStorageBroken: boolean` from the hook + `LibraryPage` fires `toast.warning(strings.library.cart.storageUnavailableToast)` in a `useEffect`.

  **Tier 2 — Hardening / correctness:**
  - **H — SSE double-`start()` leaks orphan stream** (`useCopySession.ts:65`). No guard before opening a new EventSource. Fix: `closeStream()` before `new EventSource(...)`.
  - **I — SSE `onerror` closes unconditionally** (`useCopySession.ts:116`). Eliminates EventSource auto-reconnect on transient drops. Fix: only close when `readyState === EventSource.CLOSED`; surface non-terminal drops via toast or progress-bar warning state.
  - **J — SSE unmount race** (`useCopySession.ts:44-45`). Component unmounts after `start.mutate()` but before `onSuccess` → orphan stream survives until `job_finished`. Fix: track a `cancelled` flag in a ref, gate `onSuccess` body on it.
  - **K — `JSON.parse` on SSE data with no try/catch** (`useCopySession.ts:67`). Malformed server push throws inside `onmessage`; React doesn't catch. Fix: try/catch + `console.warn` on parse failure.
  - **L — `resolveConflict` accepts typed param it ignores** (`useCopySession.ts:141-146`). User clicks Resolve, decision discarded silently. Fix: drop the parameter (signature `()`) or `console.warn` to make the discard traceable; document the no-backend-endpoint constraint.
  - **M — `handleBulkAdd` adds page slice, not filter total** (`pages/LibraryPage.tsx:161`). Label promises "Add all 6847", action delivers up to `pageSize=200`. Fix path: (a) add `GET /api/games/ids?<filter>` returning all matching shortnames, (b) iteratively fetch all pages before `addAll`, OR (c) cap label to `min(total, pageSize)` and amend the spec contract. (a) is spec-faithful.
  - **N — `handleCopy` double-submit guard missing** (`pages/LibraryPage.tsx:176-197`). Two clicks within validate→start latency fire two start() calls. Fix: disable Copy button while `validateCart.isPending || copySession.state` is non-null (pass disabled flag through CartBar).
  - **O — Clear all missing AlertDialog** (`components/library/CartPanel.tsx:55`). Coding-standards § 4 mandates AlertDialog for destructive ops; cart has no undo. Fix: wrap `onClearAll` in an AlertDialog naming the count.
  - **P — FeaturedTilesRow tile buttons have no accessible name** (`components/library/FeaturedTilesRow.tsx:53-59`). Button's accessible name is the concatenation of `<p>` children — "Capcom ClassicsCapcom CPS-1...38 games" with no separators. Fix: `aria-label={tile.title}` on the `<button>`.
  - **Q — Focus ring invisible on GameCard** (`components/library/GameCard.tsx:60-65`). `className="contents"` removes the button's CSS box; the brand `focus-visible:ring-2 focus-visible:ring-ring` on Card never fires because Card is a `<div>`. Fix lands with E (replace outer button with `role="button"` div + ring on the wrapper).
  - **R — `useCart.readInitial` doesn't validate `chosenVariant` type** (`hooks/useCart.ts:28-33`). A persisted entry `{ shortName: "sf2", chosenVariant: 123 }` passes the filter. Fix: extend the predicate to assert `typeof i.chosenVariant === 'undefined' || typeof i.chosenVariant === 'string'`.
  - **S — `useCart.addAll` truncation silent** (`hooks/useCart.ts:89-91`). Spec § 8 risk 6 mandates a toast on truncation. Fix: return `{ added: number, truncated: number }` so the caller can fire `toast.warning(strings.library.cart.maxCartReachedToast(MAX_CART_SIZE))`.
  - **T — Stale-closure risk on cart auto-clear effect** (`pages/LibraryPage.tsx:200-206`). `eslint-disable-next-line react-hooks/exhaustive-deps` with no comment naming the stability invariant. Fix: confirm `cart.clear` and `copySession.reset` are stable `useCallback` refs in their respective hooks; document the invariant in the suppression comment.
  - **U — Raw `fetch` in `fetchTileCount`** (`pages/LibraryPage.tsx:51-61`). Coding-standards § 4: "No raw `fetch` in components." Fix: route through `apiRequest` from `@/api/client`.
  - **V — `openedWinner` re-creation on every render** (`pages/LibraryPage.tsx:107`, eslint pre-finding). `cards = games.data?.items ?? []` creates a new array reference each render-while-loading; downstream `useMemo` re-runs needlessly. Fix: `const cards = useMemo(() => games.data?.items ?? [], [games.data])`.
  - **W — CartBar missing `aria-expanded` + `aria-controls`** (`components/library/CartBar.tsx:56-65`). WAI-ARIA disclosure-button pattern requires both. Fix: add both; CartPanel needs `id="cart-panel"` to anchor.
  - **X — CartBar `bulkAddTotal=0` renders "Add all 0"** (`components/library/CartBar.tsx:45`). Confusing affordance when filter returns zero. Fix: change guard to `bulkAddTotal !== null && bulkAddTotal > 0`.
  - **Y — Banner roles wrong** (`components/library/{ListxmlBanner.tsx:25, OnboardingBanner.tsx:47}`). `role="alert"` on listxml is too aggressive for an informational notice; `role="status"` on onboarding misuses the live-region role on a static banner. Fix: ListxmlBanner → `role="status"`; OnboardingBanner → `role="note"` or remove the role.
  - **Z — Tile counts flash "0 games" on load** (`pages/LibraryPage.tsx:122`). `(tileQueries[idx].data as ...)?.total ?? 0` → 0 during loading; FeaturedTilesRow checks `count !== undefined` so a literal `0` displays. Fix: omit the `?? 0` so loading shows undefined and the tile suppresses the count label.

  **Tier 3 — Structural / debt:**
  - **AA — Hardcoded user strings** (`GameCard.tsx:92` `'+Add'`; `CartPanel.tsx:26` `aria-label="Cart contents"`). Add `strings.library.cart.add` and `strings.library.cart.contentsRegionLabel`; reference both. (Coding-standards § 4 single-source-of-truth.)
  - **BB — `listxml_available` zombie field** (`api/schemas.py:472`, `api/routes/stubs.py`). Computed server-side but no frontend consumer (banner re-derives from `exists` + `cloneof_map_size`). Fix: either wire ListxmlBanner to consume it as the single source of truth, or delete the field entirely.
  - **CC — `_probe_path kind` parameter unused** (`api/routes/stubs.py:27-31`). Required keyword arg silently discarded. Fix: implement `path.is_dir()` / `path.is_file()` validation, OR delete the parameter.
  - **DD — `Badge.BIOS_MISSING` never appended** (`api/routes/games.py:39-50`). Enum value declared, filter param exists, but `_badges()` doesn't add it. Fix: append when `short in world.bios_chain`, OR document as filter-only.
  - **EE — `schemas.py` over hard cap** (557 / 500 lines). Coding-standards § 2. Fix: extract a `schemas_setup.py` for setup/updates models.
  - **FF — `dryRunConfirmDeferred` dead string** (`strings.ts:195-197`). No consumer post-F11. Fix: delete.
  - **GG — `FeaturedTile` type duplicated** between `strings.ts` (inline cast) and `FeaturedTilesRow.tsx` (export). Fix: hoist to `strings.ts` or `api/types.ts` and import.
  - **HH — Tile count uses `page_size=1`, spec said `0`** (`pages/LibraryPage.tsx:52`). Backend rejects 0 (`Query(50, ge=1, le=500)`). Fix: update spec § 4.2 to reflect `page_size=1` rationale; consider a count-only `?count_only=true` parameter to skip the unused `items` payload.
  - **II — `Cmd+K` kbd label on Linux** (`components/layout/AppShell.tsx:123`). Project runs on Linux per CLAUDE.md; `useKeyboard` uses `meta` (= Super on Linux). Fix: detect platform and label accordingly, OR rename to `Ctrl+K` and update the binding.
  - **JJ — eslint `_` and `_req` unused-var warnings** (`useCart.ts:106`, `useCopySession.ts:142`). Project eslint config doesn't accept the `^_` prefix convention. Fix: add `argsIgnorePattern: '^_'` + `varsIgnorePattern: '^_'` to `frontend/eslint.config.js` `@typescript-eslint/no-unused-vars` rule, OR rename the destructure leftover.
  - **KK — E2E coverage gaps:** pre-Copy validate orphan-drop toast, cart auto-clear after Copy, AlternativesDrawer variant tracking, ListxmlBanner empty-parse trigger, SettingsPage `cart_clear_on_copy` round-trip. Add Playwright cases or accept Vitest-only coverage with a spec § 6 note.
  - **LL — `handleTileSelect` resets ALL filters on toggle-off** (`pages/LibraryPage.tsx:143-146`). User who set search="contra" then clicked "Run & Gun" loses the search on toggle-off. Fix: preserve non-tile-driven filter state.

  Source: P15 closing `/audit` (4 actionable lint findings) + 8-lane `/indie-review` (cross-cutting + per-lane HIGH/MEDIUM); filed 2026-05-08.
  Dependencies: P15 (still 🚧). FP24 must close before P15 can close.

---

## P15 — Cart and curated library (closed 2026-05-08)

**Theme:** [`docs/superpowers/specs/2026-05-07-cart-and-curated-library-design.md`](docs/superpowers/specs/2026-05-07-cart-and-curated-library-design.md) — turned the dead `21,049 games · 0.0 GB` bottom-bar into a cart-first selection model with featured INI-derived tiles, dismissible onboarding banner, sticky cart-bar with expand-up panel, and live Copy + DryRun flows. Picker runtime symptom shipped fixed in FP23; this phase added the regression test that locks `cloneof_map` non-empty ⇒ winners < machines, plus the `listxml_available` + `cloneof_map_size` setup-check fields that let the banner cover the "supplied but parsed empty" edge case.

### 🎨 Features

- ✅ **P15** [mame-curator-1024] **Cart-first selection + curated featured tiles + live Copy.**
  Lanes: api, frontend, docs.
  - **Backend (B1–B5).** `tests/api/test_routes_games.py::test_cloneof_map_collapses_winners` regression for FP23; `/api/setup/check` extended with `listxml_available` and `cloneof_map_size`; `GamesPage.total_bytes` server-summed; `POST /api/games/validate` for cart reconciliation; `UiConfig.cart_clear_on_copy` literal Union (`'always' | 'on_success' | 'never'`, default `'on_success'`).
  - **Frontend (F1–F14).** `useCart` (localStorage v1, `addAll` truncates at MAX_CART_SIZE, `isStorageBroken` probe); `useValidateCart`; `useCopySession` SSE hook (job_started → progress → terminal, transient-error reconnect); `FeaturedTilesRow` + `OnboardingBanner` (localStorage-keyed dismissal + auto-dismiss on first add); `CartBar` (replaces ActionBar) + `CartPanel` (expand-up); `GameCard` `+Add` affordance + cart-aware "✓ Added"; `LibraryPage` end-to-end wiring with pre-Copy `validate` orphan-drop; `ListxmlBanner` empty-parse branch; top-nav reshape (Library + 🛒 + Settings + Help + ⋯ More); `SettingsPage` `cart_clear_on_copy` Select.
  - **E2E.** Playwright `cart-flow.spec.ts` covers banner dismiss → tile filter → bulk-add → expand-panel → Copy.
  - **Docs.** Implementation plan at `docs/superpowers/plans/2026-05-07-cart-and-curated-library-plan.md`; closing fold-in tracked in FP24.

  Plan was a single ship — no mid-phase splits. Closing `/audit` (4 actionable lint findings) + 8-lane `/indie-review` folded into FP24 (30+ findings across Tier 1/2/3 closed in 13 commits 2026-05-08); `P15-complete` tags the docs-close commit, distinct from `FP24-complete` (which tags yesterday's FP24 close).
  Source: user feedback 2026-05-07 ("21,049 games, no clear path to pick three"); brainstorm + 7-round cold-eyes review APPROVE.
  Dependencies: FP23 ✅ (listxml banner foundation), FP19 ✅ (RetroArch launch — cart preserves), FP17 ✅ (`/api/library/facets` for tile counts).
  See `docs/journal/P15.md`.

---

## FP23 — Parent/clone collapse listxml fix + DryRun wiring (closed 2026-05-07)

**Theme:** discovered during the P15 cart-and-curated-library
brainstorm: the running v1.2.0 app showed 21,049 cards in the
Library bottom-bar with the 1942 family appearing 7 times across
regions / revisions / bootlegs / hacks. Round 1 of the P15 spec
cold-eyes review caught the mis-diagnosis ("the picker isn't
wired" — wrong) and pointed at the real cause: `cloneof_map={}`
at world-load time, so `filter/runner.run_filter` groups by self
and every machine becomes its own winner.

Per [ADR-0002](docs/decisions/0002-cloneof-from-listxml.md),
parent/clone relationships are stripped from Pleasuredome DATs
and must come from MAME `-listxml`. The user's `config.yaml` had
`paths.listxml: null` since v1.0.0 — silent failure (FP18's
setup banner counts INIs but not listxml).

### 🐛 Bug fixes

- ✅ **FP23** [mame-curator-1023] **Parent/clone collapse listxml fix + DryRun wiring.**
  Lanes: api, frontend.
  - **A — Listxml installed.** Generated MAME 0.287 listxml
    (302 MB, 27,604 cloneof entries; 3 versions newer than the
    user's 0.284 DAT — cloneof for old arcade titles is stable
    across this drift). User's `config.yaml` now references it
    (config is gitignored; fix lives locally per project policy).
    Verified `/api/games?total` drops 21,049 → 10,591 after
    restart; `/api/games/1942/alternatives` returns the parent +
    7 clones, matching the original screenshot exactly.
  - **B — `ListxmlBanner.tsx`** (3 unit tests) renders above the
    Library grid when
    `setupCheck.reference_files.listxml.exists === false` so
    future users see the silent-failure state explicitly. Pairs
    with the existing FP16 § C INI banner; closes the gap that
    let the bug ship for 23 days. Future enhancement: extend the
    setup-check `reference_files` block with cloneof-coverage
    statistics (P15 § 4.3.1) so the banner can also flag a
    listxml that loaded but parsed empty.
  - **C — `useDryRun` hook** (`POST /api/copy/dry-run` mutation)
    wired to the previously-no-op `onDryRun` handler in
    `LibraryPage`; opens the existing `DryRunModal` with the
    report on success. P15 swaps the `selected_names` source
    from `cards` → `cart.items` — modal contract unchanged so
    this hook keeps working through the cart redesign.
  - **D — `onCopy` stays a no-op stub.** Full Copy lifecycle
    (SSE + conflict resolution) is genuinely P15-scale
    (~500 lines + tests) and fits naturally with the cart-driven
    input swap. Scope reset surfaced to user mid-session after
    initial under-estimate.

  Source: P15 brainstorm 2026-05-07 ("Library shows 21,049 with
  1942 appearing 7×"); cold-eyes review round 1 reframe.
  Dependencies: FP18 ✅ (banner pattern), P03 ✅ (`DryRunReport`
  contract), [ADR-0002](docs/decisions/0002-cloneof-from-listxml.md).

---

## FP22 — Launch button shows when RetroArch unconfigured (closed 2026-05-08)

**Theme:** user reported 2026-05-04 a 422 on
`POST /api/games/ddragon3p/launch` after clicking the Launch button:

```
INFO: 127.0.0.1:51874 - "GET /api/games/ddragon3p/alternatives HTTP/1.1" 200 OK
INFO: 127.0.0.1:51874 - "POST /api/games/ddragon3p/launch HTTP/1.1" 422 Unprocessable Content
```

The 422 is the FP19 contract's "RetroArch not configured" envelope
(`api/routes/games.py:213-220`) — `paths.retroarch` and / or
`paths.retroarch_core` is unset in `config.yaml`. The bug is UX:
the **Launch button shipped unconditionally** in
`AlternativesDrawer.tsx:135-145` and the SettingsPage Setup banner
doesn't track RetroArch config state, so a user with no RetroArch
configured can click Launch and only learns from a toast that
something needs editing in `config.yaml`.

### 🐛 Bug fixes

- ✅ **FP22** [mame-curator-1022] **Launch button gates on RetroArch config + Setup banner surfaces it.**
  Lanes: api, frontend. Shipped 2026-05-08.
  - **A — `/api/setup/check` returns `retroarch_configured: bool`.** ✅
    Derived flag in `api/routes/stubs.py:setup_check` (true iff both
    `paths.retroarch` and `paths.retroarch_core` are non-null);
    Pydantic mirror in `api/schemas_setup.py:SetupCheck`; TS mirror
    + Zod schema in `frontend/src/api/types.ts`. Three new pytest
    cases in `tests/api/test_routes_stubs.py` (default-false /
    one-of-two-set / both-set).
  - **B — Launch button gates on `retroarch_configured`.** ✅
    `AlternativesDrawer.tsx` accepts a new `retroarchConfigured?:
    boolean` prop. The button is disabled when the prop is anything
    other than strictly `true` (so `undefined` while the
    `useSetupCheck` query is still loading also gates, preventing a
    fast-clicker from racing into a 422). When the prop is `false`,
    an inline `<p role="status">` hint surfaces under the button
    linking to `/settings?tab=paths` via a react-router `<Link>`.
    Three new vitest cases (false / true / undefined). LibraryPage
    threads `setupCheck.data?.retroarch_configured` through.
  - **C — Setup banner surfaces RetroArch state.** ✅
    `SettingsPage.tsx` Setup banner gains a third `<span>` after the
    INI status line: "RetroArch: configured." or "RetroArch: not
    configured — set paths.retroarch and paths.retroarch_core in the
    Paths tab to enable launching." Two new vitest cases.
  - **D — 422 envelope copy upgrade.** ⏭️ Deferred to FP21 § J.
    Spec said "A/B/C ship without it"; landing the byCode mapping
    without the typed `RetroArchNotConfiguredError` would have left
    a dead string-table entry (the strings.ts contract is "no
    `byCode` entry is dead"). FP21 § J already promises the typed
    error class with the `code` field, so D rides along there
    naturally — extended below.

  Source: user 2026-05-04 ("trying to launch a game" → 422 with
  no in-app guidance to fix).
  Dependencies: FP19 ✅. D folded into FP21 § J.

---

## FP20 — `/indie-review` Tier 1: security + data-loss (closed 2026-05-11)

**Theme:** fold-in of the 2026-05-04 multi-agent independent review
across 10 lanes (parser, filter, copy, api-data, api-mutation,
bootstrap, frontend library, frontend settings, frontend
alternatives/help/sessions, frontend infra). Tier 1 covers the
ship-this-week class: spec-mandated locks that aren't installed,
non-atomic writes on the data path, sandbox-escape vectors,
silent-failure surfaces. Post-v1.2.0 hardening pass; no functional
regressions expected. **All 12 sub-bullets A–L shipped 2026-05-11 across
14 commits (`c3ee50c..d819181`); closing `/audit` + `/indie-review`
surfaced 1 Tier 1 spec-violation + 7 Tier 2 + 10 Tier 3 — folded into
FP25. FP20 stays 🚧 until FP25 closes.**

### 🔒 Security

- ✅ **FP20** [mame-curator-1019] **Indie-review Tier 1 — security + data-loss fixes.**
  Lanes: parser, copy, api, frontend.
  - **A — Parser XXE + zip-bomb hardening.** `parser/dat.py:94`
    and `parser/listxml.py:38,71,102` use `lxml.iterparse(...)`
    with default settings; `# nosec B410` claims `no_network=True`
    is sufficient but it does not block `file://` URIs nor
    internal-entity expansion. Fix: pass an explicit
    `XMLParser(resolve_entities=False, no_network=True,
    huge_tree=False)` via the `parser=` kwarg at all four call
    sites. Also cap `zf.getinfo(member).file_size` at
    `_MAX_DAT_BYTES` (e.g. 256 MiB) before `zf.extract` in
    `parser/dat.py:84` so a malicious 100 KB zip can't decompress
    to gigabytes. Update the inline `# nosec` comment.
  - **B — Activity log + recyclebin manifest non-atomic writes.**
    `copy/activity.py:26-29` claims O_APPEND PIPE_BUF atomicity but
    Python `BufferedWriter` may split a `write()` across multiple
    syscalls; large `copy_started` events can exceed 4 KiB. Fix:
    use `os.open(O_WRONLY|O_APPEND|O_CREAT)` + a single
    `os.write(fd, line_bytes)` (or document the deviation and
    relax the spec claim). Same fix shape for `copy/recyclebin.py`
    `manifest.json` write (line 51) and `copy/playlist.py`
    `write_lpl` — replace ad-hoc tmp+replace with the project's
    `_atomic.atomic_write_text` helper. Closes 3 non-atomic write
    sites and a Rule-of-Three reuse violation.
  - **C — `app.state.world_lock` not installed.** P04 spec lines
    104-115 require a per-app `asyncio.Lock` guarding all
    `set_world` writes; none exists. Two concurrent PATCHes (e.g.
    frontend slider autosave under retry) interleave reads and
    silently lose one write. Fix: instantiate
    `app.state.world_lock = asyncio.Lock()` in `app.py`'s
    lifespan; convert `patch_config`, `restore_config_snapshot`,
    `import_config`, `fs_grant_root`, `fs_revoke_root` to `async`;
    wrap each read-merge-write-snapshot-set_world block in
    `async with request.app.state.world_lock`.
  - **D — `compose_allowlist` admits non-existent paths.**
    `api/fs.py:55-56` resolves `Path(raw).resolve(strict=False)`
    so allowlist entries pointing at non-existent or removed
    directories survive in `granted_roots`; if the user later
    creates / symlinks anything at that name it's silently inside
    the sandbox. Fix: filter resolved entries to those that
    `exists()` and `is_dir()`; log INFO on dropped entries so the
    Settings UI can surface "your granted root `<path>` is gone".
  - **E — `help.py` env-override path traversal.**
    `api/routes/help.py:24-27` reads `MAME_CURATOR_HELP_DIR`
    without `.resolve()`. A symlinked override directory then
    passes the `relative_to` traversal check at line 54. Fix:
    `return Path(override).resolve()` and likewise for the
    package-relative path.
  - **F — `download()` URL scheme allowlist.**
    `downloads.py:73-101` passes any URL straight to
    `httpx.AsyncClient.get`. Fix: reject schemes other than
    `http`/`https` at function entry (5-line `urlparse` check on
    `url` and each `mirrors[]`).
  - **G — `useApiQuery` silent error path.**
    `frontend/src/hooks/useApi.ts:19-25` has no error toast hook;
    every query failure (R01 games, R03 alternatives, R07 stats,
    R10 sessions, R28 activity, R37 help, R29 fs, R35 setup, R14
    config) drops to per-route silence. P06 spec § "Error
    envelope handling" mandates `strings.errors.byCode` toast.
    Fix: at the App.tsx queryClient ctor, pass
    `queryCache: new QueryCache({ onError: toastApiError })` and
    matching `mutationCache`. Funnels every failure through the
    toast and removes per-mutation `onError` boilerplate.
  - **H — `GameCard` `aria-label` clobbers accessible name.**
    `frontend/src/components/library/GameCard.tsx:55` sets
    `aria-label={card.description}` on the wrapper button, which
    overrides the accessible-name calculation entirely — screen
    readers announce only the description, hiding year /
    publisher / badges / shortname. Fix: drop `aria-label` from
    the button; let the `<h3>` compute the accessible name; set
    `alt=""` on the `<img>` (the heading already names it).
  - **I — `LibraryPage` swallows query errors.**
    `frontend/src/pages/LibraryPage.tsx:67-69` reads `games.data`
    without checking `games.isError`; backend down → user sees
    "No games match your filters" with disabled action bar. Fix
    becomes trivial once H/G land (global toast surfaces the
    error); also render an inline error panel with a Retry
    button calling `games.refetch()`.
  - **J — `SnapshotsTab` restore failure has no inline surface.**
    Restore mutation routes errors to `toastApiError` only;
    dialog auto-closes; the snapshot list does not invalidate.
    Fix: add `restoreError?: string | null` prop, render
    `<p role="alert">` above the list when set (mirrors
    `BackupTab.error` pattern already in place).
  - **K — `FsBrowser` `Esc`-closes-everything bug.**
    `frontend/src/components/settings/FsBrowser.tsx:90-234`
    renders the grant `ConfirmationDialog` *inside* a fragment
    co-mounted with the outer `Dialog`; `Esc` in the grant prompt
    fires the outer `Dialog`'s `onOpenChange(false)`, closing the
    entire browser. Fix: gate the grant prompt's `onOpenChange`
    on its own state; close the inner Dialog first when
    `sandboxBlocked` flips true, OR render the AlertDialog as the
    only layer when sandbox blocked.
  - **L — `HelpPage` DOMPurify config hardening.**
    `frontend/src/pages/HelpPage.tsx:28` calls
    `DOMPurify.sanitize(topicHtml)` with no config; default
    profile permits `<a target="_blank">` without
    `rel="noopener"` (reverse-tabnabbing) and `data:` URLs on
    `<img>`. Fix: add config object `{ALLOWED_URI_REGEXP:
    /^(?:https?|mailto):/i, FORBID_TAGS: ['style','form'],
    FORBID_ATTR: ['style']}` plus a one-time
    `DOMPurify.addHook('afterSanitizeAttributes', ...)` to set
    `rel="noopener noreferrer"` on `target="_blank"`. Closes
    `allowlist-004`'s contracted hardening that shipped FP16 § H4.

  Source: `/indie-review` 2026-05-04, 10 lanes parallel-dispatch.
  Dependencies: none (post-v1.2.0; `main` baseline). FP25 closing-review
  fold-in must close before FP20 can flip to ✅.

---

## FP25 — FP20 closing-review fold-in (closed 2026-05-11)

**Theme:** FP20's closing `/audit` (semgrep + gitleaks on the FP20 surface
plus CI-clean ruff/mypy/bandit/eslint/tsc) returned a single allowlist-004
re-confirmation; the 5-lane `/indie-review` (parser / copy / api-mutation
+ sandbox / frontend infra+library / frontend settings+help) surfaced
**1 Tier 1 spec-violation, 7 Tier 2 hardening gaps, 10 Tier 3 polish
items**. FP20 cannot close until these are folded. Findings batched into
three tiers; all share a single `FP25` ID per the FP24 / FP19 / FP12
closing-review precedent.

### 🐛 Bug fixes

- ✅ **FP25** [mame-curator-1027] **FP20 closing-review fold-in.**
  Lanes: api, copy, frontend, docs, tests.

  **Tier 1 — Critical / ship-this-week:**
  - **A — `world_lock` covers only 5 of the 7 spec-required mutation
    routes** (Lane 3 F1). `docs/specs/P04.md:104-115` is normative:
    PATCH config, overrides POST/DELETE, sessions
    POST/DELETE/activate, notes PUT, snapshot restore, fs
    grant/revoke must all run under `app.state.world_lock`. FP20-C
    wired `patch_config`, `restore_config_snapshot`, `import_config`,
    `fs_grant_root`, `fs_revoke_root`. Still racy: `api/routes/curate.py`
    (six `set_world` sites — overrides POST/DELETE, sessions
    POST/DELETE/activate/deactivate) and `api/routes/games.py:put_notes`.
    The FP20-C inline comment at `api/app.py:111-113` minimises this as
    "deferred", but the spec table is normative — the lock contract is
    currently half-delivered. Fix: convert the seven remaining routes to
    `async`, drop their `Depends(get_world)` injection, re-read
    `request.app.state.world` inside `async with` and run
    read-merge-write-set_world under the lock. Closes the data-loss
    class on concurrent PATCH + sessions/overrides/notes races. Add an
    acceptance test that fires two `asyncio.gather`-ed mutations across
    different routes and asserts both edits land.

  **Tier 2 — Hardening / correctness:**
  - **B — Activity-log durability + typed errors** (Lane 2 W1–W3).
    `src/mame_curator/copy/activity.py:34-38` bypasses `BufferedWriter`
    correctly but (a) does not fsync the fd — module docstring claims
    atomicity but the page-cache flush is at the kernel's discretion;
    (b) ignores `os.write` return value — POSIX permits short writes
    on regular files (signal-interrupted, ENOSPC partway); (c)
    propagates raw `OSError` instead of wrapping in
    `ActivityLogError(CopyError)` per the `copy/spec.md` envelope. Fix:
    optional best-effort fsync after write (suppress OSError on tmpfs
    per allowlist-007's pattern), loop until `total == len(line_bytes)`,
    wrap OSError in a typed `ActivityLogError`. Update the module
    docstring to name the durability semantic explicitly.
  - **C — Recyclebin manifest atomicity envelope** (Lane 2 W4).
    `src/mame_curator/copy/recyclebin.py:44-60`: if `shutil.move`
    succeeds but `atomic_write_text(manifest, ...)` fails, the recycled
    `.zip` sits with no `manifest.json` — `purge_recycle` still cleans
    after 30d, but forensics has no record. Worse: `atomic_write_text`
    raises `OSError` raw, bypassing the `RecycleError` envelope
    established at line 47. Fix: wrap the `atomic_write_text` call in a
    try/except that raises `RecycleError`; either roll back the move on
    manifest failure (preserves the all-or-nothing invariant) or comment-
    pin the partial state as deliberate with a recovery note.
  - **D — `_atomic.py` perm-mode parity** (Lane 2 W5).
    `tempfile.NamedTemporaryFile` defaults to `0o600`; the resulting file
    after `os.replace` retains those perms. `copy/activity.py` uses
    `os.open(..., 0o644)` and respects umask. Result: recyclebin
    manifest and RetroArch `.lpl` are owner-only readable while activity
    log is world-readable. Fix: `os.fchmod(tmp.fileno(), 0o644)` before
    close in `_atomic.atomic_write_text` / `atomic_write_bytes`, OR
    comment-pin the 0o600 mode as deliberate (with reasoning).
  - **G — `toastApiError` toast burst on cold-start outage** (Lane 4
    T2-1). When the backend is down, `LibraryPage` fires 9+ near-
    simultaneous query failures (six tile counts via `useQueries` fan-
    out + games + facets + config + sessions + setupCheck), and
    `queryCache.onError` produces one toast per failure. Sonner does
    not dedup. Fix: add a coalescing window (1–2s last-seen
    `(code, detail)`) inside `frontend/src/lib/apiErrorToast.ts` so
    cold-start outages produce one toast, not nine.
  - **H — Retry button has no in-flight feedback** (Lane 4 T2-2).
    `LibraryErrorPanel` Retry calls `games.refetch()` but does not
    disable during the in-flight fetch. The user can mash it. Fix:
    plumb `isFetching` through to `LibraryErrorPanel` and set
    `disabled={isFetching}`; optionally show a small spinner / "Retrying…"
    label so the affordance is unambiguous.
  - **I — DOMPurify hooks are global singletons** (Lane 5 T2-2).
    `frontend/src/pages/HelpPage.tsx` registers
    `uponSanitizeAttribute` + `afterSanitizeAttributes` at module
    evaluation. Any future `DOMPurify.sanitize(...)` call anywhere in
    the bundle silently inherits the `target="_blank"` `forceKeepAttr`,
    rel-injection, and `data:` src strip on
    IMG/SOURCE/AUDIO/VIDEO/TRACK. No current victims, but the next
    developer adding a Markdown-rendered notes field will be surprised.
    Fix: either (a) module-level `hooksInstalled` guard + comment, (b)
    use `DOMPurify.removeAllHooks()` before adding, or (c) refactor to
    a HelpPage-scoped DOMPurify instance via `DOMPurify(window)` factory.
    Add a top-of-module warning naming the global-side-effect class.

  **Tier 3 — Tests + doc cleanup:**
  - **E — Concurrent-write property test for activity log** (Lane 2
    T3a). The existing `test_activity_log_append_uses_single_os_write`
    asserts a necessary condition (one syscall) but not sufficient
    (concurrent appenders interleaving). Add a fork-2-child test that
    each appends N × 6 KiB lines and asserts every resulting JSONL line
    parses cleanly. Proves the POSIX O_APPEND guarantee end-to-end.
  - **F — Manifest-atomicity test for recyclebin** (Lane 2 T3b). No
    test verifies tmp cleanup-on-failure or that a half-written
    `manifest.json` never appears. Monkeypatch `os.replace` to raise
    inside `atomic_write_text` during `recycle_file`, assert no
    `manifest.json` and no `manifest.json.*.tmp` remain. Locks the
    crash-safety contract.
  - **J — Strengthen data-URL test in HelpPage** (Lane 5 T2-4). The
    current assertion `if (img !== null) { expect(src).not.toMatch
    (/^data:/) }` passes vacuously if `<img>` is removed entirely.
    Assert deterministic outcome: either `<img>` is absent, OR `<img>`
    survives with `alt=""` and no `src`. Prevents a future config
    change from silently failing-open.
  - **K — Doc + comment cleanup batch.** Twelve sub-items grouped:
    (1) `parser/dat.py:23` + `listxml.py:16` rewrite `# nosec B410`
    comments to lead with the hardening (drop the misleading "trusted
    source" framing — Phase 4 routes parse through the API);
    (2) `parser/dat.py:32-35` zip-bomb cap comment naming the single-
    member upstream enforcement;
    (3) `tests/parser/test_dat.py:206` Billion Laughs timing assertion
    — switch from `elapsed < 1.0` to `len < 1000 AND elapsed < 5.0`
    for CI tolerance;
    (4) `_atomic.py:27, 85` `# noqa: SIM115` add reason comment per
    project rule (CLAUDE.md);
    (5) `api/routes/help.py:60` drop the redundant `.resolve()` (FP20-E
    made `_help_dir()` canonical at source); add a one-line comment
    instead;
    (6) `api/fs.py:68-72` dedupe the FP20-D INFO log — cache seen-stale
    paths on the world to avoid log spam under polling load;
    (7) `frontend/src/components/library/GameCard.tsx:56` document the
    `aria-labelledby` id uniqueness invariant (currently relies on MAME
    short_name uniqueness within a DAT — fragile if cards repeat in a
    drawer + grid concurrently);
    (8) `frontend/src/lib/__tests__/queryClient.test.tsx` add
    `.toHaveBeenCalledTimes(1)` assertion to lock the once-per-failure
    contract;
    (9) `frontend/src/components/settings/SnapshotsTab.tsx` JSDoc
    `restoreError` lifetime contract ("alert lifetime = SettingsRoute
    mount + one mutation cycle");
    (10) `HelpPage.tsx:59` SVG tagName casing comment (HTML tagName is
    uppercase, SVG is lowercase — currently safe because DATA_URI_TAGS
    is HTML-only, but worth documenting);
    (11) `HelpPage.tsx:73` drop the dead `el.getAttribute?.` optional
    chain (Element always has the method);
    (12) `App.tsx:285-291` clear `restoreError` during
    `restore.isPending` to avoid the stale-flash on rapid retries.

  Source: FP20 closing `/audit` (1 allowlist-004 re-confirmation, no new
  findings) + 5-lane `/indie-review` (parser / copy / api-mutation +
  sandbox / frontend infra+library / frontend settings+help); filed
  2026-05-11.
  Dependencies: FP20 (still 🚧). FP25 must close before FP20 can flip ✅.

---

## FP26 — FP25 closing-review fold-in + UX e2e walkthrough (closed 2026-05-11)

**Theme:** FP25's closing `/audit` returned clean across ruff +
ruff format + mypy + bandit + semgrep (0 results, 65 files) +
gitleaks + ESLint + tsc. The 4-lane `/indie-review` surfaced
**5 Tier 1 findings (test sufficiency + envelope hole),
12 Tier 2 findings (doc/test polish), 15+ Tier 3 polish items**.
User added a fifth scope item: Playwright e2e walkthroughs that
exercise the FP25 user-facing changes (toast dedup, retry-disable,
help DOMPurify, settings restore retry) so the UX is validated
end-to-end, not just unit-tested. FP25 cannot close until FP26
closes.

### 🐛 Bug fixes / test strengthening

- ✅ **FP26** [mame-curator-1028] **FP25 closing-review fold-in + UX e2e walkthrough.**
  Lanes: api, copy, frontend, tests, docs, e2e.

  **Tier 1 — test sufficiency + envelope holes:**
  - **A — L1-H1 + L1-H2: FP25-A world_lock tests don't prove the
    contract.** `tests/api/test_fp25_world_lock.py` has no `await`
    inside its critical sections, so the `asyncio.gather` "both
    edits land" assertion passes even when the lock is removed.
    The 7 per-route tests only prove `__aenter__` ran, not that
    `set_world` ran inside the critical section. Fix: inject a
    deliberate yield via a monkey-patched async `_persist_*` that
    `await asyncio.sleep(0)`s mid-write; assert observed
    serialization (read_world_id → wrote_world_id chain has no
    fork). Tighten the per-route tests to track "set_world calls
    while lock held == 1".
  - **B — L2-H1: `mkdir(parent)` in `activity.py:54` escapes the
    ActivityLogError envelope.** A permission error on `data/`
    raises raw `OSError` and bypasses the `CopyError` CLI catch
    boundary. Fix: move the `log_path.parent.mkdir` inside a
    try/except that raises `ActivityLogError("failed to prepare
    activity log directory", path=log_path.parent)`.
  - **C — L2-H2: FP25-F tests are vacuously true.**
    `tests/copy/test_fp25_recyclebin.py:142-146, 173-178` guard
    their assertions inside `if target_dir.exists():`, but FP25-C's
    successful rollback removes `target_dir` first. Fix: assert
    outside the guard against `recycle_root.rglob("manifest.json*")`
    being empty, OR additionally break the rollback for these two
    tests so the target_dir survives.
  - **D — L2-H3: FP25-E concurrent test will hang/fail on macOS CI.**
    `tests/copy/test_fp25_activity_concurrent.py:82` forces
    `mp.get_context("fork")` but `OBJC_DISABLE_INITIALIZE_FORK_SAFETY`
    isn't set; macOS CoreFoundation post-init makes fork unsafe.
    Fix: extend the skipif gate to `sys.platform not in ("linux",)`
    (i.e. skip on darwin + win32), OR migrate to `spawn` with a
    top-level worker function.

  **Tier 2 — doc/test polish (12 items):**
  - **E — L1-M3** P04 spec line 110 doesn't enumerate the
    `_deactivate` route; add it for completeness.
  - **F — L2-M2** activity log misses parent-dir fsync on first
    create; add `_fsync_parent_dir(log_path)` post-write.
  - **G — L2-M3** `copy/spec.md` drift: "FP25-C is open" stale text,
    broken "§ Errors envelope below" reference, `ActivityLogError`
    missing from the errors enumeration. Update inline.
  - **H — L2-M4** add a test for the `written == 0` defensive
    branch (monkey-patch `os.write` to return 0 without raising).
  - **I — L3-M1** `queryClient.test.tsx` doesn't reset the
    dedup Map across tests; add `_resetApiErrorToastDedupForTests()`
    to its `beforeEach` to neutralise the latent pollution.
  - **J — L3-M2** add a comment on `lastSeen` Map's deliberate
    unboundedness in `apiErrorToast.ts`, OR a coarse prune at
    size-threshold (5× window age). Comment is cheaper.
  - **K — L3-M3** docblock improvements for `apiErrorToast` —
    name the rejected `toast({id})` alternative for the next
    maintainer.
  - **L — L4-M1: drop the FP25-K(12) no-op.** React Query 5.x's
    `useMutation` already clears `error` to null on `mutate()`;
    the `restore.isPending ? null : ...` conditional is dead
    defence. Either remove the conditional and the K(12) entry,
    or rewrite the comment to be honest about why it's there
    despite being redundant.
  - **M — L4-M2** allowlist-004 line citation is stale
    (`HelpPage.tsx:72` → current line 176), and the wording
    quotes `DOMPurify.sanitize(...)` but post-FP25-I the call
    is `helpSanitizer.sanitize(...)`. Refresh the entry; bump
    "Confirmed by phase" to FP26.
  - **N — L1-M1** `_TrackingLock` is a duck-type; document why
    it's not subclassing `asyncio.Lock` (or convert).
  - **O — L1-M2** FP25-A concurrent test's overrides assertion
    is tautological (asserts the same response that did the
    override). Re-GET `/api/overrides` after both writes complete
    to make it symmetric with the sessions assertion.
  - **P — L2-M1** double-failure user signal: when manifest write
    AND rollback fail, attach the orphan path to `RecycleError`
    as a machine-readable attribute; escalate the log to
    `logger.error`.

  **Tier 3 — UX e2e walkthroughs (shipped 2026-05-11 as `e2e/fp25-ux-walkthrough.spec.ts`):**
  - **Q ✅** — Playwright spec for FP25-G toast dedup. Verified:
    11 failing /api/* requests on cold start produce exactly 1
    Sonner toast (was 9+ pre-FP25-G).
  - **R ✅** + **V** — Playwright spec for FP25-H Retry-disabled.
    Walkthrough surfaced a **new Tier 1 bug** the unit test
    missed (see FP26-V below). The spec currently locks the
    observed (buggy) behavior so the future fix flips the
    assertions in the same commit.
  - **S ✅** — Playwright spec for FP25-I HelpPage DOMPurify.
    Verified at the rendered DOM: `<script>` stripped (no
    `window.PWND` side-effect), `target="_blank"` anchor carries
    `rel="noopener noreferrer"`, `<img src="data:...">` has no
    surviving data: src.
  - **T ✅** — Playwright spec for FP25-K(12) settings restore
    retry flow. Verified the persistent alert surfaces the
    `ApiError.detail` from a forced 422.
  - **U** — LOW-tier polish batch. Any remaining Tier 3 items
    from the four indie-review lanes that didn't get their own
    sub-bullet, plus the LOW findings from L1/L2/L3/L4 audits
    that the user signs off on inline.

  **Tier 1 — newly surfaced via Playwright walkthrough (after
  initial scoping):**
  - **V — LibraryErrorPanel unmounts on Retry click; FP25-H
    affordance never visible to the user.** Clicking Retry calls
    `games.refetch()`; react-query resets `games.isError` to
    false for the duration of the in-flight refetch;
    LibraryPage's `{games.isError ? <Panel/> : <Grid/>}` ternary
    unmounts the panel, so the `disabled={isFetching}` /
    "Retrying…" label that FP25-H plumbed through is rendered to
    a DOM tree the user never sees. The unit test passes because
    it directly renders `<LibraryErrorPanel isFetching />`,
    bypassing the host component's conditional. Fix: keep the
    panel mounted while a refetch from an errored state is in
    flight — e.g.
    `games.isError || (games.isFetching && games.errorUpdateCount > 0)`.
    Then update the FP26-R spec's assertions from "panel
    disappears" back to the FP25-H contract ("disabled +
    Retrying… visible while refetching"). Surfaced by user
    direction to walk through features end-to-end with
    Playwright; the precise instance the user's "smaller fix-
    passes converge faster" lesson would predict static unit
    tests miss.

  Source: FP25 closing `/audit` (clean) + 4-lane `/indie-review`
  (api mutation lock / copy durability+atomicity / frontend
  error+library surface / frontend help+settings+parser-doc-cleanup);
  filed 2026-05-11.
  Dependencies: FP25 (still 🚧). FP26 must close before FP25 can
  flip ✅, which is what FP20 is waiting on.

---

## FP21 — `/indie-review` Tier 2: hardening sweep (closed 2026-05-11)

**Theme:** Tier 2 fold-in from the 2026-05-04 multi-agent review.
Real-bug class — manifests on common paths, but not a security
hole or silent-loss vector. Bundles spec drift, recycle-bin
correctness, SSE edge cases, and the API mutation route
ergonomics.

20 sub-bullets shipped across 5 commits (filter A/B/C → copy
D/E/F/G → api H/J → api I/K/L/M/N/O → downloads P + run.sh Q +
frontend R/S/T). 523 backend / 273 frontend tests green; coverage
86.79%; ruff + ruff format + mypy + bandit + eslint + tsc clean.
FP21-L investigated and ruled non-reachable; defensive guard
preserved with a pinning test. FP22-D (RetroArchNotConfiguredError
byCode) closed in J. FP25-C move-then-rollback envelope superseded
by D's write-then-move ordering — source intact under any single-
step failure path.

### 🐛 Bug fixes

- ✅ **FP21** [mame-curator-1020] **Indie-review Tier 2 — hardening + correctness.**
  Lanes: filter, copy, api, frontend.
  - **A — `filter/picker.py:182-185` `explain_pick` decisive
    semantics.** Spec line 63: "the tiebreaker(s) that **actually
    decided** the winner." Implementation records every
    tiebreaker where the winner beat *any* opponent, including
    pairings already settled by an earlier tier. Fix: per
    opponent, find the *first* non-zero tiebreaker; collect the
    union across opponents.
  - **B — `filter/sessions.py:40` `Session._validate_session`
    typed-error drift.** Spec line 139 promises `SessionsError`;
    direct callers get Pydantic `ValidationError`. Fix: raise
    `SessionsError` from the validator (or update spec.md to
    acknowledge `ValidationError` for direct construction).
  - **C — `filter/drops.py:38` `_device` strict-identity.**
    `not m.runnable` differs from spec rule 2's
    `m.runnable is False` if `Machine.runnable` is ever widened
    to `bool | None`. Latent today; one-character fix.
  - **D — `copy/recyclebin.py` manifest atomicity + per-file
    shape.** Multiple `recycle_file` calls into the same
    `target_dir` overwrite each other's `manifest.json`. Fix:
    move to per-file `<basename>.manifest.json` (or list-shaped
    manifest). Write manifest **before** moving the file so a
    failure mid-recycle leaves the original intact.
  - **E — `copy/preflight.py:48-55` free-space estimate ignores
    BIOS chain.** Sums only `plan.winners` zip sizes; `run_copy`
    actually copies `winners | bios_set`. Fix: accept `bios_set`
    as a preflight parameter (or compute it there); subtract
    `already_copied` so reruns report meaningfully.
  - **F — `copy/recyclebin.py:71-81` `purge_recycle` mtime
    drift.** Uses dir `st_mtime` which advances on any new file
    added; spec semantics are keyed to
    `manifest.json["recycled_at"]`. Fix: read
    `recycled_at` from manifest with dir-mtime fallback. Move
    `bytes_freed` accumulation inside try/except to avoid
    over-reporting on partial `rmtree` failure.
  - **G — `executor.copy_one` TOCTOU vs source disappearance.**
    Source vanishing between `runner.exists()` check and
    `executor.stat()` raises `FileNotFoundError`, surfaces as
    `FAILED` rather than `SKIPPED_MISSING_SOURCE`. Fix: wrap the
    initial `src.stat()` in `try/except FileNotFoundError` →
    return `SKIPPED_MISSING_SOURCE` for that errno.
  - **H — `api/routes/media.py:56` blocks the event loop.**
    `path.read_bytes()` is a sync call inside an async handler.
    Under `LibraryGrid` fan-out (50 thumbnails per view) this
    serialises behind one another. Fix: replace with
    `FileResponse(path, media_type="image/png")` — `FileResponse`
    reads via `anyio.to_thread`.
  - **I — `api/app.py:120-124` shutdown silent-detach.**
    `thread.join(timeout=5.0)` may return with the worker still
    alive; lifespan exits without logging. Fix: log a warning on
    `current.thread.is_alive()` post-join; consider one extra
    `controller.cancel(recycle_partial=True)`.
  - **J — `launch_game` should use typed `ApiException`.**
    `api/routes/games.py:214,229` raises `HTTPException` instead
    of project-typed `ApiException` subclasses, breaking the
    error-envelope contract (`code` / `fields` fields are
    omitted). Fix: add `RetroArchNotConfiguredError` (422) and
    `RomFileNotFoundError` (404) to `api/errors.py`; raise those
    instead. **Folds in FP22-D** — once these typed errors carry
    `code` fields, add the matching
    `strings.errors.byCode.retroarch_not_configured` and
    `rom_file_not_found` mappings in `frontend/src/strings.ts` so
    `toastApiError` surfaces friendly copy instead of the raw
    `detail` string. (FP22 deliberately deferred D so the byCode
    entries land beside the codes they describe — strings.ts'
    "no dead byCode entries" contract.)
  - **K — `api/jobs.py` SSE register-before-replay race.**
    `_events_iterator` merges live `lifecycle_history` +
    `progress_history` deque/list while the worker keeps
    appending; `RuntimeError: deque mutated during iteration`
    is reachable. Also: events emitted between replay end and
    `subscribers.append(q)` are lost for the new subscriber.
    Fix: snapshot history into local `tuple()` copies *before*
    merging; register the subscriber **before** replay so race
    events queue up.
  - **L — `api/jobs.py` late-progress-after-terminal drops.**
    Worker's last `on_progress` may execute on the loop thread
    after `_on_worker_done` set `self._current = None`,
    delivering a `file_progress` past the `None` sentinel — out
    of order. Fix: drain pending dispatches before
    `_close_subscribers`; make terminal+sentinel a single
    finalisation step on the loop thread.
  - **M — Snapshot directory unbounded.** Every PATCH /
    override / session / notes / grant / import creates a new
    snapshot dir; no LRU. Fix: add `MAX_SNAPSHOTS = 200` (or
    config knob); after `mkdir`, list siblings, prune oldest
    beyond cap.
  - **N — `patch_config` accepts bare `dict[str, Any]`.**
    P04 spec lines 645-657 specify a typed `AppConfigPatch`
    Pydantic model with `extra="forbid"` per section; the
    implementation skips it. Cheap DoS via `deep_merge` recursion
    is a side-effect. Fix: define `AppConfigPatch` per spec; drop
    bare-dict ingestion.
  - **O — `import_config` cross-file crash atomicity.**
    Four files written in sequence; each is atomic, the batch is
    not. Fix: stage all four `.tmp`s first, then issue the four
    `os.replace` calls back-to-back; add an `import.in_progress`
    sentinel for half-applied detection.
  - **P — `downloads.py` Content-Length cap + streaming.**
    `client.get()` buffers full body in memory; fine for 5 INIs,
    not for future ~50 MB MAME `-listxml` use. Fix: stream into
    a hash + tempfile with a configurable `max_bytes` (default
    100 MB); abort on Content-Length exceed.
  - **Q — `run.sh` uv-install integrity.**
    `curl -LsSf https://astral.sh/uv/install.sh | sh` has no
    integrity check. Fix (cheap): pin
    `--proto '=https' --tlsv1.2`. Fix (proper): write an ADR
    documenting the trade-off, OR vendor the uv release.
  - **R — `useLaunchGame` / `useOverride` bake `onError`.**
    `frontend/src/hooks/useAlternatives.ts:38-69` mutations rely
    on call-sites passing `onError: toastApiError`. Fix: bake
    the toast into the hook; let call-sites override.
  - **S — `useKeyboard` re-binds on every render.**
    `frontend/src/hooks/useKeyboard.ts:34-87` declares
    `[bindings]` as the effect dep; call-sites pass a fresh
    array literal on every render → tear-down + reattach every
    render. Chord support (spec § step 12 `g l`) is unreliable
    because re-renders reset pending state. Fix: ref-based
    handler that reads bindings on each event so `bindings` is
    not a dep.
  - **T — `LibraryGrid` keyboard nav gap.** No `role="grid"` /
    roving tabindex / arrow-key navigation despite spec
    requirement (`j`/`k`/`o`/`Enter`). Fix: add the WAI-ARIA
    composite-grid pattern; wire keys via `useKeyboard`.

  Source: `/indie-review` 2026-05-04 Tier 2.
  Dependencies: FP20 ✅ (Tier 1 lands first).

---

## DS02 — `/indie-review` Tier 3: structural debt sweep (planned)

**Theme:** Tier 3 fold-in — structural debt the review surfaced
that doesn't manifest as a user-visible bug today: file-cap
violations, i18n leaks, accessibility polish, spec-doc
synchronisation. Defer to a debt-sweep pass per project policy
("every released version is debt-swept").

### 🧹 Cleanup / debt

- 📋 **DS02** [mame-curator-1021] **Indie-review Tier 3 — structural debt.**
  Lanes: backend, frontend, docs.
  - **A — File-cap splits (5 files over hard cap).**
    `copy/runner.py` 518 → extract `_resolve_append_conflict`,
    `_overwrite_recycle_existing`, `_recycle_partial_session`,
    `_build_playlist_entries` helpers (drops to ~250 LoC).
    `cli/__init__.py` 594 → extract `cli/_cmd_setup.py`,
    `cli/_cmd_refresh_inis.py`, `cli/_cmd_serve.py`,
    `cli/_cmd_copy.py`, `cli/_cmd_filter.py` per spec layout
    (drops to ~250). `frontend/src/pages/SettingsPage.tsx` 367
    → extract `UiTab.tsx` + `SetupBanner.tsx` (drops to ~270).
    `frontend/src/App.tsx` 381 → extract the five `*Route`
    containers into `src/routes/{Sessions,Activity,Stats,
    Help,Settings}Route.tsx` (drops to ~140; closes a missed
    P06 spec line 37 deliverable). `api/jobs.py` 434 → extract
    `_ProgressSynthesizer` + `Job` dataclass into helper modules
    (drops to ~200).
  - **B — CI gate for file caps.**
    `find -name '*.py' | xargs wc -l | awk '$1>500'` blocks PR;
    same for `.tsx` at 350. Prevents recurrence.
  - **C — i18n leaks into `strings.ts`.** Hardcoded strings in
    `DryRunModal.tsx`, `YearRangeEditor.tsx:87,97`,
    `WhyPickedPanel.tsx:49`, `SettingsPage.tsx` per-INI list,
    Suspense fallback `App.tsx:339-341`, route loading
    skeletons (5 sites in App.tsx).
  - **D — Accessibility polish.** Skip-to-main link in
    `AppShell.tsx`; `aria-label` on `<aside>` + `<nav>`
    landmarks; `aria-busy` + scoped game-name on Launch button
    (`AlternativesDrawer.tsx:135-145`); per-thumb `aria-label`s
    on the year-range slider; `aria-live` on route loading
    skeletons.
  - **E — `parse_listxml_bios_chain` spec orphan.**
    `BIOSChainEntry` and `parse_listxml_bios_chain` are imported
    by `cli/__init__.py:50`, `api/state.py:39-40`,
    `copy/bios.py:9`, `copy/types.py:18`, but absent from
    `parser/__init__.py:19-37` `__all__` AND from
    `parser/spec.md`'s "Public functions" section. Fix:
    promote to public surface in `parser/spec.md` + `__all__`,
    OR move to a non-public location.
  - **F — `_atomic.atomic_write_*` mkdir contract.** Function
    silently `mkdir(parents=True, exist_ok=True)` the parent;
    the docstring doesn't mention it. Fix: pick a contract
    (`*, parents: bool = False` opt-in OR explicit caller-
    mkdir). Document; update `media/cache.py:78` and
    `cli/__init__.py:543` to mkdir explicitly.
  - **G — Settings tab URL state.**
    `frontend/src/pages/SettingsPage.tsx:188` uses local
    `defaultValue="paths"` Tabs state — refresh loses the user's
    place. Fix: `useSearchParams` controlled `Tabs` per P06
    URL-state precedent.
  - **H — `tab` routes panel-mount strategy.** All 8
    `<TabsContent>` panels mount simultaneously even when
    hidden. Fix: investigate Radix `forceMount={false}` or
    conditional render to defer hidden-panel hooks.
  - **I — `apiRequestVoid` strict-vs-permissive asymmetry.**
    `frontend/src/api/client.ts:202-216` accepts any 2xx
    silently while `apiRequest` rejects unexpected 204. Pick
    one model.
  - **J — Spec doc updates.** `docs/audit-allowlist.md`
    entry-004's claim that "the project's mitigation is in
    place" updated post-FP20-L (DOMPurify config). `parser/
    spec.md` adds zip-bomb cap clause + hardened-parser clause.
    `copy/spec.md` clarifies activity-log atomicity claim and
    multi-file recycle manifest shape.

  Source: `/indie-review` 2026-05-04 Tier 3.
  Dependencies: FP20 + FP21 (lands after the bug-class fixes;
  CI gate naturally lands last to avoid blocking the splits).

---

## DS03 — Dependency freshness sweep (planned)

**Theme:** verify every external library in `pyproject.toml` and `frontend/package.json` is on its **latest stable release**, and update the version constraints (or pinned exacts) to match. Per global rule § 5 ("Use the latest external-library version, with current idioms"), the project prefers latest-stable unless there's an explicit reason to pin. This sweep audits that invariant project-wide and ships a single coordinated bump.

**Why now (vs. ad-hoc):** the project has shipped 24 fix-passes plus 15 phases without a dedicated dependency-refresh pass. Individual deps have been updated as they came up (radix-ui during FP12, framer-motion during P15, etc.) but there's no single moment that says "everything is current." A dedicated sweep is cheaper than piecemeal upgrades because the test suites + CI matrix run once for the whole bump, not once per dep.

### 🧹 Cleanup / debt

- 📋 **DS03** [mame-curator-1025] **Dependency freshness sweep — pyproject.toml + frontend/package.json on latest stable.**
  Lanes: deps, build, ci.
  - **A — Backend audit (`pyproject.toml`).** Walk every entry under `[project.dependencies]` and `[project.optional-dependencies].dev`; for each, compare the floor constraint against the current PyPI latest stable (`uv pip list --outdated` + manual check for major-version-gated packages). Note any pinned-on-purpose entries (Pydantic v2 vs. v1 etc.) so the sweep doesn't regress them.
  - **B — Frontend audit (`frontend/package.json`).** Same shape against npm: `npm outdated` lists candidate bumps; verify each major-version bump's release notes for breaking changes. React 19, Tailwind 4, Vite 6+, TypeScript 6+ are already current as of P15 close — note in passing if any of them have shipped a newer point release.
  - **C — Github Actions audit (`.github/workflows/ci.yml`).** Bump pinned action SHAs / tags (`actions/checkout`, `actions/setup-python`, `astral-sh/setup-uv`, `actions/upload-artifact`). The 2026-05-08 CI run flagged `actions/upload-artifact@v4` as Node.js 20 deprecated — covered here.
  - **D — Coordinated bump commit.** Single commit that lifts every floor / pinned version together. Run the full local CI gate (`uv run pytest && uv run ruff check && uv run ruff format --check && uv run mypy && uv run bandit -c pyproject.toml -r src` + `npm test` + `npm run build`) before commit. CI matrix re-runs across Ubuntu / macOS / Windows × 3.12 / 3.13 confirms cross-platform compatibility of the bumped set.
  - **E — Idiom-modernise check.** Per global rule § 5 second clause: where a dep's major version brings new idioms (e.g. Pydantic 2.11+ deprecation warnings, FastAPI route-decorator style changes, React 19 use() hook), surface the idiom-drift in a follow-up note rather than bulk-rewriting in DS03 itself. Idiom changes go into a separate fix-pass if non-trivial; DS03 stays scoped to floor-bumps + green CI.

  Source: user request 2026-05-08 ("ensure that we are on the latest version of all dependencies"); reinforces global rule § 5.
  Dependencies: none. Slot DS03 anywhere in the queue — independent of FP22 / FP20 / FP21 / DS02 work.
  Out of scope: idiom-modernisation rewrites (separate fix-pass if a major version's new idioms would land alongside as drive-by edits — see § E above); semver-minor floor bumps that would force a downstream API break (defer to a follow-up if surfaced).

---

## FP19 — Launch games from the site (closed 2026-05-04)

**Theme:** user request 2026-05-04 "offer the option to launch the
games from the site, check /mnt/Games/Scripts/Linux/RetroDB/
(RetroDB project; was `/mnt/Storage/...` at the time of the
original request) for references on doing that." The library now
shows games and lets you copy them, but had no in-app way to
actually play one. FP19 adds the missing "play this" button.

### 🎨 Features

- ✅ **FP19** [mame-curator-1018] **RetroArch launch integration (v1.2.0).**
  Lanes: api, frontend.
  - **A — `paths.retroarch` + `paths.retroarch_core`** config
    fields (PathsConfig). Both required for launch; absent
    configuration → 422 with a helpful message.
  - **B — POST `/api/games/{name}/launch`** spawns RetroArch via
    `subprocess.Popen(shell=False)`. ROM resolved from
    `dest_roms/<name>.zip` → `source_roms/<name>.zip`
    (404 if neither exists). Adapted from RetroDB's launcher
    pattern (logged subprocess argv; close_fds=True;
    stdout/stderr/stdin DEVNULL so the worker doesn't deadlock
    on a long-running RetroArch).
  - **C — "Launch in RetroArch" button** in AlternativesDrawer
    (next to the alternatives list). `useLaunchGame` mutation
    + success toast + `toastApiError` on failure (e.g. RetroArch
    not configured surfaces the 422 detail).

  Source: user feedback 2026-05-04 with RetroArch path
  `/mnt/Emulators/Multi-System/RetroArch/RetroArch-Linux-x86_64.AppImage`.
  Dependencies: P03 ✅ (dest_roms layout), P04 ✅ (config + world).

---

## FP18 — refresh-inis auto-patches config.yaml (closed 2026-05-04)

**Theme:** v1.1.0 left the user's INIs downloaded but unused —
`config.yaml`'s `paths.{catver,languages,bestgames,series,mature}`
fields were unset by default and the user had no idea they needed
to be filled in. FP18 closes the loop: `refresh-inis` now patches
the config.

### 🐛 Bug fixes

- ✅ **FP18** [mame-curator-1017] **refresh-inis auto-patches config.yaml + 5-INI banner count.**
  Lanes: cli, frontend.
  - **A — `refresh-inis --config` flag.** After a successful
    download, `paths.{ini-field}` entries that are currently
    unset are pointed at the downloaded files. Existing user-
    supplied paths are preserved (never clobbered). Atomic write
    via `_atomic.atomic_write_text`. Prints a "restart the server"
    hint. `--no-config` opts out.
  - **B — SettingsPage Setup banner counts 5 INIs** (was 4 in
    FP16 § C). `mature.ini` joined the default download set in
    v1.0.1; banner now reflects that.

  Source: user 2026-05-04 ("ini files downloaded. Is the site
  using them though?" then confirmed the banner showed 0/4).
  Dependencies: FP17 ✅, v1.0.1 ✅ (mature.ini in defaults).

---

## FP17 — Library filter expansion (closed 2026-05-04)

**Theme:** user request 2026-05-04 ("Let's add the letter filter
and a few other filters too please. I don't see where the genre
filters are."). The /library FiltersSidebar shipped with only
search + year-range + 4 toggles; missing letter / genre / publisher
/ developer filters that users reasonably expect.

### 🎨 Features

- ✅ **FP17** [mame-curator-1016] **Library filter expansion (v1.1.0).**
  Lanes: api, frontend.
  - **A — Backend `letter` query param** on `/api/games`. Match
    case-insensitive against the description's first character;
    `letter='#'` selects digit-prefixed games (1942, 005, ...).
  - **B — Backend `/api/library/facets`** endpoint. Returns
    `{genres, publishers, developers, letters}` drawn from the
    winners set, deduped + sorted. New `LibraryFacets` schema.
    Backend `developer` param also added (parallel to existing
    `genre` / `publisher`).
  - **C — Frontend filter UI in FiltersSidebar.** Letter row
    (A-Z + `#` buttons, click again to clear); Genre / Publisher /
    Developer Selects with sentinel "(any)" option. New
    `useFacets()` hook (60s staleTime).

  Source: user feedback 2026-05-04 mid-FP16: "Let's add the letter
  filter (oh yes, search filter is working now) and a few other
  filters too please. I don't see where the genre filters are."
  Dependencies: FP16 ✅ (search/year params fix; would have been
  blocked by the same param-name mismatch).

---

## FP16 — Library shipping blockers + INI visibility (closed 2026-05-04)

**Theme:** four user-reported bugs from real-data UAT during the
v1.0.0 cut: search/year-range silently no-op'd (param-name mismatch),
clicking a game did nothing (FP11 § B6 placeholder), no UI signal of
INI presence (FP11 § B3 SetupCheck wiring never landed), and a stale
`index.html` cached by the browser referenced deleted bundle hashes.
All four shipped + bundled with the 0.0.1 → 1.0.0 version bump.

### 🐛 Bug fixes

- ✅ **FP16** [mame-curator-1015] **Search params + drawer + INI banner + cache headers + v1.0.0 bump.**
  Lanes: frontend, api, scripts.
  - **A — useGames param names.** `search` → `q`,
    `year_from` → `year_min`, `year_to` → `year_max` to match the
    backend `/api/games` route.
  - **B — `LibraryPage.onOpen` → AlternativesDrawer.**
    `useAlternatives` + `useOverride` hooks added; drawer mounts on
    selection; success toast + drawer close on override mutation.
  - **C — `useSetupCheck` hook + per-INI status line in Settings →
    Setup banner.** Banner now renders "Reference INIs: 4 / 4
    present" or "Missing: catver.ini, … — run `mame-curator
    refresh-inis --dest data/ini` to download." Inline runtime
    guidance closes the discoverability gap.
  - **D — Backend SPA cache-control headers.** `assets/*` →
    `public, max-age=31536000, immutable`; `index.html` + SPA
    fallback → `no-cache, must-revalidate`. Prevents future
    stale-shell-after-deploy 404s.
  - **E — Bundled with v1.0.0 version bump.** pyproject.toml +
    __init__.py 0.0.1 → 1.0.0; classifier "3 - Alpha" → "5 -
    Production/Stable". Same-SHA tags `FP16-complete` + `v1.0.0`.

  Source: user UAT 2026-05-04 ("Nothing happens when I click on a
  game and the search filter isn't working"; "How do I tell if
  the inis have been downloaded?"; "Failed to fetch dynamically
  imported module: SessionsPage-…js").
  Dependencies: P06 ✅, FP11 ✅ (the FP11 § B3 / § B6
  placeholders).

---

## FP15 — Sessions UX (closed 2026-05-04)

**Theme:** user asked 2026-05-04 "how do I start a session?" —
investigation found three problems: the "Save as session" button
was a no-op stub (`LibraryPage:65`'s `onSaveSession={() => {}}`
that FP11 § B8 was supposed to wire but didn't), no active-session
indicator was visible on /library, and no inline explainer told
first-time users what a session captures.

### 🎨 Features

- ✅ **FP15** [mame-curator-1012] **Sessions UX — Save wiring + active pill + explainer.**
  Lanes: frontend.
  - **A — Wire `LibraryPage.onSaveSession`** to
    `useSessionUpsert.mutate`. Session shape: `include_year_range`
    from FiltersSidebar draft, `include_genres / publishers /
    developers` from `config.filters.preferred_*` chip lists.
    Success toast; `toastApiError` on failure.
  - **B — Active-session pill in /library header.** Click
    navigates to /sessions. Shows "Session: <name>" when active,
    "No active session" when not.
  - **C — One-line explainer above Save button.** "Sessions save
    your current focus (year range + preferred genres / publishers
    / developers) under a name you can return to."

  Source: user follow-up 2026-05-04 ("Also consider, how do we
  start a session. From this screen, what do I need to do.
  Please consider user-friendliness when updating the UX.").
  Dependencies: P06 ✅, FP11 ✅ (sessions hooks).

---

## FP14 — GameCard layout overflow (closed 2026-05-04)

**Theme:** every game tile rendered blank in production because
`aspect-[3/4]` on the image area pushed total card height above
the virtualizer's 280px row, and `Card.overflow-hidden` clipped
the description heading. With 26.5k games and most without art,
the library was unusable — no way to identify games whose
box art hadn't been fetched yet.

### 🎨 Features

- ✅ **FP14** [mame-curator-1008] **GameCard layout overflow + always-on identifier.**
  Lanes: frontend, tests.
  - **A — Card layout fits the virtualizer row.** Replaced
    `aspect-[3/4]` + `object-cover` on the image area with
    `flex-1 min-h-0` + `object-contain`; CardContent gets
    `flex-shrink-0` so it always renders. Card itself gets
    `h-full` to fill the row exactly. Works at any rowHeight
    (covers = 360, masonry / grouped = 280).
  - **B — Always identify the game without art.** When the image
    fails (or never loads), the placeholder div now renders
    `card.description` instead of the generic "No artwork
    available" string. Plus: shortname `<p>` (font-mono) added
    below the description heading — what `mame-curator copy`
    consumes; also disambiguates same-name re-releases
    (1942 Capcom vs Williams).

  Source: user screenshot 2026-05-04 showing 26,539 games in
  Grouped layout, every tile blank with no labels. Verified
  cause: `aspect-[3/4]` at ~360px column width forces 480px
  image height; total card ~540px exceeds 280px rowHeight;
  bottom ~260px clipped by `overflow-hidden`.
  Dependencies: P06 ✅, FP11 ✅ (P06's surface).

---

## P07 — Reference-data refresh + in-app help (planned, slim)

**Theme:** users can refresh stale INI reference data via a CLI
command, search bundled help via Cmd-K, and tweak cards-per-row
from Settings. Introduces the shared `downloads.py` primitive
that P08's setup wizard reuses.

**Scope refinement (2026-05-04):** original P07 included in-app
self-update with rollback and INI-refresh-with-diff-preview UI.
Both moved to **P12 (post-v1)** per user direction "I do still
want self-update but that can be added later" — open-source Linux
audience self-builds via `git pull` for now, and INI refresh as
a CLI subcommand is sufficient for v1 (the diff-preview modal is
a polish-pass UI). Keeping P07 lean unblocks P08+P09 inside the
v1 budget.

**Long-form contract:**
[`docs/superpowers/specs/2026-04-27-roadmap.md` § Phase 7](docs/superpowers/specs/2026-04-27-roadmap.md).

### 🎨 Features

- ✅ **P07** [mame-curator-1009] **`downloads.py` + `help/` + INI-refresh CLI + cards-per-row UI.**
  Lanes: updates, help, downloads, cli, frontend, tests.
  - **A — `downloads.py` primitive.** Async HTTP get with
    sha256 checksum verification, exponential retry (1s/2s/4s/8s,
    max 4 attempts), atomic writes (`.tmp` + rename),
    manual-fallback hook (returns sentinel + URL on final
    failure). Reused by P08's setup wizard. Coverage ≥90%.
  - **B — INI refresh CLI command.** `mame-curator refresh-inis`
    downloads the 5 INI files (categories.ini, mature.ini,
    nplayers.ini, languages.ini, version.ini) from progettoSnaps
    via `downloads.py`. Stdout summary: which files updated, sizes,
    checksums verified. **No diff-preview UI** — that's P12.
  - **C — `cards_per_row_hint` UI control.** `<Select>` (values
    `'auto' | 4 | 5 | 6 | 8`) next to the layout switcher in
    Settings → UI tab. Closes the P06 spec § 210 deferral.
  - **D — HelpPage DOMPurify.** Closes FP11 § H4 security debt:
    sanitize markdown-rendered HTML via DOMPurify before
    `dangerouslySetInnerHTML` (or migrate to react-markdown).
    Per 2026 best-practice, memoize sanitised content.
  - **E — Cmd-K help-topic search.** Wire bundled help articles
    into existing `CmdKPalette` so users can jump to a topic by
    name. Index over titles + first paragraph; ~10 topics
    bundled (Quickstart, Filters, Sessions, Overrides, Playlist
    conflicts, Troubleshooting, Keyboard shortcuts, Glossary).

  Kind: implement.
  Dependencies: P06, FP11, FP12, FP14.

---

## P08 — Setup wizard (closed 2026-05-04, slim)

**Theme:** `git clone && ./run.sh` → working app. Slim P08 ships
the bootstrap scripts only; the original in-browser FileBrowser
wizard with state persistence is deferred to post-v1 per Karpathy 9
push-back — the existing terminal `mame-curator setup` + the
Settings → Setup banner (FP11 § B3) cover the same ground for v1.

**Long-form contract:**
[`docs/superpowers/specs/2026-04-27-roadmap.md` § Phase 8](docs/superpowers/specs/2026-04-27-roadmap.md).

### 🎨 Features

- ✅ **P08** [mame-curator-1011] **Clone-and-run bootstrap scripts.**
  Lanes: setup, scripts.
  - **A — `run.sh` (Linux/macOS).** Python 3.12+ detection
    (with platform-specific install hints on failure), uv
    auto-install via the official installer if missing,
    `uv sync`, runs interactive `mame-curator setup` if
    `config.yaml` is missing, then `mame-curator serve` +
    best-effort browser open. Idempotent — re-run does the
    right thing.
  - **B — `run.bat` (Windows).** Same flow on Windows;
    PowerShell `irm | iex` for the uv install path.

  Scope refinement (2026-05-04): the original plan included a
  full Stage 2 in-browser wizard with `FsBrowser`-driven
  multi-step UI + state persistence + filter preview / filter
  customization steps. Per Karpathy 9 push-back, those layer on
  top of an already-working terminal flow that satisfies the
  "non-technical user can clone-and-run" v1 contract. The
  in-browser wizard is captured as a post-v1 candidate (P13);
  v1 ships with the slim bootstrap.
  Source: P07 close 2026-05-04.
  Dependencies: P07 ✅.

---

## P09 — Polish + v1.0.0 (planned)

**Theme:** finishing work — README hero shot, screenshots,
CONTRIBUTING, final UAT, tag `v1.0.0`, GitHub publish.

### 📚 Documentation

- ✅ **P09** [mame-curator-1013] **v1.0.0 release (slim).**
  Lanes: docs, packaging.
  - **A — README rewrite.** `./run.sh` 3-command quickstart
    front-and-centre; phase status table dropped (everything ✅);
    "What it does" rewritten in user-outcome language; Developer
    setup section preserved for contributors.
  - **B — CHANGELOG `[1.0.0]` bootstrap.** Phase-by-phase summary
    rolled up from the existing `[Unreleased]` body so the v1.0.0
    tag has a single self-contained release note. Keep-a-Changelog
    format preserved.
  - **C — Tag `v1.0.0`.** Annotated tag at the P09 close commit.
    Signals the first stable API contract (post-v1 changes follow
    SemVer).

  Scope refinement (2026-05-04): the original P09 contract called
  for 4-6 screenshots, CONTRIBUTING.md, hero-shot, cross-platform
  UAT on real data. Per Karpathy 9 push-back, those are post-v1
  polish — the user (project author) does Linux UAT on their own
  data; community contributions to screenshots / CONTRIBUTING
  arrive organically post-release. Slim P09 keeps v1 inside
  budget.
  Source: P08 close 2026-05-04.
  Dependencies: P08 ✅.

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

## P11 — Contribute missing thumbnails upstream (planned, post-v1)

**Theme:** the media subsystem (P05) consumes the
[`libretro-thumbnails`](https://github.com/libretro-thumbnails/MAME)
GitHub repos read-only. P11 adds a **push-back** surface: when
the user has a CC-compatible image for a game that isn't yet
in the upstream repo, generate a stage-and-PR flow so the
artwork can be contributed back. Composes with P10 (which
fills gaps from additional scraped sources locally) — once a
gap is filled and the source license allows redistribution,
P11 lets the user push it upstream.

### 🎨 Features

- 📋 **P11** [mame-curator-1007] **Contribute missing thumbnails to libretro-thumbnails.**
  Lanes: api, frontend, media.
  - **A — Upload-prep flow.** Pick a local image file →
    preview at the target dimensions per category
    (`Named_Boxarts` / `Named_Snaps` / `Named_Titles`, PNG,
    256×~) → re-encode + rename to the canonical
    `<short-name>.png`. Backend module under
    `media/contribute/`.
  - **B — License gate.** Confirmation dialog citing
    libretro-thumbnails CC-BY licensing requirement;
    user must affirm the image is their own scan or
    otherwise CC-compatible (publisher-owned official
    artwork explicitly excluded). The dialog uses the
    design §8 concrete-action-label rule.
  - **C — Manual-PR path.** Default low-friction flow: emit
    a directory of staged files + a generated
    `git format-patch` instruction sheet so the user can
    fork + PR manually. No GitHub auth required.
  - **D — Auto-PR path (optional, gated).** With a user-
    supplied GitHub PAT (stored in OS keychain via
    `keyring`, never in `config.yaml`), open the PR via
    GitHub API. Strictly opt-in; the manual path remains
    the default. Threat model: PAT scope must be limited
    to `public_repo`; we never write to repos outside
    `libretro-thumbnails/*`.
  - **E — "Missing-upstream" filter.** Library-page filter
    surfacing games where (a) we have a local image AND
    (b) the libretro-thumbnails 404 was cached. Lets the
    user batch contribute. Driven by the existing media-
    cache index plus a new `upstream_has_thumbnail`
    boolean column in the library state.

  Source: user follow-up question 2026-05-04 ("I see that
  some of the boxarts are from github. Can we upload ones
  they don't have on this github project?"). Captured +
  recommended placement post-v1 (after the project reaches
  daily-driver state); user accepted the same day with
  "this is a feature that can be added towards the end of
  this project."
  Kind: implement.
  Dependencies: P05 (media subsystem); P10 (more useful
  alongside P10's expanded local sources). No dependency
  on P07 / P08 / P09 / FP##.
  Out-of-scope for v1 deliberately — the release-bar focus
  is "user can drive their own library end-to-end"; the
  push-upstream community-contribution path is a quality-
  of-ecosystem feature, not a core-loop blocker.

---

## P14 — Per-game review state (planned, post-v1)

**Theme:** the user's mental model when first running v1 expected
"sessions" to mean "I've reviewed games A through C, resume at D"
— but the v1 Sessions feature is filter-set bookmarking, not
per-game progress tracking. P14 builds the missing feature.

### 🎨 Features

- 📋 **P14** [mame-curator-1014] **Per-game review state.**
  Lanes: api, frontend, persist, tests.
  - **A — `state.yaml` per-game review enum.** New persist file:
    `data/state/<short>.yaml` or one consolidated map. Values:
    `pending` (default) / `reviewed` / `skipped` / `needs-decision`.
    Backend POST `/api/games/<short>/state` mutator + GET on the
    games listing returns the state per item.
  - **B — Library badge for review state.** GameCard shows a small
    icon when state ≠ pending. Filter sidebar adds "Only pending"
    toggle.
  - **C — Per-game decision shortcuts.** Keyboard (R = reviewed,
    S = skipped, ? = needs-decision) when a card is focused or
    while the alternatives drawer is open.
  - **D — Progress chip in /library header.** Shows "1,234 / 26,539
    reviewed (4.6%)" + click → filter to pending only.
  - **E — Per-letter / per-decade walkthrough mode.** Optional
    cluster: a "walkthrough" button that walks the alphabet (or
    decade ranges), surfacing one bucket of pending items at a
    time and tracking completion per bucket.

  Source: user feedback 2026-05-04 mid-FP16: "When I mentioned
  sessions I meant more in terms of I went through all games A to
  C." The v1 Sessions feature is filter-bookmark, not progress
  tracker — this is the missing feature.
  Kind: implement.
  Dependencies: P06 ✅, P04 ✅. No dependency on P10 / P11 / P12.

---

## P12 — In-app self-update + INI diff-preview UI (planned, post-v1)

**Theme:** the deferred-from-P07 surface — in-app self-update
with snapshot+rollback, `updates.channel` (stable/dev) wiring,
UpdatesPanel in Settings, and the INI-refresh diff-preview modal
that shows winners-changed before applying. Split out from P07
2026-05-04 to keep v1 shippable inside budget; user explicitly
wants the feature ("I do still want self-update but that can be
added later").

### 🎨 Features

- 📋 **P12** [mame-curator-1010] **In-app self-update + INI diff-preview UI.**
  Lanes: updates, frontend, api, tests.
  - **A — App self-update (`updates/app.py`).** Version compare,
    snapshot config/overrides/sessions before update,
    git-pull (dev mode) or release-download (frozen install),
    restart hand-off, one-click rollback to prior `git` ref or
    snapshot. Reuses `downloads.py` from P07.
  - **B — `updates.channel` wiring.** `'stable'` checks tagged
    releases; `'dev'` checks `main`. The Settings dropdown
    already exists from FP12 § E; this lane wires it through to
    the check logic.
  - **C — `/api/updates/*` full route logic.** Replaces the
    Phase 4 stubs with real implementations: `/check`,
    `/apply`, `/rollback`, snapshot endpoints.
  - **D — UpdatesPanel UI in Settings.** "Check now" button,
    version-available toast, "What's new" modal (renders
    upstream CHANGELOG), "Apply update" with progress + rollback.
  - **E — INI refresh diff-preview modal.** P07 ships the CLI
    command without a UI; P12 adds a Settings-page preview that
    runs the new INI files against the parsed DAT and shows:
    new winners, dropped winners, changed winners. Confirm-then-
    apply. Reuses the dispatcher pattern from `BackupTab`.

  Source: deferred from original P07 scope 2026-05-04 to keep
  v1 budget tight; user accepted the split with "I do still
  want self update but that can be added later."
  Kind: implement.
  Dependencies: P07 (downloads.py, INI refresh CLI), P09 (v1.0.0
  released — self-update updates _to_ a published version).

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

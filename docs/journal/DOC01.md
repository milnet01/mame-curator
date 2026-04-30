# DOC01 — Phase D documentation audit fold-in

- **Status:** ✅ closed 2026-04-30
- **Original phase label:** (no original — App-Build `DOC##` prefix
  introduced this pass)
- **Long-form contract:** none — DOC01 is a Phase D fix-pass per the
  [`app-workflow` skill](~/.claude/skills/app-workflow/SKILL.md);
  findings are inline in [`ROADMAP.md`](../../ROADMAP.md) under the
  DOC01 section.
- **Spec:** none — Phase D fix-passes use the per-lane review prompts
  as the spec.
- **Theme:** four-round cold-eyes documentation review across five
  lanes — standards consistency / workflow integration / spec ↔
  architecture alignment / phase-history accuracy / discoverability +
  onboarding. Loop closed when one round returned zero actionable
  findings across every touched lane.

## What shipped

### Round 1 (3 Tier-1 / 17 Tier-2 / 7 Tier-3)

- **Tier 1 — Long-form roadmap acceptance checkboxes for shipped
  phases.** Phase 0 + Phase 1 acceptance lists at
  `docs/superpowers/specs/2026-04-27-roadmap.md` were unticked
  despite both phases shipping. Ticked all boxes citing journal
  entries; reworded Phase 0's `uv run ty check` line to `uv run mypy`
  with a note about the Ty deferral.
- **Tier 1 — Fabricated closing-commit citations in three journals.**
  `docs/journal/{P00,P01,P02}.md` cited commit subjects that did
  not exist in `git log`. Replaced with real commits: P00 + P01
  shipped together in `56449c6 chore(scaffold): phase-0 tooling
  and CI baseline + phase-1 parser`; P02's closing landmark is
  `ee80a55 docs(roadmap): tick Phase 2 acceptance — pass-3 Tier 1
  findings closed`. Added 7-char SHA prefixes everywhere.
- **Tier 1 — README front page misrepresented project status.**
  P02 was marked `🔜 next` despite shipping. Flipped to `✅ done`
  with the filter pipeline summary; advanced "next" indicator to
  P03.
- **Tier 2 — Standards slot `coding.md` omitted §8.** Added
  Dependencies-and-tooling row.
- **Tier 2 — `roadmap-format.md` "verbatim" wording misleading.**
  Reworded to "structure verbatim, examples customised."
- **Tier 2 — `filter/spec.md` declared `winners: list[str]` /
  `contested_groups: list[ContestedGroup]`.** Code uses tuples;
  spec updated; `warnings: tuple[str, ...]` added.
- **Tier 2 — `filter/spec.md` advertised `apply_overrides()` /
  `apply_session()` as standalone callables.** Both inlined into
  `run_filter`; spec reworded to describe Phase C / D as internal
  phases.
- **Tier 2 — `filter/spec.md` Phase A rule 5 had a stale
  Mature-category-fallback parenthetical.** No fallback exists in
  `_mature` (`drops.py:52`); rewrote.
- **Tier 2 — `pick_winner` exported but not in spec.** Added to
  Phase B Public-API block.
- **Tier 2 — `parser/spec.md` cross-reference §6.7 should be
  §6.1.** Fixed and cited ADR-0003.
- **Tier 2 — `cli/spec.md` filter status flipped from `planned`
  to `shipped`.**
- **Tier 2 — P00 journal omitted `CHANGELOG.md` skeleton + example
  yaml configs.** Added.
- **Tier 2 — P00 journal had no Spec line.** Added "(none —
  scaffold phase has no module spec)".
- **Tier 2 — `docs/glossary.md` missing "Non-merged ROM set".**
  Added entry explaining merged / split / non-merged ship styles.
- **Tier 2 — README missing links to authoritative docs.**
  Added a "Project docs" section with 9 links.
- **Tier 2 — README did not mention Conventional Commits.**
  Added under Contributing.
- **Tier 2 — README "Project structure" was a one-line stub.**
  Inlined the layered dependency graph.
- **Tier 2 — `git clone <repo>` placeholder.** Replaced with
  `https://github.com/milnet01/mame-curator.git`.
- **Tier 2 — Workflow.md closure dates ambiguous (commit-author vs
  tag).** Annotated as "shipped 2026-04-27, retroactively tagged
  2026-04-30 at the App-Build alignment commit."
- **Tier 2 — CHANGELOG `[Unreleased]` policy unstated.** Added
  "All shipped work stays under `[Unreleased]` until v1.0.0 cut at
  P09" note.
- **Tier 3 — `coding-standards.md` §15 silent about §16 scope.**
  Added scope note.
- **Tier 3 — `commits.md` example "phase A drop predicates" stale.**
  Replaced with real `git log` examples.
- **Tier 3 — CLAUDE.md silent on PR-vs-direct-push for feature
  work.** Stated direct-push is established habit.
- **Tier 3 — Design spec § 12 Phase 4 wizard parenthetical.**
  Added "(consumed by the Phase 8 wizard)".
- **Tier 3 — CLAUDE.md filter smoke missing `--mature` optional
  note.** Added comment.
- **Tier 3 — P02 journal truncated fix-commit subjects.** Quoted
  full subjects.
- **Tier 3 — Closing-commit citations missing SHA prefixes.**
  Added 7-char prefixes.

### Round 2 (2 Tier-1 / 7 Tier-2 / 4 Tier-3) — round-1 patch propagation gaps

- **Tier 1 — `.claude/workflow.md` § Phase history table malformed**
  (4-column rows under a 6-column header for P03–P09). Fixed.
- **Tier 1 — DOC01 finding-count drift between prose and bullets.**
  Round-1 prose advertised 5/17/12 but actual sub-bullets were
  3/17/7 after deduplication. Reconciled in ROADMAP and CHANGELOG.
- **Tier 2 — Long-form roadmap Phase 2 step 7 still described
  `apply_overrides(decisions, overrides_yaml) -> decisions` as a
  public callable.** Round-1 patched only the per-module spec.
  Reworded.
- **Tier 2 — Long-form roadmap Phase 2 step 8 still said `winners:
  list[str]`.** Updated to tuples; added `warnings` field.
- **Tier 2 — `filter/spec.md` `pick_winner` signature wrong**
  (`(candidates, ctx, config) -> Machine | None`). Code is
  `(candidates, parent, ctx, cfg) -> Machine` (4 args, never
  None). Fixed.
- **Tier 2 — `filter/spec.md` `explain_pick` return type wrong**
  (`list[TiebreakerHit]`). Code returns `tuple[TiebreakerHit, ...]`.
  Fixed.
- **Tier 2 — `filter/spec.md` "session-excluded winner remains a
  winner in the underlying `FilterResult`" promised a data shape
  not implemented.** Rewrote: `winners` is the post-slice set, no
  separate underlying field exists.
- **Tier 2 — README and CLAUDE.md layer diagrams in different
  order.** Aligned both to README's order (groups by phase
  number).
- **Tier 2 — Glossary missing `DOC##` entry.** Added.
- **Tier 3 — `docs/standards/README.md` `coding.md` slot row
  omitted §15.** Added.
- **Tier 3 — "Phase D" terminology collision** between App-Build
  Phase D (documentation audit) and filter Phase D (session
  slice). Added two glossary disambiguation entries.
- **Tier 3 — Glossary missing `App-Build alignment commit` entry.**
  Added.
- **Tier 3 — README "Project docs" omitted housekeeping doc
  pointers.** Added bullet for known-issues / ideas /
  audit-allowlist.

### Round 3 (1 Tier-1 / 3 Tier-2 / 3 Tier-3)

- **Tier 1 — Long-form roadmap step 8 still had stale `run_filter`
  signature** (`(parsed, config, overrides, cloneof_map)`). Real
  signature is `(machines, ctx, cfg, overrides, sessions)` — round 2
  fixed result-type shape but missed parameter list. Fixed.
- **Tier 2 — `filter/spec.md` "winner is the maximum element" vs
  `sorted(...)[0]` implementation.** Reworded to "highest-ranked
  candidate (i.e. the first element after the rank-sort, NOT
  Python `max()`; the cmp polarity puts the winner at index 0)".
- **Tier 2 — `preferred_*` substring matching not pinned in
  spec.** `picker.py:67` claims it's pinned by spec, but spec
  didn't say. Added a sentence under the Phase B table
  explicitly documenting Python `in` substring containment.
- **Tier 2 — CLAUDE.md reflow regression — `docs/specs/<ID>.md`
  convention silently dropped.** The streamlining pass collapsed
  this; restored as a one-line note paired with the
  shipped-modules `src/mame_curator/<module>/spec.md` rule.
- **Tier 3 — Glossary alphabetic ordering broken** by the new
  Phase D entries (sat between Fix-pass / Kind instead of Lane /
  Source). Re-sorted.
- **Tier 3 — CLAUDE.md no longer enumerated ADR-0001/0002/0003
  by name** after reflow. Re-added the inline list.
- **Tier 3 (Lane 2 nit) — Workflow.md status header used "Phase D
  documentation audit" terminology that the round-2 disambiguation
  finding flagged.** Already-tracked; closed implicitly when DOC01
  closed.

### Round 4 — clean

Lanes 1, 2, 4 were already clean at round 3 (round-3 patches did
not affect their territory). Lanes 3 and 5 — the only lanes
touched by round-3 patches — both returned zero actionable
findings on round 4. Loop closed.

## What was learned

- **Cold-eyes review reliably catches drift between sibling
  documents.** Round 1 closed all the "easy" findings (a doc said
  X; the truth is Y); round 2 caught the case where the patch
  landed in one of two sibling files (e.g. round-1 fixed
  `filter/spec.md` to say `tuple` not `list`, but the long-form
  roadmap step 8 still claimed `list`). Round 3 caught one final
  near-miss (the `run_filter` parameter list while result type was
  patched). The lesson: when a finding mentions "this spec says X
  but the code says Y", check **every** spec that names the same
  symbol — not just the per-module one.
- **Token-efficiency reflow on context-loaded docs is real.**
  CLAUDE.md went 232 → 166 → 102 lines (-56% line count) without
  dropping load-bearing content; reflow alone (no mid-sentence
  newlines) accounted for ~40% of the savings. Saved as a feedback
  memory for future projects.
- **The `<ID>-complete` retroactive-tag pattern works.** All three
  P-tags annotate the right commits; the per-journal "(retroactively
  tagged at the App-Build alignment commit)" annotation is enough
  for a six-month reader.
- **The CHANGELOG-as-sweep-log convention scaled to multi-round
  doc-fix-passes** — Tier 2 / Tier 3 findings rolled into
  `[Unreleased]` cleanly without inflating the active fix-pass
  bullet count.
- **`--mature` fixture is missing** from `tests/filter/fixtures/`;
  CLI smoke command in CLAUDE.md works without it because the
  flag is optional, but a fixture would let smoke-tests cover the
  Mature drop path. Logged as a follow-up consideration.

## Closing commit

`docs(workflow): close DOC01 — Phase D documentation audit (4 rounds, ~50 findings)`
(this commit). The journal's "What shipped" section enumerates
every Tier-1 / Tier-2 / Tier-3 finding from each round; full diff
covers ~17 files: `ROADMAP.md`, `CHANGELOG.md`, `CLAUDE.md`,
`README.md`, `.claude/workflow.md`, the three journal files, the
six standards slot files, the three per-module specs, the long-form
roadmap, the design spec, and the glossary.

## Tag

`DOC01-complete`.

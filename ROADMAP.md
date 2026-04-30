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

## P03 — Copy + BIOS resolution + RetroArch playlist (next)

**Theme:** given a winner list from P02, copy each winner's `.zip`
plus all transitively-required BIOS `.zip`s to the destination,
write a RetroArch `mame.lpl` playlist, and emit a copy report.

**Long-form contract:**
[`docs/superpowers/specs/2026-04-27-roadmap.md` § Phase 3](docs/superpowers/specs/2026-04-27-roadmap.md).

### 🎨 Features

- 📋 **P03 — `copy/` module.** Implements: BIOS chain resolution
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

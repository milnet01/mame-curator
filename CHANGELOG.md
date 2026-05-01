# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Versioning policy.** This project is pre-alpha. **All shipped
> work stays under `[Unreleased]` until the v1.0.0 cut at P09.**
> No intermediate `v0.0.X` / `v0.Y.0` tags are produced — the
> first git release tag will be `v1.0.0`. Phase-closing
> `<ID>-complete` annotated tags (`P00-complete`, `P01-complete`,
> `P02-complete`, …) mark per-phase ship landmarks but are
> distinct from semver-versioned releases. The CHANGELOG is the
> authoritative record of what shipped per phase; consult
> `git tag --list 'P*-complete'` to map phases to commits.

## [Unreleased]

### FP05 — DS01 closing-review fold-in (closed 2026-05-01)

DS01's closing `/indie-review` returned 14+ surrounding-code findings; FP05 absorbed 20 actionable sub-bullets across Tier 1 (3 real bugs: recycle_partial=True implementation, empty-string `active` rejection, `MemoryError` swallow narrowing), Tier 2 (8 hardening items + 2 reclassified after empirical investigation: B1 transitive-missing-warning conflated with leaf BIOS machines; B4 pause/cancel race didn't apply because `pause()` already short-circuits on `_cancel_flag`), Tier 3 (3 refactors: `_io.read_capped_text` + `_atomic.atomic_write_text` helper extraction; EXDEV handling), and 6 minor LOWs. Three rounds of cold-eyes spec review preceded sign-off (round 1: 8 issues; round 2: 5 + 2 contradictions; round 3: clean). FP05's own closing review surfaced 6 FP05-introduced drift items (Cluster R per the FP02 precedent), all closed inside FP05: recycle_root path mismatch, residual self-reference guard in bios.py, lingering BIOSResolutionError spec mention, dead OSError clause in _atomic.py, atomic_write_text call outside the try block, and cli/spec.md exit-code table out of sync with B10. 275 tests pass; coverage 94.67%; all five gates green. Long-form contract: [`docs/specs/FP05.md`](docs/specs/FP05.md). Follow-ups: FP06 (4 findings in surrounding code from FP05 closing review); FP04 (parser hardening, unchanged).

### DS01 — Pre-P04 debt-sweep fold-in (closed 2026-05-01)

`/debt-sweep` 2026-05-01 (scope `P02-complete..HEAD`) surfaced findings; four rounds of cold-eyes spec review converged on **20 actionable sub-bullets** (with C9 retained in the spec body as a footnoted stale-finding entry — flags already had `help=` strings at HEAD; shipped silently in DOC01/P03). D3 was added during cold-eyes review to prune two stale Tier-3 entries from this same `[Unreleased]` block. Folded into one fix-pass per the App-Build "every audit finding is tracked" hard rule. Prefix is `DS##` (debt-sweep) per the App-Build ID scheme — sourced from `/debt-sweep`, even though many sub-bullets are recovered FP-shaped findings (FP01 deferrals that did not actually close in FP02; pre-P03 sweep `[Unreleased]` Tier-2/3 hardening items; the `runner.py:258` swallow that FP02 deferred forward; record drift on commit `179325a`). Long-form contract: [`docs/specs/DS01.md`](docs/specs/DS01.md). Roadmap: [`ROADMAP.md` § DS01](ROADMAP.md). 20 sub-bullets across four clusters:

- **Cluster A — `copy/` spec+code drift (5):** `data/copy-history` persistence claim drop (3 sites: per-module spec + long-form roadmap); `session_id` ULID claim narrow; unused `self_reference` enum arm drop; `wait_if_paused` race-safety comment; `logger.exception()` on `runner.py:258` bare `except`.
- **Cluster B — Test gaps (4):** Hypothesis property tests for `resolve_bios_dependencies`; `test_cancel_with_keep_partial` strengthened to mid-session cancel; `test_lpl_no_bom` strengthened to UTF-8 round-trip; `source_dir` fixture widened to `scope="module"`.
- **Cluster C — `filter/` + `cli/` hardening (8):** `Sessions(active=...)` `model_validator`; `FilterResult.dropped` to tuple (with enumerated test rewrites at `tests/filter/test_runner.py:71-75`); YAML 1 MB cap; explicit `None` checks over `or {}` falsy-coalesce; `try/except OSError` around `read_text`; CLI `_cmd_filter` `OSError` wrap; atomic report write; sentinel-path antipattern removal.
- **Cluster D — Allowlist + record (3):** `_preferred_score` substring-vs-fnmatch allowlisted (see `docs/audit-allowlist.md` allowlist-001); commit `179325a` (2026-04-30) credited as a body bullet (below) — closes the FP01-deferred macOS/Windows path-separator entry; stale Tier-3 entries struck through with dated footnote.

**Body bullets — DS01 record-keeping closures**

- **`179325a` (2026-04-30)** — cross-platform path-separator fix in `tests/copy/test_fp01_fixes.py` and `tests/copy/test_playlist.py`. The FP01 deferred-list entry for the macOS/Windows path-separator known-issues note was uncredited until DS01.

**Out of scope (deferred to FP04):** `parser/dat.py` `_resolve_xml` `OSError` non-catch + theoretical fd-leak. Tracked as `FP04 — Parser hardening sweep` in ROADMAP, opened by DS01 cold-eyes review so the items are tracked as a roadmap entry rather than CHANGELOG-only prose.

### FP02 — FP01 round-2 fold-in (2026-04-30)

Round-2 indie-review on FP01-patched code surfaced 3 fresh-eyes Tier-2 + 6 Tier-3 findings on the surrounding `copy/` code (not regressions on FP01 fixes themselves). Folded into FP02; closing audit + indie-review pass on FP02 itself surfaced spec drift introduced by the FP02 changes (duplicate `AppendDecision` definition in `copy/spec.md`; stale `recycle_file` docstring), folded into the same FP02 round and closed. Highlights:

- **Tier 2** — `OverwriteRecord.parent` field dropped (always equalled `old_short`; the runner has no `cloneof_map` to compute the actual parent — FP01 #4 design contract); `AppendDecision` widened from a `StrEnum` to a Pydantic model `(kind: AppendDecisionKind, replaces: str | None)` so multi-conflict sessions steer to the right existing entry instead of relying on a brittle "first existing-but-not-winner" heuristic; recycle directories now keyed on `session_id` (`data/recycle/<session_id>/`) instead of just the timestamp, so two sessions recycling within the same second can no longer collide on the directory and overwrite each other's `manifest.json`.
- **Tier 3** — spec typo `mid-copy3` → `mid-copy`; `_chd_missing(plan)` helper extracted (was duplicated across `run_copy` and `_finalize`); `make_cb` closure factory replaced by `functools.partial`; playlist entries filtered to `SUCCEEDED` + `SKIPPED_IDEMPOTENT` (pre-FP02 the builder included `SKIPPED_MISSING_SOURCE` outcomes whose `dst` was never written, producing `mame.lpl` entries pointing at non-existent files); `KeyboardInterrupt` test extended to cover the `progress=callback` branch (previously only `progress=None`); recycle 3+ same-name same-session collision test added.

### FP01 — P03 indie-review fold-in (2026-04-30, closed)

Indie-review pass against fresh P03 surfaced 6 Tier-1 spec/code drift + atomicity bugs that `/audit` (ruff/mypy/bandit/pytest-cov/grep) missed. P03 stays open until FP01 closes; tag `P03-complete` will land after FP01 close. Findings folded into ROADMAP under `## FP01`. Highlights:

- Tier 1 — `copy_one` signature drift (spec lists `progress=None` only; code requires `short_name`/`role` kwargs); missing `KeyboardInterrupt` cleanup in `copy_one`; `OverwriteRecord` allocated but never appended; `PlaylistError` not raised on missing append decision (spec mandates); broken `recycle_file` collision logic (`for _ in [None]` is a 1-shot generator); `read_lpl` doesn't tolerate the legacy 6-line format spec promised — narrowing spec to v1.5+ JSON only.
- Tier 2 — six `# type: ignore[arg-type]` without rationale (root-cause fix: type the work list as `tuple[str, Literal["winner","bios"]]`); FAILED-branch + OVERWRITE+delete coverage gaps; `self_reference` warning enum arm unused; `wait_if_paused` race comment; `O_APPEND` 4 KiB atomicity comment; chunked-path failure test; cancel-keeps-partial test strengthening; hypothesis property tests for `resolve_bios_dependencies`.
- Tier 3 — `errors.py` `__str__` test; `playlist.py` error-branch tests; `session_id` ULID claim narrowed; `data/copy-history` persistence claim dropped (out of v1 scope); known-issues note for cross-platform path separators; `test_lpl_no_bom` strengthened.

### DOC01 — Phase D documentation audit fold-in (2026-04-30)

Five-lane cold-eyes documentation review across standards consistency, workflow integration, spec ↔ architecture alignment, phase-history accuracy, and discoverability/onboarding. Round 1 batched 3 Tier-1 / 17 Tier-2 / 7 Tier-3 actionable findings (after deduplicating cross-lane overlaps and one Tier-1 demoted to Tier-3 on re-read). Round 2 surfaced 2 Tier-1 / 7 Tier-2 / 4 Tier-3 follow-on findings — round-1 patches that did not propagate fully to sibling files (long-form roadmap step 7/8, `pick_winner` / `explain_pick` signatures in spec, layer-diagram order between README and CLAUDE.md, `DOC##` glossary gap). Both rounds folded into the same `DOC01` fix-pass; loop closes when one re-review pass returns zero actionable findings. Highlights:

- **Tier 1** — long-form roadmap acceptance checkboxes for shipped
  phases (P00/P01) ticked; fabricated closing-commit citations in
  `docs/journal/{P00,P01,P02}.md` corrected against `git log`
  (P00 + P01 shipped together in `56449c6`); README front-page
  status flipped (P02 ✅, advance "next" indicator to P03).
- **Tier 2** — standards slot `coding.md` adds §8; spec ↔ code
  drift fixes in `filter/spec.md` (`tuple` not `list`, no
  `apply_overrides()` standalone, no Mature-category fallback,
  `pick_winner` documented); `parser/spec.md` listxml-acquisition
  cross-reference fixed; `cli/spec.md` `filter` flipped to
  shipped; README adds links to authoritative docs, Conventional
  Commits note, inline layer diagram, real clone URL; glossary
  adds "non-merged ROM set"; `[Unreleased]`-until-v1.0.0 policy
  documented.
- **Tier 3** — §15 scope note added; CLAUDE.md PR-vs-direct-push
  policy stated; design § 12 wizard parenthetical; P02 journal
  fix-commit subjects un-truncated; SHA prefixes added to
  closing-commit citations.

### Pre-Phase-3 independent-review sweep — pass 3 (2026-04-27)

Third multi-agent sweep, dispatched after Phase 2 shipped. Four lanes
(filter rule chain / filter YAML I/O / CLI surface / parser deltas).
Two CRITICAL spec violations and one HIGH zombie field surfaced — folded
into the roadmap as Phase 2 → Phase 3 gate criteria (see roadmap §Phase 2
"Pre-Phase-3 indie-review findings"). Tier 2 hardening + Tier 3 structural
findings tracked here per the project's CHANGELOG-as-sweep-log convention.

#### Tier 2 — hardening (deferred until Tier 1 ships)

- 🔒 **filter rule chain** — `_score_preferred` uses substring `in` match where
  spec implies `fnmatch` (drops + sessions both use fnmatch).
  (`filter/picker.py:40-52`)
- 🔒 **filter rule chain** — `explain_pick` reports any non-uniform tiebreaker;
  spec says "tiebreakers that actually decided the winner." The strict reading
  is "would removing this tiebreaker change the winner?" — implementation
  over-reports. (`filter/picker.py:121-126`)
- 🔒 **filter rule chain** — `Sessions(active=...)` model construction bypasses
  validation; only `load_sessions` enforces `active in sessions`. Programmatic
  callers crash with `KeyError` at `runner.py:100` instead of `SessionsError`.
  Move into a Pydantic `model_validator`.
- 🔒 **filter rule chain** — `_score_region` returns `-1` for both `Region.UNKNOWN`
  and the second-priority region (USA at index 1). Spec says UNKNOWN ranks last.
  (`filter/picker.py:67-74`)
- 🔒 **filter rule chain** — `FilterResult.dropped` is `dict[str, DroppedReason]`
  (mutable in-place despite `frozen=True`). All other fields are tuples.
  (`filter/types.py:51-59`)
- 🛡️ **filter YAML I/O** — `yaml.safe_load` defends against CWE-502 deserialization
  but not against alias-bombs; loaders also read entire file into memory before
  parse. Threat is low for self-authored configs but escalates when Phase 7's
  `setup/` ships preset downloads. Cap file size now (1 MB suggested).
  (`filter/overrides.py:31`, `filter/sessions.py:59`)
- 🛡️ **filter YAML I/O** — `sessions: null` (and `[]`, `0`, `""`) silently coerced
  to empty by `raw.get("sessions") or {}`. Same falsy-coalesce bug at
  `body or {}` for individual session bodies. Replace with explicit `None`
  + `isinstance` checks. (`filter/sessions.py:66,71`)
- 🛡️ **filter YAML I/O** — TOCTOU between `path.exists()` fast-path and
  `path.read_text()` lets `OSError` (file deleted, NFS hiccup) escape as
  untyped exception. Wrap `read_text` in `try/except OSError`.
  (`filter/overrides.py:28-31`, `filter/sessions.py:56-59`)
- 🛡️ **filter YAML I/O** — non-string YAML keys silently coerced to strings by
  Pydantic (`overrides: { 123: foo }` → `{"123": "foo"}`); empty key (`: x`)
  becomes `{"None": "x"}`. Spec says "non-empty strings"; no `min_length=1`
  constraint enforces it. (`filter/overrides.py:23`)
- 🛡️ **CLI** — `_cmd_filter` doesn't catch `OSError` from `--catver`/`--listxml`/etc.
  pointing at a directory or unreadable file; raw Python traceback reaches the
  user, violating cli/spec.md §"Errors the CLI catches but never raises."
  (`cli/__init__.py:126`)
- 🛡️ **CLI** — non-atomic write of report JSON. `args.out.write_text(...)` left
  half-written on Ctrl-C / OOM. Phase 3's `copy/` will consume this report;
  use tmp-file + `Path.replace` for atomicity. (`cli/__init__.py:131`)
- 🛡️ **CLI** — sentinel-path antipattern: when `--overrides` / `--sessions` are
  unset, the loader is called with `Path("/nonexistent/overrides.yaml")` to
  trigger the missing-file fast path. Brittle (someone creates the path,
  loaded silently); fails six-month test. Replace with direct `Overrides()` /
  `Sessions()` construction. (`cli/__init__.py:115-124`)
- 🛡️ **parser deltas** — `_resolve_xml` doesn't catch `OSError` from
  `zipfile.ZipFile(...)` (perm-denied, EIO, broken symlink). Same root cause
  as the CLI finding; spec line 138 says every CLI-visible error path stays
  inside `ParserError`. Tier-2 BadZipFile fix scoped narrowly; this completes
  the hardening. (`parser/dat.py:48-50`)
- 🛡️ **parser deltas** — fd leak window in `_resolve_xml`: `zip_ctx = zipfile.ZipFile(path)`
  binds before the `with` block, so a future `__enter__` failure leaks the fd.
  Theoretical (CPython `__enter__` is `return self`) but the idiomatic fix is
  one-line: move `ZipFile(path)` inside the `with` and the `try` around it.
  (`parser/dat.py:49-56`)

#### Tier 3 — structural / spec-tightening

- 🧹 **filter rule chain** — `contested_groups` and `warnings` ordering depends
  on Python dict iteration order; sort by `parent` / canonical key before
  tupling for byte-identical determinism. (`filter/runner.py:43-46,64`)
- 🧹 **filter rule chain** — `_cmd_filter` is 39 lines, conflates four concerns
  (build context, overrides, sessions, run + report). Extract `_build_context`.
  (`cli/__init__.py:99-138`)
- <del>🧹 **CLI** — module docstring (used as `--help` description) lists `copy` as a
  shipped subcommand; only `parse` and `filter` are. (`cli/__init__.py:1-7`)</del>
  — *closed silently in DOC01/P03 (2026-04-30); confirmed stale in DS01 cold-eyes review 2026-05-01*
- <del>🧹 **CLI** — `--catver`, `--dat`, `--languages`, `--bestgames`, `--overrides`,
  `--sessions` lack `help=` strings. (`cli/__init__.py:48-54`)</del>
  — *closed silently in DOC01/P03 (2026-04-30); confirmed stale in DS01 cold-eyes review 2026-05-01*
- 🧹 **CLI** — `args.out.parent.mkdir(parents=True, exist_ok=True)` silently
  materializes arbitrary directory trees from a typo. Document or constrain.
  (`cli/__init__.py:130`)
- 🧹 **CLI** — no INFO log lines for milestones; `-v / --verbose` flips the
  level but the CLI itself emits nothing. Add `logger.info()` at parse and
  load steps for slow-DAT visibility.
- 📝 **spec — filter** — pin: `preferred_*` is `fnmatch` (or `in`); session
  None-value behavior on year/publisher/developer; `lo == hi` is single-year-OK;
  listxml-vs-DAT `<machine>`-name strictness asymmetry is intentional.
- 📝 **spec — filter** — `populate_by_name=True` on `Overrides` is dead weight
  given the loader doesn't accept the alternate key; remove or document the
  alternate YAML key.
- 📝 **spec — parser** — listxml-vs-DAT strictness asymmetry: DAT raises
  `DATError` on missing `<machine name>`; listxml silently skips. Defensible
  but spec is silent.

### Phase 2 complete — filter rule chain (2026-04-27)

Implemented the four-phase filter pipeline: drop (Phase A) → pick
(Phase B) → override (Phase C) → session-slice (Phase D). 154 tests
pass at 97.4% overall coverage; every `filter/` submodule sits at
≥97% (per-phase floor 95% met). All five CI gates green.

#### Added
- **`filter/spec.md`** — full audit-surface contract: 13 typed
  drop reasons, 7-step tiebreaker chain, override + session
  semantics, YAML schemas for `overrides.yaml` / `sessions.yaml`,
  region + revision-key heuristic regexes.
- **`filter/config.py`** — `FilterConfig` (frozen Pydantic, defaults
  match design spec §6.2).
- **`filter/overrides.py`** — `Overrides` model + `load_overrides`
  with `populate_by_name=True` so callers can use either the
  in-memory `entries=` form or the YAML `overrides:` alias.
- **`filter/sessions.py`** — `Session` / `Sessions` models +
  `load_sessions` with empty-session and reversed-year-range guards.
- **`filter/heuristics.py`** — `region_of` (15 region tags + UNKNOWN)
  and `revision_key_of` (family ranks: v-version > rev-letter >
  set-number > unmarked).
- **`filter/types.py`** — `DroppedReason` (StrEnum), `TiebreakerHit`,
  `ContestedGroup`, `FilterResult`, `FilterContext` (all frozen
  Pydantic models with `extra="forbid"`).
- **`filter/drops.py`** — 13 Phase A predicates evaluated in spec
  order; `drop_reason()` returns the first matching reason.
- **`filter/picker.py`** — 7-step Phase B tiebreaker chain composed
  via tuple sort key; `pick_winner()` + `explain_pick()`.
- **`filter/runner.py`** — `run_filter()` orchestrator composing
  Phases A → B → C → D. Override warnings (unknown parent / target /
  cross-group) surface in `FilterResult.warnings` rather than
  crashing.
- **`parser/listxml.py`** — added `parse_listxml_cloneof()` to
  reconstruct parent/clone relationships that Pleasuredome DATs
  strip. Same lxml fast-iter streaming pattern as the existing
  `parse_listxml_disks`.
- **`cli/__init__.py`** — `mame-curator filter` subcommand reads
  DAT + listxml + 5 INIs + overrides + sessions, runs the pipeline,
  writes a JSON `report.json`, prints a one-line summary per result
  group. Honors the cli/spec.md error-routing + exit-code-1 contract.
- **`tests/filter/`** — 90 new tests covering: config schema (4),
  overrides (7), sessions (10), heuristics (17), listxml-cloneof (4),
  drop predicates (16), picker tiebreakers (10), runner end-to-end
  (10), Hypothesis property determinism + idempotency (2),
  30-machine snapshot regression (1), CLI filter (2). Snapshot
  fixture exercises every drop reason, every tiebreaker, the
  override path, and the session slicer.

### Pre-Phase-2 Tier 2 hardening (2026-04-27)

Closed the three Tier 2 items deferred from the first indie-review sweep, plus
their associated spec gaps. 72 tests pass at 95% coverage; all five CI gates
green.

#### Code fixes
- 🐛 **H2** — `_parse_simple_ini` required `]` to be the last character, so
  `[Section] ; trailing comment` and `[Section]# comment` were silently dropped.
  A real-world consequence: an inline-commented `[FOLDER_SETTINGS]` header would
  fail to filter and its keys (`RootFolderIcon=...`) would leak into the parsed
  output as fake machines. Switched to truncating at the first `]`.
  (`parser/ini.py:_parse_simple_ini`)
- 🐛 **M2** — `_resolve_xml` opened `zipfile.ZipFile` without catching
  `zipfile.BadZipFile`. A corrupt or truncated `.zip` would propagate that
  exception out of the parser, slip past the CLI's `ParserError` catch, and
  surface as a Python traceback in the user's terminal — a `cli/spec.md`
  contract violation. Wrapped to `DATError` with the path attached.
  (`parser/dat.py:_resolve_xml`)
- 🛡️ **M3** — `run()` had `return 1` as an "unreachable" fall-through after
  the dispatch chain. Argparse's `required=True` makes that branch unreachable
  from any real argv, so reaching it would mean the dispatch table is out of
  sync with `build_parser()`. Returning `1` would silently hide the bug
  (looks like a runtime error); raising `AssertionError` surfaces it loudly in
  tests. (`cli/__init__.py:run`)

#### Spec edits
- **`parser/spec.md`** — pinned: INI section headers with inline comments
  (`[Mature] ; old format`) are tolerated by truncating at the first `]`;
  corrupt/truncated DAT zips raise `DATError`, never propagate `BadZipFile`.
- **`cli/spec.md`** — added the "unreachable fall-through discipline" clause
  to the dispatch-pattern section: `run()`'s default branch MUST raise
  `AssertionError`, not return a runtime-error exit code.

### Pre-Phase-2 independent-review sweep — pass 2 (2026-04-27)

Second multi-agent sweep after Tier 1 fixes landed. Reframed around spec
accuracy: "where is the spec unclear, not the code wrong?" Every finding
classified as (a) code-not-following-spec → fix code, (b) spec gap → tighten
spec, or (c) code-quality → backlog. Closed nine spec gaps (G1–G10) and
created `cli/spec.md` (C1) so the CLI surface has a contract per standards §7.

#### Spec edits
- **`parser/spec.md`** — pinned: empty `<rom>`/`<biosset>` `name` → DATError;
  `<year>` outside `[1970, 2100]` → None; DriverStatus is open-membership
  (warn + None on unknown, never DATError); INI encoding policy (strict
  UTF-8 with latin-1 fallback warning, never silent U+FFFD); zip-slip
  protection on `.zip` wrappers; `Rom.size` non-negative; `_META_SECTIONS`
  filter applies to all five INI parsers.
- **`coding-standards.md`** — §9 now mandates errors → stderr, success/summary
  → stdout, and that errors at trust boundaries MUST include the offending
  input identifier (path, URL, key, line). §8 adds phase-staged dependency
  declaration: phase-N runtime deps live in `[project.optional-dependencies]`
  until the importing code ships.
- **`cli/spec.md` (new)** — pins subcommand inventory, exit codes (1 runtime,
  2 reserved for argparse), output routing, error-message contract, logging
  configuration discipline, and the `set_defaults(func=...)` migration plan
  for Phase 2/3.

#### Code fixes (one commit per gap)
- 🛡️ **G1+G6** — empty `<rom>`/`<biosset>` `name` and negative `Rom.size`
  raise DATError via Pydantic Field constraints.
- 🛡️ **G2** — `<year>` outside `[1970, 2100]` → None.
- 🛡️ **G3** — unknown `<driver status>` warning rate-limited to once per
  unique status string (avoids 43k log lines on a single MAME schema bump).
- 🛡️ **G4** — INI encoding: try strict UTF-8, fall back to latin-1 with a
  warning. Never silent corruption.
- 🛡️ **G5** — zip-slip protection: `.zip` member with absolute path or `..`
  component → DATError.
- 🛡️ **G7** — `_META_SECTIONS` filter applied to `parse_languages`,
  `parse_bestgames`, `parse_mature` (was: only catver + series).
- 🛡️ **G8+G9** — CLI errors route to stderr with the input path prefixed.
- 📦 **G10** — `fastapi` / `uvicorn` / `httpx` / `sse-starlette` moved from
  `[project.dependencies]` to `[project.optional-dependencies].api`. Phase 1
  end users no longer pull the web stack.

### Pre-Phase-2 independent-review sweep (2026-04-27)

Three-lane multi-agent review (parser / CLI / filter spec). 6 actionable Tier 1
findings, 5 Tier 2, 3 Tier 3. Tier 1 fixed in this batch.

#### Tier 1 — fixed
- 🐛 **parser**: `<rom size>` non-numeric value raised bare `ValueError` instead
  of `DATError`, breaking the spec's typed-exception contract. (`dat.py:_rom_from_element`)
- 🐛 **parser**: `lxml.iterparse` sibling cleanup was incomplete — `Element.clear()`
  empties an element but doesn't detach it from its parent, so the spine of the
  43k-machine DAT accumulated empty `<machine>` siblings throughout the parse,
  defeating streaming. Applied the canonical lxml fast-iter idiom. (`dat.py`, `listxml.py`)
- 🐛 **parser**: `parse_series` accepted progettoSnaps' `[FOLDER_SETTINGS]` /
  `[ROOT_FOLDER]` metadata sections as if they were series names. Added a
  metadata-section deny-list. (`ini.py:parse_series`)
- 🐛 **parser**: spec promised duplicate-key INI emits `logger.warning`;
  implementation silently overwrote. (`ini.py:_parse_simple_ini`)
- 🐛 **cli**: runtime errors returned exit code 2, conflicting with argparse's
  reserved meaning (usage error). Changed to 1. (`cli.py:_cmd_parse`)
- 🐛 **cli**: `logging.basicConfig(...)` ran at module import time, mutating
  global root-logger state for any process importing `mame_curator.main`. Moved
  into `main()` and gated level on a new `--verbose` flag. (`main.py`)

#### Tier 2 — deferred (hardening, pre-Phase-2)
- INI section headers with inline `;` comments silently dropped (parser H2).
- Unknown driver-status warning fires per element instead of once per status (parser M5).
- CLI errors should go to stderr, not stdout, with path-prefixed messages (cli M1).
- `_cmd_parse` doesn't catch `BadZipFile` (cli M2).
- Replace unreachable fall-through in `run()` with an explicit assertion (cli M3).

#### Tier 3 — structural backlog
- Adopt `parse_cmd.set_defaults(func=...)` dispatch pattern for Phase 2/3 subcommands.
- Add at least one `tests/parser/test_real_dat_fixture.py` with a truncated
  Pleasuredome-style DAT to anchor tests against external behavior, not internal modules.
- Add `--version` flag.

### Added
- **Phase 1 complete** — DAT and INI parsers (`parser/`):
  - Streaming DAT parser (`lxml.iterparse`) tolerant of `.xml` or `.zip` input.
  - Five INI parsers (catver / languages / bestgames / mature / series) sharing a single small walker.
  - CHD detector via official MAME `-listxml`.
  - `Machine` Pydantic model (frozen, validated) with `Rom`, `BiosSet`, and `DriverStatus`.
  - Manufacturer split for `"Foo (Bar license)"` → `(publisher, developer)`.
  - CLI subcommand `mame-curator parse <dat>` prints summary stats.
  - Smoke run against the user's real 43,579-machine 0.284 DAT: parsed in 4.6 s.
  - Empirical finding: Pleasuredome DATs strip `cloneof` / `romof` — Phase 2's filter joins parent/clone info from official MAME `-listxml` instead.
- **Phase 0 complete** — project scaffolding: uv-managed Python ≥ 3.12 venv,
  src/ layout, ruff (lint + format), mypy (strict), pytest (with coverage + ≥85%
  enforced gate), bandit, pre-commit hooks (mirroring CI), GitHub Actions CI matrix
  on Linux/macOS/Windows × Python 3.12/3.13, MIT license, README skeleton,
  example yaml configs (config / overrides / sessions).
- Release workflow gated on green CI: tagging `vX.Y.Z` triggers a re-run of
  all CI checks against the tag; only if every check passes is a GitHub
  Release created with the built sdist + wheel attached.

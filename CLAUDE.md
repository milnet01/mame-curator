# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when
working with code in this repository.

This project follows the
[**Ants App-Build** workflow](~/.claude/skills/app-workflow/SKILL.md).
Phases A–C produced docs (signed off); P00–P02 shipped (parser +
filter); P03 onwards is implementation work.

## Where state lives — read these on session start

1. **This file** — stable rules and conventions.
2. **`.claude/workflow.md`** — live status header (current phase,
   active item, step number, blockers). After reading, **summarise
   back to the user** before doing any work (per
   [`app-workflow` SKILL.md "Resumption flow"](~/.claude/skills/app-workflow/SKILL.md)).
3. **`docs/standards/coding-standards.md`** — consolidated rules
   (the four App-Build slot files in `docs/standards/` redirect
   here; §15 precedence depends on single-file ordering).
4. **`docs/specs/<active-id>.md`** OR **`src/mame_curator/<module>/spec.md`** —
   the contract for the currently-active item. Per-module specs
   exist for shipped modules (`parser`, `filter`, `cli`); upcoming
   P##/FP## items each get a `docs/specs/<ID>.md` written at Step 1
   of the per-phase loop.
5. **`docs/audit-allowlist.md`** — read **additionally** before
   invoking `/audit` or `/indie-review` so already-confirmed
   project-specific false positives aren't re-flagged.

## Project status

Pre-alpha, phase-based development on `main`. Currently shipped:

- **P00 ✅** — scaffold + tooling + CI baseline.
  See [`docs/journal/P00.md`](docs/journal/P00.md).
- **P01 ✅** — `parser/` (DAT + 5 INIs + listxml CHD detector +
  cloneof map + manufacturer split).
  See [`docs/journal/P01.md`](docs/journal/P01.md).
- **P02 ✅** — `filter/` (drop/pick/override/session-slice rule
  chain). `mame-curator filter` CLI subcommand. 158 tests pass;
  filter coverage 96%+.
  See [`docs/journal/P02.md`](docs/journal/P02.md).

**Next:** P03 — `copy/` module (BIOS chain resolution, atomic
copy, RetroArch `.lpl` writer, pause/resume/cancel, recycle-bin).
See [`ROADMAP.md`](ROADMAP.md).

Everything else (`copy/`, `api/`, `media/`, frontend, `updates/`,
`help/`, `setup/`) is unimplemented.

## Authoritative docs — read before writing code

These supersede anything inferred from existing code:

- **`docs/standards/coding-standards.md`** — enforceable rules
  (file-size caps, security, testing, imports/layering). When two
  rules conflict, the lower-numbered section wins (§15). The four
  App-Build slot files in `docs/standards/` (`coding.md`,
  `testing.md`, `commits.md`, `documentation.md`) are redirect
  pointers, not duplicates.
- **`docs/standards/roadmap-format.md`** — `ROADMAP.md` and
  `CHANGELOG.md` authoring contract.
- **`docs/superpowers/specs/2026-04-27-roadmap.md`** — long-form
  authoritative phase plan with anti-jump rules. **Do not import
  or stub modules from a later phase**, and do not advance until
  the current phase's acceptance checkboxes are ticked.
- **`docs/superpowers/specs/2026-04-27-mame-curator-design.md`** —
  full design spec (flow, routes, data shapes).
- **`ROADMAP.md`** — queue summary (links to the long-form plan).
- **`docs/decisions/<NNNN>-<slug>.md`** — ADRs for non-obvious
  choices (currently: ADR-0001 record-decisions, ADR-0002
  cloneof-from-listxml, ADR-0003 listxml-tiered-acquisition).
- **`src/mame_curator/<module>/spec.md`** — per-feature contract.
  The spec is the audit surface; **no feature merges without a
  `spec.md` next to its code**, and the test file enforces every
  clause in it.

## Common commands

Setup:
```bash
uv sync --extra dev
uv run pre-commit install
```

Full local CI gate (all five must pass on `main`):
```bash
uv run pytest
uv run ruff check
uv run ruff format --check
uv run mypy
uv run bandit -c pyproject.toml -r src
```

Run a single test:
```bash
uv run pytest tests/parser/test_dat.py::test_parse_dat_minimal -xvs
```

CLI smoke:
```bash
# P01 — parse a DAT and print summary stats
uv run mame-curator parse <path-to-DAT.xml-or-.zip>

# P02 — run the filter pipeline against a fixture set
uv run mame-curator filter \
    --dat tests/filter/fixtures/snapshot_dat.xml \
    --listxml tests/filter/fixtures/snapshot_listxml.xml \
    --catver tests/filter/fixtures/snapshot_catver.ini \
    --languages tests/filter/fixtures/snapshot_languages.ini \
    --bestgames tests/filter/fixtures/snapshot_bestgames.ini \
    --overrides tests/filter/fixtures/snapshot_overrides.yaml \
    --sessions tests/filter/fixtures/snapshot_sessions.yaml \
    --out /tmp/report.json
```

## Architecture

Layered, acyclic dependency graph (enforced by review;
`import-linter` planned). **Do not violate the layer order:**

```
parser/    ← pure, no internal deps
filter/    ← depends on parser/
media/     ← depends on parser/
copy/      ← depends on parser/ + filter/
updates/   ← depends on parser/ (re-parse on INI refresh) + downloads.py
help/      ← filesystem only (loads bundled markdown)
api/       ← depends on all of the above
setup/     ← depends on parser/ (filter preview) + downloads.py
main.py    ← wires everything together
```

CLI entry is `mame_curator.main:main` (registered in
`pyproject.toml [project.scripts]`); subcommands are dispatched in
`cli/__init__.py` via `argparse.set_defaults(func=...)` per
`cli/spec.md`.

### Parser specifics worth knowing

- **DAT parsing streams via `lxml.iterparse`**, never
  `etree.parse` — the real DAT is ~48 MB / 43k machines. Each
  `<machine>` element is `.clear()`ed after processing.
- **DAT input may be `.xml` or `.zip`** containing exactly one
  XML; both paths route through `parse_dat()`.
- **Pleasuredome DATs strip `cloneof` / `romof`.** P01 records
  this faithfully (`Machine.cloneof = None` for every machine).
  Parent/clone relationships come from the official MAME
  `-listxml` and are joined by short name in P02's filter — see
  [ADR-0002](docs/decisions/0002-cloneof-from-listxml.md).
- **`Machine` is a frozen Pydantic model** with `extra="forbid"`.
  All parser data structures are immutable.
- **Manufacturer field carries two facts.** `"Capcom (Sega license)"`
  → `(publisher="Capcom", developer="Sega")` via
  `split_manufacturer()`.

### Errors and logging

- Each module defines its own typed exception hierarchy
  (`parser.ParserError` with `DATError` / `INIError` /
  `ListxmlError` subclasses). Never raise bare `Exception`.
- Library code uses `logging.getLogger(__name__)`. **`print()` is
  forbidden outside `cli/`** — CLI surfaces use `rich.Console`.
- Error messages must be actionable: name the file, the cause,
  and the next step the user should take (see
  `coding-standards.md` § 9).

## Workflow rules specific to this repo

- **TDD is the default for non-trivial logic.** Write `spec.md`
  first, then failing tests, then implementation. The long-form
  roadmap's per-phase "Tests to write first" list is binding, not
  suggestive.
- **File-size caps:** Python files soft 300 / hard 500 lines;
  functions soft 50 / hard 80. Hitting the hard cap means the
  file or function is doing too much.
- **No backwards-compat shims pre-v1.0.0.** Until v1.0.0, breaking
  is fine — config formats and APIs are explicitly unstable.
- **Conventional Commits** (`feat:`, `fix:`, `chore:`, etc.) per
  `coding-standards.md` § 12. App-Build's `<ID>: <description>`
  mandate from `commits.md` § 1.1 is **deliberately not adopted**
  here — see `docs/standards/commits.md` for the rationale and how
  to cite stable IDs in commit bodies/scopes when relevant.
- **Phase-closing commits** state which phase finished, e.g.
  `feat(parser): phase-1 dat and ini parsers with CLI smoke`. Tag
  the closing commit `<ID>-complete` (e.g. `P02-complete`) per the
  app-workflow `/close-phase` flow.
- **No `--no-verify`, no `# nosec` without an inline threat-model
  comment, no `# type: ignore` without a reason.** Workarounds
  need a root-cause fix or a comment naming the constraint.
- **Coverage gates per module:** `parser/` ≥90%, `filter/` ≥95%,
  `copy/` ≥85%, `api/` ≥80%, frontend ≥70%, overall backend ≥85%.

## Closing a phase

Run **`/close-phase`** once steps 1–4 of the per-phase 9-step
loop are done. The skill orchestrates `/audit` + `/indie-review`
(in parallel), triages findings, and either closes the phase
cleanly (tag + push prompt) or spawns the next `FP##` for fix-
pass work.

## Push policy

Public repo (verified via `gh repo view --json visibility`); per
the user's global `~/.claude/CLAUDE.md` § 6, push freely after
each release. No batching gate. Repo visibility cached in
`.claude/workflow.md` § 1 status header.

## Resumption flow — MANDATORY summarise-back

Per the app-workflow skill:

1. **Parallel batch:** read this file + `.claude/workflow.md`
   status header (one tool-call batch).
2. Once the active item Kind is known, read the matching
   `docs/standards/<which>.md` (single read).
3. **Summarise back to the user:** "We're on `<ID>` step `<N>`,
   last did `<X>`, next is `<Y>`."
4. Wait for confirm or redirect.

**Never skip step 3.** Catching state-recovery errors before
working is cheaper than corrective rounds later.

## Things this project deliberately does not do

- No telemetry / analytics endpoints, ever (verified by grep gate
  per long-form roadmap Phase 7).
- No client-side filesystem access in the (planned) frontend —
  all disk operations cross the API.
- No software-list routing, no LaunchBox/EmulationStation export,
  no cloud sync — those are post-v1 (see long-form roadmap
  "Future enhancements").

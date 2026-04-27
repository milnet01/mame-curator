# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

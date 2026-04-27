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
- **Phase 0 (partial)** — local Python scaffolding: uv-managed Python ≥ 3.12 venv,
  src/ layout, `pyproject.toml` configured for ruff (lint + format), mypy (strict),
  pytest (with coverage + ≥85% gate), bandit; MIT license; README skeleton;
  example yaml configs (config / overrides / sessions).
- **Phase 0 (pending)** — git scaffold and CI: `.gitignore`, `.gitleaksignore`,
  `.pre-commit-config.yaml`, `.github/workflows/ci.yml`, and `.github/workflows/release.yml`
  are still to be created (per `docs/superpowers/plans/2026-04-27-phase-0-scaffold.md`
  Tasks 7–11). The repository has not yet been initialized as a git project.

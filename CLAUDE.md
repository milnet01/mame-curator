# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Pre-alpha, phase-based development. Currently shipped:

- **Phase 0 (partial)** — local Python tooling (`uv`, `pyproject.toml`, ruff/mypy/pytest/bandit configured). **Pending:** `.gitignore`, `.gitleaksignore`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml`, `.github/workflows/release.yml`. The repo is **not yet a git project** (no `.git/`). Per the roadmap's anti-jump rules these gaps must be closed before Phase 2 begins.
- **Phase 1 (complete)** — `parser/` (DAT + 5 INIs + listxml CHD detector + manufacturer split). 51 tests pass; coverage on `parser/` ≥ 95%.

Everything else (`filter/`, `copy/`, `api/`, `media/`, frontend, `updates/`, `help/`, `setup/`) is unimplemented.

## Authoritative docs — read before writing code

These supersede anything inferred from existing code:

- `docs/standards/coding-standards.md` — enforceable rules (file-size caps, security, testing, imports/layering). When two rules conflict, the lower-numbered section wins (§15).
- `docs/superpowers/specs/2026-04-27-roadmap.md` — strictly sequential phase plan with anti-jump rules. **Do not import or stub modules from a later phase**, and do not advance until the current phase's acceptance checkboxes are ticked.
- `docs/superpowers/specs/2026-04-27-mame-curator-design.md` — full design spec (flow, routes, data shapes).
- `src/mame_curator/<module>/spec.md` — per-feature contract. The spec is the audit surface; **no feature merges without a `spec.md` next to its code**, and the test file enforces every clause in it.

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

CLI smoke (Phase 1):
```bash
uv run mame-curator parse <path-to-DAT.xml-or-.zip>
```

## Architecture

Layered, acyclic dependency graph (enforced by review; `import-linter` planned). **Do not violate the layer order**:

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

CLI entry is `mame_curator.main:main` (registered in `pyproject.toml [project.scripts]`); subcommands are dispatched in `cli.py` and grow as phases land.

### Parser specifics worth knowing

- **DAT parsing streams via `lxml.iterparse`**, never `etree.parse` — the real DAT is ~48 MB / 43k machines. Each `<machine>` element is `.clear()`ed after processing.
- **DAT input may be `.xml` or `.zip`** containing exactly one XML; both paths route through `parse_dat()`.
- **Pleasuredome DATs strip `cloneof` / `romof`.** Phase 1 records this faithfully (`Machine.cloneof = None` for every machine). Parent/clone relationships come from the official MAME `-listxml` and are joined by short name in Phase 2's filter — see `parser/spec.md` "Edge cases" and the roadmap's Phase 2 notes.
- **`Machine` is a frozen Pydantic model** with `extra="forbid"`. All parser data structures are immutable.
- **Manufacturer field carries two facts.** `"Capcom (Sega license)"` → `(publisher="Capcom", developer="Sega")` via `split_manufacturer()`.

### Errors and logging

- Each module defines its own typed exception hierarchy (`parser.ParserError` with `DATError` / `INIError` / `ListxmlError` subclasses). Never raise bare `Exception`.
- Library code uses `logging.getLogger(__name__)`. **`print()` is forbidden outside `cli.py`** — CLI surfaces use `rich.Console`.
- Error messages must be actionable: name the file, the cause, and the next step the user should take (see standards §9 for the canonical good/bad examples).

## Workflow rules specific to this repo

- **TDD is the default for non-trivial logic.** Write `spec.md` first, then failing tests, then implementation. The roadmap's per-phase "Tests to write first" list is binding, not suggestive.
- **File-size caps:** Python files soft 300 / hard 500 lines; functions soft 50 / hard 80. Hitting the hard cap means the file or function is doing too much.
- **No backwards-compat shims pre-v1.0.0.** Until v1.0.0, breaking is fine — config formats and APIs are explicitly unstable.
- **Conventional Commits** (`feat:`, `fix:`, `chore:`, etc.). Phase-completing commits state which phase finished, e.g. `feat(parser): phase-1 dat and ini parsers with CLI smoke`.
- **No `--no-verify`, no `# nosec` without an inline threat-model comment, no `# type: ignore` without a reason.** Workarounds need a root-cause fix or a comment naming the constraint.
- **Coverage gates per module:** `parser/` ≥90%, `filter/` ≥95%, `copy/` ≥85%, `api/` ≥80%, frontend ≥70%, overall backend ≥85%.

## Things this project deliberately does not do

- No telemetry / analytics endpoints, ever (verified by grep gate per roadmap Phase 7).
- No client-side filesystem access in the (planned) frontend — all disk operations cross the API.
- No software-list routing, no LaunchBox/EmulationStation export, no cloud sync — those are post-v1 (see roadmap "Future enhancements").

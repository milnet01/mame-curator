# CLAUDE.md

Layered on `~/.claude/CLAUDE.md`. Both apply; project rules below extend, never contradict.

This project follows the global workflow, [`~/.claude/workflow.md`](~/.claude/workflow.md): its five states, its gates, and § 6's six conditions for an item being done. The App-Build phase workflow it replaced was retired 2026-09-28; its state file is kept as history at [`docs/history/app-build-workflow-state.md`](docs/history/app-build-workflow-state.md).

## Session start — read & summarise

1. **This file** + **`roadmap_query status:active`** (what is open; the roadmap intro says what is next) — one parallel read.
2. **Summarise back to the user**: "We're on `<ID>` (or between items), last did `<X>`, next is `<Y>`." Wait for confirm or redirect. **Never skip this step**.
3. When the active item's `Kind` is known, read the matching `docs/standards/<which>.md` (one read).
4. Before invoking `check-code` or `review-code`, additionally read `docs/audit-allowlist.md`.

For shipped status and what's next, see [`ROADMAP.md`](ROADMAP.md) and [`CHANGELOG.md`](CHANGELOG.md). Per-phase journals up to 2026-09-27 live in [`docs/journal/`](docs/journal/). Rule pedigree moved out of this file is in [`docs/history/claude-md.md`](docs/history/claude-md.md).

## Authoritative docs (supersede anything inferred from code)

- [`docs/standards/coding-standards.md`](docs/standards/coding-standards.md) — enforceable rules. When two rules conflict, lower-numbered section wins (§15 precedence).
- [`docs/plans/phase-plan.md`](docs/plans/phase-plan.md) — long-form phase plan with anti-jump rules. **Do not import or stub modules from a later phase**, and do not advance until current acceptance checkboxes are ticked.
- [`docs/design.md`](docs/design.md) — full design spec.
- `~/.claude/standards/spec-format.md` (global, read in place) + [`docs/standards/spec-format-overrides.md`](docs/standards/spec-format-overrides.md) (this project's deltas O1–O4) — how `docs/specs/` and `docs/plans/` files are named and structured. Skeletons are the global ones in `~/.claude/standards/skeletons/`.
- `src/mame_curator/<module>/spec.md` — per-feature contract for shipped modules; the audit surface. **No feature merges without a `spec.md` next to its code**, and the test file enforces every clause. In-flight `P##` items use `docs/specs/<ID>-<topic>.md`. Fix-passes (`FP##` / `DS##`) correct code against the existing module spec and don't *require* one of their own — but a **multi-tier fold-in** (one spanning several themed clusters) MAY carry a long-form spec at `docs/specs/<ID>-<topic>.md` when an upfront contract earns its keep by catching drift before implementation.
- [`docs/decisions/`](docs/decisions/) — ADRs for non-obvious choices.

## Common commands

```bash
# Setup
uv sync && uv run pre-commit install

# Full CI mirror — runs every check .github/workflows/ci.yml runs, in the
# same order (backend gates + api-type-sync + frontend + gitleaks). Keep it
# in lockstep with ci.yml. `--fresh` provisions first (uv sync + npm ci).
./local-CI.sh

# Backend-only gate (must pass on `main`; a subset of the above)
uv run ruff check && uv run ruff format --check && uv run mypy \
    && uv run bandit -c pyproject.toml -r src && uv run pytest

# Single test
uv run pytest tests/parser/test_dat.py::test_parse_dat_minimal -xvs

# CLI smoke
uv run mame-curator parse <DAT.xml-or-.zip>
uv run mame-curator filter --help
uv run mame-curator copy --help
```

**The dev tools are the `dev` dependency group** (mame-curator-1106), which
a plain `uv sync` installs. The old `uv sync --extra dev` now fails: there is
no such extra. **Trap — `uv sync --no-dev` strips them.** The next
`uv run mypy` then finds a copy outside the project that cannot see
`fastapi`, and `uv run pytest` dies on the `--cov` args in `pyproject.toml`'s
addopts. It reads as broken code, not as an environment change. `run.sh` /
`run.bat` sync with `--inexact --no-dev`, so launching the app installs no
dev tools and removes none. Recover with a plain `uv sync`.

## Architecture

Layered, acyclic dependency graph (enforced by review):

```
parser/    ← pure, no internal deps           (P01 ✅)
filter/    ← parser/                          (P02 ✅)
copy/      ← parser/ + filter/                (P03 ✅)
api/       ← all of the above                 (P04 ✅)
media/     ← parser/                          (P05 ✅, P10 ✅)
updates/   ← parser/ + downloads.py           (P07 ✅)
cli/       ← parser/ + filter/ + copy/ + api/ (subcommand dispatch)
main.py    ← wires everything together
frontend/  ← React/Vite SPA, separate JS tree (P06 ✅, P14 ✅)

(Help docs are filesystem-only — served by `api/routes/help.py` from a
repo-root `docs/help/` directory; setup-wizard endpoints live in
`api/routes/stubs.py`. Neither is a Python package under
`src/mame_curator/`.)
```

CLI entry: `mame_curator.main:main`; subcommands dispatch in `cli/__init__.py` via `argparse.set_defaults(func=...)` per `cli/spec.md`.

### Load-bearing parser facts

- **DAT parsing streams via `lxml.iterparse`** with per-element `.clear()` — never `etree.parse`; the real DAT is too large to load whole.
- **DAT input may be `.xml` or `.zip`** (single XML inside); both route through `parse_dat()`.
- **Pleasuredome DATs strip `cloneof` / `romof`.** Parent/clone relationships come from MAME `-listxml` joined by short name — see [ADR-0002](docs/decisions/0002-cloneof-from-listxml.md). They carry no `<driver>` either; `driver_status` is filled from `-listxml` by `apply_driver_status`.
- **`Machine` is a frozen Pydantic model** (`extra="forbid"`); all parser data structures are immutable.
- **Manufacturer carries two facts.** `"Capcom (Sega license)"` → `(publisher="Capcom", developer="Sega")` via `split_manufacturer()`.

### Errors and logging

- Each module defines a typed exception hierarchy (`parser.ParserError` → `DATError` / `INIError` / `ListxmlError`). Never raise bare `Exception`.
- Library code uses `logging.getLogger(__name__)`. **`print()` is forbidden outside `cli/`** — CLI surfaces use `rich.Console`.

## Project-specific overrides

- **TDD is the default** for non-trivial logic. The long-form roadmap's per-phase "Tests to write first" list is binding.
- **File-size caps:** Python files soft 300 / hard 500 lines; functions soft 50 / hard 80.
- **Coverage gates per module:** `parser/` ≥90%, `filter/` ≥95%, `copy/` ≥85%, `api/` ≥80%, frontend ≥70%, overall backend ≥85%.
- **What counts as breaking is [`docs/standards/versioning-overrides.md`](docs/standards/versioning-overrides.md).** Past v1.0.0, a `config.yaml` key rename or removal either migrates the old form or ships as a MAJOR. The HTTP API is internal and is not a breaking surface.
- **No `# nosec` without an inline threat-model comment, no `# type: ignore` without a reason.**
- **Conventional Commits** (`feat:`, `fix:`, `chore:`, etc.) per `coding-standards.md` § 12. App-Build's `<ID>: <description>` mandate is **deliberately not adopted**; cite phase IDs in body or scope. See `docs/standards/commits.md`.
- **No `<ID>-complete` tags and no new `docs/journal/` entries.** Both were App-Build habits, dropped 2026-09-28; the existing tags and journals stay as history. Releases still get their `vX.Y.Z` tag.
- **Direct push to `main`**. Repo is **PUBLIC** (checked 2026-04-30 via `gh repo view`), so push freely per global rule 6.

## Karpathy clarity — where it lands here

The six conditions in global `workflow.md` § 6 are the verify-step plan global 12 mandates. Beyond that:

- **Surface ambiguity** → where an item needs a spec, `review-contract` reads it cold before user sign-off — an independent reviewer catches author bias up front.
- **Push back on complexity** → before writing tests: name the simpler alternative, defer to user on the call.
- **Reproduce before fixing** → on every fix: the failing test lands first, proves the diagnosis, locks in regression coverage.
- **Stay in your lane** → while implementing and while fixing findings: every changed line traces to the active item; no drive-by reformat or preferred-idiom rewrite of working code; pre-existing dead code is surfaced in the reply, not deleted.

## Finishing an item

Global `workflow.md` § 6 decides when an item is done. Here that means: `check-code` + `review-code` (read `docs/audit-allowlist.md` first), every finding given a disposition by `close-findings`, then the record made true — `CHANGELOG.md`, the roadmap status flip, and `review-ledger` / `/debt-sweep` where the item warrants it.

## Things this project deliberately does not do

- No telemetry / analytics, ever (grep-gated per long-form roadmap Phase 7).
- No client-side filesystem access in the planned frontend — all disk operations cross the API.
- No software-list routing, no LaunchBox / EmulationStation export, no cloud sync — post-v1 (see long-form roadmap "Future enhancements").

# CLAUDE.md

Guidance for Claude Code working in this repo. Project follows the [**Ants App-Build** workflow](~/.claude/skills/app-workflow/SKILL.md); the skill auto-loads when `.claude/workflow.md` is present.

## Session start — read & summarise

1. **This file** + **`.claude/workflow.md` § 1 status header** — one parallel read.
2. **Summarise back to the user**: "We're on `<ID>` step `<N>`, last did `<X>`, next is `<Y>`." Wait for confirm or redirect. **Never skip this step** — state-recovery errors are cheaper to catch before working than to undo after.
3. When the active item's `Kind` is known, read the matching `docs/standards/<which>.md` (one read).
4. Before invoking `/audit` or `/indie-review`, additionally read `docs/audit-allowlist.md`.

For status of shipped phases and what's next, see [`ROADMAP.md`](ROADMAP.md) (queue summary) and [`CHANGELOG.md`](CHANGELOG.md) (what shipped). Per-phase journals live in [`docs/journal/`](docs/journal/). Currently shipped: P00, P01, P02; **next: P03 (`copy/`)**.

## Authoritative docs (supersede anything inferred from code)

- **[`docs/standards/coding-standards.md`](docs/standards/coding-standards.md)** — enforceable rules. When two rules conflict, lower-numbered section wins (§15 precedence). Slot files in `docs/standards/` are redirect pointers, not duplicates.
- **[`docs/superpowers/specs/2026-04-27-roadmap.md`](docs/superpowers/specs/2026-04-27-roadmap.md)** — long-form authoritative phase plan with anti-jump rules. **Do not import or stub modules from a later phase**, and do not advance until current acceptance checkboxes are ticked.
- **[`docs/superpowers/specs/2026-04-27-mame-curator-design.md`](docs/superpowers/specs/2026-04-27-mame-curator-design.md)** — full design spec (flow, routes, data shapes).
- **`src/mame_curator/<module>/spec.md`** — per-feature contract for shipped modules; the audit surface. **No feature merges without a `spec.md` next to its code**, and the test file enforces every clause in it. In-flight `P##` / `FP##` / `DOC##` items use `docs/specs/<ID>.md`, written at Step 1 of the 9-step loop.
- **[`docs/decisions/`](docs/decisions/)** — ADRs for non-obvious choices. Currently: ADR-0001 (record-decisions), ADR-0002 (cloneof-from-listxml), ADR-0003 (listxml-tiered-acquisition).

## Common commands

```bash
# Setup
uv sync --extra dev && uv run pre-commit install

# Full local CI gate (all five must pass on `main`)
uv run pytest && uv run ruff check && uv run ruff format --check && \
    uv run mypy && uv run bandit -c pyproject.toml -r src

# Single test
uv run pytest tests/parser/test_dat.py::test_parse_dat_minimal -xvs

# CLI smoke — P01
uv run mame-curator parse <path-to-DAT.xml-or-.zip>

# CLI smoke — P02 (--mature is optional; all other inputs required)
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

Layered, acyclic dependency graph (enforced by review; `import-linter` planned). **Do not violate the layer order:**

```
parser/    ← pure, no internal deps           (P01 ✅)
filter/    ← parser/                          (P02 ✅)
copy/      ← parser/ + filter/                (P03 — next)
media/     ← parser/                          (P05)
api/       ← all of the above                 (P04)
updates/   ← parser/ + downloads.py           (P07)
help/      ← filesystem only (bundled MD)     (P07)
setup/     ← parser/ + downloads.py           (P08)
main.py    ← wires everything together
```

CLI entry: `mame_curator.main:main` (registered in `pyproject.toml [project.scripts]`); subcommands dispatch in `cli/__init__.py` via `argparse.set_defaults(func=...)` per `cli/spec.md`.

### Load-bearing parser facts

- **DAT parsing streams via `lxml.iterparse`** with per-element `.clear()` — never `etree.parse`; the real DAT is ~48 MB / 43k machines.
- **DAT input may be `.xml` or `.zip`** (single XML inside); both route through `parse_dat()`.
- **Pleasuredome DATs strip `cloneof` / `romof`.** P01 records this faithfully (`Machine.cloneof = None` for every machine); parent/clone relationships come from the official MAME `-listxml`, joined by short name in P02 — see [ADR-0002](docs/decisions/0002-cloneof-from-listxml.md).
- **`Machine` is a frozen Pydantic model** (`extra="forbid"`); all parser data structures are immutable.
- **Manufacturer carries two facts.** `"Capcom (Sega license)"` → `(publisher="Capcom", developer="Sega")` via `split_manufacturer()`.

### Errors and logging

- Each module defines a typed exception hierarchy (`parser.ParserError` → `DATError` / `INIError` / `ListxmlError`). Never raise bare `Exception`.
- Library code uses `logging.getLogger(__name__)`. **`print()` is forbidden outside `cli/`** — CLI surfaces use `rich.Console`.
- Error messages must be actionable: file, cause, next step (see `coding-standards.md` § 9).

## Workflow rules specific to this repo

- **TDD is the default** for non-trivial logic. The long-form roadmap's per-phase "Tests to write first" list is binding.
- **File-size caps:** Python files soft 300 / hard 500 lines; functions soft 50 / hard 80. Hard cap = doing too much.
- **Coverage gates per module:** `parser/` ≥90%, `filter/` ≥95%, `copy/` ≥85%, `api/` ≥80%, frontend ≥70%, overall backend ≥85%.
- **No backwards-compat shims pre-v1.0.0.** Config formats and APIs are explicitly unstable until v1.0.0.
- **No `--no-verify`, no `# nosec` without an inline threat-model comment, no `# type: ignore` without a reason.** Workarounds need a root-cause fix or a comment naming the constraint.
- **Conventional Commits** (`feat:`, `fix:`, `chore:`, etc.) per `coding-standards.md` § 12. App-Build's `<ID>: <description>` mandate is **deliberately not adopted**; cite phase IDs in body or scope. See `docs/standards/commits.md`.
- **Phase-closing commits** name the phase, e.g. `docs(roadmap): tick Phase 2 acceptance — pass-3 Tier 1 findings closed`. Tag with `<ID>-complete`. (P00 + P01 shipped together in `56449c6`; both tags point at it.)
- **Direct push to `main`** for all work (feature, fix, doc, debt-sweep) — solo development; PR-based workflow is **not** adopted (no opt-in signals: no `CODEOWNERS`, no branch protection, no `Merge pull request` history).
- **Push freely after each ship.** Repo is public (cached `PUBLIC` in `.claude/workflow.md` § 1 via `gh repo view`); no CI-minutes batching per global `~/.claude/CLAUDE.md` § 6.

## Closing a phase

Run **`/close-phase`** after steps 1–4 of the 9-step loop. The skill orchestrates `/audit` + `/indie-review` in parallel, triages, and either closes cleanly (tag + push prompt) or spawns the next `FP##`.

## Things this project deliberately does not do

- No telemetry / analytics, ever (grep-gated per long-form roadmap Phase 7).
- No client-side filesystem access in the planned frontend — all disk operations cross the API.
- No software-list routing, no LaunchBox / EmulationStation export, no cloud sync — post-v1 (see long-form roadmap "Future enhancements").

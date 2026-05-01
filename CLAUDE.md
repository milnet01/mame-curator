# CLAUDE.md

Layered on top of the global rules at `~/.claude/CLAUDE.md` (rules 1–12, including the Karpathy clarity / surgical-edit rules 8–12). Both apply; project rules below extend, never contradict.

This project follows the [**Ants App-Build** workflow](~/.claude/skills/app-workflow/SKILL.md); the skill auto-loads when `.claude/workflow.md` is present.

## Session start — read & summarise

1. **This file** + **`.claude/workflow.md` § 1 status header** — one parallel read.
2. **Summarise back to the user**: "We're on `<ID>` step `<N>`, last did `<X>`, next is `<Y>`." Wait for confirm or redirect. **Never skip this step** — state-recovery errors are cheaper to catch before working than to undo after.
3. When the active item's `Kind` is known, read the matching `docs/standards/<which>.md` (one read).
4. Before invoking `/audit` or `/indie-review`, additionally read `docs/audit-allowlist.md`.

For shipped status and what's next, see [`ROADMAP.md`](ROADMAP.md) and [`CHANGELOG.md`](CHANGELOG.md). Per-phase journals live in [`docs/journal/`](docs/journal/).

## Authoritative docs (supersede anything inferred from code)

- [`docs/standards/coding-standards.md`](docs/standards/coding-standards.md) — enforceable rules. When two rules conflict, lower-numbered section wins (§15 precedence).
- [`docs/superpowers/specs/2026-04-27-roadmap.md`](docs/superpowers/specs/2026-04-27-roadmap.md) — long-form phase plan with anti-jump rules. **Do not import or stub modules from a later phase**, and do not advance until current acceptance checkboxes are ticked.
- [`docs/superpowers/specs/2026-04-27-mame-curator-design.md`](docs/superpowers/specs/2026-04-27-mame-curator-design.md) — full design spec.
- `src/mame_curator/<module>/spec.md` — per-feature contract for shipped modules; the audit surface. **No feature merges without a `spec.md` next to its code**, and the test file enforces every clause. In-flight `P##` items use `docs/specs/<ID>.md`. Fix-passes (`FP##` / `DS##`) don't get specs — they correct code against the existing module spec.
- [`docs/decisions/`](docs/decisions/) — ADRs for non-obvious choices.

## Common commands

```bash
# Setup
uv sync --extra dev && uv run pre-commit install

# Full local CI gate (all five must pass on `main`)
uv run pytest && uv run ruff check && uv run ruff format --check \
    && uv run mypy && uv run bandit -c pyproject.toml -r src

# Single test
uv run pytest tests/parser/test_dat.py::test_parse_dat_minimal -xvs

# CLI smoke (full P02 invocation lives in tests/filter/fixtures/)
uv run mame-curator parse <DAT.xml-or-.zip>
uv run mame-curator filter --help
uv run mame-curator copy   --help
```

## Architecture

Layered, acyclic dependency graph (enforced by review):

```
parser/    ← pure, no internal deps           (P01 ✅)
filter/    ← parser/                          (P02 ✅)
copy/      ← parser/ + filter/                (P03 ✅)
api/       ← all of the above                 (P04 — next)
media/     ← parser/                          (P05)
updates/   ← parser/ + downloads.py           (P07)
help/      ← filesystem only (bundled MD)     (P07)
setup/     ← parser/ + downloads.py           (P08)
main.py    ← wires everything together
```

CLI entry: `mame_curator.main:main`; subcommands dispatch in `cli/__init__.py` via `argparse.set_defaults(func=...)` per `cli/spec.md`.

### Load-bearing parser facts

- **DAT parsing streams via `lxml.iterparse`** with per-element `.clear()` — never `etree.parse`; the real DAT is ~48 MB / 43k machines.
- **DAT input may be `.xml` or `.zip`** (single XML inside); both route through `parse_dat()`.
- **Pleasuredome DATs strip `cloneof` / `romof`.** Parent/clone relationships come from MAME `-listxml` joined by short name — see [ADR-0002](docs/decisions/0002-cloneof-from-listxml.md).
- **`Machine` is a frozen Pydantic model** (`extra="forbid"`); all parser data structures are immutable.
- **Manufacturer carries two facts.** `"Capcom (Sega license)"` → `(publisher="Capcom", developer="Sega")` via `split_manufacturer()`.

### Errors and logging

- Each module defines a typed exception hierarchy (`parser.ParserError` → `DATError` / `INIError` / `ListxmlError`). Never raise bare `Exception`.
- Library code uses `logging.getLogger(__name__)`. **`print()` is forbidden outside `cli/`** — CLI surfaces use `rich.Console`.
- Error messages must be actionable: file, cause, next step (see `coding-standards.md` § 9).

## Project-specific overrides

- **TDD is the default** for non-trivial logic. The long-form roadmap's per-phase "Tests to write first" list is binding.
- **File-size caps:** Python files soft 300 / hard 500 lines; functions soft 50 / hard 80.
- **Coverage gates per module:** `parser/` ≥90%, `filter/` ≥95%, `copy/` ≥85%, `api/` ≥80%, frontend ≥70%, overall backend ≥85%.
- **No backwards-compat shims pre-v1.0.0.** Config formats and APIs are explicitly unstable.
- **No `# nosec` without an inline threat-model comment, no `# type: ignore` without a reason.** Refines global rule 1 for the project's preferred suppression form.
- **Conventional Commits** (`feat:`, `fix:`, `chore:`, etc.) per `coding-standards.md` § 12. App-Build's `<ID>: <description>` mandate is **deliberately not adopted**; cite phase IDs in body or scope. See `docs/standards/commits.md`.
- **Phase-closing commits** name the phase and tag with `<ID>-complete` (annotated). E.g. `feat(parser): close FP04 — typed-error OSError catches`.
- **Direct push to `main`** — solo development; no PR-workflow opt-in signals (no `CODEOWNERS`, no branch protection, no `Merge pull request` history). Repo is **PUBLIC** (cached in `.claude/workflow.md`), so push freely per global rule 6.

## Closing a phase

Run **`/close-phase`** after steps 1–4 of the 9-step loop. The skill orchestrates `/audit` + `/indie-review` in parallel, triages, and either closes cleanly (tag + push prompt) or spawns the next `FP##`.

## Things this project deliberately does not do

- No telemetry / analytics, ever (grep-gated per long-form roadmap Phase 7).
- No client-side filesystem access in the planned frontend — all disk operations cross the API.
- No software-list routing, no LaunchBox / EmulationStation export, no cloud sync — post-v1 (see long-form roadmap "Future enhancements").

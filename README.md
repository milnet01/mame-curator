# MAME Curator

> Curate the best playable arcade games from a MAME ROM set, with a modern web UI.

**Status:** pre-alpha, in active development on `main`. APIs and config formats may change without notice until v1.0.0.

## What works today

| Phase | Status | What you can do |
|---|---|---|
| 0 — Scaffold | ✅ done | `uv sync --extra dev` produces a green project; lint/type/test/security gates pass |
| 1 — Parser | ✅ done | `mame-curator parse <DAT>` streams a 43,579-machine DAT in ~5 s and prints summary stats; the five progettoSnaps INI files and the official MAME `-listxml` (for CHD detection) are also parsed |
| 2 — Filter | ✅ done | `mame-curator filter` runs the four-phase rule chain (drop → pick → override → session-slice) and emits a deterministic JSON report. 158 tests; `filter/` coverage 96%+ |
| 3 — Copy | ✅ done | `mame-curator copy` ships atomic copy + BIOS resolution + RetroArch `.lpl` writer + playlist conflict handling. 5 fix-passes + 1 debt-sweep folded in (FP01, FP02, DS01, FP05, FP06, FP07, FP08, FP04); 300 tests; `copy/` coverage 95%+ |
| 4 — API | 🔜 next | FastAPI surface + SSE for live progress |
| 5 — Media | ⏳ planned | libretro-thumbnails URL builder + lazy-fetch cache |
| 6 — Frontend | ⏳ planned | React 19 + Tailwind v4 + shadcn/ui — grid, alternatives drawer, themes, layouts |
| 7 — Updates + Help | ⏳ planned | Self-update, INI-refresh-with-diff, in-app help |
| 8 — Setup wizard | ⏳ planned | Bootstrap script + browser-based first-run flow |
| 9 — Release | ⏳ planned | v1.0.0 on GitHub |

The full plan lives in [`docs/superpowers/specs/2026-04-27-roadmap.md`](docs/superpowers/specs/2026-04-27-roadmap.md).

## What it does (when finished)

- Reads a MAME non-merged ROM set + DAT XML.
- Drops non-arcade entries (BIOSes, devices, computers, console BIOSes, mahjong/casino/etc.) using community reference data (`catver.ini`, `languages.ini`, `bestgames.ini`, ...).
- Picks the best version from each parent/clone group via a deterministic rule chain (community ratings → parent over clone → driver status → region → revision → ...).
- Lets you override picks through a modern web UI with cover art, screenshots, and side-by-side comparisons.
- Copies the chosen ROMs (plus required BIOSes) to a separate destination, leaving the source untouched.
- Generates a RetroArch playlist (`mame.lpl`) so games show pretty descriptions in RetroArch without renaming files.

See the [design spec](docs/superpowers/specs/2026-04-27-mame-curator-design.md) for the full picture.

## Requirements

- Python ≥ 3.12
- `uv` ≥ 0.5 ([install](https://docs.astral.sh/uv/getting-started/installation/))
- A modern web browser
- A MAME non-merged ROM set + matching DAT XML (you supply these)

## Dev environment setup

```bash
git clone https://github.com/milnet01/mame-curator.git
cd mame-curator
uv sync --extra dev
uv run pre-commit install
```

## Run the app (dev mode)

For visual testing of the SPA against a live backend:

```bash
./scripts/dev.sh                  # uses ./config.yaml
./scripts/dev.sh --config /elsewhere/config.yaml
```

This starts the FastAPI backend on `:8080` and the Vite dev server on
`:5173` with hot-module reload. Visit
[http://127.0.0.1:5173](http://127.0.0.1:5173). Ctrl+C stops both.

A real `config.yaml` with paths to your MAME ROM set + DAT is
required — the backend's startup parses the DAT before serving any
routes.

For a "production-shape" run (single `:8080` serving the
pre-built SPA from `frontend/dist/`) without HMR:

```bash
( cd frontend && npm run build )
uv run mame-curator serve --config config.yaml
```

## Run the full CI gate locally

All five must pass on `main`:

```bash
uv run pytest
uv run ruff check
uv run ruff format --check
uv run mypy
uv run bandit -c pyproject.toml -r src
```

## Project structure

Layered, acyclic dependency graph (lower layers have no
dependencies on higher ones; enforced by review):

```
parser/    ← pure, no internal deps           (P01 ✅)
filter/    ← depends on parser/               (P02 ✅)
copy/      ← depends on parser/ + filter/     (P03 ✅)
api/       ← depends on all of the above      (P04 — next)
media/     ← depends on parser/               (P05)
updates/   ← parser/ + downloads.py           (P07)
help/      ← filesystem only (bundled MD)     (P07)
setup/     ← parser/ + downloads.py           (P08)
main.py    ← wires everything together
```

`mame_curator.main:main` is the CLI entry; subcommands live in
`cli/__init__.py` and dispatch via `argparse.set_defaults(func=...)`.
The full layout is in the [design spec §11](docs/superpowers/specs/2026-04-27-mame-curator-design.md).

## Project docs

- [`ROADMAP.md`](ROADMAP.md) — queue summary, links to long-form
  per-phase plan.
- [`CHANGELOG.md`](CHANGELOG.md) — what shipped (Keep-a-Changelog
  format).
- [`CLAUDE.md`](CLAUDE.md) — project rules and Claude Code
  resumption protocol.
- [`docs/standards/coding-standards.md`](docs/standards/coding-standards.md)
  — enforceable code rules; supersedes anything inferred from
  existing code.
- [`docs/glossary.md`](docs/glossary.md) — domain terms (MAME,
  Pleasuredome, listxml, BIOS chain, etc.).
- [`docs/decisions/`](docs/decisions/) — ADRs for non-obvious
  architectural choices.
- [`docs/journal/`](docs/journal/) — phase-closing journals
  (P00 / P01 / P02 closed).
- [`docs/superpowers/specs/2026-04-27-roadmap.md`](docs/superpowers/specs/2026-04-27-roadmap.md)
  — long-form authoritative phase plan.
- [`docs/superpowers/specs/2026-04-27-mame-curator-design.md`](docs/superpowers/specs/2026-04-27-mame-curator-design.md)
  — full design spec (flow, routes, data shapes).
- **Workflow housekeeping:**
  [`docs/known-issues.md`](docs/known-issues.md) (deferrals
  blocked by missing dependencies),
  [`docs/ideas.md`](docs/ideas.md) (post-v1 ideas captured during
  development),
  [`docs/audit-allowlist.md`](docs/audit-allowlist.md)
  (confirmed-false-positive memory for `/audit` and
  `/indie-review`).

## License

[MIT](LICENSE).

## Contributing

This project is in active development. See the [implementation
roadmap](docs/superpowers/specs/2026-04-27-roadmap.md) for the
planned phases. Issues and PRs welcome.

**Commit format.** This project uses [Conventional
Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`,
`docs:`, `chore:`, `test:`, `refactor:`, `ci:` …). The
deliberate deviation from App-Build's `<ID>: <description>`
mandate is documented in
[`docs/standards/commits.md`](docs/standards/commits.md). Cite
roadmap IDs (`P03`, `DOC01`) in the commit body when relevant,
not the subject.

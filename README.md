# MAME Curator

> Curate the best playable arcade games from a MAME ROM set, with a modern web UI.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

MAME Curator turns a ~26,000-machine MAME DAT into a small,
human-usable arcade library: it drops the BIOS-and-device cruft, picks
the best version of each game from parent/clone groups, lets you
override picks through a browser UI, and copies the chosen ROMs (plus
required BIOSes) to a separate destination — leaving the source
untouched and writing a RetroArch playlist (`mame.lpl`) on the way
out.

## Quickstart

```bash
git clone https://github.com/milnet01/mame-curator.git
cd mame-curator
./run.sh             # macOS / Linux  —  use run.bat on Windows
```

`run.sh` provisions Python 3.12+, installs `uv`, syncs deps, runs the
interactive setup wizard the first time (it asks for your MAME DAT,
ROM directory, and destination), then opens
[http://127.0.0.1:8080](http://127.0.0.1:8080) in your browser.

Re-run `./run.sh` anytime — it's idempotent.

## What it does

- **Reads a MAME non-merged ROM set + DAT XML** (~48 MB / 43k machines
  streams in ~5 s via `lxml.iterparse`).
- **Drops non-arcade entries** (BIOSes, devices, computers, console
  BIOSes, mahjong / casino / mature) using community reference data
  (`catver.ini`, `languages.ini`, `bestgames.ini`, ...).
- **Picks the best version** from each parent/clone group via a
  deterministic rule chain (community ratings → parent over clone →
  driver status → region → revision → ...).
- **Lets you override picks** through a browser UI with cover art,
  screenshots, and side-by-side comparisons of alternative versions.
- **Saves curation focus as named sessions** (year range + preferred
  genres / publishers / developers) you can switch between.
- **Copies the chosen ROMs** (plus required BIOSes) atomically to a
  separate destination, leaving the source untouched, with a recycle-
  bin for replaced files.
- **Writes a RetroArch playlist** (`mame.lpl`) so games show pretty
  descriptions in RetroArch without renaming files.
- **Stays local-only** — no telemetry, no analytics, no cloud sync,
  ever (grep-gated; see `docs/standards/coding-standards.md`).

## Requirements

- **Python ≥ 3.12** — `run.sh` / `run.bat` will tell you where to
  install it if missing.
- **A modern web browser** — the SPA is shipped pre-built in
  `frontend/dist/` so no Node toolchain is needed for end users.
- **A MAME non-merged ROM set + matching DAT XML** — you supply
  these. The setup wizard prompts for paths.
- **(Optional)** the four progettoSnaps reference INIs — fetch them
  any time after first run with `uv run mame-curator refresh-inis
  --dest data/ini`.

## Common operations

```bash
# Refresh the four mandatory progettoSnaps reference INIs
uv run mame-curator refresh-inis --dest data/ini

# Re-run the interactive setup wizard (overwrite existing config)
uv run mame-curator setup --force

# Run the API server explicitly (run.sh does this for you)
uv run mame-curator serve --config config.yaml --port 8080

# CLI dry-run / copy without the UI
uv run mame-curator filter --dat ... --catver ... --out report.json
uv run mame-curator copy --dry-run --filter-report report.json --source ... --dest ...
```

## Developer setup

If you want to hack on the SPA itself (HMR, Vite dev server):

```bash
git clone https://github.com/milnet01/mame-curator.git
cd mame-curator
uv sync --extra dev
uv run pre-commit install
( cd frontend && npm install )
./scripts/dev.sh                  # backend :8080 + Vite :5173 (HMR)
```

The full local CI gate (must be green on `main`):

```bash
uv run pytest && uv run ruff check && uv run ruff format --check \
    && uv run mypy && uv run bandit -c pyproject.toml -r src
( cd frontend && npx vitest run && npx tsc --noEmit && npm run build )
```

## Project structure

Layered, acyclic dependency graph:

```
parser/    ← pure, no internal deps           (P01)
filter/    ← parser/                          (P02)
copy/      ← parser/ + filter/                (P03)
api/       ← all of the above                 (P04)
media/     ← parser/                          (P05)
frontend/  ← React 19 + Tailwind v4 + shadcn  (P06)
updates/   ← parser/ + downloads.py           (P07)
help/      ← filesystem only (bundled MD)     (P07)
main.py    ← wires everything together
```

## Project docs

- [`ROADMAP.md`](ROADMAP.md) — what shipped + post-v1 backlog.
- [`CHANGELOG.md`](CHANGELOG.md) — release notes (Keep-a-Changelog).
- [`CLAUDE.md`](CLAUDE.md) — project rules.
- [`docs/standards/coding-standards.md`](docs/standards/coding-standards.md)
  — enforceable code rules.
- [`docs/glossary.md`](docs/glossary.md) — MAME / Pleasuredome /
  listxml / BIOS-chain terminology.
- [`docs/decisions/`](docs/decisions/) — ADRs for non-obvious choices.
- [`docs/journal/`](docs/journal/) — per-phase shipping journals.

## License

[MIT](LICENSE).

## Contributing

Issues and PRs welcome. The project uses [Conventional
Commits](https://www.conventionalcommits.org/) (`feat:` / `fix:` /
`docs:` / `chore:` / `test:` / `refactor:` / `ci:`); cite roadmap IDs
(e.g. `P07`, `FP15`) in the commit body when relevant, not the
subject. See [`docs/standards/commits.md`](docs/standards/commits.md)
for details.

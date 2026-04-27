# MAME Curator

> Curate the best playable arcade games from a MAME ROM set, with a modern web UI.

**Status:** pre-alpha, in active development on `main`. APIs and config formats may change without notice until v1.0.0.

## What works today

| Phase | Status | What you can do |
|---|---|---|
| 0 — Scaffold | ✅ done | `uv sync --extra dev` produces a green project; lint/type/test/security gates pass |
| 1 — Parser | ✅ done | `mame-curator parse <DAT>` streams a 43,579-machine DAT in ~5 s and prints summary stats; the five progettoSnaps INI files and the official MAME `-listxml` (for CHD detection) are also parsed |
| 2 — Filter | 🔜 next | Drop rules (categories / language / driver status / CHD / genre / publisher / developer / year), winner-pick tiebreaker chain, manual overrides, session focus |
| 3 — Copy | ⏳ planned | Atomic copy + BIOS resolution + RetroArch `.lpl` writer + playlist conflict handling |
| 4 — API | ⏳ planned | FastAPI surface + SSE for live progress |
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
git clone <repo>
cd mame-curator
uv sync --extra dev
uv run pre-commit install
```

## Run the test suite

```bash
uv run pytest
uv run ruff check
uv run ruff format --check
uv run mypy
uv run bandit -c pyproject.toml -r src
```

All five must pass on `main`.

## Project structure

See [the design spec §11](docs/superpowers/specs/2026-04-27-mame-curator-design.md) for the canonical layout.

## License

[MIT](LICENSE).

## Contributing

This project is in active development. See the [implementation roadmap](docs/superpowers/specs/2026-04-27-roadmap.md) for the planned phases. Issues and PRs welcome.

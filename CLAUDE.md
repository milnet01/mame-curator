# CLAUDE.md

Layered on `~/.claude/CLAUDE.md`; this file holds only where the project differs. It follows [`~/.claude/workflow.md`](~/.claude/workflow.md), whose § 6 decides when an item is done.

## Session start

1. Read this file and `roadmap_query status:active` in parallel.
2. Summarise: "We're on `<ID>` (or between items), last did `<X>`, next is `<Y>`." Then wait for a confirm, unless the user pasted a handoff note: that is the go-ahead, so summarise and start in the same reply (user, 2026-11-11). Never skip the summary, except when the session opens with another session's request: answer that first.
3. Once the item's `Kind` is known, read the matching `docs/standards/<which>.md`.
4. Before `check-code` or `review-code`, read `docs/audit-allowlist.md`.

## Authoritative docs (supersede anything inferred from code)

- [`docs/standards/coding-standards.md`](docs/standards/coding-standards.md): enforceable rules, including file-size caps, coverage gates, `# nosec` and `# type: ignore` reasons. On a conflict the lower-numbered section wins (§ 15).
- [`docs/plans/phase-plan.md`](docs/plans/phase-plan.md): never import or stub a later phase's modules; each phase's "Tests to write first" list is binding.
- [`docs/design.md`](docs/design.md): the design spec.
- `~/.claude/standards/spec-format.md` plus [`docs/standards/spec-format-overrides.md`](docs/standards/spec-format-overrides.md) (O1–O4).
- `src/mame_curator/<module>/spec.md`: the contract for a shipped module. **No feature merges without a `spec.md` next to its code**, and its test file enforces every clause. An in-flight `P##` item uses `docs/specs/<ID>-<topic>.md`. A fix-pass (`FP##` / `DS##`) needs no spec of its own; one spanning several clusters may carry one.
- [`docs/decisions/`](docs/decisions/): ADRs.
- [`docs/standards/versioning-overrides.md`](docs/standards/versioning-overrides.md): what counts as breaking. Past v1.0.0 a `config.yaml` key rename or removal migrates the old form or ships as a MAJOR. The HTTP API is internal; the Backup export file is a breaking surface.

## Commands

[`docs/dev-commands.md`](docs/dev-commands.md) holds setup, the gates, single tests, the desktop bundles and the CLI smoke. Read it before running any of them. `./local-CI.sh` is the full CI mirror.

## Architecture

Layered and acyclic, enforced by review:

```
parser/    ← pure, no internal deps
filter/    ← parser/
copy/      ← parser/ + filter/
api/       ← all of the above
media/     ← parser/
updates/   ← parser/ + downloads.py
cli/       ← parser/ + filter/ + copy/ + api/
main.py    ← wires everything together
frontend/  ← React/Vite SPA, separate JS tree
```

Help pages are files in `docs/help/`, served by `api/routes/help.py`; setup-wizard endpoints live in `api/routes/stubs.py`. CLI entry is `mame_curator.main:main`; subcommands dispatch in `cli/__init__.py` per `cli/spec.md`.

- **DAT parsing streams** via `lxml.iterparse` with per-element `.clear()`, never `etree.parse`: the real DAT is too large to load whole. Input may be `.xml` or a `.zip` holding one XML; both go through `parse_dat()`.
- **Pleasuredome DATs strip `cloneof` / `romof` and `<driver>`.** Parent/clone links come from MAME `-listxml`, joined by short name ([ADR-0002](docs/decisions/0002-cloneof-from-listxml.md)); `apply_driver_status` fills `driver_status` from it.
- **`Machine` is a frozen Pydantic model** (`extra="forbid"`); all parser structures are immutable.
- **Manufacturer carries two facts:** `split_manufacturer("Capcom (Sega license)")` gives publisher Capcom, developer Sega.
- **Errors:** each module has a typed exception hierarchy (`parser.ParserError` → `DATError` / `INIError` / `ListxmlError`). Never raise bare `Exception`.
- **Logging:** library code uses `logging.getLogger(__name__)`. `print()` is forbidden outside `cli/`, which uses `rich.Console`.

## Commits and pushes

- Conventional Commits (`docs/standards/commits.md`). Phase ids go in the body or scope, never as an `<ID>:` subject.
- No `<ID>-complete` tags and no new `docs/journal/` entries. Releases still get a `vX.Y.Z` tag.
- The repo is public: push straight to `main`, no PRs.
- The pre-commit `pytest-fast` hook runs the test-count pins in `tests/docs/test_ds05_test_count_stable.py` against the working tree, untracked files included, so another worker's uncommitted tests block every commit.
- `frontend/dist` is committed. A `frontend/src` change that alters the build needs `npm run build` and the new `dist` in the same push, or the push gate fails.

## Finishing an item

`check-code` and `review-code` (after `docs/audit-allowlist.md`), every finding dispositioned by `close-findings`, then `CHANGELOG.md`, the roadmap flip, and `review-ledger` / `/debt-sweep` where the item warrants it.

**`ROADMAP.md` is never edited directly** (user, 2026-11-26). Every change goes through `roadmap_log`, which re-renders the whole file and drops any hand edit; check each reply for `publish_overwrote_file_text`.

## Things this project deliberately does not do

- No telemetry or analytics, ever (gated by `tests/docs/test_no_telemetry.py`).
- No client-side filesystem access: all disk operations cross the API.
- No software-list routing, LaunchBox / EmulationStation export or cloud sync: post-v1.

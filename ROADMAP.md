<!-- ants-roadmap-format: 1 -->
# MAME Curator — Roadmap

> **Current version:** 0.0.0 (pre-alpha). See [CHANGELOG.md](CHANGELOG.md)
> for what's shipped; this file covers what's **planned**.
>
> **Format:** v1 — see
> [docs/standards/roadmap-format.md](docs/standards/roadmap-format.md).
>
> **Long-form authoritative phase plan:**
> [`docs/superpowers/specs/2026-04-27-roadmap.md`](docs/superpowers/specs/2026-04-27-roadmap.md)
> carries every phase's pre-conditions, tests-to-write-first list,
> ordered implementation steps, acceptance criteria, and out-of-scope
> list. **Read it before starting any phase.** This file is the
> **queue summary** that bridges App-Build's per-phase loop to that
> long-form plan.
>
> Stable per-bullet IDs (`mame-curator-NNNN`) are assigned **lazily**
> via `.roadmap-counter` — only for items that need cross-referenced
> identity (multi-commit features, fix-passes). Phase IDs (`P##`,
> `FP##`, `DS##`, `DOC##`) categorise blocks.

**Legend** (per `docs/standards/roadmap-format.md § 3.3`)

- ✅ Done (shipped)
- 🚧 In progress (being tackled now)
- 📋 Planned (next up)
- 💭 Considered (research phase; scope or feasibility uncertain)

**Themes** (per `docs/standards/roadmap-format.md § 3.4`)

- 🎨 Features · ⚡ Performance · 🔌 Plugins · 🖥 Platform
- 🔒 Security · 🧰 Dev experience · 📚 Documentation
- 📦 Packaging · 🐛 Bug fixes · 🔍 Findings fold-in
- 🧹 Cleanup / debt

---

## P00 — Scaffold and tooling (shipped 2026-04-27)

**Theme:** `uv` + ruff + mypy + pytest + bandit + pre-commit + CI
matrix. Coverage gate at 85% enforced.

### 🧰 Dev experience

- ✅ **P00 — scaffold + tooling baseline.** All five CI gates green
  on empty test suite. See `docs/journal/P00.md`.
  Kind: chore.
  Lanes: build, ci.

---

## P01 — DAT + INI parsers (shipped 2026-04-27)

**Theme:** pure-Python parser turning the user's DAT XML and the
five `.ini` reference files into typed in-memory data; CLI smoke
prints summary stats.

### 🎨 Features

- ✅ **P01 — `parser/` module shipped.** `parse_dat()` (lxml.iterparse
  on `.xml` / `.zip`), `parse_catver()`, `parse_languages()`,
  `parse_bestgames()`, `parse_mature()`, `parse_series()`,
  `parse_listxml_disks()`, `split_manufacturer()`. Coverage 90%+;
  `mame-curator parse` CLI smoke ships. See `docs/journal/P01.md`.
  Kind: implement.
  Lanes: parser, tests.

---

## P02 — Filter rule chain (shipped 2026-04-27)

**Theme:** deterministic curated set from parsed data — drop +
pick + override + session-slice rule chain, with a JSON report
CLI subcommand.

### 🎨 Features

- ✅ **P02 — `filter/` module shipped.** Phase A drops, Phase B
  tiebreakers (region, revision, tier, language, preferred boosts),
  Phase C overrides, Phase D session focus. `cmp_to_key` picker per
  spec line 55; `set_defaults(func=...)` CLI dispatch.
  Coverage 96%+; 158 tests; snapshot test on hand-picked 30-machine
  fixture; hypothesis property tests for determinism + idempotency.
  See `docs/journal/P02.md`.
  Kind: implement.
  Lanes: filter, parser, cli, tests.

### 🔍 Indie-review pass-3 fold-in (2026-04-27)

Tier 1 closed before P03 (the three sub-bullets below); Tier 2 / 3
findings tracked in CHANGELOG `[Unreleased]` per the project's
CHANGELOG-as-sweep-log convention.

- ✅ **CRITICAL — picker uses `functools.cmp_to_key`.** Was using a
  score-tuple + `max()` that made `sf2ce` win over `sf2` on alpha
  fallback. Fix pinned by
  `test_alphabetical_fallback_spec_lower_wins_with_prefix_collision`.
  Kind: review-fix. Source: indie-review-2026-04-27.
- ✅ **CRITICAL — CLI dispatch via `set_defaults(func=)`.**
  `cli/spec.md` updated to record migration as current contract.
  Kind: review-fix. Source: indie-review-2026-04-27.
- ✅ **HIGH — `drop_bios_devices_mechanical` config field wired.**
  Was zombie. Now honoured by Phase A predicates 1-3 with
  early-return when False. `filter/spec.md` updated.
  Kind: review-fix. Source: indie-review-2026-04-27.

---

## P03 — Copy + BIOS resolution + RetroArch playlist (next)

**Theme:** given a winner list from P02, copy each winner's `.zip`
plus all transitively-required BIOS `.zip`s to the destination,
write a RetroArch `mame.lpl` playlist, and emit a copy report.

**Long-form contract:**
[`docs/superpowers/specs/2026-04-27-roadmap.md` § Phase 3](docs/superpowers/specs/2026-04-27-roadmap.md).

### 🎨 Features

- 📋 **P03 — `copy/` module.** Implements: BIOS chain resolution
  (transitive `romof` + `<biosset>` walk, dedup), atomic copy
  (`.tmp` + `os.replace`, `shutil.copy2` mtime preservation), `.lpl`
  RetroArch v6+ JSON writer, playlist conflict resolution
  (append vs overwrite, per-game version replace, recycle-bin),
  pause/resume/cancel semantics, activity-log append, copy report.
  Two file schemas to pin in `copy/spec.md`: `data/activity.jsonl`
  event format, `CopyReport` Pydantic model.
  CLI: `mame-curator copy --dry-run` and `--apply`.
  Coverage target: ≥85%.
  Kind: implement.
  Lanes: copy, tests.
  Dependencies: P02 ✅.

---

## P04 — HTTP API (planned)

**Theme:** FastAPI server exposing P01-P03 over HTTP + SSE for
copy progress.

**Long-form contract:**
[`docs/superpowers/specs/2026-04-27-roadmap.md` § Phase 4](docs/superpowers/specs/2026-04-27-roadmap.md).

### 🎨 Features

- 📋 **P04 — `api/` module.** All routes from design spec § 6.5;
  Pydantic schemas; SSE for copy progress; sandboxed `/api/fs/*`
  browser routes. Coverage target: ≥80%.
  Kind: implement.
  Lanes: api, tests.
  Dependencies: P03.

---

## P05 — Media subsystem (planned)

**Theme:** libretro-thumbnails URL builder + lazy fetch + sha256-
keyed disk cache through the API proxy.

**Long-form contract:**
[`docs/superpowers/specs/2026-04-27-roadmap.md` § Phase 5](docs/superpowers/specs/2026-04-27-roadmap.md).

### 🎨 Features

- 📋 **P05 — `media/` module.** URL escape rules
  (`&*/:\<>?\|"` → `_`); `urls_for(machine)`; async
  `fetch_with_cache(url, cache_dir)`; cache key = `sha256(url)`.
  Coverage target: ≥90%.
  Kind: implement.
  Lanes: media, api, tests.
  Dependencies: P04.

---

## P06 — Frontend MVP (planned)

**Theme:** Vite + React 19 + Tailwind v4 + shadcn/ui browser UI
with virtualized grid, alternatives drawer, copy modal with SSE,
multiple themes/layouts, Cmd-K palette.

**Long-form contract:**
[`docs/superpowers/specs/2026-04-27-roadmap.md` § Phase 6](docs/superpowers/specs/2026-04-27-roadmap.md).

### 🎨 Features

- 📋 **P06 — frontend MVP.** All component tests + one Playwright
  E2E. `Switch` for binary preferences (not `Checkbox`).
  `AlertDialog` on every destructive action. Coverage target: ≥70%.
  Kind: implement.
  Lanes: frontend, tests.
  Dependencies: P05.

---

## P07 — Self-update + in-app help (planned)

**Theme:** in-app updates (git-pull / release-download with
snapshot+rollback), INI refresh with diff preview, bundled
markdown help searchable via Cmd-K. Introduces the shared
`downloads.py` primitive that P08 reuses.

**Long-form contract:**
[`docs/superpowers/specs/2026-04-27-roadmap.md` § Phase 7](docs/superpowers/specs/2026-04-27-roadmap.md).

### 🎨 Features

- 📋 **P07 — `updates/` + `help/` modules.** `downloads.py`
  primitive (sha256-pinned, exponential retry, atomic writes,
  manual-fallback hook); app self-update + rollback;
  INI refresh with diff preview; bundled help server.
  Coverage targets: updates ≥85%, help ≥90%.
  Kind: implement.
  Lanes: updates, help, downloads, frontend, tests.
  Dependencies: P06.

---

## P08 — Setup wizard (planned)

**Theme:** `git clone && ./run.sh` → curated grid via in-browser
wizard, no manual config. Reuses P07's `downloads.py`. Two-flow
reference-data acquisition (INIs checksum-pinned; `-listxml`
tiered).

**Long-form contract:**
[`docs/superpowers/specs/2026-04-27-roadmap.md` § Phase 8](docs/superpowers/specs/2026-04-27-roadmap.md).
**Two-flow `-listxml` acquisition:**
[ADR-0003](docs/decisions/0003-listxml-tiered-acquisition.md).

### 🎨 Features

- 📋 **P08 — `setup/` module.** `run.sh` / `run.bat` Stage 1;
  Stage 2 in-browser wizard with `FileBrowser`. Resumable across
  reboots. Coverage target: ≥85%.
  Kind: implement.
  Lanes: setup, frontend, tests.
  Dependencies: P07.

---

## P09 — Polish + v1.0.0 (planned)

**Theme:** finishing work — README hero shot, screenshots,
CONTRIBUTING, final UAT, tag `v1.0.0`, GitHub publish.

### 📚 Documentation

- 📋 **P09 — v1.0.0 release.** README quickstart that a
  non-technical user can follow; 4-6 screenshots from a working
  install; CHANGELOG bootstrapped with v1.0.0 entry summarising
  every phase; release workflow validated; tag + push.
  Kind: release.
  Lanes: docs, packaging, ci.
  Dependencies: P08.

---

## Future enhancements (post-v1.0.0)

Captured in
[`docs/superpowers/specs/2026-04-27-roadmap.md` § "Future
enhancements"](docs/superpowers/specs/2026-04-27-roadmap.md):
software-list routing, EmulationStation `gamelist.xml` exporter,
LaunchBox interop, DAT-version-upgrade workflow, cloud sync of
`overrides.yaml` / `sessions.yaml`, multi-user mode, i18n,
themes from more arcade classics. **Deliberately deferred** to
keep v1.0.0 shippable; not part of the v1 plan.

---

## How to add an item

1. Allocate the next ID (only if cross-referenced identity is
   needed):
   ```bash
   echo $(($(cat .roadmap-counter) + 1)) > .roadmap-counter
   printf "mame-curator-%04d\n" $(cat .roadmap-counter)
   ```
2. Insert at the position where it should be tackled (not blindly
   at the end).
3. Set the status emoji (📋 Planned, 💭 Considered).
4. Add `Kind:`, `Lanes:`, optionally `Source:` and `Dependencies:`.

See `docs/standards/roadmap-format.md § 3.5` for the full bullet
contract.

## How findings get folded

After every `/audit` + `/indie-review` (and `/debt-sweep`):

```
Phase closes
  → Run /audit + /indie-review (parallel)
  → Triage findings
  → If clean: phase fully closed.
  → If actionable: batch into one new fix-pass FP## (next-up),
    add [Unreleased] entry, run that fix-pass through the
    9-step loop; its own closing audits may produce another.
```

See `docs/standards/roadmap-format.md § 3.6` and the
[app-workflow skill](~/.claude/skills/app-workflow/SKILL.md)
for the full pattern.

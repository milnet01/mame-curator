# MAME Curator — Glossary

Domain-specific and workflow-specific terms used in code,
docs, and commits.

## App-Build / workflow vocabulary

| Term | Definition |
|------|------------|
| **ADR** | Architecture Decision Record — a one-page note explaining a non-obvious design choice, the alternatives considered, and the reasoning. Lives in `docs/decisions/`. |
| **App-Build alignment commit** | The 2026-04-30 commit that retrofitted this project to App-Build conventions. Adds `.claude/workflow.md`, the `docs/standards/` slot files, the `docs/journal/` entries for already-shipped phases, and the retroactive `<ID>-complete` annotated tags. Why it matters: tag dates and commit-author dates diverge for P00–P02 (work shipped 2026-04-27, tags applied 2026-04-30). |
| **Convergence checkpoint** | The fix-pass count (default 5) at which Claude pauses to ask whether to keep iterating, accept remaining findings into known-issues, or rethink design. Configurable in `.claude/workflow.md` § 1. |
| **Debt-sweep (`DS##`)** | A scan for cumulative drift introduced over multiple phases, run by `/debt-sweep`. Default cadence: as part of `/release` before the version bump. |
| **Doc-pass (`DOC##`)** | A roadmap item batching documentation-audit findings (Phase D loop) into a single piece of work that runs through the 9-step loop. Parallel to `FP##` but scoped to documentation only. Each round of cold-eyes review may extend an open `DOC##` rather than spawning a new one — the loop closes when one round returns zero actionable findings. |
| **Fix-pass (`FP##`)** | A roadmap item generated automatically after `/audit` + `/indie-review` to track findings as a single batched piece of work that runs through the full 9-step loop. |
| **Kind** | A roadmap-bullet metadata field declaring the work type (`implement`, `fix`, `refactor`, `audit-fix`, `review-fix`, `doc`, `doc-fix`, `test`, `chore`, `release`). |
| **Lane** | A named subsystem owner (e.g. `parser`, `filter`, `copy`, `api`, `frontend`, `tests`, `docs`). |
| **Phase D (App-Build)** | The documentation-audit phase of App-Build (Phases A discovery → B design → C documentation → D documentation audit). Distinct from the filter pipeline's "Phase D" (session-slice). When ambiguous, qualify as "Phase D (App-Build)" or "Phase D (filter)". |
| **Phase D (filter)** | The session-slice phase of `filter/` (Phase A drops → Phase B picks → Phase C overrides → Phase D session focus). See `filter/spec.md`. Distinct from App-Build's "Phase D" (documentation audit). |
| **Source** | A roadmap-bullet metadata field naming where the item came from (`audit`, `indie-review`, `debt-sweep`, `user`, `planned`). |
| **TDD** | Test-driven development. Write the failing test first, watch it fail for the right reason, then write the smallest code that makes it pass. |
| **Triage** | The process of sorting findings into three buckets: actionable (folds into a fix-pass), blocked-by-dependency (logs to `known-issues.md`), false-positive (logs to `audit-allowlist.md`). |

## MAME / arcade-curation domain vocabulary

| Term | Definition |
|------|------------|
| **BIOS set** | A non-runnable `.zip` whose ROM content is required by other machines that reference it via `<biosset>` or `romof`. Example: `neogeo.zip` is the BIOS for every Neo-Geo title. Phase 3's copy step resolves these dependencies transitively. |
| **CHD** | Compressed Hunks of Data — MAME's format for bulky disk-based assets (laserdiscs, hard drives, CDs). Phase 1 detects which machines need a CHD by inspecting `<disk>` entries in the `-listxml`. |
| **catver.ini** | Community-maintained INI mapping each short-name to a category string (e.g. `Shooter / Vertical`). Sourced from progettoSnaps. |
| **cloneof** | The MAME relationship from a clone short-name to its parent short-name. Pleasuredome DATs strip this attribute, so Phase 2 reconstructs it from the official `-listxml` instead. |
| **DAT** | An XML file describing every machine in a MAME ROM set (short name, description, year, manufacturer, parent/clone, ROM hashes). Pleasuredome ships ~48 MB / 43k entries per release; Phase 1 streams it via `lxml.iterparse`. |
| **Description** | The human-readable game title, e.g. `Pac-Man (Midway)`. Used as the playlist label and as input to region/revision heuristics. |
| **Listxml** | The XML output of `mame -listxml`. Carries the canonical parent/clone graph and disk-requirement signals; Phase 1 parses the disk subset, Phase 2 parses the cloneof subset. |
| **Manufacturer** | DAT field carrying two facts as one string (`"Capcom (Sega license)"` → publisher Capcom, developer Sega). Phase 1 splits these via `split_manufacturer()`. |
| **Non-merged ROM set** | One of the three MAME ship styles. **Merged**: clones live inside their parent's `.zip`. **Split**: parent and clone each in their own `.zip`, but clones depend on the parent's ROMs being present. **Non-merged**: every machine's `.zip` is fully self-contained — clone `.zip`s carry their own copies of any ROMs they share with the parent. This project requires non-merged because Phase 3's copy step ships individual `.zip`s to RetroArch's MAME core, which expects each `.zip` to be standalone. |
| **Override** | A user-supplied `overrides.yaml` entry that pins a specific clone as the winner for a parent/clone group, beating the rule chain's tiebreakers. Phase C of the filter applies these. |
| **Parent / clone** | MAME's grouping for hardware variants of the same game. The parent is the canonical entry; clones differ by region, revision, language, or hardware tweak. The filter picks one winner per group. |
| **Pleasuredome DAT** | The community-maintained DAT used by this project. Strips `cloneof` and `romof` attributes (verified: zero matches on the 0.284 DAT) — Phase 2 uses the official `-listxml` for parent/clone relationships. |
| **Preliminary driver** | A MAME machine flagged `runnable="no"` or `status="preliminary"`. Phase 2 drops these by default. |
| **`mame.lpl`** | RetroArch's JSON-format playlist file. Phase 3 writes this so RetroArch shows pretty names and launches the curated set. |
| **Session** | A user-defined slice of the curated library (e.g. "vertical shooters from Capcom 1980-1990"). Active sessions filter what's visible in the frontend; null session shows the full library. |
| **Short name** | The MAME ROM short-name (e.g. `pacman`, `sf2ce`). The primary key everywhere in the data model. |
| **Tier (best/great/good/...)** | Bestgames.ini ranks machines on a 7-level scale (Best > Great > Good > Average > Bad > Awful > unrated). Phase 2 uses tier as a tiebreaker. |
| **Winner** | The single machine the filter picks per parent/clone group, by drop rules + tiebreaker chain (+ overrides, + session slice). The winner-set is what gets copied. |

## External resources

- **libretro-thumbnails** — community thumbnail repo. Phase 5's media subsystem builds URLs against it using its escape rules (`&*/:\<>?\|"` → `_`).
- **progettoSnaps** — canonical source for the five INI files (catver, languages, bestgames, mature, series).
- **Pleasuredome** — community ROM-set archive. Source of the DAT and zips this project consumes.

## Conventions

- **Bold the term** in its first use in this file.
- **One-line definition.** If a term needs more, link to an ADR or design-doc subsection.
- **Append-only.** When a term is renamed, add the new term and mark the old one as `(retired in vX.Y.Z, see "<new name>")`.
- **Sort alphabetically** within each section.

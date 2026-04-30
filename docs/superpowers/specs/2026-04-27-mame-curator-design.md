# MAME Curator — Design Spec

**Date:** 2026-04-27
**Status:** Draft (pending user review)
**License (planned):** MIT
**Companion docs:** [Coding standards](../../standards/coding-standards.md) · [Implementation roadmap](2026-04-27-roadmap.md)

---

## 1. Problem

A full Pleasuredome MAME 0.284 ROM set is enormous — 43,579 `.zip` files, ~150 GB. The vast majority are not playable arcade games: ATMs, calculators, chess boards, UNIX workstations, BIOS chips, sub-devices, slot machines, mahjong, gambling, prototypes, regional clones of clones, and broken/preliminary emulation. For a RetroArch user who just wants the **best playable arcade games**, manually combing the set is impractical.

There are existing community ROM-management tools (ClrMamePro, RomVault, etc.) but they focus on verification/dedup, not on *curation* with rich visual feedback. None of them are friendly to share with a non-technical friend.

## 2. Goals

- **Curate the "best playable arcade games"** from a Pleasuredome non-merged ROM set, copying the chosen subset to a separate destination so the source remains untouched.
- **Auto-pick winners** for parent/clone groups using community-consensus reference data; let the user **override picks** through a modern web UI when they disagree.
- **Generate a RetroArch playlist** (`mame.lpl`) so games show pretty descriptive names in RetroArch without renaming files (which would break MAME's short-name lookup).
- **Auto-include required BIOS** files alongside chosen games so they actually launch.
- **Be shareable on GitHub under MIT** with the easiest possible setup for non-technical end users.

## 3. Non-goals (for v1)

- Renaming ROM `.zip` files. (RetroArch uses MAME short names — renaming breaks launches.)
- Verifying ROM CRCs / repairing damaged sets. (RomVault/ClrMamePro territory; assume the source set is verified.)
- Downloading ROMs or CHDs from anywhere. (Legal landmine — users supply their own.)
- Multi-user / network deployment. This is a single-user local tool.
- Telemetry or analytics of any kind. The app makes no outgoing requests beyond the documented ones (libretro thumbnails, progettoSnaps INI files, GitHub releases for self-update).
- Multi-language UI. (Strings are kept in one place to make future i18n possible, but v1 ships English-only.)

Tracked for **post-v1** (see also `docs/superpowers/specs/2026-04-27-roadmap.md` "Future enhancements"):

- EmulationStation `gamelist.xml` and LaunchBox importers / exporters.
- MAME software-list routing to per-system folders (see §13).
- Cloud sync of `overrides.yaml` / `sessions.yaml`.
- Multi-user profiles.
- Localization / i18n.

## 4. Key design decisions (summary)

| Decision | Choice | Rationale |
|---|---|---|
| Filenames in destination | Keep MAME short names (`1on1gov.zip`) | RetroArch + MAME core load by short name; renaming breaks launches |
| Pretty display names | RetroArch `.lpl` playlist | Standard RetroArch mechanism; zero filename risk |
| Filter source-of-truth data | Bake in community `.ini` files + manual `overrides.yaml` | Deterministic, reproducible, no live web calls per game |
| GUI | Local web app (FastAPI backend + React frontend in browser) | Modern UI, single codebase, no per-OS native build, easy GitHub sharing |
| CHD-required games | Detected via official MAME `-listxml`, marked unplayable, skipped in copy | Pleasuredome ROM-set DAT does not list CHDs; they aren't packed in any zip (verified empirically) |
| Frontend distribution | Pre-built `dist/` committed to repo | End users don't need Node.js; only contributors do |
| Filter rules | All drop-categories user-configurable in `config.yaml` | One person's "drop mahjong" is another's "keep mahjong"; defaults match user's request |

## 5. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Browser (localhost:8080)                                    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  React + Tailwind + shadcn/ui (pre-built dist/)      │    │
│  │  • Game grid (poster cards w/ flyer art)             │    │
│  │  • Filters / search / sort                           │    │
│  │  • "Show alternatives" drawer                        │    │
│  │  • Bulk-action toolbar                               │    │
│  │  • Setup wizard (first-run + reconfig)               │    │
│  └──────────────────────────────────────────────────────┘    │
│                          │ JSON / SSE                        │
└──────────────────────────┼───────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  Python backend (FastAPI + uvicorn)                          │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  setup/     dependency check + interactive wizard    │    │
│  │  parser/    DAT XML + .ini files → in-memory model   │    │
│  │  filter/    rule chain → Decision per machine        │    │
│  │  media/     URL builder + lazy-fetch + disk cache    │    │
│  │  copy/      copy game zips + BIOS + write .lpl       │    │
│  │  api/       FastAPI routes + SSE for progress        │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
        Disk: source ROMs, dest ROMs, media cache, config
```

### Surface boundaries

- **Frontend ⇄ Backend:** JSON API + Server-Sent Events (for live copy progress). The browser never reads the user's filesystem directly; everything goes through the backend.
- **Backend ⇄ Filesystem:** the backend is the only thing that touches `/mnt/Games/MAME/` (read) and `/mnt/Games/ROMS/mame/` (write).
- **Backend ⇄ Internet:** only during setup (downloading `.ini` files, MAME `-listxml`) and lazy media fetches. After setup, the app works fully offline if desired.

## 6. Components

### 6.1 `parser/`

Streams the non-merged DAT XML once at startup, builds an in-memory dict `{shortname → Machine}` where `Machine` carries: description, year, manufacturer, `cloneof`, `romof`, `isbios`, `isdevice`, `ismechanical`, `runnable`, `<rom>` list, `<biosset>` list, driver status, sample-of, etc.

Also parses these reference files (downloaded once during setup, cached in `data/`):

- **`catver.ini`** (progettoSnaps) — category per machine (`Casino / Slot Machine`, `Mahjong / Reels`, `Quiz / Japanese`, `Mature *`, etc.)
- **`languages.ini`** (progettoSnaps) — languages required to play
- **`bestgames.ini`** (progettoSnaps) — community rating tier (Best, Great, Good, Average, Bad, Awful)
- **`series.ini`** (progettoSnaps) — sequel/series grouping
- **`mature.ini`** (progettoSnaps) — adult-content flag
- **Official MAME `-listxml` for 0.284** — for CHD detection (`<disk>` elements) and parent/clone relationships. Pleasuredome's ROM-set DAT doesn't include either piece of information; the official XML does.

All five `.ini` files load into hash-map lookups keyed by short name. Missing entries are tolerated (the rule chain treats absence as "no signal"). Update-checking against newer published reference data is the responsibility of `updates/` (§6.7), not the parser.

#### Where `-listxml` comes from

There is no canonical web mirror for MAME's `-listxml` output — it is generated by running the user's local `mame` binary with the `-listxml` flag, and its size (~250 MB uncompressed) makes redistribution impractical. The wizard (§6.6 stage 2 step 4) handles acquisition with a tiered approach:

1. **Run locally (preferred).** If a `mame` (or `mame.exe`) binary is on `PATH` or at a user-supplied path, the wizard offers to run `mame -listxml > data/mame-listxml.xml`. This is the only source that is *guaranteed* to match the user's MAME version.
2. **User-supplied path.** The wizard accepts a path to an existing listxml file the user has obtained themselves. No checksum pinning (the version varies per user); a structural validity check (root element, ≥1 `<machine>`) is sufficient.
3. **Community mirror, opt-in.** If neither (1) nor (2) is available, the wizard offers a manual link to a community-mirrored copy for the closest MAME version, with a clear warning that the mirror is unverified and may not match the user's DAT.

Phase 1's parser only consumes the file once it exists on disk; how it got there is the wizard's problem.

### 6.2 `filter/` — the rule chain

The filter has four phases: **drop** (remove unwanted machines) → **pick** (choose one winner per parent/clone group) → **apply overrides** (manual user picks) → **apply session focus** (continuation / "today's slice" mode).

#### Phase A — drop (defaults; all configurable in `config.yaml`)

Each rule is independently togglable; rules listed below are the defaults. In order:

1. Drop `isbios=yes`, `isdevice=yes`, `runnable=no`
2. Drop `ismechanical=yes`
3. Drop machines whose `catver.ini` category matches any pattern in `drop_categories`:
   - `Casino*`, `Slot Machine*`
   - `Mahjong*`, `Quiz / Japanese*`
   - `Mature*` (adult content)
   - `Console*`, `Computer*`, `Calculator*`, `Handheld*` (non-arcade — see §13)
   - `Utilities*`, `Tabletop*`, `Misc.*`
4. Drop machines whose `languages.ini` language is **only** `Japanese` (keeps games with no language requirement)
5. Drop machines whose `<driver status>` is `preliminary` (broken emulation)
6. Drop machines requiring CHDs (detected from official `-listxml`) — separately listed in the UI's "missing CHD" section
7. **Drop by genre / publisher / developer** (configurable allowlists or denylists). Examples:
   - `drop_genres: ["Casino", "Mahjong"]`
   - `drop_publishers: ["Aristocrat"]` (drops all of a vendor's slot machines)
   - `drop_developers: ["..."]` — same idea
   - `drop_year_before: 1985` / `drop_year_after: 2010` — optional year-range gates

   Genre comes from `catver.ini` (the part after the last `/`). Publisher and developer come from the DAT's `<manufacturer>` field, which sometimes encodes both as `"Capcom (Sega license)"` — the parser splits these. Combinations are AND'd: `drop_genres: [Maze]` + `drop_publishers: [Namco]` drops only Namco maze games.

#### Phase B — pick winner per parent/clone group

Within each group, pick the winner using this tiebreaker chain (top wins; later rules only break ties from earlier rules):

1. Highest `bestgames.ini` tier (Best > Great > Good > Average > Bad > Awful > unrated)
2. **Preferred genres / publishers / developers boost.** If the user has set `picker.preferred_genres: ["Shoot 'em Up"]`, machines matching get a boost ahead of generic tiebreakers. Same for `preferred_publishers` and `preferred_developers`. (No effect if the user hasn't set them.)
3. Parent over clone
4. `<driver status>` `good` over `imperfect`
5. **Region preference** (parsed from description tags): `World > USA > Europe > Japan > Asia > Brazil > others > unspecified`
6. Latest revision/version detected in description (rev letters, dates, "v2" tags)
7. Final fallback: alphabetical short name (deterministic)

#### Phase C — apply `overrides.yaml`

A simple YAML file the user edits (or the GUI edits on their behalf) that maps a parent short name to a chosen winner short name. Overrides bypass the entire pick chain. Example:

```yaml
overrides:
  sf2:        sf2ce       # user prefers Champion Edition over vanilla
  mslug:      mslug       # explicit confirmation; pin against future rule changes
  pacman:     pacmanf     # speedup hack? user's choice
```

#### Phase D — session focus (continuation mode)

The user does not have to curate the whole library in one sitting. They can save **session focuses** that limit the visible/operable set to a slice — e.g. "today: shoot-em-ups" or "today: Capcom fighters from 1991-1995." A session focus is just a reusable named filter:

```yaml
sessions:
  shoot_em_ups:
    include_genres: ["Shooter*", "Shoot 'em Up*"]
  capcom_fighters_early_90s:
    include_publishers: ["Capcom*"]
    include_genres: ["Fighter*"]
    include_year_range: [1991, 1995]
  todo_after_shooters:
    include_genres: ["Fighter*", "Beat'em up*", "Platformer*"]
```

When a session is active, the UI shows only matching games and the copy operation only acts on those. Session state (which sessions exist, which is active) lives in `sessions.yaml`, separate from `config.yaml` and `overrides.yaml` so users can share session presets without sharing personal config. **Sessions never overwrite — they slice.** A user can run today's session, copy those games, then tomorrow load a different session and copy more without losing yesterday's work (see §6.4 playlist append/conflict logic).

### 6.3 `media/`

For each machine, construct URLs to:
- **Flyer (boxart equivalent for arcade):** `https://raw.githubusercontent.com/libretro-thumbnails/MAME/master/Named_Boxarts/<urlencode(description)>.png`
- **Title screen:** `…/Named_Titles/<description>.png`
- **Snap (gameplay):** `…/Named_Snaps/<description>.png`
- **Video preview (optional, opt-in):** progettoSnaps videosnap pattern, fetched only when user opens the detail drawer

The browser fetches images directly via `<img src>` — no Python proxy needed for hits. A small `/media/<name>` proxy endpoint exists for **fallback only**: if libretro doesn't have a thumbnail, the proxy tries alternate sources (progettoSnaps mirrors) and caches the result to `data/media-cache/`.

**Cache is permanent by default.** Once an image is cached, it is never re-downloaded. The cache filename is `sha256(url).<ext>` — i.e. the cache key is the URL, not the response bytes. This means a hit can be answered without contacting the network, and any URL change (e.g. a description change after a DAT version bump) naturally produces a new cache entry without invalidating the old one. Old entries remain valid for any user still on the previous DAT version. The user can clear the cache from the Settings page (one click) or by deleting `data/media-cache/`. A cache-size indicator is shown in Settings so the user always knows the disk footprint.

### 6.4 `copy/`

Given an approved set of winner short names:

1. **Resolve dependencies.** For each winner, walk `romof` and `<biosset>` chains. The transitive closure is the BIOS set required.
2. **Preflight.** Confirm each `.zip` (game + BIOS) exists in the source dir. Confirm destination is writable and has enough free space.
3. **Detect existing playlist.** If `mame.lpl` already exists at the destination, prompt the user with three options (see "Playlist conflict resolution" below).
4. **Copy.** Stream each `.zip` from source to destination. Use `shutil.copy2` to preserve mtime. BIOS files are deduped (copied once even if 100 games need `neogeo.zip`).
5. **Write `mame.lpl`.** RetroArch playlist format — JSON; one entry per game with full path, description as label, MAME core path placeholder.
6. **Write copy report.** `report.json` with: succeeded, skipped (with reason), failed (with reason), overwritten (with old → new), total bytes copied, BIOS files included, CHD-missing games skipped.
7. **Append to activity log.** A persistent `data/activity.jsonl` (append-only) records every copy session: timestamp, action counts, user-confirmed deletions, etc. Visible in the Activity page (see §8).

Copy progress is streamed via SSE so the GUI shows a live progress bar with **pause / resume / cancel** controls. Pause holds the worker between files (does not interrupt mid-file). Cancel asks the user whether to keep already-copied files (default: keep) or remove them.

#### Playlist conflict resolution

When `mame.lpl` already exists at the destination (a previous session was run), the user is asked how to proceed:

- **Append** — add new games to the existing playlist; resolve per-game conflicts as below.
- **Overwrite** — discard the entire existing playlist (and optionally the existing `.zip` files in the destination — confirmation required).
- **Cancel** — abort this run.

For **append**, each new winner is checked against the existing playlist:

| Existing in playlist? | New version differs? | Default action |
|---|---|---|
| No | n/a | Add new |
| Yes | No (same short name) | Skip (already there); count in report |
| Yes | Yes (different short name, e.g. `sf2` vs `sf2ce`) | **Ask the user, per game**, with both versions' media side-by-side. Options: (a) keep existing, (b) replace with new |

When the user chooses (b) **replace**:

1. The new game is copied (atomic).
2. The new playlist entry replaces the old one.
3. The user is asked a second confirmation: "Also delete the old `.zip` (and any orphaned BIOS) from the destination drive? Default: keep — they take little space and removing them is irreversible." Confirmation must be explicit.
4. If confirmed, the old file is moved to a `data/recycle/` directory (not immediately deleted — survives accidents) where it remains for 30 days before final cleanup. The activity log records the deletion.

**No file is deleted from the user's source ROM library — only from the destination.**

#### Idempotency

Re-running the copy with no changes is a no-op (each game is detected as already-copied with matching CRC, skipped, and reported as such). This makes "I forgot whether I already ran this" safe.

### 6.5 `api/` — FastAPI routes

```
# Games / metadata
GET    /api/games                       paginated grid (optionally filtered)
GET    /api/games/{name}                detail view
GET    /api/games/{name}/alternatives   parent + all clones with media URLs
GET    /api/games/{name}/explanation    "why was this winner picked?" — chain of reasoning
GET    /api/games/{name}/notes          user's personal notes for the game
PUT    /api/games/{name}/notes          set notes (single text field)
GET    /api/stats                       library stats (counts by genre/year/manufacturer/etc.)

# Overrides + sessions
POST   /api/overrides                   {parent, winner} → updates overrides.yaml
DELETE /api/overrides/{parent}          remove an override
GET    /api/sessions                    list saved session focuses
POST   /api/sessions                    create / update a named session
DELETE /api/sessions/{name}             remove a session
POST   /api/sessions/{name}/activate    set the active session focus

# Config
GET    /api/config                      current config.yaml
PATCH  /api/config                      update filter rules / paths
GET    /api/config/snapshots            list backup snapshots of config/overrides/sessions
POST   /api/config/snapshots/{id}/restore  roll back to a snapshot
POST   /api/config/export               export all settings as a single JSON
POST   /api/config/import               import settings from JSON

# Copy
POST   /api/copy/dry-run                preview: counts, sizes, BIOS deps, conflicts
POST   /api/copy/start                  {selected_names, conflict_strategy} → start copy job
POST   /api/copy/pause                  pause between files
POST   /api/copy/resume                 resume after pause
POST   /api/copy/abort                  cancel; keeps or removes partial per request
GET    /api/copy/status                 SSE stream of progress events
GET    /api/copy/history                paginated list of past copy sessions
GET    /api/copy/history/{id}/report    full report for a past session

# Activity log
GET    /api/activity                    paginated activity log (filterable by action)

# Setup wizard
GET    /api/setup/check                 dependency + path validation
POST   /api/setup/install               trigger downloads / install
GET    /api/setup/state                 current wizard step (resumable)
POST   /api/setup/state                 advance / set wizard step

# Filesystem browser (used by wizard "Browse..." buttons)
GET    /api/fs/list?path=...            sandboxed directory listing
GET    /api/fs/home                     user's home dir resolved
GET    /api/fs/roots                    available drive roots (Windows: C:/D:/...; *nix: /)

# Updates
GET    /api/updates/check               new app version? new INI files?
POST   /api/updates/apply               apply available updates

# Media
GET    /media/{name}/{kind}             proxy/fallback for media images

# Help / docs (served from bundled markdown)
GET    /api/help/index                  table of contents
GET    /api/help/{topic}                rendered markdown for a topic
```

### 6.6 `setup/` — the install/setup wizard

This is the component that ensures **"the wizard shouldn't fail arbitrarily"**.

#### Layered setup model

The wizard runs in **two stages**:

**Stage 1 — bootstrap (CLI, before the web app exists).** The user runs `./run.sh` (Linux/Mac) or `run.bat` (Windows). The script:

1. Checks for Python 3.12+ on PATH. If absent: prints platform-specific install instructions with copy-pasteable commands (`apt`, `dnf`, `brew`, winget, python.org link). Exits cleanly.
2. Checks for `uv`. If absent, installs it via the official one-liner (with the user's confirmation), or shows manual instructions if confirmation is declined.
3. Runs `uv sync` — uv automatically creates a project-local `.venv/`, syncs deps from the lockfile, and the user never has to think about activation. From the user's perspective there is no venv; from the tooling's perspective there is one. This is the modern uv-managed model: project-isolated dependencies without the user-visible activation step.
4. **Port-availability check.** Probes the configured port (default `8080`); if busy, scans `8080..8090` for a free port; if all are busy, prompts the user to specify one or kill the offending process.
5. Verifies the pre-built frontend `dist/` is present (it is — committed to repo).
6. Launches uvicorn on the chosen port → opens the user's default browser to `http://localhost:<port>`.

Each step produces either success or a specific actionable error message. No silent failures.

**Note on virtual environments.** The venv is automatically created and managed by `uv` in `<project>/.venv/`. The user does not run `source .venv/bin/activate` — `uv run` and the launcher script handle it transparently. Pros: isolation from system Python, no root needed, no conflicts with other apps, reproducible from `uv.lock`, uninstall = `rm -rf` the project folder. Cons (vs no venv): a few hundred MB on disk. The "no venv" feel is preserved by `uv` doing the work invisibly.

**Stage 2 — first-run wizard (in the browser).** When the backend boots and detects no `config.yaml`, the frontend renders a multi-step wizard:

1. **Welcome** — what this tool does, license, no-telemetry statement, link to help.
2. **Source paths** — pick the folder containing `*.zip` ROMs and the DAT XML. **Includes a "Browse..." button that opens the in-app file browser** (a custom UI driven by `GET /api/fs/list` — a browser-native dialog can't return an absolute path to JS, so we implement our own). User can also paste a path. Validates the dir exists and contains `.zip`s, validates DAT parses.
3. **Destination path** — where to copy curated ROMs. Same Browse button. Validates writable, warns if non-empty.
4. **Reference data download** — fetches `catver.ini`, `languages.ini`, `bestgames.ini`, `mature.ini`, `series.ini`, MAME `-listxml`. Each download:
   - Has a primary URL + ≥2 mirrors
   - Validates checksum (SHA-256 pinned in the wizard for the targeted MAME version)
   - Retries with exponential backoff (1s, 2s, 4s, 8s — max 4 attempts)
   - On final failure shows the URL and lets the user manually drop the file into `data/` and click "I downloaded it manually"
5. **Filter preview** — runs the rule chain against the user's DAT, shows summary: "Of 43,579 machines, 38,200 dropped (BIOS/devices/non-arcade/...), 5,379 candidates, 2,847 winners after deduplication." User confirms or jumps to filter customization.
6. **Filter customization (optional)** — **on/off switches** (not checkboxes — see §8) for each drop category, language gate, driver-status gate, and CHD-required gate. Re-runs filter live as toggles change.
7. **Done** — drops user into the main grid view.

All wizard state is **resumable across sessions and reboots**. State persists to `data/.wizard-state.json` (atomic write). If the user closes the browser, restarts the machine, then runs `./run.sh` again, the wizard resumes at the exact step they left off.

#### Robustness rules

- Every step must produce either success or a **specific, actionable error message** with at least one suggested fix.
- Every download is idempotent (skips if already present and checksum-valid).
- Network failures don't poison cache: partially-downloaded files are deleted before retry.
- File-system failures (read-only, no space, permission) show the exact path and required permission.
- An "Advanced / manual install" section is always visible: lists every dependency, every URL, every command, so a sufficiently technical user can do it by hand and still arrive at a working install.

### 6.7 `updates/` — self-update and INI refresh

Two independent update channels, both manual-trigger and both checked at startup with a non-blocking notification if newer versions are available.

#### App self-update

- On startup the backend queries the GitHub Releases API for the latest tag of the `mame-curator` repo. If the latest tag is newer than the running version, surfaces a "Update available: vX.Y.Z" toast in the UI with "What's new" and "Update now" buttons.
- "Update now" runs `git pull` (when the install is a clone) or downloads the release tarball (when the install is a download). The update process: pre-flight `git status` is clean, fetch + verify, run `uv sync` for new deps, restart the backend. If anything fails, the previous version remains running.
- Settings page has an "Auto-check on startup" switch (default on) and a "Check now" button.
- The user can opt into a release channel: `stable` (tagged releases) or `dev` (latest `main` branch) — defaults to `stable`.

#### INI refresh

- On startup, fetches the version manifest from progettoSnaps' GitHub mirror (`AntoPISA/MAME_SupportFiles`) and compares against locally cached versions.
- If a newer INI is available, surfaces a separate notification: "Newer reference data: catver.ini 0.290 (you have 0.284). Refresh? Refreshes affect filter results — your overrides and sessions are preserved."
- Refresh re-downloads the ini files (with checksum + retry, same logic as the wizard), then re-runs the filter and shows a diff of decisions: "X games newly included, Y newly dropped, Z winners changed."

#### Safety rails

- All app updates create a snapshot of `config.yaml`, `overrides.yaml`, `sessions.yaml`, `data/notes.json` first.
- INI refreshes never touch user files; they only update `data/*.ini` plus the in-memory model.
- "Roll back to previous version" is one click in Settings (uses `git reset --hard <prev-tag>` for clones, swap-in for downloads).

### 6.8 `help/` — in-app help

A `Help` page (always reachable from the top nav) renders bundled markdown from `docs/help/*.md`. Topics:

- **Quickstart** — three-screenshot walk-through.
- **Filters explained** — what each Phase A drop and Phase B picker rule does.
- **Sessions** — how to set up and reuse a session focus.
- **Overrides** — when to override and how it interacts with the auto-picker.
- **Playlist conflicts** — append vs overwrite, version replacement.
- **Troubleshooting** — common errors and their fixes.
- **Keyboard shortcuts** — full list.
- **Glossary** — short-name vs description, parent vs clone, BIOS, CHD, etc.

Help is searchable via the global Cmd-K palette. All help pages are versioned with the app — they ship in the repo, not fetched from elsewhere, so the docs always match the running version.

## 7. Configuration model

Configuration is split into four files so users can share `config.yaml` and `sessions.yaml` without leaking personal `overrides.yaml` and `notes.json`. Every change to any of these files snapshots the previous version into `data/snapshots/<timestamp>/` for one-click rollback (kept 30 days).

### `config.yaml` (created by wizard, editable by user)

```yaml
# All paths use forward slashes; on Windows the app normalizes via pathlib.
paths:
  source_roms: /mnt/Games/MAME/MAME 0.284 ROMs (non-merged)
  source_dat:  /mnt/Games/MAME/MAME 0.284 ROMs (non-merged).zip
  dest_roms:   /mnt/Games/ROMS/mame
  retroarch_playlist: /mnt/Games/ROMS/mame/mame.lpl

server:
  port: 8080                # auto-incremented up to 8090 if busy at start
  open_browser_on_start: true

filters:
  drop_bios_devices_mechanical: true
  drop_categories:
    - "Casino*"
    - "Slot Machine*"
    - "Mahjong*"
    - "Quiz / Japanese*"
    - "Mature*"
    - "Console*"            # NES/SNES system BIOS — see §13
    - "Computer*"
    - "Calculator*"
    - "Handheld*"
    - "Utilities*"
    - "Tabletop*"
  drop_genres: []            # extra genre denylist beyond catver categories
  drop_publishers: []        # e.g. ["Aristocrat", "IGT"]
  drop_developers: []
  drop_year_before: null     # e.g. 1978
  drop_year_after: null      # e.g. 2015
  drop_japanese_only_text: true
  drop_preliminary_emulation: true
  drop_chd_required: true

picker:
  region_priority: [World, USA, Europe, Japan, Asia, Brazil]
  preferred_genres: []        # boost matching games up the tiebreaker chain
  preferred_publishers: []
  preferred_developers: []
  prefer_parent_over_clone: true
  prefer_good_driver: true

media:
  fetch_videos: false         # opt-in, bandwidth-heavy
  cache_dir: ./data/media-cache

ui:
  theme: dark                 # dark | light | double_dragon | pacman | sf2 | neogeo
  layout: masonry             # masonry | list | covers | grouped
  default_sort: name          # name | year | manufacturer | rating
  show_alternatives_indicator: true
  cards_per_row_hint: auto    # auto | 4 | 5 | 6 | 8

updates:
  channel: stable             # stable | dev
  check_on_startup: true
  ini_check_on_startup: true
```

There is deliberately no `privacy:` section. Telemetry is a hard non-goal (§3) — there are no analytics endpoints in the codebase, and a CI grep gate enforces that none get added. A configurable "opt out of telemetry" toggle would imply telemetry exists; it doesn't.

### `overrides.yaml` (per-user manual picks)

```yaml
overrides:
  sf2: sf2ce                  # user prefers Champion Edition over vanilla
  # ...
```

### `sessions.yaml` (named session focuses for continuation mode)

```yaml
active: shoot_em_ups          # null = no active session, show full library

sessions:
  shoot_em_ups:
    include_genres: ["Shooter*", "Shoot 'em Up*"]
  capcom_fighters_early_90s:
    include_publishers: ["Capcom*"]
    include_genres: ["Fighter*"]
    include_year_range: [1991, 1995]
  todo_after_shooters:
    include_genres: ["Fighter*", "Beat'em Up*", "Platformer*"]
```

### `data/notes.json` (per-game user notes)

```json
{
  "sf2ce": "Best with arcade stick; co-op is great",
  "pacman": "Use the original; the speedup hack is for nostalgia only"
}
```

## 8. UI design

### Top-level navigation

A persistent left rail (or top bar on narrow screens) holds:
- **Library** (the grid; default landing page)
- **Sessions** (manage and activate session focuses)
- **Activity** (history of copy operations + log)
- **Stats** (overview of the curated library — counts by genre/year/decade/publisher, total size, etc.)
- **Settings**
- **Help**
- A persistent global search affordance (Cmd-K / Ctrl-K palette: search games, settings, actions, help topics)

### Layout (key screens)

#### Library

The library has **multiple selectable layouts** (chosen in Settings or via a layout-picker control on the page itself):

1. **Masonry** (default) — Pinterest-style; cards size to flyer aspect; visually rich and the easiest to skim.
2. **List** — dense table-style row per game with sortable columns (description, year, publisher, genre, status badges); fast for quick filtering and large libraries.
3. **Covers** — large cover-flow row of fewer-but-bigger flyers per scroll; for browsing in a "what jumps out" mode.
4. **Grouped** — sectioned by genre (or year, or publisher — user-selectable group key); each section a horizontal scroller of compact cards.

Cards in any layout share the same metadata + corner badges:
- 🔀 has alternatives — click to open drawer
- ✏️ manual override
- ⚠️ BIOS missing
- 💿 CHD missing
- ⭐ user override-pinned to "always include this version"
- 📝 has user notes

#### Detail drawer (slide-in from right)

Full flyer + title screen + gameplay snap (+ optional embedded video). Below: full metadata, **"Why was this picked?"** explanation (the chain of tiebreaker rules that led to this winner), the user-notes field, "Show all candidates" → side-by-side strip of parent + clones with current pick highlighted, and click-to-override.

#### Filters sidebar (left)

Search box, category pills, manufacturer / publisher / developer, genre, year range slider, **on/off switches** for quick toggles ("only contested picks", "only manual overrides", "only CHD-missing", "only BIOS-missing"), free-text DAT search, and a "Save current filters as session" button.

#### Bottom action bar (sticky)

`2,847 games selected · 18.2 GB · 47 BIOS deps · [Dry-run] [Copy to /mnt/Games/ROMS/mame]`. Dry-run opens a preview modal showing the diff (new / replace / skip) without touching disk. Copy opens the live modal.

#### Copy modal

Live progress bar with ETA, current-file display, **Pause / Resume / Cancel** buttons. Pause holds at the next file boundary. Cancel asks whether to keep already-copied files or remove them. The modal is dismissible during copy (work continues in the background; a small status indicator stays in the top bar).

#### Sessions page

List of saved sessions, an "Active" indicator, a "+ New session" button, and an inline editor for each session's filter rules. Activating a session immediately re-filters the Library view.

#### Activity page

Reverse-chronological feed of copy events, override changes, session activations, INI refreshes, app updates, and confirmed deletions. Each entry expands to show the full report.

#### Stats page

Quick visual overview: total games / total size, breakdown by genre (donut), by decade (bar), top 10 publishers (bar), CHD-missing count, BIOS-missing count, "best games" tier distribution.

#### Settings page

Sections: Paths, Filters, Picker, UI (theme + layout + sort), Updates, Media (cache size + clear), Snapshots (rollback config/overrides/sessions), Export/Import settings, Re-run wizard, About (version, license, links).

### UI controls — switches over checkboxes

**Use the shadcn `Switch` (on/off, Mac-style) for every binary preference.** Checkboxes are reserved for cases where checkbox semantics genuinely fit (e.g. multi-selecting games for a bulk action). This rule is also captured in the coding standards.

### Look and feel

- **Dark mode default** with light mode toggle.
- **Theme palettes** beyond plain dark/light, switchable in Settings:
  - `dark` — default; slate-950 background, emerald-400 accent.
  - `light` — clean white; emerald-600 accent.
  - `double_dragon` — warm reds and golds inspired by the Double Dragon arcade marquee.
  - `pacman` — black background with the iconic blue + yellow palette.
  - `sf2` — Street Fighter II's deep blue + crimson accent.
  - `neogeo` — Neo-Geo's red + black + chrome aesthetic.
  - Themes are pure CSS variable swaps; no asset weight per theme.
- Tailwind v4 `@theme` directive for theme variables.
- shadcn/ui primitives: `Card`, `Sheet`, `Dialog`, `Toast`, `Progress`, `Tabs`, `Accordion`, `Switch`, `Slider`, `Command` (Cmd-K palette), `Tooltip`, `AlertDialog` (for confirmations).
- Typography: Inter (system fallback). Generous spacing. Subtle card elevation.
- Motion: small hover lift on cards, smooth drawer slides, no aggressive animations (≤300ms per UI feedback).
- The whole app should feel like a modern Steam/GoG-style library, not a 1990s ROM manager.

### Empty states

- **No config / first run:** routed to setup wizard (per §6.6).
- **No winners after filter:** "Your current filters dropped every game. Soften filters in the sidebar, or load a session."
- **No alternatives for a game:** drawer shows "This is the only version in the library."
- **No copy history yet:** Activity page shows "Nothing here yet — your first copy will appear here."

### Confirmation dialogs (destructive operations)

Every destructive action surfaces an `AlertDialog` with:
- The exact thing being destroyed (path, count, name)
- Whether it's reversible (and how to reverse)
- Distinct primary button text (never just "OK") — e.g. "Delete 3 files from drive", "Discard playlist and overwrite"

This applies to: overwrite playlist, replace-and-delete-old version, clear media cache, restore a snapshot, reset config, abort copy with file removal, app rollback.

### Keyboard shortcuts

Built-in, listed in Help, partially shown as tooltips:

- `⌘K` / `Ctrl-K` — global palette (search games, settings, actions, help)
- `/` — focus the library search box
- `?` — show all keyboard shortcuts
- `g` then `l` / `s` / `a` / `t` / `g` / `h` — go to Library / Settings / Activity / Stats / seSsions / Help (Vim-style chord)
- `j` / `k` — next / previous card in grid
- `o` or `Enter` — open detail drawer for focused card
- `a` — open alternatives drawer for focused card
- `n` — edit notes for focused card
- `Esc` — close drawer / dialog

## 9. Error handling

| Scenario | Behavior |
|---|---|
| DAT XML missing or corrupt | Wizard re-prompts; backend refuses to start with a clear message |
| `.zip` listed in DAT but missing on disk | Skip in filter; surface in copy report under "missing source" |
| Required BIOS missing | Mark game with ⚠️ in UI; user can choose to skip or copy-anyway |
| CHD-required game | Mark with 💿; default-skipped; listed in setup-wizard summary |
| Media URL 404 | Show placeholder card art; no error toast (too noisy at scale) |
| Destination not writable | Preflight check fails; copy never starts; modal shows path + permission needed |
| Copy paused mid-run | Holds at next file boundary; resume continues; cancel asks about partial keep/remove |
| Copy aborted mid-run | Finish current file (atomic), stop cleanly, surface partial-run report |
| Reference `.ini` download fails after retries | Wizard pauses; offers manual-download link with "I dropped it in `data/`" button |
| Configured port 8080 in use | Auto-scan up to 8090 for a free port; if all busy, prompt user to specify or kill the offender |
| `uv sync` fails | `run.sh` shows the exact uv error + suggested fix; offers offline-wheel fallback if `wheels/` is present |
| `overrides.yaml` references unknown short name | Warn in UI but don't crash; rule chain falls back to auto-pick for that group |
| Existing playlist found at destination | Modal asks: append / overwrite / cancel (per §6.4) |
| Per-game version conflict on append | Modal asks per-game: keep existing or replace; replace asks about deleting old `.zip` |
| User confirms delete-from-drive | File is moved to `data/recycle/` (not unlinked); 30-day retention; visible in Activity |
| Self-update fails mid-pull | Previous version remains running; user sees error toast with details; no half-state |
| INI refresh diff shows large drop | Modal shows the diff (X new, Y dropped, Z changed) and requires explicit confirm before applying |
| User pastes non-existent path in wizard | Validation error inline in field; "Browse..." button auto-opens the file browser |
| File-browser endpoint asked for restricted path | Returns 403 with friendly message; sandboxes to user's home + configured roots |

## 10. Testing strategy

- **Unit tests** for the rule chain. Synthetic `Machine` fixtures cover each rule's edge cases. Property-based tests assert: same input → same output (determinism); adding an override only changes that group's winner.
- **Snapshot test** with a hand-picked fixture DAT (~30 machines exercising every filter and tiebreaker). The expected curated set is a JSON checked into `tests/snapshots/` and regenerated only intentionally.
- **Parser tests** against real-world DAT samples (truncated to ~100 entries to stay in-repo).
- **Integration test for copy:** temp `tmp_path` fixtures with fake `.zip` files, run the copy pipeline, assert dest layout, BIOS presence, `.lpl` contents.
- **API smoke tests** — FastAPI TestClient hitting every route.
- **Frontend tests** — component tests with Vitest + Testing Library on the grid card, drawer, alternatives view, override flow.
- **End-to-end** — Playwright script: launch backend with fixture data → open UI → search for "Pac" → open alternatives → set an override → trigger copy → assert report. One smoke E2E is enough.
- **Manual UAT** — run against the user's real 43,579-entry DAT, eyeball ~30 contested picks, refine.

## 11. Project layout

```
mame-curator/
├── README.md                # what it does, install, run
├── LICENSE                  # MIT
├── CHANGELOG.md
├── CONTRIBUTING.md
├── pyproject.toml           # Python project + deps (uv-managed)
├── uv.lock                  # committed lockfile
├── run.sh / run.bat         # one-command launcher (bootstrap stage 1)
├── config.example.yaml
├── overrides.example.yaml
├── sessions.example.yaml
├── docs/
│   ├── help/                # in-app help markdown (served via /api/help)
│   ├── screenshots/         # for README + GitHub
│   ├── standards/
│   │   └── coding-standards.md
│   └── superpowers/
│       └── specs/
│           ├── 2026-04-27-mame-curator-design.md
│           └── 2026-04-27-roadmap.md
├── src/
│   └── mame_curator/
│       ├── parser/        # XML + ini parsers           (+ spec.md, tests/)
│       ├── filter/        # 4-phase rule chain           (+ spec.md, tests/)
│       ├── media/         # URL builder + lazy fetch     (+ spec.md, tests/)
│       ├── copy/          # copy + BIOS + lpl + conflicts (+ spec.md, tests/)
│       ├── api/           # FastAPI routes               (+ spec.md, tests/)
│       ├── setup/         # wizard logic, downloads      (+ spec.md, tests/)
│       ├── updates/       # self-update + INI refresh    (+ spec.md, tests/)
│       ├── help/          # help-page server             (+ spec.md, tests/)
│       └── main.py        # uvicorn entrypoint, lifespan
├── tests/                  # cross-cutting integration + e2e tests
├── frontend/
│   ├── package.json       # React 19 + Vite + Tailwind v4 + shadcn/ui
│   ├── src/
│   ├── public/
│   └── dist/              # ← pre-built bundle, COMMITTED so end users don't need Node
├── data/                  # gitignored
│   ├── *.ini              # downloaded reference files
│   ├── mame-listxml.xml   # downloaded official MAME XML
│   ├── media-cache/       # content-hashed cached images
│   ├── snapshots/         # config/overrides/sessions auto-snapshots (30-day retention)
│   ├── recycle/           # files removed during overwrite, 30-day retention
│   ├── activity.jsonl     # append-only activity log
│   ├── notes.json         # per-game user notes
│   └── .wizard-state.json # resumable wizard progress
└── wheels/                # offline pip wheel fallback (optional)
```

Notes:
- Single `pyproject.toml` at the repo root (per `uv init --package` convention) — no nested `backend/pyproject.toml`. The `src/` layout is the modern Python packaging standard.
- Every backend module has both a `spec.md` (audit surface) and a `tests/` subdirectory next to its code, per coding standards §7.

## 12. Phasing

The canonical implementation order lives in **[the roadmap doc](2026-04-27-roadmap.md)** — read it before writing any code. It defines ten sequential phases (0 scaffold → 9 release) with explicit pre-conditions, tests-first sequences, and binary acceptance criteria per phase. The roadmap also enumerates anti-jump rules to keep implementation strictly in order.

High-level summary of those phases (full detail in the roadmap):

- **Phase 0** — Tooling and CI scaffold.
- **Phase 1** — DAT + INI parsers (`parser/`).
- **Phase 2** — Filter rule chain (`filter/`) — Phase A drops, Phase B picks, Phase C overrides, Phase D session focus.
- **Phase 3** — Copy + BIOS + `.lpl` writer (`copy/`) — including playlist conflict resolution + recycle bin + pause/resume/cancel.
- **Phase 4** — FastAPI HTTP surface (`api/`) — including filesystem-browser routes (consumed by the Phase 8 setup wizard's Browse buttons; the routes ship in Phase 4 because the API surface is cohesive there, even though the wizard itself does not arrive until Phase 8).
- **Phase 5** — Media subsystem (`media/`) — libretro-thumbnails escape rules + lazy-fetch cache.
- **Phase 6** — Frontend MVP — grid, themes, layouts, sessions, activity, stats, settings, switches everywhere.
- **Phase 7** — Self-update + in-app help (`updates/` + `help/`).
- **Phase 8** — Setup wizard — bootstrap (`run.sh`) + browser-based first-run flow.
- **Phase 9** — Polish, docs, GitHub publish.

## 13. Non-arcade systems and per-system routing

**Important clarification:** MAME's main ROM set (the 43,579 `.zip` files in this user's set) does **not** contain console games. It contains:

- **Arcade games** (the great majority — what we want)
- **Console *system BIOSes*** (e.g. `snes.zip` = 209 bytes — just the SPC700 sound chip boot ROM; `gameboy.zip` = 762 bytes — just the DMG boot ROM). No `nes.zip`, `psx.zip`, or `genesis.zip` exist at all in this set.
- **Computer system BIOSes** (Apple II, ZX Spectrum, etc. — same idea, just bootstrap firmware)
- **Handhelds, calculators, ATMs, chess boards, lab equipment, ...** (single-purpose hardware MAME happens to emulate)

Actual console *games* (Super Mario Bros NES, Sonic Genesis, etc.) live in entirely separate ROM sets — No-Intro, TOSEC, or MAME's optional "Software List" packs (additional hundreds of GB the user does not have). Those, in a RetroArch setup, belong in **dedicated cores** like `fceumm` (NES), `snes9x` (SNES), `picodrive` (Genesis), `mednafen_psx_hw` (PSX), etc., not in the MAME core.

**Therefore the user's requirement is already satisfied** by the default filters: `Console*`, `Computer*`, `Handheld*`, `Calculator*` are in `drop_categories`, so none of those BIOS-only system entries will end up in `/mnt/Games/ROMS/mame/`. The MAME folder receives only true arcade games.

**Future enhancement — software-list routing.** If the user later acquires MAME Software List ROM sets (which *do* contain console games via MAME emulation), MAME Curator could route those to per-system folders (`/mnt/Games/ROMS/nes/`, `/mnt/Games/ROMS/snes/`, etc.) using a `system_routing` config map. This is **out of scope for v1** but the architecture allows it cleanly: software-list machines have a `<softwarelist name="...">` element pointing at the parent system, which gives us a clean routing key. Adding it later is a feature flag, not a redesign.

## 14. Open questions / risks

- **MAME version drift.** When the user upgrades to MAME 0.285 (or later) next year, `bestgames.ini` etc. must be re-downloaded. The §6.7 update channel handles this with explicit user confirmation.
- **`bestgames.ini` coverage.** It rates only ~3,000 of the most well-known games. For long-tail picks, the rating is "unrated" and we fall through to other rules — fine, but worth noting.
- **Region detection from descriptions** is heuristic. Edge cases like `(World, Set 2)` or `(Europe v2.1)` may need iteration. Fixture tests should pin known good descriptions; refine as we hit edge cases.
- **Media `.png` filename mismatches.** libretro-thumbnails uses the description verbatim, but characters `&*/:\`<>?\|"` are escaped to `_`. We must mirror their escaping exactly — covered by media-subsystem unit tests.
- **Source DAT format variance.** If the user's DAT is from a different aggregator (e.g. EmuMovies, redump), short names should still match MAME's, but we validate at startup that the DAT has the expected XML structure and surface a clear error if not.
- **Pleasuredome DATs strip `cloneof` / `romof` attributes** (verified empirically against both merged and non-merged 0.284). Parent/clone relationships therefore come from the official MAME `-listxml` and are joined onto Pleasuredome machines by short name in Phase 2's filter. This is recorded in `parser/spec.md` and is the reason the Phase 1 smoke run shows `clones: 0` against the Pleasuredome DAT alone — that's correct behavior, not a parser bug.
- **Self-update on Windows.** `git pull` works for clones but a downloaded zip release needs a different mechanism (download-new, swap, restart). Phase 7's update logic handles both, but the swap-on-Windows path is the trickiest because the running process holds open handles — we restart via a small bootstrap helper.
- **Genre/publisher/developer filters depend on `catver.ini` and DAT `<manufacturer>` quality.** Both have inconsistencies (e.g. `"Capcom (Sega license)"` vs `"Capcom"`). Filtering uses prefix matching by default; users may need to add multiple patterns to catch variants. The filter customization UI shows a live count so users can iterate.
- **Recycle directory growth.** The 30-day retention is configurable but defaults could surprise users with low disk space. Settings shows the current recycle-bin size and offers immediate purge.
- **uv availability.** `uv` is the modern standard but new enough that some users may not have it. The bootstrap script offers to install it via the official one-liner, but a small fraction of users may need to install manually. Manual instructions are surfaced clearly.

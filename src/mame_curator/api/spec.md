# api/ spec

## Contract

The FastAPI HTTP surface that exposes the curation engine
(`parser/` + `filter/` + `copy/` + `media/`) to the React SPA and to any
HTTP client. The API is a **thin route layer** over an immutable
in-memory world: it parses + validates requests, calls library code, and
serialises typed Pydantic responses. Business logic lives in the library
modules, not here.

Four cross-cutting contracts bind every route and are the audit surface
of this spec:

1. **One frozen `WorldState`** lives on `app.state.world`. Reads borrow it;
   writes build a *new* `WorldState` and swap it wholesale under a lock.
2. **One uniform error envelope** (`ApiErrorBody`: `detail` / `code` /
   `fields[]`) is returned for every non-2xx response, with a stable
   machine-readable `code`.
3. **At most one copy job** runs at a time (`JobManager` singleton on
   `app.state.job`); progress streams over Server-Sent Events.
4. **All filesystem access is sandboxed** to a composed allowlist; a path
   outside it is a `403 fs_sandboxed`, never an open read.

Layering: `api/ ← parser/ + filter/ + copy/ + media/` (all of the
above). The CLI launches the server; this spec owns the HTTP contract,
not the launch wiring (see `cli/spec.md`). The long-form design is
`docs/specs/P04.md`; this file is the co-located, audit-facing contract.

## App factory + lifespan

`create_app(config_path: Path) -> FastAPI` builds a configured instance.
The async **lifespan** populates `app.state` once at startup:

| `app.state.*` | Type | Built from |
|---|---|---|
| `world` | `WorldState` | `build_world(config_path)` |
| `job` | `JobManager` | `history_dir = world.data_dir / "copy-history"` |
| `world_lock` | `asyncio.Lock` | guards every world-mutating route (below) |
| `media_client` | `httpx.AsyncClient` | shared; `timeout=10s`, `follow_redirects=True`, descriptive `User-Agent` |
| `arcadedb_limiter` | `TokenBucket` (`mame_curator.media`) | `rate = N/60` per s, `capacity = N`, where `N = config.media.arcadedb_rate_limit_per_min` |
| `wikipedia_limiter` | `TokenBucket` (`mame_curator.media`) | `rate = 1.0` per s, `capacity = 60` — 60 req/min hardcoded courtesy cap |

On shutdown the lifespan closes `media_client` and, if a copy job is
in flight, cancels its controller and joins the worker thread with a
5-second timeout (logging a warning if it does not exit — the daemon
thread is then reaped at interpreter exit).

The order of registration is load-bearing: `install_handlers(app)` →
`include_router(api_router)` → (only if `frontend/dist/` exists) mount
the SPA at `/`. The SPA mount is **last** so `/api/*` and `/media/*`
keep routing precedence over the catch-all.

## WorldState model

`WorldState` is a **frozen** Pydantic model (`frozen=True`,
`extra="forbid"`) — the single source of truth for one server process.
It bundles the parsed DAT (`machines`), the listxml joins (`cloneof_map`,
`bios_chain`, `chd_required`), the `FilterContext` + `FilterResult`,
curation state (`overrides`, `sessions`, `review_state`, `notes`), the
composed `allowed_roots`, the resolved `config` + `config_path` +
`data_dir`, and the DS02 precomputed `bytes_by_machine` map.

- **`build_world(config_path)`** — called once at startup. Parses the DAT,
  the five reference INIs (each optional in config), and the listxml joins;
  runs the filter; composes the allowlist; returns the assembled world.
- **`replace_world(*, base, ...)`** — builds a *new* world from `base` with
  selected fields swapped. It is the only mutation path. Recompute triggers:
  - `filter_result` is re-run **only** when `config`, `overrides`, or
    `sessions` changed (or `rerun_filter=True`).
  - `allowed_roots` is re-composed **only** when `config` changed
    (`compose_allowlist` is a pure function of `config.paths` +
    `config.fs.granted_roots`; see the load-bearing comment in
    `replace_world` before short-circuiting it).
  - `review_state` is a **passive field swap** (P14 INV-4): it does *not*
    trigger a filter recompute — review state never gates eligibility; the
    visibility filter is applied per-request in `routes/games.py`.
  - `machines` / `bytes_by_machine` are immutable post-parse and pass
    through unchanged on every swap.

### Concurrency invariant (the world lock)

Every route that mutates the world performs a
**read-merge-write-swap** under `async with app.state.world_lock`. Without
the lock two concurrent mutating requests read the same base world and the
later writer clobbers the earlier — silently dropping a user edit. The
lock-guarded routes are:

`PATCH /api/config`, `POST /api/config/snapshots/{id}/restore`,
`POST /api/config/import`, `POST`/`DELETE /api/fs/allowed-roots`,
`POST`/`DELETE /api/overrides`, `POST`/`DELETE /api/sessions`,
`POST /api/sessions/{name}/activate`, `POST /api/sessions/_deactivate`,
`PUT /api/games/{name}/notes`, and `POST /api/state` /
`DELETE /api/state/{short_name}`.

(The `app.py` comment enumerates the guarded routes in three waves —
FP20-C's five, FP25-A's seven, and P14's two (`POST`/`DELETE /api/state`) —
for fourteen total (5 + 7 + 2). New world-mutating routes MUST acquire the
lock.)

## Error envelope

Every non-2xx response is an `ApiErrorBody` (`frozen`, `extra="forbid"`):

```
{ "detail": "<single-line human message>",
  "code":   "<stable machine code>",
  "fields": [ { "loc": "...", "msg": "...", "type": "..." }, ... ] }
```

`detail` is always a **single line** (multi-line library errors are
`repr`-quoted before they reach it). `code` is the contract the frontend
keys on (`strings.errors.byCode[...]`); `fields` is populated only for
validation-style failures.

Throwables subclass `ApiException` (each carries `code` + `status_code`
class vars). `install_handlers` registers three handlers:

- `ApiException` → render its `code` + `status_code`.
- `RequestValidationError` → `422` with `code="validation_error"` and the
  per-field `fields[]` (overrides FastAPI's default `{detail:[...]}` shape).
- bare `Exception` → `500` with `code="internal"`, logged with traceback;
  no internal detail leaks to the client.

### Typed exception → code / status map

| Exception | `code` | HTTP |
|---|---|---|
| `ConfigError` | `config_invalid` | 422 |
| `FsSandboxError` | `fs_sandboxed` | 403 |
| `FsAlreadyCoveredError` | `fs_already_covered` | 409 |
| `FsPathInvalidError` | `fs_path_invalid` | 400 |
| `FsNotFoundError` | `fs_not_found` | 404 |
| `FsRootNotFoundError` | `fs_root_not_found` | 404 |
| `FsConfigRootNotRevocableError` | `fs_config_root_not_revocable` | 400 |
| `JobAlreadyRunningError` | `job_already_running` | 409 |
| `JobNotFoundError` | `job_not_found` | 404 |
| `CopyReportCorruptError` | `copy_report_corrupt` | 502 |
| `PlaylistConflictCancelledError` | `playlist_conflict_cancelled` | 409 |
| `SnapshotNotFoundError` | `snapshot_not_found` | 404 |
| `GameNotFoundError` | `game_not_found` | 404 |
| `OverrideNotFoundError` | `override_not_found` | 404 |
| `SessionNotFoundError` | `session_not_found` | 404 |
| `SessionNameInvalidError` | `session_name_invalid` | 422 |
| `HelpTopicNotFoundError` | `help_topic_not_found` | 404 |
| `MediaKindInvalidError` | `media_kind_invalid` | 400 |
| `MediaUpstreamError` | `media_upstream_error` | 502 |
| `MediaUpstreamNotFoundError` | `media_upstream_not_found` | 404 |
| `RetroArchNotConfiguredError` | `retroarch_not_configured` | 422 |
| `RomFileNotFoundError` | `rom_file_not_found` | 404 |
| (`ApiException` base / fallback) | `internal` | 500 |
| (request-validation handler) | `validation_error` | 422 |

A new typed exception MUST set both class vars and add a `byCode` entry on
the frontend, in the same change (per coding-standards §7).

## Route inventory

Routers are aggregated in `routes/__init__.py` and mounted by `create_app`.
"Mut." marks a world-mutating route that takes `world_lock`.

| Method | Path | Response model | Mut. |
|---|---|---|---|
| GET | `/api/config` | `AppConfigResponse` | |
| PATCH | `/api/config` | `AppConfigResponse` | ✓ |
| GET | `/api/config/snapshots` | `SnapshotsListing` | |
| POST | `/api/config/snapshots/{snap_id}/restore` | `AppConfigResponse` | ✓ |
| POST | `/api/config/export` | `ConfigExportBundle` | |
| POST | `/api/config/import` | `AppConfigResponse` | ✓ |
| GET | `/api/games` | `GamesPage` | |
| GET | `/api/games/{name}` | `GameDetail` | |
| POST | `/api/games/validate` | `ValidateResponse` | |
| POST | `/api/games/{name}/launch` | `LaunchResponse` | |
| GET | `/api/games/{name}/alternatives` | `Alternatives` | |
| GET | `/api/games/{name}/explanation` | `Explanation` | |
| GET | `/api/games/{name}/notes` | `Notes` | |
| PUT | `/api/games/{name}/notes` | `Notes` | ✓ |
| GET | `/api/library/facets` | `LibraryFacets` | |
| GET | `/api/stats` | `Stats` | |
| GET | `/api/state` | `StateView` | |
| POST | `/api/state` | `StateView` | ✓ |
| DELETE | `/api/state/{short_name}` | `StateView` | ✓ |
| POST | `/api/overrides` | `OverridesView` | ✓ |
| DELETE | `/api/overrides/{parent}` | `OverridesView` | ✓ |
| GET | `/api/sessions` | `SessionsListing` | |
| POST | `/api/sessions` | `SessionsListing` | ✓ |
| DELETE | `/api/sessions/{name}` | `SessionsListing` | ✓ |
| POST | `/api/sessions/{name}/activate` | `SessionsListing` | ✓ |
| POST | `/api/sessions/_deactivate` | `SessionsListing` | ✓ |
| POST | `/api/copy/dry-run` | `DryRunReport` | |
| POST | `/api/copy/start` | `JobAccepted` | |
| POST | `/api/copy/pause` | `JobStatus` | |
| POST | `/api/copy/resume` | `JobStatus` | |
| POST | `/api/copy/abort` | `JobStatus` | |
| GET | `/api/copy/status` | SSE (`text/event-stream`) | |
| GET | `/api/copy/history` | `HistoryListing` | |
| GET | `/api/copy/history/{job_id}/report` | `CopyReport` | |
| GET | `/api/fs/list` | `FsListing` | |
| GET | `/api/fs/home` | `FsPath` | |
| GET | `/api/fs/roots` | `FsDriveRoots` | |
| GET | `/api/fs/allowed-roots` | `FsAllowedRoots` | |
| POST | `/api/fs/allowed-roots` | `FsAllowedRoots` | ✓ |
| DELETE | `/api/fs/allowed-roots/{root_id}` | `FsAllowedRoots` | ✓ |
| GET | `/api/activity` | `ActivityPage` | |
| GET | `/api/help/index` | `HelpIndex` | |
| GET | `/api/help/{topic}` | `HelpContent` | |
| GET | `/api/setup/check` | `SetupCheck` | |
| GET | `/api/updates/check` | `UpdatesCheck` | |
| GET | `/media/{name}/{kind}` | image bytes (`FileResponse`) | |

Route ordering note: `POST /api/sessions/_deactivate` is registered
**before** the dynamic `POST /api/sessions/{name}/activate` so FastAPI
matches the static `_deactivate` path first.

## Copy job lifecycle

`JobManager` owns `app.state.job` and enforces the single-job invariant:

- **`start(plan, world)`** raises `JobAlreadyRunningError` (409) if a job
  is already current. Otherwise it resolves the BIOS chain, computes
  `files_total` / `bytes_total`, spawns a **daemon worker thread** running
  `copy.run_copy`, and emits the initial `job_started` event. Returns a
  `Job` whose `id` the route returns as `JobAccepted`.
- `POST /api/copy/start` first calls `check_playlist_conflict(plan)` —
  a `CANCEL` conflict strategy against an existing playlist raises
  `PlaylistConflictCancelledError` (409) before the worker spawns.
- **`pause` / `resume` / `abort`** drive the `CopyController` and return a
  `JobStatus`. `abort` takes `recycle_partial`. An operation with no current
  job raises `JobNotFoundError` (404).
- **`GET /api/copy/status`** returns an `EventSourceResponse` streaming
  `JobEvent` payloads (`job_started`, progress, terminal). No active job →
  `JobNotFoundError` (404). Progress events carry `files_total` /
  `bytes_total` keys matching the typed `JobStatus` / frontend contract.
- Worker→loop handoff uses `loop.call_soon_threadsafe` (FP28-A1) so all
  `app.state` mutation and event emission happen on the event-loop thread,
  never the worker thread.

### Copy history

Completed jobs persist a `report.json` under
`data_dir / copy-history / <job_id>/`. `GET /api/copy/history` paginates
(`page` ≥ 1, `page_size` 1..500, newest first), skipping unreadable /
unparseable report dirs. `GET /api/copy/history/{job_id}/report` validates
the file against `CopyReport` on egress: missing id → `404 job_not_found`;
present-but-unreadable / corrupt → `502 copy_report_corrupt` (a distinct
"filesystem rot" code, separate from the 404).

## Filesystem sandbox

All FS browsing crosses `api/fs.py`:

- **`compose_allowlist(config)`** builds the allowed-root tuple from the
  **home directory** (`Path.home()`) plus four config-derived paths
  (`source_roms`, `source_dat.parent`, `dest_roms`,
  `retroarch_playlist.parent`), plus `config.fs.granted_roots` (user-granted
  via the API). Each root has a stable `id` (first 12 hex chars of the
  SHA-256 of the resolved path) and a
  `source` (`config` vs `granted`); a granted path overlapping a
  config-derived root takes the `config` label. Granted roots whose target
  is no longer an existing directory are dropped.
- **`validate_fs_path` / `validate_within_allowlist`** reject any requested
  path that resolves outside every allowed root → `FsSandboxError` (403).
  Empty / NUL-byte / non-directory paths → `FsPathInvalidError` (400);
  non-existent paths → `FsNotFoundError` (404).
- **Grant** (`POST /api/fs/allowed-roots`) adds a `granted` root; a path
  already covered by an existing root → `FsAlreadyCoveredError` (409).
- **Revoke** (`DELETE /api/fs/allowed-roots/{root_id}`) removes a `granted`
  root; an unknown id → `FsRootNotFoundError` (404); a `config`-derived root
  is **not revocable** via the API → `FsConfigRootNotRevocableError` (400)
  (it is removed by editing config, which re-composes the allowlist).

## Config persistence + snapshots

`api/persist.py` performs all disk writes **atomically** (temp file +
`os.replace` + parent fsync) so a crash mid-write never leaves a truncated
`config.yaml` / `notes.json`:

- `PATCH /api/config` deep-merges the patch (`deep_merge`, depth-capped at
  10 for defence-in-depth), validates against `AppConfig`, writes the YAML,
  and swaps the world.
- `snapshot_files` captures the pre-write state before each config mutation;
  `restore_snapshot` reverts to a captured snapshot id (unknown id →
  `SnapshotNotFoundError` 404). Old snapshots are pruned.
- `export` returns a `ConfigExportBundle`; `import` validates + applies a
  bundle (invalid → `ConfigError` 422).

## Media proxy

`GET /media/{name}/{kind}` proxies cover art through `media/`:

- Valid kinds are `boxart`, `title`, `snap`, `video`; anything else →
  `MediaKindInvalidError` (400). Unknown `name` → `GameNotFoundError` (404).
- `video` has no libretro upstream and short-circuits to
  `MediaUpstreamNotFoundError` (404). Video art is sourced from
  progettoSnaps rather than libretro-thumbnails (design §6.3) and is not
  served by this proxy today.
- The URL is built by `media.urls_for(machine)`; bytes are lazily fetched
  and disk-cached by `media.fetch_with_cache` using the shared
  `app.state.media_client`. An upstream failure → `MediaUpstreamError`
  (502); an upstream 404 → `MediaUpstreamNotFoundError` (404).
- A cache hit returns a `FileResponse` (content-type sniffed from the
  cached file's suffix) with a 30-day `immutable` `Cache-Control`.
- This proxy path (libretro-thumbnails) is **not** rate-limited. The
  `arcadedb_limiter` / `wikipedia_limiter` token buckets on `app.state` gate
  the P10 media-metadata sources (ArcadeDB / Wikipedia), which are not yet
  exposed through a shipped route; their `MediaRateLimited` is a
  `media`-internal exception (not an `ApiException`) and does not reach the
  error envelope today.

## SPA fallback

When `frontend/dist/` is present, `_SPAStaticFiles` serves the bundle at
`/` and falls back to `index.html` for **path-shaped** 404s so deep
client-side routes (`/sessions/foo`) boot the SPA. Carve-outs that MUST
surface a real 404 instead of `index.html`:

- `api/`, `media/` — an unrouted API path must 404 so the frontend's zod
  validator distinguishes "missing route" from "shape mismatch"; HTML for
  `/api/...` masks routing bugs.
- `assets/` — a missing bundle asset must 404 visibly; returning HTML makes
  the browser parse it as JS (`Unexpected token '<'`) and boot opaquely.

Cache-Control: `assets/*` (content-addressed hashes) → 1-year `immutable`;
the SPA shell (`index.html`, direct or via fallback) → `no-cache,
must-revalidate`, so a fresh deploy never hands users a stale shell that
references deleted bundle hashes.

## Out of scope

- Business logic of every domain operation — parsing (`parser/`), winner
  selection + filtering (`filter/`), copy execution + playlist + recycle
  (`copy/`), media URL rules + cache (`media/`). Routes call into these and
  serialise the result; they do not reimplement it.
- Request/response **schema field details** — each lives in
  `api/schemas*.py` (`schemas.py`, `schemas_copy.py`, `schemas_fs.py`,
  `schemas_games.py`, `schemas_overrides.py`, `schemas_setup.py`); this
  spec pins the route → response-model wiring and the error contract, not
  every field.
- Server launch / uvicorn lifecycle and the `serve` entrypoint — see
  `cli/spec.md` and `main.py`.
- Help-doc content + the setup-wizard flow — `routes/help.py` serves
  filesystem `docs/help/`, `routes/stubs.py` holds the wizard-check stubs;
  neither is a Python package under `src/mame_curator/`.
- Authentication / multi-user / remote access — the server is a
  single-user localhost tool; there is no auth layer by design.

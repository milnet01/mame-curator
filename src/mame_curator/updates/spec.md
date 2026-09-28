# updates/ spec

## Contract

Reference-data refresh primitives. Given a destination directory and a
caller-supplied `httpx.AsyncClient`, this module:

1. Downloads the five progettoSnaps reference INI files — four mandatory
   (`catver.ini`, `languages.ini`, `bestgames.ini`, `series.ini`) plus
   `mature.ini` — from a stable GitHub mirror into a local directory
   (`refresh_inis`).
2. Discovers + downloads + extracts the progettoSnaps **snap** image pack
   (PNGs) into `<dest>/snap/` (`refresh_snaps` + `discover_snap_pack_url`).
3. Checks for and applies an app update (`updates/app.py`,
   mame-curator-1010): what kind of install this is, the latest GitHub
   release, a git clone's fast-forward with rollback, and a bundle's
   verified download. See § App self-update.

Both operations report outcomes through a **frozen dataclass report**
rather than raising on per-source failure — the CLI surfaces both the
"landed" and "failed (with URL)" lists so the user always knows what to
fetch manually. The one exception is `discover_snap_pack_url`, which
raises `ValueError` when the upstream index yields zero candidates (there
is no partial-success path to report).

All HTTP work is delegated to the shared `mame_curator.downloads.download`
primitive (sha256-verified, atomic, retrying — see "Out of scope"); this
module owns only the *what to fetch / where to put it / how to report it*
layer.

Layering: `updates/ ← parser/ + downloads.py + _resources.py` (no other
internal deps). `updates/app.py` never imports `api/`: the route hands it
the snapshot step as a callable and records the result itself.
The caller owns the `AsyncClient` lifecycle (project convention — one
client reused across many downloads).

## Public surface

Re-exported from `mame_curator.updates.__init__`:

| Name | Kind | Source module |
|---|---|---|
| `refresh_inis` | async function | `updates/ini.py` |
| `INIRefreshReport` | frozen dataclass | `updates/ini.py` |
| `INI_DEFAULT_SOURCES` | `dict[str, str]` | `updates/ini.py` |
| `INI_CONFIG_FIELDS` | `dict[str, str]` — INI file → `paths.<field>` | `updates/ini.py` |
| `refresh_snaps` | async function | `updates/snaps.py` |
| `discover_snap_pack_url` | async function | `updates/snaps.py` |
| `SnapsRefreshReport` | frozen dataclass | `updates/snaps.py` |
| `SNAPS_INDEX_URL` (`= snaps.INDEX_URL`) | `str` | `updates/snaps.py` |
| `SNAP_PACK_MAX_BYTES` | `int` | `updates/snaps.py` |

`updates/app.py` is imported directly (`from mame_curator.updates.app
import …`), not re-exported: `install_kind`, `latest_release`, `is_newer`,
`dev_status`, `head_commit`, `apply_git_update`, `rollback_git_update`,
`bundle_target`, `download_bundle`, the `ReleaseInfo` / `ReleaseAsset` /
`GitUpdateResult` dataclasses, `UpdateCheckError`, and `UpdateError`.

## Public functions

### `refresh_inis(*, dest_dir, client, sources=INI_DEFAULT_SOURCES) -> INIRefreshReport`

- Downloads each `(name, url)` in `sources` to `dest_dir / name`, atomically
  (via `download`). `dest_dir` is created (`parents=True, exist_ok=True`).
- A failed download (bad URL, upstream 404, exhausted retries → the
  `download` primitive returns `ManualFallback`) is collected as a
  `(name, fallback_url)` pair in `INIRefreshReport.failed` and logged at
  `warning`; it is **not** raised. Successful files land in `.updated`.
- `sources` defaults to `INI_DEFAULT_SOURCES` but is injectable so the
  wizard / tests can point at a fixture server or a pinned mirror.

### `discover_snap_pack_url(*, client, index_url=INDEX_URL) -> str`

- GETs the progettoSnaps Snapshots index page and scrapes every
  `pS_snap_fullset_<NNN>.zip` link via `PACK_URL_PATTERN`, returning the
  URL with the **highest** `<NNN>` (latest MAME version).
- Both relative (`/snapshots/...`) and absolute
  (`https://www.progettosnaps.net/snapshots/...`) hrefs appear on the live
  page side by side; relative hits are normalised to absolute.
- Raises `ValueError` if zero candidates are found (upstream restructured)
  — the caller falls back to an explicit `url=` or surfaces the error.
- Calls `response.raise_for_status()` on the index GET, so a non-2xx index
  response raises `httpx.HTTPStatusError` out of this function — and out of
  `refresh_snaps` when `url is None` (discovery is not wrapped). Like the
  extract path, this is a *raise*, not a reported `error`.

### `refresh_snaps(*, dest_dir, client, url=None, force=False) -> SnapsRefreshReport`

- `url is None` → calls `discover_snap_pack_url` first; a non-`None` `url`
  pins the pack (older MAME version, or a manual override around upstream
  URL drift) and **skips discovery**.
- **Disk-space gate**: probes the pack's `Content-Length` via HEAD and
  refuses the download when the target filesystem has less than **2×** the
  declared size free, returning a report with `downloaded=False` and a
  populated `error` (no GET is issued). The free-space probe targets
  `dest_dir` if it already exists, else `dest_dir.parent` (so a not-yet-
  created `dest_dir` measures the parent's mount). When the HEAD probe fails
  or omits `Content-Length`, the gate is skipped and the download proceeds.
- Downloads the pack to `<dest_dir>/pS_snap_fullset.zip` (body cap
  `SNAP_PACK_MAX_BYTES` = `600 * 1024 * 1024` bytes = 600 MiB ≈ 629 MB,
  comfortably above the ~500 MB pack; the default `download` cap,
  `DEFAULT_MAX_BYTES` = `100 * 1024 * 1024` bytes, is sized for INIs, not
  packs). A `ManualFallback`
  download result → report with `downloaded=False` + `error`.
- Extracts every **flat** `*.png` entry into `<dest_dir>/snap/`
  (created if missing). Returns counts in `files_extracted` /
  `files_skipped`. A corrupt / unreadable ZIP raises out of `refresh_snaps`
  at this step (it is **not** caught into `error`; see "Edge cases").

## Public types

### `class INIRefreshReport` (frozen dataclass)

| Field | Type | Meaning |
|---|---|---|
| `updated` | `list[str]` | filenames that downloaded successfully |
| `failed` | `list[tuple[str, str]]` | `(filename, manual_fallback_url)` per failure |
| `all_succeeded` | `bool` (property) | `True` iff `failed` is empty |

### `class SnapsRefreshReport` (frozen dataclass)

| Field | Type | Meaning |
|---|---|---|
| `downloaded` | `bool` | `True` iff a fresh pack was fetched + extracted |
| `pack_url` | `str` | the URL fetched (post-discovery or `--url` override) |
| `files_extracted` | `int` | PNG entries written to disk |
| `files_skipped` | `int` | PNG entries left untouched (existed, `force=False`) |
| `error` | `str \| None` | populated on disk-gate **or** download failure; an extract failure raises instead (see "Edge cases") |

## INI sources

`INI_DEFAULT_SOURCES` mirrors AntoPISA's `MAME_SupportFiles` GitHub repo
rather than progettoSnaps directly: progettoSnaps URLs are versioned per
MAME release (no permanent paths), while AntoPISA republishes the same
files at stable `raw.githubusercontent.com` paths. The repo nests each
file under a same-named subdirectory (`catver.ini/catver.ini`); `mature.ini`
lives inside `catver.ini/` alongside the main catver file. Four files are
mandatory (`catver` / `languages` / `bestgames` / `series`); `mature.ini`
is the fifth. This mandatory/fifth split is **descriptive of downstream
role only** — `refresh_inis` fetches and reports all five identically (a
failed `mature.ini` lands in `failed` and flips `all_succeeded` just like
any other source); the label is not a refresh-behaviour tier.

## Snap pack model

Snap is the **only** kind progettoSnaps actively publishes (verified
2026-05-18); other kinds (title, flyer, …) are not maintained upstream and
are out of scope here. The pack URL pattern is
`.../snapshots/packs/full_sets/pS_snap_fullset_<NNN>.zip` where `<NNN>` is
the MAME version. The documented archive layout is flat
`<short_name>.png` at the root.

**Destination.** Both `refresh_inis` and `refresh_snaps` take `dest_dir` as
a **required** keyword — neither function defaults it. The module exposes a
`DEFAULT_DEST = Path("./data/snaps")` convention (the conventional default
destination for snap packs); it is a module constant, not part of the
re-exported public surface (`__all__`), so callers pass `dest_dir`
explicitly.

## Edge cases handled

- INI download failure (bad URL / 404 / retries exhausted) → `failed` entry
  with the URL, logged `warning`, never raised.
- `discover_snap_pack_url` finds zero `pS_snap_fullset_<NNN>.zip` links →
  `ValueError` (upstream restructure signal).
- `discover_snap_pack_url` index GET returns a non-2xx status →
  `httpx.HTTPStatusError` raised (via `raise_for_status()`), propagating out
  of `refresh_snaps` when `url is None` — a raise, not a reported `error`.
- Snap disk-space gate fails (< 2× declared free) → `SnapsRefreshReport`
  with `downloaded=False` + `error`, **before** any GET.
- HEAD probe fails or omits / malformed `Content-Length` → gate skipped,
  download proceeds (the streaming byte-cap in `download` is the backstop —
  the 600 MiB `SNAP_PACK_MAX_BYTES` passed by `refresh_snaps`, not the
  100 MiB default).
- Snap pack download failure (`ManualFallback`) → report with
  `downloaded=False` + `error`.
- Corrupt / unreadable pack ZIP at extract → **raises** (`zipfile.BadZipFile`
  or `OSError`) out of `refresh_snaps`; this is the one failure mode that is
  *not* folded into the `error` field. The disk-gate and download failures
  above are reported; extract failures propagate.
- The downloaded pack ZIP is **retained** at `<dest_dir>/pS_snap_fullset.zip`
  after extraction — `refresh_snaps` does not delete it. The `.zip` and its
  extracted PNGs coexist on disk, which is why the disk-space gate requires
  **2×** the declared pack size free.
- Existing PNG + `force=False` → counted in `files_skipped`, left on disk;
  `force=True` → overwritten and counted in `files_extracted`.
- Non-PNG ZIP entries (READMEs, manifests) → skipped silently.
- ZIP entry with a directory component (`a/b.png`) → skipped; the
  documented layout is flat. The check rejects **any entry containing a
  path separator** (`/` or `\`) — the necessary ingredient of every
  directory-escape — so a **zip-slip** path like `../evil.png` is skipped
  and a malicious archive cannot place files outside `snap/`.

## App self-update

`docs/specs/mame-curator-1010-self-update.md` is the contract; this is the
module's share of it.

- `install_kind()` is `bundle` when frozen, `git` when `bundle_root()` holds
  `.git`, else `package` (INV-1).
- `latest_release(client)` reads GitHub's `releases/latest`; any network
  error, non-200 or unparseable body raises `UpdateCheckError`. An asset's
  `sha256` comes from its `digest` field, and is `None` without one.
- `is_newer(candidate, current)` compares X.Y.Z numerically; a pre-release
  candidate is never newer (INV-2).
- `apply_git_update(repo, *, target, before_move, run)` runs, in `repo`:
  the pre-flight (`git` and `uv` on `PATH`, no modified tracked files),
  `before_move()`, `git fetch`, an ancestry check, `git merge --ff-only`,
  then `uv sync --no-dev --inexact`. A failed sync, or a merge that fails
  after moving `HEAD`, resets to the previous commit and syncs again; the
  result says `rolled_back` and, if the second sync failed too,
  `sync_failed` (INV-5 to INV-8). Where the reset itself fails the result
  says `sync_failed` without `rolled_back`: the tree is on the new commit.
- Every `git` and `uv` call goes through `run` as an argument list with no
  shell (INV-13), with a timeout (`GIT_TIMEOUT_SECONDS`, `UV_TIMEOUT_SECONDS`)
  and `GIT_TERMINAL_PROMPT=0`; a timeout comes back as a failed command. A
  tag reaches git after `--end-of-options`.
- `UpdateError` carries the API's `code` and HTTP `status`:
  `update_tool_missing`, `update_dirty_tree`, `update_fetch_failed`,
  `update_not_fast_forward`, `update_merge_refused`, `update_no_asset`,
  `update_unverifiable`, `update_download_failed`, `update_digest_mismatch`.
  The routes raise the rest.
- `download_bundle` writes `<name>.partial`, hashes it, and renames it into
  place only when the hash equals the asset's digest; every failure leaves
  no file (INV-9).

## Out of scope

- The HTTP download primitive itself — sha256 verification, exponential-
  backoff retry, mirror fallback, atomic write, URL-scheme allowlist, and
  body-size streaming cap all live in `mame_curator/downloads.py`.
- Parsing the downloaded INIs into machine maps — handled by `parser/`.
- CLI wiring of the `refresh-inis` / `refresh-snaps` subcommands (flag
  surface, exit codes, console output) — handled by `cli/`.
- Acquiring the official MAME `-listxml` and the DAT — the wizard / setup
  flow's responsibility, not this module's.
- The update routes, `data/update-state.json`, the activity entries and the
  INI diff preview — `api/routes/updates.py` and `updates_ini.py`
  (see `api/spec.md`).

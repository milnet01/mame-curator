# mame-curator-1010 — Update the app and its INI files from inside it

**Status:** accepted (2026-09-28).
**Kind:** implement.
**Source:** ROADMAP mame-curator-1010 (P12; deferred from P07 on
2026-05-04 with the user's "I do still want self update but that can be
added later").

**Pairs with:** mame-curator-1095 (desktop bundles; §9 of its spec hands
this item the bundle update path and the Updates banner's wording).

**Layman:** Settings → Updates tells you when a newer MAME Curator exists,
shows what changed, and updates it for you; it also previews what new
reference lists would change in your library before you accept them.

## 1. Goal

A user learns about a new release inside the app, reads its notes there,
and takes it with one click: a git clone updates in place with its data
snapshotted first and the code rolled back if anything fails; a desktop
bundle downloads the new release file to where its user will find it
(§4.4). Refreshing the INI
reference files shows which games would join or leave the library before
anything changes, and applies only on confirmation.

## 2. Problem

1. **Nothing checks for updates.** `api/routes/stubs.py::updates_check`
   returns `AppUpdateInfo(current_version=__version__,
   latest_version=None, update_available=False)` and `ini=()` every time,
   and no frontend code requests `/api/updates/check`: `App.tsx` renders
   `<SettingsPage>` without the `updateInfo` prop, so
   `UpdatesTab.tsx`'s banner never shows.
2. **The config's update settings do nothing.** `api/schemas.py::UpdatesConfig`
   declares `channel: Literal["stable", "dev"] = "stable"`,
   `check_on_startup: bool = True` and `ini_check_on_startup: bool = True`.
   The only reader is `api/routes/config.py`, which echoes the section back.
3. **The only update instruction is wrong for bundle users.**
   `strings_internal.ts`'s `updateAvailable` tells the user to `git pull`,
   which someone who downloaded a bundle (mame-curator-1095) cannot do.
4. **INI refresh is blind.** `updates/ini.py::refresh_inis` downloads the
   five INI files over the configured ones through the CLI
   (`cli/commands/refresh_inis.py`), with no preview of how the library
   changes and no way to decline.

## 3. Scope decisions (agreed with the user)

1. **A desktop bundle updates by downloading the new release file into the
   same folder** (on macOS `~/Downloads`, §4.4), then telling the user to
   close this one and open the new one. The old file stays as the fallback. User, 2026-09-28, chosen over
   replacing the running file (uneven across platforms: Windows and macOS
   cannot overwrite a running app) and over only linking to the Releases
   page.
2. **A git clone updates in place**, with a snapshot of the user's files
   first and the code rolled back if the update fails. `docs/design.md`
   § 6.7 decided this on 2026-05-04; the roadmap bullet carries it.
3. **An INI refresh never applies without a preview and a confirmation.**
   `docs/design.md` § 6.7 and `docs/plans/phase-plan.md`'s P12 test list
   (`test_ini_refresh_requires_explicit_confirm`).

## 4. Design

### 4.1 Install kind

New module `src/mame_curator/updates/app.py` (`updates/` may import
`downloads.py` and `_resources.py`, never `api/`):

```python
InstallKind = Literal["git", "bundle", "package"]

def install_kind() -> InstallKind:
    """bundle when frozen; git when bundle_root() holds a .git; else package."""
```

`package` is a `pip install` or any tree without `.git`: it can check but
cannot apply (§4.4).

### 4.2 Checking for a new version

```python
@dataclass(frozen=True)
class ReleaseInfo:
    version: str            # "1.4.0", no leading v
    tag: str                # "v1.4.0"
    notes_markdown: str     # the release body (the CHANGELOG section)
    html_url: str           # the release page
    assets: tuple[ReleaseAsset, ...]

@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    url: str                # browser_download_url
    sha256: str | None      # from the API's "digest": "sha256:<hex>"

async def latest_release(client: httpx.AsyncClient) -> ReleaseInfo:
    """GET https://api.github.com/repos/milnet01/mame-curator/releases/latest.
    Raises UpdateCheckError on a network error, a non-200, or a body that
    does not parse."""

def is_newer(candidate: str, current: str) -> bool:
    """Strictly greater, comparing X.Y.Z numerically. A candidate carrying a
    pre-release suffix (-rc.N) is never newer on the stable channel."""
```

GitHub's `releases/latest` excludes pre-releases and drafts, so the stable
channel never sees a candidate. The API allows 60 unauthenticated requests
an hour per address, so a check result is **cached on `app.state` for one
hour**; `?refresh=true` bypasses the cache.

**The dev channel applies to git installs only**: it compares `HEAD`
with `origin/main` after `git fetch origin main`, and offers an update when
`origin/main` has commits `HEAD` lacks. `latest_version` is then the short
commit id. A bundle or package on the dev channel is checked as stable.

`GET /api/updates/check` replaces the stub. The response widens
`AppUpdateInfo`:

```python
class AppUpdateInfo(BaseModel):          # api/schemas_setup.py
    current_version: str
    latest_version: str | None
    update_available: bool
    install_kind: Literal["git", "bundle", "package"]
    can_apply: bool                      # git or bundle, and an update exists
    notes_html: str | None               # release notes, rendered (§4.5)
    release_url: str | None
    check_error: str | None              # why the check failed; never a 5xx
    restart_pending: bool                # an update was applied; this process predates it
    rollback_available: bool             # git, and data/update-state.json records one
```

`restart_pending` and `rollback_available` come from
`data/update-state.json` (§4.3 step 7). At startup a git install records
`git rev-parse HEAD` as `app.state.started_commit`; restart is pending
while the recorded `to_commit` differs from it, on either channel. A bundle
is never restart-pending: its update is a new file the user opens (§4.4).
`rollback_available` is true while the record holds a `previous_commit`.

`UpdatesCheck.ini` stays `()`: an INI check needs a download (§4.6), so it
is an explicit action, not part of the version check.

### 4.3 Applying on a git clone

`updates/app.py::apply_git_update(repo, *, target, before_move, run)` owns
the steps; `before_move: Callable[[], str]` takes the snapshot and returns
its id, so `updates/` never imports `api/`. The route passes a closure over
`api/persist.py::snapshot_files`, and `run` (default `subprocess.run`) is
the seam the tests replace. `POST /api/updates/apply` on a git install
calls it in a worker thread, holding `app.state.update_lock` (a second
request gets `409 update_in_progress`):

1. **Pre-flight.** `git` and `uv` must resolve on `PATH` (`shutil.which`),
   else `409 update_tool_missing` naming the tool; then `git status
   --porcelain --untracked-files=no` must print nothing, else `409
   update_dirty_tree`. Either way nothing has changed.
2. **Snapshot** `config.yaml`, `overrides.yaml`, `sessions.yaml`,
   `data/notes.json` and `data/state.yaml` into `data/snapshots/` through
   `before_move`, keyed by the bare names `state.yaml` and `notes.json` as
   `snapshot_files` keys the others. Its id goes in the response and in
   `data/update-state.json`. The Settings restore route's targets gain
   `data/state.yaml`, and the route reloads it with `load_review_state` and
   passes it to `replace_world(review_state=)`, so this snapshot restores
   whole. Without the reload the next review-state write would save the
   stale world over the restored file.
3. **Record** `git rev-parse HEAD` as `previous_commit`.
4. **Fetch and fast-forward.** Stable: `git fetch --tags origin` then
   `git merge --ff-only <tag>`. Dev: `git fetch origin main` then
   `git merge --ff-only origin/main`. A failed fetch answers `502
   update_fetch_failed` with git's output. A merge that is not a
   fast-forward answers `409 update_not_fast_forward`; one git refuses for
   another reason, such as an untracked file it would overwrite, answers
   `409 update_merge_refused` with git's output. `HEAD` is unchanged in all
   three (measured 2026-09-28: `git merge --ff-only` over a colliding
   untracked file exits 1 and leaves `HEAD` where it was).
5. **Dependencies.** `uv sync --no-dev --inexact`, the launchers' own form
   (`run.sh`), so dev tools are neither installed nor removed.
6. **Roll back on failure.** If step 4's merge or step 5 fails after the
   tree moved: `git reset --hard <previous_commit>`, then step 5 again, and
   the response says `rolled_back: true` with the failing command's output.
   If that second sync fails too, it also says `sync_failed: true`: the code
   is back, and `run.sh`'s own `uv sync` on the next start repairs the
   environment.
7. **Return** the result with `previous_commit` and `to_commit`
   (`git rev-parse HEAD` after the merge) and `restart_required: true`. The
   route, not `apply_git_update`, then writes `data/update-state.json`
   (`previous_commit`, `to_commit`, `snapshot_id`, `from_version`,
   `to_version`) and appends an `AppUpdatedDetails` activity entry
   (`copy/types.py`), so `updates/` imports neither `copy/` nor a data
   directory. On the dev channel `to_version` is the short commit id, as
   `latest_version` is (§4.2). The running server keeps the old code until
   the user restarts it.

Every `git` and `uv` call is an argument list run with `subprocess.run`
and no shell, with `repo` as its working directory; the route passes
`bundle_root()`.

Apply and rollback both answer:

```python
class UpdateApplyResult(BaseModel):      # api/schemas_setup.py
    install_kind: Literal["git", "bundle"]
    from_version: str
    to_version: str
    rolled_back: bool = False
    sync_failed: bool = False
    restart_required: bool = False
    snapshot_id: str | None = None
    downloaded_path: str | None = None   # bundle only
    output: str | None = None            # the failing command's output
```

`POST /api/updates/rollback` (git only) resets to the `previous_commit` in
`data/update-state.json`, re-runs step 5, and returns
`restart_required: true`; without a recorded `previous_commit` it answers
`409 update_nothing_to_roll_back`. The route then rewrites the record:
`to_commit` becomes the old `previous_commit`, `to_version` the old
`from_version`, and `previous_commit` is removed. So a second rollback is
refused, and restart stays pending until the process runs the restored
commit. It does not restore the snapshot: user files
may have changed since, and Settings → Snapshots already restores one.

### 4.4 Applying on a bundle, and refusing on a package

On a bundle, `POST /api/updates/apply` downloads the release asset for this
platform with `downloads.py::download(url=, dest=, client=)` to a
`.partial` name beside its destination, hashes it, and renames it into
place only when the hash equals the asset's `digest`:

| Platform | Asset | Written to |
|---|---|---|
| Linux | `MAME_Curator-<v>-x86_64.AppImage` | the directory of `$APPIMAGE` (set by the AppImage runtime), then `chmod 0755` |
| Windows | `MAME_Curator-<v>-x86_64.exe` | the directory of `sys.executable` |
| macOS | `MAME_Curator-<v>-<machine>.dmg` | `~/Downloads` (the running app sits in `/Applications`, which may need an administrator) |

The running file is never written to. A release with no matching asset
answers `409 update_no_asset`, and one whose asset carries no `digest`
answers `409 update_unverifiable`; the page then links the release. A
download that fails in transit answers `502 update_download_failed`; a
hash that differs deletes the `.partial` file and answers `502
update_digest_mismatch`. Neither leaves a file behind. On success the
download is recorded in `data/update-state.json` and `downloaded_path`
names it; the page tells the user to close this window and open it.

On a package install, apply answers `409 update_not_supported`; the page
links `release_url` instead.

### 4.5 What's new

`notes_html` is the release body rendered by the Help pages' Markdown
renderer, moved from `api/routes/help.py::_render_markdown` to
`api/markdown.py::render_markdown` so both routes share one. Settings →
Updates opens it in a modal.

### 4.6 INI refresh with a preview

`POST /api/updates/ini/preview` downloads the five INI files
(`updates/ini.py::refresh_inis`) into `data/ini-staging/`, parses them,
builds a new context from the current one —

```python
new_ctx = world.ctx.model_copy(update={
    "category": ..., "languages": ..., "mature": ..., "bestgames_tier": ...,
})
```

— and runs `filter.run_filter(world.machines, new_ctx, world.config.filters,
world.overrides, world.sessions)`. It answers:

```python
class IniPreview(BaseModel):
    changed_files: tuple[str, ...]     # INI names whose bytes differ from the live file
    failed: tuple[tuple[str, str], ...]  # (name, manual-download URL) from INIRefreshReport
    winners_added: tuple[str, ...]     # sorted short names
    winners_removed: tuple[str, ...]   # sorted short names
```

The live INI files and the world are untouched. `POST
/api/updates/ini/apply` requires a staged preview (else `409
ini_preview_missing`), snapshots the live INI files with `snapshot_files`
into `data/ini-snapshots/` — not `data/snapshots/`, which Settings →
Snapshots restores with other targets — moves the staged files onto the
configured `paths.<ini>` (a path left unset gets `data/ini/<name>`, and the
config gains it, as the CLI does, written to disk first), swaps the world
under `world_lock` with `replace_world(base=world, config=new_config,
ctx=new_ctx, rerun_filter=True)` — `replace_world` gains the `ctx`
argument, and a new `ctx` triggers the filter re-run — and appends an
`IniRefreshedDetails` activity entry per changed file.

### 4.7 The page

`UpdatesTab.tsx` gains a **Check now** button, the banner driven by
`/api/updates/check`, a **What's new** button opening `notes_html`, an
action button by install kind (git: **Update**, then "Restart MAME Curator
to finish"; bundle: **Download update**, then the downloaded path; package:
a link to the release), a **Roll back** button when an update is
recorded, and an **INI files** panel (**Preview** → the added and removed
games → **Apply**). A new `useUpdatesCheck` hook calls the check when the
tab opens, and once at app start when `updates.check_on_startup` is true.
When that startup check finds an update, a toast says "Update available:
vX.Y.Z" with a button that opens Settings → Updates, as design § 6.7
promises; a failed or empty check shows nothing.
The `updateAvailable` string stops mentioning `git pull`.

## 5. Invariants

- **INV-1** — `install_kind()` is `bundle` when frozen, `git` when
  `bundle_root()` holds `.git`, else `package`.
  *Test:* `tests/updates/test_app_update.py::test_install_kind`.
  *Breaks when:* a frozen bundle extracted into a directory that happens to
  hold `.git` reports `git` and tries to run `git`.

- **INV-2** — `is_newer` is strict numeric X.Y.Z order, and a pre-release
  candidate is never newer.
  *Test:* `tests/updates/test_app_update.py::test_is_newer`.
  *Breaks when:* versions compare as strings (`1.10.0` < `1.9.0`), or
  `1.4.0-rc.1` is offered as an update from `1.3.0`.

- **INV-3** — A second check within an hour makes no request; `refresh=true`
  makes one.
  *Test:* `tests/api/test_routes_updates.py::test_check_is_cached_for_an_hour`
  (an `httpx.MockTransport` counting requests).
  *Breaks when:* every Settings visit calls GitHub, exhausting the
  60-an-hour limit.

- **INV-4** — A failed check returns 200 with `update_available: false` and
  `check_error` set.
  *Test:* `tests/api/test_routes_updates.py::test_check_failure_is_reported_not_raised`.
  *Breaks when:* a network error or a 403 rate-limit answer surfaces as a
  500 and the Updates tab shows an error toast on every open.

- **INV-5** — A git apply with modified tracked files answers `409
  update_dirty_tree` and changes nothing: no snapshot, no fetch.
  *Test:* `tests/updates/test_git_update.py::test_dirty_tree_refuses_before_anything`
  (a throwaway repository and origin under `tmp_path`).
  *Breaks when:* the pre-flight runs after the snapshot or the fetch.

- **INV-6** — The snapshot exists before the tree moves, and its id is in
  the response.
  *Test:* `tests/updates/test_git_update.py::test_snapshot_precedes_merge`.
  *Breaks when:* the snapshot is taken after the merge, so a failed update
  has nothing to fall back to.

- **INV-7** — A diverged clone answers `409 update_not_fast_forward` with
  `HEAD` unchanged.
  *Test:* `tests/updates/test_git_update.py::test_diverged_clone_is_refused`.
  *Breaks when:* the update merges or rebases the user's local commits.

- **INV-8** — A failing dependency sync after the merge resets `HEAD` to
  `previous_commit` and reports `rolled_back: true`.
  *Test:* `tests/updates/test_git_update.py::test_failed_sync_rolls_back`
  (the sync command injected to fail).
  *Breaks when:* the tree is left on the new code with the old
  dependencies.

- **INV-9** — A bundle apply writes the platform's asset to its §4.4
  destination only after its digest verifies; a mismatch, a missing digest
  or a failed download leaves no file.
  *Test:* `tests/updates/test_bundle_update.py` (`MockTransport` serving an
  asset with a right and a wrong digest).
  *Breaks when:* the running file is overwritten, or an unverified or
  partial download is left where the user will open it.

- **INV-10** — A package install reports `can_apply: false`, and apply
  answers `409 update_not_supported`.
  *Test:* `tests/api/test_routes_updates.py::test_package_install_cannot_apply`.
  *Breaks when:* a pip install runs `git` in `site-packages`.

- **INV-11** — An INI preview leaves the live INI files and the world
  unchanged, and reports the winners that would join and leave.
  *Test:* `tests/api/test_routes_updates_ini.py::test_preview_changes_nothing`
  (a staged `mature.ini` flagging a current winner).
  *Breaks when:* the preview downloads over the live files, as the CLI does.

- **INV-12** — An INI apply without a staged preview answers `409
  ini_preview_missing`; with one, the world's winners become the preview's.
  *Test:* `tests/api/test_routes_updates_ini.py::test_apply_needs_preview_and_matches_it`.
  *Breaks when:* apply downloads afresh, so what is applied is not what was
  previewed.

- **INV-13** — `git` and `uv` run as argument lists with no shell.
  *Test:* `tests/updates/test_git_update.py::test_no_shell` (asserts every
  `subprocess.run` call the seam records has a list and `shell` unset).
  *Breaks when:* a tag or branch name reaches a shell string.

## 6. Failure modes

| Assumption | When it breaks | Result |
|---|---|---|
| GitHub is reachable | offline, blocked, or rate-limited | `check_error` says so; the page offers the Releases link (INV-4) |
| The release carries this platform's asset | a release built without one bundle | `409 update_no_asset`; the page offers the Releases link |
| The API reports a digest | a release without `digest` | `409 update_unverifiable`; the page links the release instead of downloading it |
| `git` and `uv` are on `PATH` | a clone run without them | `409 update_tool_missing` from the pre-flight, naming the tool, before anything changes |
| The user restarts after a git update | they keep the old process running | the old code keeps serving; the banner says a restart is pending |
| `git fetch` reaches origin | offline or refused | `502 update_fetch_failed`; `HEAD` unchanged |
| The fast-forward merge succeeds | an untracked file in the way | `409 update_merge_refused` with git's output; `HEAD` unchanged |
| `uv sync` needs the network | offline after the fetch | the sync fails, the rollback resets the code and re-syncs its lock; if that re-sync fails too, `sync_failed: true` and `run.sh`'s next `uv sync` repairs it (§4.3 step 6) |

## 7. Tests

New files, each seen failing before its code exists:

- `tests/updates/test_app_update.py` — INV-1, INV-2.
- `tests/updates/test_git_update.py` — INV-5, INV-6, INV-7, INV-8, INV-13,
  against a throwaway repository and a bare origin under `tmp_path`.
- `tests/updates/test_bundle_update.py` — INV-9.
- `tests/api/test_routes_updates.py` — INV-3, INV-4, INV-10.
- `tests/api/test_routes_updates_ini.py` — INV-11, INV-12.
- Vitest: `UpdatesTab` renders each install kind's action, the What's new
  modal and the INI preview's lists.

The git tests are POSIX-only (they run `git`), marked
`skipif(sys.platform == "win32")` per
`tests/docs/test_posix_only_tests_skip_on_win32.py`. The DS05 declaration
pins move in the same commits as the tests.

## 8. Alternatives considered (and rejected)

- **Replace the running bundle in place** — uneven: Linux can rename over a
  running AppImage, Windows and macOS cannot overwrite a running app. The
  user chose the download (§3 decision 1).
- **Only link to the Releases page** — the lightest option, and what a
  package install still gets; the user wanted the download done for them.
- **`git pull` for the stable channel** — follows `main`, which carries
  unreleased work; fast-forwarding to the release tag gives the stable
  channel only released code.
- **Restore the snapshot on rollback** — discards user edits made after the
  update; the snapshot stays available through Settings → Snapshots.
- **Streaming progress (SSE) for apply** — the long step is `uv sync`, one
  command; a single request with a spinner shows the same thing with no
  job machinery.

## 9. Out of scope

- Restarting the server automatically after a git update — deferred; not
  yet queued.
- An INI check on startup (`updates.ini_check_on_startup`) — the preview
  downloads five files, so it stays an explicit action; deferred, not yet
  queued.
- Signed bundles and signature checks beyond the release digest — see
  mame-curator-1095 § 9.

## 10. What checks this

| Rule | What catches a breach |
|------|----------------------|
| INV-1 | `tests/updates/test_app_update.py::test_install_kind` |
| INV-2 | `tests/updates/test_app_update.py::test_is_newer` |
| INV-3 | `tests/api/test_routes_updates.py::test_check_is_cached_for_an_hour` |
| INV-4 | `tests/api/test_routes_updates.py::test_check_failure_is_reported_not_raised` |
| INV-5 | `tests/updates/test_git_update.py::test_dirty_tree_refuses_before_anything` |
| INV-6 | `tests/updates/test_git_update.py::test_snapshot_precedes_merge` |
| INV-7 | `tests/updates/test_git_update.py::test_diverged_clone_is_refused` |
| INV-8 | `tests/updates/test_git_update.py::test_failed_sync_rolls_back` |
| INV-9 | `tests/updates/test_bundle_update.py` |
| INV-10 | `tests/api/test_routes_updates.py::test_package_install_cannot_apply` |
| INV-11 | `tests/api/test_routes_updates_ini.py::test_preview_changes_nothing` |
| INV-12 | `tests/api/test_routes_updates_ini.py::test_apply_needs_preview_and_matches_it` |
| INV-13 | `tests/updates/test_git_update.py::test_no_shell` |
| A real update from one release to the next | **nothing** automated — needs two published releases; checked by hand at the first release after this ships |

## 11. Cross-doc impact

- `src/mame_curator/updates/spec.md` — `app.py`'s public surface; the
  layering rule gains `_resources.py`.
- `src/mame_curator/api/spec.md` — the five routes, `replace_world`'s
  `ctx` argument, the new error codes, `api/markdown.py`, and the
  snapshot restore route's targets gaining `data/state.yaml` and its
  reload of review state.
- `frontend/src/api/schemas.ts` + `types.ts` — `AppUpdateInfo`'s new
  fields, `UpdateApplyResult` and `IniPreview`, as
  `check_api_types_sync.py` requires.
- `frontend/src/strings_internal.ts` — the new strings and `byCode`
  entries for each new error code.
- `docs/help/` — a Help page section on updating.
- `CHANGELOG.md` — a user-facing entry.
- `docs/design.md` § 6.7 — the bundle path this spec adds, and the INI
  safety rail "INI refreshes never touch user files" amended: a previewed
  apply may overwrite INIs at their configured `paths.<ini>` and write the
  `config.yaml` path for an unset one, after the snapshot (§4.6).

## 12. Cold-eyes loop log

Rows live in `../reviews/mame-curator-1010-self-update-loop-log.md`.

# mame-curator-1010 — Update the app and its INI files from inside it

**Status:** spec draft (2026-09-28).
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
bundle downloads the new release file next to itself. Refreshing the INI
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
   same folder**, then telling the user to close this one and open the new
   one. The old file stays as the fallback. User, 2026-09-28, chosen over
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
```

`UpdatesCheck.ini` stays `()`: an INI check needs a download (§4.6), so it
is an explicit action, not part of the version check.

### 4.3 Applying on a git clone

`POST /api/updates/apply` on a git install runs these steps in a worker
thread, holding `app.state.update_lock` (a second request gets `409
update_in_progress`):

1. **Pre-flight.** `git status --porcelain --untracked-files=no` must print
   nothing, else `409 update_dirty_tree` and nothing has changed.
2. **Snapshot** `config.yaml`, `overrides.yaml`, `sessions.yaml`,
   `data/notes.json` and `data/state.yaml` with
   `api/persist.py::snapshot_files` into `data/snapshots/`. Its id goes in
   the response and in `data/update-state.json`.
3. **Record** `git rev-parse HEAD` as `previous_commit`.
4. **Fetch and fast-forward.** Stable: `git fetch --tags origin` then
   `git merge --ff-only <tag>`. Dev: `git fetch origin main` then
   `git merge --ff-only origin/main`. A merge that is not a fast-forward
   fails with `409 update_not_fast_forward` and `HEAD` unchanged.
5. **Dependencies.** `uv sync --no-dev --inexact`, the launchers' own form
   (`run.sh`), so dev tools are neither installed nor removed.
6. **Roll back on failure.** If step 4's merge or step 5 fails after the
   tree moved: `git reset --hard <previous_commit>`, then step 5 again, and
   the response says `rolled_back: true` with the failing command's output.
7. **Record success** in `data/update-state.json`
   (`previous_commit`, `snapshot_id`, `from_version`, `to_version`),
   append an `AppUpdatedDetails` activity entry (`copy/types.py`), and
   return `restart_required: true`. The running server keeps the old code
   until the user restarts it.

Every `git` and `uv` call is an argument list run with `subprocess.run`
and no shell, with the repository root (`bundle_root()`) as its working
directory.

`POST /api/updates/rollback` (git only) resets to the `previous_commit` in
`data/update-state.json`, re-runs step 5, and returns
`restart_required: true`; without a recorded update it answers `409
update_nothing_to_roll_back`. It does not restore the snapshot: user files
may have changed since, and Settings → Snapshots already restores one.

### 4.4 Applying on a bundle, and refusing on a package

On a bundle, `POST /api/updates/apply` downloads the release asset for this
platform with `downloads.py::download(url=, dest=, client=, sha256=)`,
which writes atomically and verifies the digest:

| Platform | Asset | Written to |
|---|---|---|
| Linux | `MAME_Curator-<v>-x86_64.AppImage` | the directory of `$APPIMAGE` (set by the AppImage runtime), then `chmod 0755` |
| Windows | `MAME_Curator-<v>-x86_64.exe` | the directory of `sys.executable` |
| macOS | `MAME_Curator-<v>-<machine>.dmg` | `~/Downloads` (the running app sits in `/Applications`, which may need an administrator) |

The running file is never written to. A release with no matching asset
answers `409 update_no_asset`; a digest mismatch answers `502
update_digest_mismatch` and leaves no file behind. The response names the
downloaded path; the page tells the user to close this window and open it.

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
    failed: tuple[tuple[str, str], ...]  # (name, reason) from INIRefreshReport
    winners_added: tuple[str, ...]     # sorted short names
    winners_removed: tuple[str, ...]   # sorted short names
```

The live INI files and the world are untouched. `POST
/api/updates/ini/apply` requires a staged preview (else `409
ini_preview_missing`), snapshots the live INI files with `snapshot_files`,
moves the staged files onto the configured `paths.<ini>` (a path left unset
gets `data/ini/<name>`, and the config gains it, as the CLI does), swaps the
world under `world_lock` with `replace_world(base=world, ctx=new_ctx,
rerun_filter=True)` — `replace_world` gains the `ctx` argument, and a new
`ctx` triggers the filter re-run — and appends an `IniRefreshedDetails`
activity entry per changed file.

### 4.7 The page

`UpdatesTab.tsx` gains a **Check now** button, the banner driven by
`/api/updates/check`, a **What's new** button opening `notes_html`, an
action button by install kind (git: **Update**, then "Restart MAME Curator
to finish"; bundle: **Download update**, then the downloaded path; package:
a link to the release), a **Roll back** button when an update is
recorded, and an **INI files** panel (**Preview** → the added and removed
games → **Apply**). A new `useUpdatesCheck` hook calls the check when the
tab opens, and once at app start when `updates.check_on_startup` is true.
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

- **INV-9** — A bundle apply writes the platform's asset beside the running
  file after its digest verifies, and a mismatch leaves no file.
  *Test:* `tests/updates/test_bundle_update.py` (`MockTransport` serving an
  asset with a right and a wrong digest).
  *Breaks when:* the running file is overwritten, or an unverified download
  is left where the user will open it.

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
| The API reports a digest | an older release without `digest` | the download proceeds unverified and the response says so; the Releases page is the check |
| `git` and `uv` are on `PATH` | a clone run without them | the pre-flight fails with the missing tool named, before anything changes |
| The user restarts after a git update | they keep the old process running | the old code keeps serving; the banner says a restart is pending |
| `uv sync` needs the network | offline after the fetch | the sync fails, the rollback resets the code, and the old dependencies still match it |

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
  `ctx` argument, the new error codes, `api/markdown.py`.
- `frontend/src/api/schemas.ts` + `types.ts` — `AppUpdateInfo`'s new
  fields and `IniPreview`, as `check_api_types_sync.py` requires.
- `frontend/src/strings_internal.ts` — the new strings and `byCode`
  entries for each new error code.
- `docs/help/` — a Help page section on updating.
- `CHANGELOG.md` — a user-facing entry.
- `docs/design.md` § 6.7 — the bundle path this spec adds.

## 12. Cold-eyes loop log

Rows live in `../reviews/mame-curator-1010-self-update-loop-log.md`.

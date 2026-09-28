# mame-curator-1010 self-update — review loop log

Rows for `docs/specs/mame-curator-1010-self-update.md` § 12.

## Cold-eyes loop log

| Loop | Date | Lanes | Q1 | Q2 | Q3 | Q4 | Outcome |
|------|------|-------|----|----|----|----|---------|
| 1 | 2026-09-28 | 2 × review-lane (neutral-lane), every lane held all four questions | 2 | 5 | 3 | 0 | **Verified 10 / fixed 10 / dismissed 0** (most found by both lanes). §4.4's macOS `~/Downloads` against INV-9 and §3's "beside the running file"; §6 downloading unverified against INV-9 (now `409 update_unverifiable`); no `AppUpdateInfo` field for a pending restart or a recorded update (now `restart_pending`, `rollback_available`); `IniPreview.failed` carries a manual-download URL, not a reason; the pre-flight never checked `git`/`uv` exist (now `409 update_tool_missing`); the INI snapshot's folder was unnamed and `data/snapshots/` would reach Settings → Snapshots (now `data/ini-snapshots/`); `data/state.yaml` was snapshotted but no restore target (restore gains it); INI apply patched the config on disk but swapped the world without `config=`; no apply result model, no transport-failure code, and `download()` cannot tell a mismatch from a network failure (now `UpdateApplyResult`, `502 update_download_failed`, the route hashes a `.partial` itself); `updates/` could not own a step that imports `api/persist` (now an injected `before_move`). **An open question led to a real defect in shipped code**: restoring a settings snapshot deleted overrides, sessions and notes — reproduced, fixed and pushed as mame-curator-1130 (9b25e86), outside this document. |

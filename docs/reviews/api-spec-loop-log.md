# Cold-eyes loop log — `src/mame_curator/api/spec.md`

Review history for the api module spec, kept outside the spec because the
spec has never carried a loop log and its standard does not require one.

## Cold-eyes loop log

| Loop | Date | Lanes | Q1 | Q2 | Q3 | Q4 | Outcome |
|------|------|-------|----|----|----|----|---------|
| 1 | 2026-10-19 | 2 | 3 | 0 | 0 | 0 | mame-curator-1131 / 1135 amendment, the `load_app_config` bullet (gated span: 7aede0a). Two lanes, each holding every question; both lanes found both lane findings independently. 3 verified / 0 dismissed; 2 fixed, 1 surfaced. [Q1] orchestrator, at packet build: "so a rollback to older code still starts" fails for an unknown key under `server:`, because `serve`'s `_load_server_config` validates that block with `ServerConfig` (`extra="forbid"`); reproduced as a `ConfigError`. Surfaced to the user: the fix touches code or changes direction. [Q1] both lanes: "The next Settings save writes the file without them" was false for a save that changes nothing, which `patch_config` short-circuits before writing; now "a save that changes a value". [Q1] both lanes: "reads `config.yaml` for `build_world`" named one of four callers; the bullet now names the restore and INI-apply routes and `refresh-snaps`. Four open questions, none became a finding. Loop 2 dispatched. |

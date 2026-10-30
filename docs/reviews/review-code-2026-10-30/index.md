# review-code --small, 2026-10-30

Scope: source changed in `2a255c9...HEAD` (mame-curator-1131 / 1133 / 1135 and PR 3's fixes), read in the context of the functions it touches. Not a full sweep; the `review-code-last` tag was not moved.

Single tier, one pass, each lane dispatched with `~/.claude/tools/neutral-lane` on model claude-opus-5-5.

| Lane | File | Covered | Turns | Cost (USD) | Critical | High | Medium | Low/Info |
|---|---|---|---|---|---|---|---|---|
| 01 api | lane-01-api.md | api/state.py, schemas.py, schemas_copy.py, jobs.py, routes/activity.py, routes/games.py | 19 | 1.07 | 0 | 0 | 1 | 3 + 1 info |
| 02 core library | lane-02-core-library.md | parser/dat.py, filter/picker.py, filter/heuristics.py, copy/runner.py, copy/playlist.py | 15 | 1.01 | 0 | 0 | 2 | 5 + 1 info |
| 03 frontend | lane-03-frontend.md | components/settings/AboutTab.tsx, pages/SettingsPage.tsx, strings_internal.ts | 14 | 0.76 | 0 | 0 | 1 | 1 + 1 info |

Each lane file is the lane's return as it came back.

# mame-curator-1144 guided library — loop log

## Cold-eyes loop log

| Loop | Date | Trigger | Lanes | Q1 | Q2 | Q3 | Q4 | Outcome |
|------|------|---------|-------|----|----|----|----|---------|
| 1 | 2026-10-30 | New draft (armed by 4037c07) | 2 (neutral-lane; each held every question) | 4 | 11 | 2 | 2 | 19 findings, 18 verified / 1 dismissed; 18 fixed. 7 came from the packet pass, 11 from lanes; both lanes found the free-space sign, the exit bounce and the setup-mode flag. Reproduced: a render-time redirect at `/` bounced both exits back to the guide; `run_copy` with APPEND replaced an unreadable playlist (filed as mame-curator-1152). Dismissed: the second `<h1>`; Settings, Stats, Help, Activity and Sessions already carry one beside AppShell's. Open questions settled clean: override carried (`replace_world` reruns the filter on `overrides`); no gate enforces the file-size cap on `LibraryPage.tsx`. Loop 2 dispatched. |

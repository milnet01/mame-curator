# review-code --since dc8bb1c~1, 2026-10-30

Scope: mame-curator-1144, commit dc8bb1c, one commit. Whole non-test files holding a change. `frontend/dist/` is generated and was not reviewed. The `review-code-last` tag was not moved.

Single tier, one pass, each lane dispatched with `~/.claude/tools/neutral-lane` on model claude-opus-5-5.

| Lane | File | Covered | Turns | Cost (USD) | Critical | High | Medium | Low/Info |
|---|---|---|---|---|---|---|---|---|
| 01 guide flow | lane-01-guide-flow.md | GuidePage, components/guide, guideState, fetchGameNames, apiErrorToast, useCopySession, useGames, AbortCopyDialog, strings_guide, strings | 42 | 2.31 | 0 | 1 | 11 | 12 |
| 02 library page | lane-02-library-page.md | LibraryPage, useLibraryController, libraryPageHelpers, libraryView, LibraryFullHeader, SimpleLibraryBar, AbortCopyDialog, CopyModal, FiltersSidebar, useCopySession, useGames | 31 | 2.13 | 0 | 4 | 8 | 11 |
| 03 shell and text size | lane-03-shell-text-size.md | App, main, index.css, AppShell, textSize, guideState, LibraryGrid, AlternativesDrawer | 29 | 2.02 | 0 | 5 | 5 | 6 |

Each lane file is the lane's return as it came back.

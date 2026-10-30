Line counts as read:
- `frontend/src/components/settings/AboutTab.tsx`: 23 lines, read in full.
- `frontend/src/pages/SettingsPage.tsx`: 473 lines, read in full.
- `frontend/src/strings_internal.ts`: I read only lines 30–40 (the `app` block) and 376–390 (`settings.sections` and `settings.about`), as the brief limited. I read them as slices, not with `Read`.

Context present on arrival, before I read the subject:
- the global `~/.claude/CLAUDE.md`, which says the user is partially sighted (your tail says it too)
- the user's email address, from the harness
- the Ants MCP startup-hook text

I had no project `CLAUDE.md`, no memory index and no git snapshot.

## Critical (0)

## High (0)

## Medium (1)

- **[dim 2]** `AboutTab.tsx:8-21` — `<p className="text-sm text-muted-foreground">{strings.app.name} · {strings.app.tagline}</p>` … `<a href={SPONSOR_URL} …>` — **The About tab still shows no version and no licence.** `docs/design.md:552` says the section holds "About (version, license, links)". The new component is now the whole About tab, and it shows only the name, tagline, disclaimer and one link. The old inline block (diff `SettingsPage.tsx` −467..470) had the same gap, so this diff did not cause it. But this diff rewrote the tab and kept the gap.
  - The version is already in reach. `AppUpdateInfo.current_version` is defined at `api/types.ts:520`, and `UpdatesTab.tsx:189` uses it. `SettingsPage` already receives `updateInfo`.
  - **Which side is wrong:** probably the code. Roadmap item 1133 asked only for the support link and the disclaimer, so the doc line may simply be older than the decision. I have put this under Open questions.
  - **Fix:** pass `updateInfo?.current_version` into `AboutTab`. Add a licence line ("MIT") and a link to the licence or the repo.

## Low / Info

- **[dim 12]** `AboutTab.tsx:13-20` — `<a href={SPONSOR_URL} target="_blank" rel="noopener noreferrer" className="self-start text-sm underline">{strings.settings.about.support}</a>` — **The link opens a new tab without saying so**, either on screen or to a screen reader. LOW.
  - WCAG 2.2 technique G201 (warn when a link opens a new window) supports SC 3.2.5, which is level AAA. No level A or AA criterion strictly requires the warning.
  - The link text "Support this project" does not say it leaves the app for a donation page on GitHub. I judge it still passes SC 2.4.4 (Link Purpose, level A) because the tab's context explains it, but the margin is thin.
  - The project's own accessibility bar is `P06-frontend-mvp.md:337`: "Lighthouse ≥ 90 … we do not aim for AA-perfect WCAG until P09".
  - **Fix:** add a string such as `supportNewTab: "(opens GitHub Sponsors in a new tab)"`, rendered as visually hidden text inside the link. Optionally add an external-link icon with `aria-hidden`.
  - I opened three sibling links only to compare the convention: `AboutSection.tsx:28`, `IniRefreshPanel.tsx:89` and `UpdatesTab.tsx:126`. They have the same gap. They are outside this diff and I have not filed them.
- **INFO:** I could not judge focus visibility or colour contrast. That needs the theme and a real browser, which this lane did not have.

## Covered by spec and looks correct

These were opened and checked:
- **[dim 3] Security.** `target="_blank"` is paired with `rel="noopener noreferrer"`, which closes the reverse-tabnabbing hole OWASP describes. It matches the HelpPage sanitizer's rule (`HelpPage.tsx:91-104`). The link's address is a fixed constant, so nothing can be injected into it.
- **[dim 15] Privacy.** The page sends nothing when it renders. GitHub is reached only if the user clicks. `noreferrer` stops the browser telling GitHub the app's local address. A click the user chooses is navigation, not one of the app's own outgoing requests (`design.md:30`, `CLAUDE.md:91`). I did not run the `test_no_telemetry` gate.
- **[dim 2b] No zombie.** `SECTION_KEYS` includes `"about"` (`SettingsPage.tsx:69`), and `TabsContent value="about"` renders `<AboutTab />` (`:467-469`). Both new strings are used. The tab is reachable.
- **[dim 2] Disclaimer wording.** It matches the README Disclaimer (`README.md:163-170`) word for word, as roadmap item 1133's "wording unchanged" requires. The address matches the roadmap and the README badge.
- **Layout.** Removing `className="flex flex-col gap-2"` from `TabsContent` is covered: `AboutTab` supplies its own flex column.
- **The rest:** dims 4, 5, 7, 8, 9, 10, 11, 16 and 17 are N/A, because this is static markup with no state, input, input/output or persisted data. Dim 13 is N/A because the app ships English only (`design.md:31`) and the strings are kept in one file.

## Open questions

- Does `design.md:552`'s "About (version, license, links)" still stand, or did the 2026-09-28 decision behind roadmap item 1133 narrow it? That settles whether the Medium finding is a code fix or a doc fix.
- How strictly does WCAG 2.2 bind here? Your tail names it, but `P06` defers "AA-perfect WCAG" to P09. That decides whether the Low finding is a contract violation or advice.
- Did I go outside the brief? To check claims, I opened parts of `ROADMAP.md`, `README.md`, `CHANGELOG.md`, `design.md`, `HelpPage.tsx` and the three sibling link components. None of my findings are filed against those files.

**Fix first:**
1. **The missing version and licence (Medium).** It is the only gap against a written contract, and the data is already in reach. Settle the doc question first.
2. **Announce the new tab (Low).** It is cheap, and the user is partially sighted. Do it in one pass with the three sibling links so the convention stays the same everywhere.
3. **Check focus and contrast in a real browser.** Neither could be judged from the code, and Settings is one of the pages the Lighthouse gate covers.

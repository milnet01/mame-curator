/**
 * DS02 E1/E2 — AlternativesDrawer + CopyModal are wrapped in ErrorBoundary.
 *
 * At HEAD `LibraryPage.tsx` renders both modals as direct siblings of
 * the page-level ErrorBoundary, not inside one of their own. A render
 * error in either crashes the whole library page (white screen)
 * instead of degrading to a fallback panel scoped to the modal
 * subtree.
 *
 * Per `ErrorBoundary.tsx` doc-comment the project supports three
 * nesting depths (route / drawer / modal). The drawer + modal sites
 * should each carry their own boundary so the failure stays local.
 *
 * Tested as source-text: a full LibraryPage render would mock dozens
 * of hooks for a trivial structural assertion; the existing test set
 * (FP27, DS04 a11y) uses the same source-text approach for
 * structural contracts.
 *
 * Pre-fix: `<AlternativesDrawer …/>` and `<CopyModal …/>` are direct
 * top-level JSX nodes under the page root.
 * Post-fix: each is the only child of an `<ErrorBoundary>` open tag.
 */
import { describe, expect, it } from 'vitest'

import libraryPageSource from '../pages/LibraryPage.tsx?raw'

// Walk back through `text` to the most recent JSX open tag (`<TagName`),
// ignoring closing tags `</…>` and self-closes. Returns the tag name, or
// null when no enclosing open tag precedes the slice.
function findLastJsxOpenTag(text: string): string | null {
  const openTagRe = /<([A-Z][A-Za-z0-9_.]*)\b(?![^>]*\/\s*>)/g
  let lastOpen: RegExpExecArray | null = null
  let m: RegExpExecArray | null
  while ((m = openTagRe.exec(text)) !== null) lastOpen = m
  return lastOpen?.[1] ?? null
}

describe('DS02 E1/E2 — modal ErrorBoundary nesting', () => {
  it('AlternativesDrawer is wrapped in an ErrorBoundary (E1)', () => {
    // Find the first occurrence of `<AlternativesDrawer` and assert the
    // immediately-enclosing JSX open tag is `<ErrorBoundary` — no other
    // JSX open-tag may sit between the boundary and the drawer.
    const drawerIdx = libraryPageSource.indexOf('<AlternativesDrawer')
    expect(drawerIdx, 'AlternativesDrawer is not rendered in LibraryPage').toBeGreaterThan(-1)
    const enclosing = findLastJsxOpenTag(libraryPageSource.slice(0, drawerIdx))
    expect(enclosing, 'no enclosing JSX component found before AlternativesDrawer').not.toBeNull()
    expect(
      enclosing,
      `AlternativesDrawer is enclosed by <${enclosing}>, expected ErrorBoundary`,
    ).toBe('ErrorBoundary')
  })

  it('CopyModal is wrapped in an ErrorBoundary (E2)', () => {
    const modalIdx = libraryPageSource.indexOf('<CopyModal')
    expect(modalIdx, 'CopyModal is not rendered in LibraryPage').toBeGreaterThan(-1)
    const enclosing = findLastJsxOpenTag(libraryPageSource.slice(0, modalIdx))
    expect(enclosing, 'no enclosing JSX component found before CopyModal').not.toBeNull()
    expect(
      enclosing,
      `CopyModal is enclosed by <${enclosing}>, expected ErrorBoundary`,
    ).toBe('ErrorBoundary')
  })

  // R1b: spec § E1/E2 names specific fallback strings — assert they're wired,
  // not the generic boundary fallback.
  it('AlternativesDrawer boundary uses the alternativesFailed fallback string', () => {
    expect(libraryPageSource).toMatch(/strings\.errors\.alternativesFailed/)
  })

  it('CopyModal boundary uses the copyModalFailed fallback string', () => {
    expect(libraryPageSource).toMatch(/strings\.errors\.copyModalFailed/)
  })
})

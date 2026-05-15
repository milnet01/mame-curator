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

describe('DS02 E1/E2 — modal ErrorBoundary nesting', () => {
  it('AlternativesDrawer is wrapped in an ErrorBoundary (E1)', () => {
    // Find the first occurrence of `<AlternativesDrawer` and assert
    // the preceding opening tag is `<ErrorBoundary`. We allow other
    // expression-tree intermediates (parentheses, conditional spread)
    // but require no other JSX open-tag between the boundary and the
    // drawer (i.e. the boundary is the immediate parent).
    const drawerIdx = libraryPageSource.indexOf('<AlternativesDrawer')
    expect(drawerIdx, 'AlternativesDrawer is not rendered in LibraryPage').toBeGreaterThan(-1)
    const before = libraryPageSource.slice(0, drawerIdx)
    // Walk back to the most recent JSX open tag (anything matching
    // `<TagName`) — ignoring closing tags `</…>` and self-closes.
    const openTagRe = /<([A-Z][A-Za-z0-9_.]*)\b(?![^>]*\/\s*>)/g
    let lastOpen: RegExpExecArray | null = null
    let m: RegExpExecArray | null
    while ((m = openTagRe.exec(before)) !== null) lastOpen = m
    expect(lastOpen, 'no enclosing JSX component found before AlternativesDrawer').not.toBeNull()
    expect(
      lastOpen?.[1],
      `AlternativesDrawer is enclosed by <${lastOpen?.[1]}>, expected ErrorBoundary`,
    ).toBe('ErrorBoundary')
  })

  it('CopyModal is wrapped in an ErrorBoundary (E2)', () => {
    const modalIdx = libraryPageSource.indexOf('<CopyModal')
    expect(modalIdx, 'CopyModal is not rendered in LibraryPage').toBeGreaterThan(-1)
    const before = libraryPageSource.slice(0, modalIdx)
    const openTagRe = /<([A-Z][A-Za-z0-9_.]*)\b(?![^>]*\/\s*>)/g
    let lastOpen: RegExpExecArray | null = null
    let m: RegExpExecArray | null
    while ((m = openTagRe.exec(before)) !== null) lastOpen = m
    expect(lastOpen, 'no enclosing JSX component found before CopyModal').not.toBeNull()
    expect(
      lastOpen?.[1],
      `CopyModal is enclosed by <${lastOpen?.[1]}>, expected ErrorBoundary`,
    ).toBe('ErrorBoundary')
  })
})

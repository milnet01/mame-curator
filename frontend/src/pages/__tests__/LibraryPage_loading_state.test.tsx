/**
 * mame-curator-1100 / mame-curator-1102 — pending-query empty states.
 *
 * Both defects share one shape: a component derives its "nothing here"
 * copy from a query result that defaults to an empty array/list before
 * the first response lands (`games.data?.items ?? []` in
 * `useLibraryController.ts`, `alternatives.data?.items ?? []` in
 * `LibraryPage.tsx`), and neither call-site checks the query's pending
 * state before handing that placeholder down. The library grid and the
 * alternatives drawer only know about `cards.length === 0` /
 * `alternatives.length === 1`; they have no loading prop to assert
 * against (`LibraryGrid.test.tsx` and `AlternativesDrawer.test.tsx`
 * exercise both purely by prop, with no loading concept). So the seam
 * these tests exercise is the real one: `LibraryPage` rendered against
 * a mocked API whose relevant response never resolves, same as a user
 * staring at a slow backend.
 *
 * INV-1 (mame-curator-1102): while `/api/games` is pending, the
 *   library grid's empty-state copy ("No games match your filters")
 *   must NOT be on screen.
 * INV-2 (mame-curator-1100): while a game's `/api/games/:name/alternatives`
 *   is pending, the alternatives drawer's zero-family copy ("0 versions
 *   in this family") must NOT be on screen.
 *
 * Pre-fix: both render immediately, because `cards` / `alternatives`
 * default to `[]` with no `isPending`/`isLoading` gate anywhere between
 * the query and the empty-state branch.
 *
 * Regression history: mame-curator-1100 (drawer) / mame-curator-1102
 * (grid), reported 2026-09 against a screenshot taken ~1-2.5s into the
 * real request; no fix is in the tree at the time this test was
 * written.
 */
import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { LibraryPage } from '../LibraryPage'
import { server, http, HttpResponse } from '@/test/handlers'
import { strings } from '@/strings'
import {
  hangingGet,
  libraryPageBaseHandlers,
  makeFakeCart,
  makeGameCard,
  makeGamesPage,
  renderLibraryPageTree,
} from './_libraryPageFixtures'

// jsdom returns 0 for layout sizes; LibraryGrid's virtualizer needs a
// sized scroll element to compute a visible window. Extends the
// `LibraryGrid.test.tsx` stub (clientHeight/clientWidth/getBoundingClientRect)
// with `offsetHeight`/`offsetWidth`: `@tanstack/virtual-core`'s
// `observeElementRect` reads those (not `getBoundingClientRect`) for its
// synchronous initial measurement (`virtual-core/src/index.ts` `getRect`),
// so without them the visible range never leaves `[0, -1]` and no row
// paints — confirmed empirically: LibraryGrid.test.tsx's own "virtualizes
// a 3,000-card fixture" test only ever asserts on the spacer's total
// height for exactly this reason (see its comment) and never asserts a
// card is actually in the DOM. Required only by the drawer scenario
// (INV-2), which must click a rendered card to open the drawer.
const originalDescriptors: {
  clientHeight: PropertyDescriptor | undefined
  clientWidth: PropertyDescriptor | undefined
  offsetHeight: PropertyDescriptor | undefined
  offsetWidth: PropertyDescriptor | undefined
  getBoundingClientRect: typeof HTMLElement.prototype.getBoundingClientRect
} = {
  clientHeight: undefined,
  clientWidth: undefined,
  offsetHeight: undefined,
  offsetWidth: undefined,
  getBoundingClientRect: HTMLElement.prototype.getBoundingClientRect,
}

beforeAll(() => {
  originalDescriptors.clientHeight = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'clientHeight')
  originalDescriptors.clientWidth = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'clientWidth')
  originalDescriptors.offsetHeight = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight')
  originalDescriptors.offsetWidth = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetWidth')
  originalDescriptors.getBoundingClientRect = HTMLElement.prototype.getBoundingClientRect

  Object.defineProperty(HTMLElement.prototype, 'clientHeight', { configurable: true, get: () => 600 })
  Object.defineProperty(HTMLElement.prototype, 'clientWidth', { configurable: true, get: () => 1200 })
  Object.defineProperty(HTMLElement.prototype, 'offsetHeight', { configurable: true, get: () => 600 })
  Object.defineProperty(HTMLElement.prototype, 'offsetWidth', { configurable: true, get: () => 1200 })
  HTMLElement.prototype.getBoundingClientRect = function () {
    return {
      width: 1200, height: 600, top: 0, left: 0, bottom: 600, right: 1200, x: 0, y: 0,
      toJSON: () => ({}),
    } as DOMRect
  }
})

afterAll(() => {
  if (originalDescriptors.clientHeight) {
    Object.defineProperty(HTMLElement.prototype, 'clientHeight', originalDescriptors.clientHeight)
  } else {
    delete (HTMLElement.prototype as unknown as Record<string, unknown>).clientHeight
  }
  if (originalDescriptors.clientWidth) {
    Object.defineProperty(HTMLElement.prototype, 'clientWidth', originalDescriptors.clientWidth)
  } else {
    delete (HTMLElement.prototype as unknown as Record<string, unknown>).clientWidth
  }
  if (originalDescriptors.offsetHeight) {
    Object.defineProperty(HTMLElement.prototype, 'offsetHeight', originalDescriptors.offsetHeight)
  } else {
    delete (HTMLElement.prototype as unknown as Record<string, unknown>).offsetHeight
  }
  if (originalDescriptors.offsetWidth) {
    Object.defineProperty(HTMLElement.prototype, 'offsetWidth', originalDescriptors.offsetWidth)
  } else {
    delete (HTMLElement.prototype as unknown as Record<string, unknown>).offsetWidth
  }
  HTMLElement.prototype.getBoundingClientRect = originalDescriptors.getBoundingClientRect
})

function renderPage() {
  return renderLibraryPageTree(
    <LibraryPage cart={makeFakeCart()} cartExpanded={false} onCartExpandedChange={() => {}} />,
  )
}

describe('LibraryPage — pending-query empty states', () => {
  it('mame-curator-1102: does not show "No games match your filters" while /api/games is pending', async () => {
    server.use(
      ...libraryPageBaseHandlers(),
      // The main games query AND the five FeaturedTilesRow tile-count
      // queries all hit this same path — hang all of them; the
      // assertion only needs the main one to never settle.
      hangingGet('/api/games'),
    )

    renderPage()

    // The grid's own empty-state test (LibraryGrid.test.tsx) proves this
    // copy is real and reachable; it must not appear while the query
    // that feeds `cards` is still in flight (INV-1).
    expect(
      screen.queryByText(strings.library.emptyTitle),
      'empty-state title rendered while /api/games is still pending — cards defaulted to [] before the query settled',
    ).not.toBeInTheDocument()
  })

  it('mame-curator-1100: does not show "0 versions in this family" while the alternatives query is pending', async () => {
    const winner = makeGameCard({ short_name: 'mshvsf', description: 'Marvel Super Heroes vs. Street Fighter' })
    server.use(
      ...libraryPageBaseHandlers(),
      // Games list resolves immediately with one card so it can be
      // clicked open; only the per-game alternatives fetch hangs.
      http.get('/api/games', () => HttpResponse.json(makeGamesPage([winner]))),
      hangingGet('/api/games/:name/alternatives'),
    )
    const user = userEvent.setup()

    renderPage()

    const card = await screen.findByText(winner.description)
    await user.click(card)

    // Drawer is now open with `alternatives.data` still undefined, so
    // `LibraryPage` passes `alternatives.data?.items ?? []` (length 0)
    // down — same shape a real 0-alternatives family would render, which
    // is exactly the bug: "0 versions in this family" reads as an
    // answer, not as "still loading" (INV-2).
    expect(
      screen.queryByText(strings.alternatives.familySummary(0)),
      'drawer showed "0 versions in this family" while the alternatives query is still pending',
    ).not.toBeInTheDocument()
  })
})

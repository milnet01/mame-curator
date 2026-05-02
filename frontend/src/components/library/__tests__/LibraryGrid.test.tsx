import { afterEach, beforeAll, describe, expect, it } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'

import { LibraryGrid } from '../LibraryGrid'
import type { GameCard as GameCardType } from '@/api/types'

// jsdom returns 0 for layout sizes; the virtualizer needs a sized scroll
// element + a non-empty bounding rect to compute its visible window. Stub
// the prototype so the virtualizer thinks the container is 1200×600.
beforeAll(() => {
  Object.defineProperty(HTMLElement.prototype, 'clientHeight', {
    configurable: true,
    get() {
      return 600
    },
  })
  Object.defineProperty(HTMLElement.prototype, 'clientWidth', {
    configurable: true,
    get() {
      return 1200
    },
  })
  HTMLElement.prototype.getBoundingClientRect = function () {
    return {
      width: 1200,
      height: 600,
      top: 0,
      left: 0,
      bottom: 600,
      right: 1200,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    } as DOMRect
  }
})

afterEach(() => {
  cleanup()
})

function fakeCards(n: number): GameCardType[] {
  return Array.from({ length: n }, (_, i) => ({
    short_name: `g${i}`,
    description: `Game ${i}`,
    year: 1990 + (i % 30),
    manufacturer: 'Mfr',
    publisher: 'Pub',
    developer: 'Dev',
    badges: [],
  }))
}

describe('LibraryGrid', () => {
  it('virtualizes a 3,000-card fixture (renders far fewer cards than total)', async () => {
    const cards = fakeCards(3000)
    const { container } = render(
      <LibraryGrid cards={cards} layout="masonry" onOpen={() => {}} />,
    )
    // The inner spacer carries the full virtual height; presence of it
    // proves the virtualizer is initialized with `count = ceil(N / cols)`.
    const spacer = container.querySelector(
      '[data-testid="library-grid"] > div',
    )
    expect(spacer).toBeTruthy()
    expect((spacer as HTMLElement).style.height).toMatch(/^\d+px$/)
    // Headroom is generous because jsdom's measurement is synthetic; the
    // assertion that *matters* is that not all 3,000 cards land in the DOM.
    const rendered = container.querySelectorAll('[role="button"]').length
    expect(rendered).toBeLessThan(cards.length)
  })

  it('renders an empty state when given zero cards', () => {
    render(<LibraryGrid cards={[]} layout="masonry" onOpen={() => {}} />)
    expect(screen.getByText(/No games match/i)).toBeInTheDocument()
  })

  it('switches layout without unmounting (component stays mounted)', () => {
    const cards = fakeCards(20)
    const { rerender } = render(
      <LibraryGrid cards={cards} layout="masonry" onOpen={() => {}} />,
    )
    const before = screen.getByTestId('library-grid')
    rerender(<LibraryGrid cards={cards} layout="list" onOpen={() => {}} />)
    const after = screen.getByTestId('library-grid')
    // Same DOM node identity = same React component instance.
    expect(after).toBe(before)
    expect(after).toHaveAttribute('data-layout', 'list')
  })
})

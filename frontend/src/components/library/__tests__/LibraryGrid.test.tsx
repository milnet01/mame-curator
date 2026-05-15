import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'

import { LibraryGrid } from '../LibraryGrid'
import type { CardsPerRowHint, GameCard as GameCardType } from '@/api/types'

// jsdom returns 0 for layout sizes; the virtualizer needs a sized scroll
// element + a non-empty bounding rect to compute its visible window. Stub
// the prototype so the virtualizer thinks the container is 1200×600.
// DS04 T1.2: capture the original descriptors so afterAll can restore
// them — otherwise the 1200×600 stub leaks into every later test file.
const originalDescriptors: {
  clientHeight: PropertyDescriptor | undefined
  clientWidth: PropertyDescriptor | undefined
  getBoundingClientRect: typeof HTMLElement.prototype.getBoundingClientRect
} = {
  clientHeight: undefined,
  clientWidth: undefined,
  getBoundingClientRect: HTMLElement.prototype.getBoundingClientRect,
}

beforeAll(() => {
  originalDescriptors.clientHeight = Object.getOwnPropertyDescriptor(
    HTMLElement.prototype,
    'clientHeight',
  )
  originalDescriptors.clientWidth = Object.getOwnPropertyDescriptor(
    HTMLElement.prototype,
    'clientWidth',
  )
  originalDescriptors.getBoundingClientRect = HTMLElement.prototype.getBoundingClientRect

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
  HTMLElement.prototype.getBoundingClientRect = originalDescriptors.getBoundingClientRect
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
  it('virtualizes a 3,000-card fixture (spacer carries the full virtual height)', async () => {
    const cards = fakeCards(3000)
    const { container } = render(
      <LibraryGrid cards={cards} layout="masonry" onOpen={() => {}} isInCart={() => false} onAdd={() => {}} />,
    )
    // DS04 T1.14: dropped the prior `<` count check on
    // `container.querySelectorAll('[role="button"]')`. It was
    // tautological — passed at zero rendered cards because the
    // selector matched any nested role=button (theme dropdown, +Add,
    // Sonner controls, etc.), and the virtualizer in jsdom isn't
    // guaranteed to emit cards under synthetic measurement. The
    // load-bearing assertion is below: the inner spacer carries the
    // full virtual height (`count * rowSize`), which proves the
    // virtualizer initialised with `count = ceil(N / cols)`. A
    // regression that disables virtualization or short-changes the
    // count would emit a wrong height.
    const spacer = container.querySelector(
      '[data-testid="library-grid"] > div',
    )
    expect(spacer).toBeTruthy()
    expect((spacer as HTMLElement).style.height).toMatch(/^\d+px$/)
    // For a 3,000-card masonry grid at 5 columns × 280 px row pitch
    // (LAYOUT_DEFAULTS.masonry.rowHeightPx in `LibraryGrid.tsx:36`),
    // the spacer height should be ≈ 168,000 px (well above the 600 px
    // visible viewport stubbed in beforeAll). Anything under
    // 10,000 px (two orders of magnitude below the expected value)
    // means the virtualizer is rendering the whole list inline (no
    // virtualization) or measuring against the wrong source.
    const heightPx = parseInt((spacer as HTMLElement).style.height, 10)
    expect(heightPx).toBeGreaterThan(10_000)
  })

  it('renders an empty state when given zero cards', () => {
    render(<LibraryGrid cards={[]} layout="masonry" onOpen={() => {}} isInCart={() => false} onAdd={() => {}} />)
    expect(screen.getByText(/No games match/i)).toBeInTheDocument()
  })

  it('switches layout without unmounting (component stays mounted)', () => {
    const cards = fakeCards(20)
    const { rerender } = render(
      <LibraryGrid cards={cards} layout="masonry" onOpen={() => {}} isInCart={() => false} onAdd={() => {}} />,
    )
    const before = screen.getByTestId('library-grid')
    rerender(<LibraryGrid cards={cards} layout="list" onOpen={() => {}} isInCart={() => false} onAdd={() => {}} />)
    const after = screen.getByTestId('library-grid')
    // Same DOM node identity = same React component instance.
    expect(after).toBe(before)
    expect(after).toHaveAttribute('data-layout', 'list')
  })

  // DS04 T1.8: three formula tests collapsed to one parametrized table.
  // The grid container's `data-columns` attribute is the deterministic
  // surface (the inline `gridTemplateColumns` style sits on each
  // virtual row, but the virtualizer only emits rows when its
  // measurement fires — best-effort in jsdom). Auto-fill rendered no
  // `data-columns` at all, so testing the attribute proves the
  // drift-fix is gone.
  it.each<['masonry' | 'list', CardsPerRowHint | undefined, string]>([
    ['masonry', undefined, '5'],
    ['masonry', 6, '6'],
    ['masonry', 'auto', '5'],
    ['list', 8, '1'],
  ])(
    'layout=%s hint=%o → data-columns=%s (FP11 § A4/B11)',
    (layout, hint, expected) => {
      const cards = fakeCards(500)
      const { container } = render(
        <LibraryGrid
          cards={cards}
          layout={layout}
          cardsPerRowHint={hint}
          onOpen={() => {}}
          isInCart={() => false}
          onAdd={() => {}}
        />,
      )
      expect(
        container.querySelector('[data-testid="library-grid"]'),
      ).toHaveAttribute('data-columns', expected)
    },
  )
})

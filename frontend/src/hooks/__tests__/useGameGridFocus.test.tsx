import { renderHook, act } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { Virtualizer } from '@tanstack/react-virtual'

import { useGameGridFocus } from '../useGameGridFocus'
import type { GameCard, StateView } from '@/api/types'

function mockCards(n: number): GameCard[] {
  return Array.from({ length: n }, (_, i) => ({
    short_name: `game${i}`,
    description: `Game ${i}`,
    year: 1990,
    manufacturer: null,
    manufacturer_raw: null,
    publisher: null,
    developer: null,
    badges: [],
    bytes: 0,
    parent: `game${i}`,
  })) as GameCard[]
}

function mockVirtualizer(): Virtualizer<HTMLDivElement, Element> {
  return {
    scrollToIndex: vi.fn(),
  } as unknown as Virtualizer<HTMLDivElement, Element>
}

describe('useGameGridFocus — FP21-T preservation', () => {
  it('initialises activeIndex at 0', () => {
    const { result } = renderHook(() =>
      useGameGridFocus(mockCards(10), undefined, 5, mockVirtualizer()),
    )
    expect(result.current.activeIndex).toBe(0)
  })

  it('move() advances activeIndex by delta, clamped to bounds', () => {
    const { result } = renderHook(() =>
      useGameGridFocus(mockCards(10), undefined, 5, mockVirtualizer()),
    )
    act(() => result.current.move(3))
    expect(result.current.activeIndex).toBe(3)
    act(() => result.current.move(100))
    expect(result.current.activeIndex).toBe(9) // clamped to last
    act(() => result.current.move(-100))
    expect(result.current.activeIndex).toBe(0) // clamped to first
  })

  it('clamps activeIndex when cards shrinks below current position', () => {
    const { result, rerender } = renderHook(
      ({ cards }: { cards: GameCard[] }) =>
        useGameGridFocus(cards, undefined, 5, mockVirtualizer()),
      { initialProps: { cards: mockCards(10) } },
    )
    act(() => result.current.move(8))
    expect(result.current.activeIndex).toBe(8)
    rerender({ cards: mockCards(3) })
    expect(result.current.activeIndex).toBe(2)
  })

  it('is a no-op when cards is empty', () => {
    const { result } = renderHook(() =>
      useGameGridFocus([], undefined, 5, mockVirtualizer()),
    )
    expect(result.current.activeIndex).toBe(0)
    act(() => result.current.move(5))
    expect(result.current.activeIndex).toBe(0)
  })
})

describe('useGameGridFocus — focusNextPending (P14 walkthrough)', () => {
  const reviewState: StateView = {
    entries: { game1: 'reviewed', game3: 'skipped' },
  }

  it('skips non-pending games and returns the first pending index', () => {
    const { result } = renderHook(() =>
      useGameGridFocus(mockCards(6), reviewState, 5, mockVirtualizer()),
    )
    // From 0: game0 is pending → 0.
    expect(result.current.focusNextPending(0)).toBe(0)
    // From 1: game1 is reviewed → skip → game2 pending → 2.
    expect(result.current.focusNextPending(1)).toBe(2)
    // From 3: game3 is skipped → skip → game4 pending → 4.
    expect(result.current.focusNextPending(3)).toBe(4)
  })

  it('returns null at end-of-list when nothing pending remains', () => {
    const all: StateView = {
      entries: { game0: 'reviewed', game1: 'reviewed', game2: 'reviewed' },
    }
    const { result } = renderHook(() =>
      useGameGridFocus(mockCards(3), all, 5, mockVirtualizer()),
    )
    expect(result.current.focusNextPending(0)).toBeNull()
  })

  it('is parameterised — caller passes startIndex (no implicit read of activeIndex)', () => {
    const { result } = renderHook(() =>
      useGameGridFocus(mockCards(6), reviewState, 5, mockVirtualizer()),
    )
    // setActive to 1; focusNextPending(2) still starts at 2.
    act(() => result.current.setActive(1))
    expect(result.current.focusNextPending(2)).toBe(2)
  })
})

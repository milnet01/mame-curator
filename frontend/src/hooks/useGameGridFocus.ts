import { useCallback, useEffect, useState } from 'react'
import type { Virtualizer } from '@tanstack/react-virtual'

import type { GameCard as GameCardType, StateView } from '@/api/types'

/**
 * P14 — owns the LibraryGrid roving-tabindex focus that was historically
 * inlined in `LibraryGrid.tsx` (FP21-T pattern). Chunk 9 hoists it into a
 * reusable hook and adds two methods P14 needs:
 *
 *  - `focusNextPending(startIndex)` — walks `cards` from `startIndex`
 *    forward, returning the first index whose state is `pending` (sparse
 *    store: short_name absent from `reviewState.entries`). Returns
 *    `null` at end-of-list. **Always parameterised** — never reads the
 *    current `activeIndex` — because callers that invoke it right after
 *    a state mutation need to skip the just-marked card before its
 *    updated state has propagated to the `cards` array.
 *
 *  - `setActive(idx)` — exported clamped setter for jump-to-index cases
 *    like the walkthrough's "next pending" advance.
 *
 * Existing FP21-T behaviour preserved verbatim: `activeIndex` clamps when
 * `cards.length` shrinks, `move(delta)` updates and scrolls the
 * virtualizer to the new row.
 */
export interface UseGameGridFocusResult {
  activeIndex: number
  move: (delta: number) => void
  setActive: (idx: number) => void
  focusNextPending: (startIndex: number) => number | null
}

export function useGameGridFocus(
  cards: GameCardType[],
  reviewState: StateView | undefined,
  columns: number,
  virtualizer: Virtualizer<HTMLDivElement, Element>,
): UseGameGridFocusResult {
  const [activeIndex, setActiveIndex] = useState(0)
  const cardsLen = cards.length

  // Clamp activeIndex when `cards` shrinks (filter change, pagination).
  useEffect(() => {
    if (activeIndex >= cardsLen && cardsLen > 0) {
      setActiveIndex(cardsLen - 1)
    }
  }, [activeIndex, cardsLen])

  const move = useCallback(
    (delta: number) => {
      setActiveIndex((prev) => {
        const next = Math.max(0, Math.min(cardsLen - 1, prev + delta))
        if (next !== prev) {
          virtualizer.scrollToIndex(Math.floor(next / columns), {
            align: 'auto',
          })
        }
        return next
      })
    },
    [cardsLen, columns, virtualizer],
  )

  const setActive = useCallback(
    (idx: number) => {
      const clamped = Math.max(0, Math.min(cardsLen - 1, idx))
      setActiveIndex(clamped)
      if (cardsLen > 0) {
        virtualizer.scrollToIndex(Math.floor(clamped / columns), { align: 'auto' })
      }
    },
    [cardsLen, columns, virtualizer],
  )

  const focusNextPending = useCallback(
    (startIndex: number): number | null => {
      const entries = reviewState?.entries ?? {}
      for (let i = startIndex; i < cards.length; i++) {
        const card = cards[i]
        if (card && !(card.short_name in entries)) return i
      }
      return null
    },
    [cards, reviewState],
  )

  return { activeIndex, move, setActive, focusNextPending }
}

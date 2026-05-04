import { useState, type KeyboardEvent } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'

import { cn } from '@/lib/utils'

export interface DragReorderListProps {
  /** Accessible name for the list (e.g. "Region priority"). */
  ariaLabel: string
  /** Current items, rendered top-to-bottom in priority order. */
  items: string[]
  /** Called with the next list whenever an item is reordered. */
  onChange: (next: string[]) => void
}

function swap(arr: string[], from: number, to: number): string[] {
  const next = arr.slice()
  ;[next[from], next[to]] = [next[to], next[from]]
  return next
}

// FP13 § D3: the FP12 § Step 1 research contract called for `role="listbox"`
// + `aria-activedescendant`, which is the standard ARIA pattern for a
// single-select keyboard-driven list. After the user elected the simpler
// arrow-button + ArrowUp/ArrowDown reorder model (Karpathy push-back over
// dnd-kit), `role="list"` is the right semantic — this is a static priority
// list whose items are reordered via per-row controls, not a single-select
// listbox. The aria-live region (D2) carries the dynamic announcement that
// `aria-activedescendant` would otherwise provide.
export function DragReorderList({
  ariaLabel,
  items,
  onChange,
}: DragReorderListProps) {
  const [announcement, setAnnouncement] = useState('')

  const move = (from: number, to: number) => {
    if (to < 0 || to >= items.length) return
    const moved = items[from]
    onChange(swap(items, from, to))
    // FP13 § D2: announce moves via an aria-live region so screen-reader
    // users hear that the action took effect. Without this the keyboard
    // reorder is silent to AT — failure mode flagged in FP12 closing review.
    setAnnouncement(
      `Moved ${moved} to position ${to + 1} of ${items.length}.`,
    )
  }

  const onKeyDown = (event: KeyboardEvent<HTMLLIElement>, index: number) => {
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      move(index, index - 1)
    } else if (event.key === 'ArrowDown') {
      event.preventDefault()
      move(index, index + 1)
    }
  }

  return (
    <>
      <ul
        role="list"
        aria-label={ariaLabel}
        className="flex flex-col gap-1"
      >
        {/* FP13 § E4: `key={item}` keeps React reconciliation stable across
            reorder so focus survives the swap (important since this list is
            keyboard-driven). The contract is that items are unique; callers
            (today only `region_priority`, fed via `ChipListEditor` and
            server-validated config) enforce uniqueness upstream. */}
        {items.map((item, i) => {
          const isFirst = i === 0
          const isLast = i === items.length - 1
          return (
            <li
              key={item}
              tabIndex={0}
              onKeyDown={(e) => onKeyDown(e, i)}
              className="flex items-center justify-between gap-2 rounded border border-input bg-muted/30 px-2 py-1 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <span>{item}</span>
              <div className="flex gap-1">
                <button
                  type="button"
                  aria-label={`Move ${item} up`}
                  disabled={isFirst}
                  onClick={() => move(i, i - 1)}
                  className={cn(
                    'rounded p-0.5 hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                    isFirst && 'opacity-40',
                  )}
                >
                  <ChevronUp size={14} aria-hidden="true" />
                </button>
                <button
                  type="button"
                  aria-label={`Move ${item} down`}
                  disabled={isLast}
                  onClick={() => move(i, i + 1)}
                  className={cn(
                    'rounded p-0.5 hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                    isLast && 'opacity-40',
                  )}
                >
                  <ChevronDown size={14} aria-hidden="true" />
                </button>
              </div>
            </li>
          )
        })}
      </ul>
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {announcement}
      </div>
    </>
  )
}

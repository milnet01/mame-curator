import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { GameCard } from './GameCard'
import { strings } from '@/strings'
import { cn } from '@/lib/utils'
import type {
  CardsPerRowHint,
  GameCard as GameCardType,
  LayoutName,
} from '@/api/types'

interface LibraryGridProps {
  cards: GameCardType[]
  layout: LayoutName
  groupKey?: 'genre' | 'year' | 'publisher'
  /** UiConfig.cards_per_row_hint — `'auto'` falls back to the layout default. */
  cardsPerRowHint?: CardsPerRowHint
  onOpen: (card: GameCardType) => void
  isInCart: (shortName: string) => boolean
  onAdd: (shortName: string) => void
}

/**
 * Per-layout default column count + row-height target. The auto-fill
 * Tailwind pattern was previously used (`grid-cols-[repeat(auto-fill,
 * minmax(180px,1fr))]`) but FP11 § A4 caught it — the actual rendered
 * column count was decoupled from the virtualization math, so wide
 * viewports clipped cards inside 280px slots and narrow viewports
 * left huge gaps. Now: explicit `repeat(${columns}, 1fr)` so DOM
 * layout matches the row-bucket bookkeeping exactly.
 */
const LAYOUT_DEFAULTS: Record<
  LayoutName,
  { columns: number; rowHeightPx: number }
> = {
  masonry: { columns: 5, rowHeightPx: 280 },
  covers: { columns: 3, rowHeightPx: 360 },
  list: { columns: 1, rowHeightPx: 96 },
  grouped: { columns: 5, rowHeightPx: 280 },
}

function resolveColumns(
  layout: LayoutName,
  hint: CardsPerRowHint | undefined,
): number {
  // `list` is always 1; the hint doesn't apply.
  if (layout === 'list') return 1
  if (hint === undefined || hint === 'auto') return LAYOUT_DEFAULTS[layout].columns
  return hint
}

export function LibraryGrid({
  cards,
  layout,
  cardsPerRowHint,
  onOpen,
  isInCart,
  onAdd,
}: LibraryGridProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const columns = resolveColumns(layout, cardsPerRowHint)
  const { rowHeightPx } = LAYOUT_DEFAULTS[layout]
  const rowCount = Math.ceil(cards.length / columns)

  const virtualizer = useVirtualizer({
    count: rowCount,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => rowHeightPx,
    overscan: 4,
  })

  const rows = useMemo(() => {
    const out: GameCardType[][] = []
    for (let i = 0; i < cards.length; i += columns) {
      out.push(cards.slice(i, i + columns))
    }
    return out
  }, [cards, columns])

  // FP21-T: roving-tabindex grid navigation. `activeIndex` is the index
  // into `cards`; arrow keys / j / k move it; Enter / o open. The
  // virtualizer scrolls the active row into view when activeIndex
  // crosses a row boundary outside the visible window.
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
        // Scroll the new row into view via the virtualizer.
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

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      switch (e.key) {
        case 'ArrowDown':
        case 'j':
          e.preventDefault()
          move(columns)
          break
        case 'ArrowUp':
        case 'k':
          e.preventDefault()
          move(-columns)
          break
        case 'ArrowRight':
          e.preventDefault()
          move(1)
          break
        case 'ArrowLeft':
          e.preventDefault()
          move(-1)
          break
        case 'Home':
          e.preventDefault()
          setActiveIndex(0)
          virtualizer.scrollToIndex(0)
          break
        case 'End':
          e.preventDefault()
          setActiveIndex(Math.max(0, cardsLen - 1))
          virtualizer.scrollToIndex(Math.max(0, rowCount - 1))
          break
        case 'Enter':
        case 'o': {
          const card = cards[activeIndex]
          if (card) {
            e.preventDefault()
            onOpen(card)
          }
          break
        }
      }
    },
    [activeIndex, cards, cardsLen, columns, move, onOpen, rowCount, virtualizer],
  )

  if (cards.length === 0) {
    return (
      <div
        data-testid="library-grid"
        data-layout={layout}
        className="flex h-full flex-col items-center justify-center gap-2 p-8 text-center"
      >
        <p className="text-lg font-medium">{strings.library.emptyTitle}</p>
        <p className="max-w-md text-sm text-muted-foreground">
          {strings.library.emptyHint}
        </p>
      </div>
    )
  }

  return (
    <div
      ref={scrollRef}
      data-testid="library-grid"
      data-layout={layout}
      data-columns={columns}
      role="grid"
      aria-rowcount={rowCount}
      aria-colcount={columns}
      aria-label={strings.library.gridLabel}
      tabIndex={-1}
      onKeyDown={onKeyDown}
      className="h-full overflow-auto focus:outline-none"
    >
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          position: 'relative',
        }}
      >
        {virtualizer.getVirtualItems().map((virtualRow) => {
          const rowCards = rows[virtualRow.index] ?? []
          const rowStartIndex = virtualRow.index * columns
          return (
            <div
              key={virtualRow.key}
              role="row"
              aria-rowindex={virtualRow.index + 1}
              data-index={virtualRow.index}
              className={cn('absolute left-0 top-0 grid w-full gap-3 px-3')}
              style={{
                transform: `translateY(${virtualRow.start}px)`,
                height: `${rowHeightPx}px`,
                gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))`,
              }}
            >
              {rowCards.map((card, colIdx) => {
                const cardIndex = rowStartIndex + colIdx
                const isActive = cardIndex === activeIndex
                return (
                  <div
                    key={card.short_name}
                    role="gridcell"
                    aria-colindex={colIdx + 1}
                    tabIndex={isActive ? 0 : -1}
                    data-active={isActive || undefined}
                  >
                    <GameCard
                      card={card}
                      inCart={isInCart(card.short_name)}
                      onOpen={() => onOpen(card)}
                      onAdd={onAdd}
                    />
                  </div>
                )
              })}
            </div>
          )
        })}
      </div>
    </div>
  )
}

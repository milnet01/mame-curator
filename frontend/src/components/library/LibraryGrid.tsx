import { useMemo, useRef } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { GameCard } from './GameCard'
import { strings } from '@/strings'
import { cn } from '@/lib/utils'
import type { GameCard as GameCardType, LayoutName } from '@/api/types'

interface LibraryGridProps {
  cards: GameCardType[]
  layout: LayoutName
  groupKey?: 'genre' | 'year' | 'publisher'
  onOpen: (card: GameCardType) => void
}

/** Per-layout column count + row height. List layout is single-column dense. */
const LAYOUT_GEOMETRY: Record<
  LayoutName,
  { columns: number; rowHeightPx: number }
> = {
  masonry: { columns: 5, rowHeightPx: 280 },
  covers: { columns: 3, rowHeightPx: 360 },
  list: { columns: 1, rowHeightPx: 96 },
  grouped: { columns: 5, rowHeightPx: 280 },
}

export function LibraryGrid({
  cards,
  layout,
  onOpen,
}: LibraryGridProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const { columns, rowHeightPx } = LAYOUT_GEOMETRY[layout]
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
      className="h-full overflow-auto"
    >
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          position: 'relative',
        }}
      >
        {virtualizer.getVirtualItems().map((virtualRow) => {
          const rowCards = rows[virtualRow.index] ?? []
          return (
            <div
              key={virtualRow.key}
              data-index={virtualRow.index}
              className={cn(
                'absolute left-0 top-0 grid w-full gap-3 px-3',
                layout === 'list' && 'grid-cols-1',
                layout === 'masonry' && 'grid-cols-[repeat(auto-fill,minmax(180px,1fr))]',
                layout === 'covers' && 'grid-cols-[repeat(auto-fill,minmax(280px,1fr))]',
                layout === 'grouped' &&
                  'grid-cols-[repeat(auto-fill,minmax(180px,1fr))]',
              )}
              style={{
                transform: `translateY(${virtualRow.start}px)`,
                height: `${rowHeightPx}px`,
              }}
            >
              {rowCards.map((card) => (
                <GameCard
                  key={card.short_name}
                  card={card}
                  onOpen={() => onOpen(card)}
                />
              ))}
            </div>
          )
        })}
      </div>
    </div>
  )
}

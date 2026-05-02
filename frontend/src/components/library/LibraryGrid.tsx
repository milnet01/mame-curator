import { useMemo, useRef } from 'react'
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
              className={cn('absolute left-0 top-0 grid w-full gap-3 px-3')}
              style={{
                transform: `translateY(${virtualRow.start}px)`,
                height: `${rowHeightPx}px`,
                gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))`,
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

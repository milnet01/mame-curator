import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'
// FP24-GG: FeaturedTile / FeaturedTileQuery hoisted into strings.ts
// so the catalogue and this component share one type definition.
import { strings, type FeaturedTile, type FeaturedTileQuery } from '@/strings'

export type { FeaturedTile, FeaturedTileQuery }

interface FeaturedTilesRowProps {
  // FP24-Z: each value may be undefined while the per-tile count
  // query is in flight, so the label can suppress until real data
  // arrives instead of flashing "0 games".
  counts: Record<string, number | undefined>
  activeTileId: string | null
  onTileSelect: (tileId: string) => void
}

/**
 * P15 § 4.2 — horizontal scroll of curated INI-derived tiles.
 *
 * Tile catalogue lives in strings.library.featured.tiles (code-
 * defined, one-PR-per-edit). Counts are supplied by the parent
 * (LibraryPage) which fans out one /api/games?…&page_size=0
 * query per tile; react-query 5min staleness keeps the cost down.
 *
 * Click filters the grid to the tile's query; CartBar morphs to
 * show "Add all N" (where N is the post-filter total). Click DOES
 * NOT auto-add to cart (D8: preview-before-add is safer).
 */
export function FeaturedTilesRow({
  counts,
  activeTileId,
  onTileSelect,
}: FeaturedTilesRowProps) {
  return (
    <section className="px-4 py-3" aria-label={strings.library.featured.heading}>
      <h2 className="mb-2 text-sm font-semibold">
        {strings.library.featured.heading}
      </h2>
      <div className="flex gap-2 overflow-x-auto pb-2">
        {strings.library.featured.tiles.map((tile) => {
          const count = counts[tile.id]
          const isActive = activeTileId === tile.id
          return (
            <button
              key={tile.id}
              type="button"
              // FP24-P: explicit aria-label — the implicit accessible
              // name was the concatenated text of the inner <p>s, which
              // produced strings like "Capcom ClassicsCapcom CPS-1...
              // 38 games" with no separators. The title alone is the
              // useful identifier for AT users.
              aria-label={tile.title}
              aria-pressed={isActive}
              onClick={() => onTileSelect(tile.id)}
              className="shrink-0 text-left"
            >
              <Card
                className={cn(
                  'flex w-40 flex-col gap-1 p-3 transition-shadow hover:shadow-lg',
                  isActive && 'ring-2 ring-ring',
                )}
              >
                <p className="text-sm font-semibold leading-tight">{tile.title}</p>
                <p className="text-xs text-muted-foreground">{tile.description}</p>
                {count !== undefined && (
                  <p className="mt-auto text-xs tabular-nums text-muted-foreground">
                    {strings.library.featured.countLabel(count)}
                  </p>
                )}
              </Card>
            </button>
          )
        })}
      </div>
    </section>
  )
}

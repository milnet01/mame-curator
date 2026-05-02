import { useState } from 'react'
import { LibraryGrid } from '@/components/library/LibraryGrid'
import { LayoutSwitcher } from '@/components/library/LayoutSwitcher'
import { ThemeSwitcher } from '@/components/library/ThemeSwitcher'
import {
  FiltersSidebar,
  type FilterSidebarState,
} from '@/components/library/FiltersSidebar'
import { ActionBar } from '@/components/library/ActionBar'
import { ErrorBoundary } from '@/components/layout/ErrorBoundary'
import { useGames, type GamesQuery } from '@/hooks/useGames'
import { useConfig, useConfigPatch } from '@/hooks/useConfig'
import type { GameCard, LayoutName, ThemeName } from '@/api/types'

const DEFAULT_FILTERS: FilterSidebarState = {
  search: '',
  yearRange: [1975, 2025],
  onlyContested: false,
  onlyOverridden: false,
  onlyChdMissing: false,
  onlyBiosMissing: false,
}

export function LibraryPage() {
  const [filters, setFilters] = useState<FilterSidebarState>(DEFAULT_FILTERS)
  const config = useConfig()
  const patch = useConfigPatch()

  const layout = (config.data?.ui.layout ?? 'masonry') as LayoutName
  const theme = (config.data?.ui.theme ?? 'dark') as ThemeName

  const query: GamesQuery = {
    page: 1,
    pageSize: 200,
    search: filters.search,
    yearFrom: filters.yearRange[0],
    yearTo: filters.yearRange[1],
    onlyContested: filters.onlyContested,
    onlyOverridden: filters.onlyOverridden,
    onlyChdMissing: filters.onlyChdMissing,
    onlyBiosMissing: filters.onlyBiosMissing,
  }
  const games = useGames(query)
  const cards: GameCard[] = games.data?.items ?? []
  const total = games.data?.total ?? 0
  const totalBytes = 0 // wired in a follow-up via useStats

  const handleLayout = (next: LayoutName) => {
    // FP11 § B2: gate on `config.data` so a click before the GET
    // resolves no-ops instead of crashing on `config.data!.ui`.
    if (!config.data) return
    patch.mutate({ ui: { ...config.data.ui, layout: next } })
  }
  const handleTheme = (next: ThemeName) => {
    if (!config.data) return
    patch.mutate({ ui: { ...config.data.ui, theme: next } })
  }

  return (
    <div className="grid h-full grid-cols-[16rem_1fr] grid-rows-[auto_1fr_auto]">
      <aside className="row-span-2">
        <FiltersSidebar
          value={filters}
          onChange={setFilters}
          onSaveSession={() => {
            // Wired to R11 in FP11 § B8 (App.tsx + container hooks).
          }}
        />
      </aside>

      <header className="flex items-center justify-end gap-2 border-b px-4 py-2">
        <LayoutSwitcher value={layout} onChange={handleLayout} />
        <ThemeSwitcher value={theme} onChange={handleTheme} />
      </header>

      <ErrorBoundary>
        <LibraryGrid
          cards={cards}
          layout={layout}
          cardsPerRowHint={config.data?.ui.cards_per_row_hint}
          onOpen={() => {
            // AlternativesDrawer wiring lands in FP11 § B6 follow-up.
          }}
        />
      </ErrorBoundary>

      <div className="col-span-2">
        <ActionBar
          gameCount={total}
          totalSizeBytes={totalBytes}
          biosDepCount={0}
          onDryRun={() => {
            /* Dry-run modal wiring follow-up. */
          }}
          onCopy={() => {
            /* Copy modal wiring follow-up. */
          }}
        />
      </div>
    </div>
  )
}

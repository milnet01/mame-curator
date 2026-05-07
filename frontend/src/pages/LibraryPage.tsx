import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'
import { useQueries } from '@tanstack/react-query'
import { AlternativesDrawer } from '@/components/alternatives/AlternativesDrawer'
import { LibraryGrid } from '@/components/library/LibraryGrid'
import { LayoutSwitcher } from '@/components/library/LayoutSwitcher'
import { ListxmlBanner } from '@/components/library/ListxmlBanner'
import { ThemeSwitcher } from '@/components/library/ThemeSwitcher'
import {
  FiltersSidebar,
  type FilterSidebarState,
} from '@/components/library/FiltersSidebar'
import { CartBar } from '@/components/library/CartBar'
import { CartPanel } from '@/components/library/CartPanel'
import { CopyModal } from '@/components/library/CopyModal'
import { DryRunModal } from '@/components/library/DryRunModal'
import { OnboardingBanner } from '@/components/library/OnboardingBanner'
import { FeaturedTilesRow } from '@/components/library/FeaturedTilesRow'
import { ErrorBoundary } from '@/components/layout/ErrorBoundary'
import { useAlternatives, useLaunchGame, useOverride } from '@/hooks/useAlternatives'
import type { UseCartResult } from '@/hooks/useCart'
import { useCopySession } from '@/hooks/useCopySession'
import { useDryRun } from '@/hooks/useDryRun'
import { useFacets } from '@/hooks/useFacets'
import { useGames, type GamesQuery } from '@/hooks/useGames'
import { useValidateCart } from '@/hooks/useValidateCart'
import { useConfig, useConfigPatch } from '@/hooks/useConfig'
import { useSessions, useSessionUpsert } from '@/hooks/useSessions'
import { useSetupCheck } from '@/hooks/useSetupCheck'
import { toastApiError } from '@/lib/apiErrorToast'
import { strings } from '@/strings'
import { GamesPageSchema, type GamesPage } from '@/api/types'
import type { DryRunReport, GameCard, LayoutName, Session, ThemeName } from '@/api/types'

const DEFAULT_FILTERS: FilterSidebarState = {
  search: '',
  yearRange: [1975, 2025],
  letter: null,
  genre: null,
  publisher: null,
  developer: null,
  onlyContested: false,
  onlyOverridden: false,
  onlyChdMissing: false,
  onlyBiosMissing: false,
}

// Module-level helper so useQueries queryFn doesn't close over any reactive
// deps — tile objects are `as const` so they're stable references.
async function fetchTileCount(tile: (typeof strings.library.featured.tiles)[number]): Promise<GamesPage> {
  const p = new URLSearchParams({ page: '1', page_size: '1' })
  if (tile.query.publisher) p.set('publisher', tile.query.publisher)
  if (tile.query.developer) p.set('developer', tile.query.developer)
  if (tile.query.genre) p.set('genre', tile.query.genre)
  if (tile.query.yearFrom) p.set('year_min', String(tile.query.yearFrom))
  if (tile.query.yearTo) p.set('year_max', String(tile.query.yearTo))
  const r = await fetch(`/api/games?${p}`)
  if (!r.ok) throw new Error(`tile count ${tile.id}: HTTP ${r.status}`)
  return GamesPageSchema.parse(await r.json())
}

interface LibraryPageProps {
  cart: UseCartResult
}

export function LibraryPage({ cart }: LibraryPageProps) {
  const [filters, setFilters] = useState<FilterSidebarState>(DEFAULT_FILTERS)
  const [openedShortName, setOpenedShortName] = useState<string | null>(null)
  const [dryRunReport, setDryRunReport] = useState<DryRunReport | null>(null)
  const [activeTileId, setActiveTileId] = useState<string | null>(null)
  const [cartExpanded, setCartExpanded] = useState(false)

  const config = useConfig()
  const patch = useConfigPatch()
  const sessions = useSessions()
  const upsertSession = useSessionUpsert()
  const alternatives = useAlternatives(openedShortName)
  const override = useOverride()
  const launch = useLaunchGame()
  const facets = useFacets()
  const setupCheck = useSetupCheck()
  const dryRun = useDryRun()
  const validateCart = useValidateCart()
  const copySession = useCopySession()

  const layout = (config.data?.ui.layout ?? 'masonry') as LayoutName
  const theme = (config.data?.ui.theme ?? 'dark') as ThemeName
  const activeSession = sessions.data?.active ?? null

  const query: GamesQuery = {
    page: 1,
    pageSize: 200,
    search: filters.search,
    yearFrom: filters.yearRange[0],
    yearTo: filters.yearRange[1],
    letter: filters.letter ?? undefined,
    genre: filters.genre ?? undefined,
    publisher: filters.publisher ?? undefined,
    developer: filters.developer ?? undefined,
    onlyContested: filters.onlyContested,
    onlyOverridden: filters.onlyOverridden,
    onlyChdMissing: filters.onlyChdMissing,
    onlyBiosMissing: filters.onlyBiosMissing,
  }
  const games = useGames(query)
  const cards: GameCard[] = games.data?.items ?? []
  const total = games.data?.total ?? 0

  // Fan out one count query per featured tile. useQueries keeps hook count
  // fixed (Rules of Hooks); tiles array is `as const` so length is stable.
  const tileQueries = useQueries({
    queries: strings.library.featured.tiles.map((tile) => ({
      queryKey: ['games', 'tile-count', tile.id],
      queryFn: () => fetchTileCount(tile),
      staleTime: 5 * 60 * 1000,
    })),
  })
  const tileCounts: Record<string, number> = Object.fromEntries(
    strings.library.featured.tiles.map((tile, idx) => [
      tile.id,
      (tileQueries[idx].data as GamesPage | undefined)?.total ?? 0,
    ]),
  )

  const openedWinner = useMemo<GameCard | null>(
    () => (openedShortName ? (cards.find((c) => c.short_name === openedShortName) ?? null) : null),
    [openedShortName, cards],
  )

  const handleLayout = (next: LayoutName) => {
    if (!config.data) return
    patch.mutate({ ui: { ...config.data.ui, layout: next } })
  }
  const handleTheme = (next: ThemeName) => {
    if (!config.data) return
    patch.mutate({ ui: { ...config.data.ui, theme: next } })
  }

  const handleTileSelect = (tileId: string) => {
    const tile = strings.library.featured.tiles.find((t) => t.id === tileId)
    if (!tile) return
    if (activeTileId === tileId) {
      setActiveTileId(null)
      setFilters(DEFAULT_FILTERS)
      return
    }
    setActiveTileId(tileId)
    setFilters({
      ...DEFAULT_FILTERS,
      publisher: tile.query.publisher ?? null,
      developer: tile.query.developer ?? null,
      genre: tile.query.genre ?? null,
      yearRange: [
        tile.query.yearFrom ?? DEFAULT_FILTERS.yearRange[0],
        tile.query.yearTo ?? DEFAULT_FILTERS.yearRange[1],
      ],
    })
  }

  const handleBulkAdd = () => cart.addAll(cards.map((c) => c.short_name))

  // P15: dry-run reads from cart.items (with chosenVariant substitution).
  const handleDryRun = () => {
    if (cart.items.length === 0) return
    dryRun.mutate(
      {
        selected_names: cart.items.map((i) => i.chosenVariant ?? i.shortName),
        conflict_strategy: 'CANCEL',
        append_decisions: {},
      },
      { onSuccess: setDryRunReport, onError: toastApiError },
    )
  }

  const handleCopy = () => {
    if (cart.items.length === 0) return
    validateCart.mutate(
      { short_names: cart.items.map((i) => i.shortName) },
      {
        onSuccess: ({ existing, missing }) => {
          if (missing.length > 0) {
            toast.warning(strings.library.cart.validateDroppedToast(missing.length))
            for (const name of missing) cart.remove(name)
          }
          if (existing.length === 0) return
          const variantBySrc = new Map(cart.items.map((i) => [i.shortName, i.chosenVariant ?? i.shortName]))
          copySession.start({
            selected_names: existing.map((s) => variantBySrc.get(s) ?? s),
            conflict_strategy: 'CANCEL',
            append_decisions: {},
          })
        },
        onError: toastApiError,
      },
    )
  }

  // Cart auto-clear on terminal copy state, per config.ui.cart_clear_on_copy.
  useEffect(() => {
    const policy = config.data?.ui.cart_clear_on_copy ?? 'on_success'
    const st = copySession.state?.state
    if (st === 'finished' && policy !== 'never') { cart.clear(); copySession.reset() }
    else if (st === 'aborted' && policy === 'always') { cart.clear(); copySession.reset() }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [copySession.state?.state, config.data?.ui.cart_clear_on_copy])

  const handleSaveSession = (name: string) => {
    if (!config.data) return
    const session: Session = {
      include_year_range: filters.yearRange,
      include_genres: config.data.filters.preferred_genres,
      include_publishers: config.data.filters.preferred_publishers,
      include_developers: config.data.filters.preferred_developers,
    }
    upsertSession.mutate(
      { name, session },
      { onSuccess: () => toast.success(strings.library.sessionSaved(name)), onError: toastApiError },
    )
  }

  return (
    <div className="grid h-full grid-cols-[16rem_1fr] grid-rows-[auto_1fr_auto]">
      <aside className="row-span-2 overflow-y-auto">
        <FiltersSidebar
          value={filters}
          onChange={setFilters}
          onSaveSession={handleSaveSession}
          facets={facets.data}
        />
      </aside>

      <header className="flex items-center justify-end gap-2 border-b px-4 py-2">
        <Link
          to="/sessions"
          className="rounded border bg-muted/50 px-2 py-1 text-xs text-muted-foreground hover:bg-muted"
          title={activeSession ? strings.library.activeSessionTitle(activeSession) : strings.library.noActiveSessionTitle}
        >
          {activeSession ? strings.library.activeSessionPill(activeSession) : strings.library.noActiveSessionPill}
        </Link>
        <LayoutSwitcher value={layout} onChange={handleLayout} />
        <ThemeSwitcher value={theme} onChange={handleTheme} />
      </header>

      <div className="flex flex-col overflow-hidden">
        <OnboardingBanner cartHasItems={cart.items.length > 0} />
        <FeaturedTilesRow
          counts={tileCounts}
          activeTileId={activeTileId}
          onTileSelect={handleTileSelect}
        />
        <ListxmlBanner
          exists={setupCheck.data?.reference_files.listxml.exists}
          cloneofMapSize={setupCheck.data?.cloneof_map_size}
        />
        <ErrorBoundary>
          <LibraryGrid
            cards={cards}
            layout={layout}
            cardsPerRowHint={config.data?.ui.cards_per_row_hint}
            isInCart={(s) => cart.has(s)}
            onAdd={(s) => cart.add(s)}
            onOpen={(card) => setOpenedShortName(card.short_name)}
          />
        </ErrorBoundary>
      </div>

      {openedWinner && (
        <AlternativesDrawer
          open={openedShortName !== null}
          onOpenChange={(o) => !o && setOpenedShortName(null)}
          winner={openedWinner}
          alternatives={alternatives.data?.items ?? []}
          onOverride={(req) => {
            override.mutate(req, {
              onSuccess: () => {
                // P15 § 5.2 — cart-aware variant tracking.
                if (cart.has(req.parent)) cart.setVariant(req.parent, req.winner)
                toast.success(strings.library.overrideApplied)
                setOpenedShortName(null)
              },
              onError: toastApiError,
            })
          }}
          onLaunch={(short) => {
            launch.mutate(short, {
              onSuccess: () => toast.success(strings.alternatives.launchSuccess(short)),
              onError: toastApiError,
            })
          }}
          launching={launch.isPending}
        />
      )}

      {dryRunReport && (
        <DryRunModal
          open={true}
          onOpenChange={(open) => !open && setDryRunReport(null)}
          report={dryRunReport}
          onConfirm={() => setDryRunReport(null)}
        />
      )}

      {copySession.state && (
        <CopyModal
          open={true}
          onOpenChange={(open) => !open && copySession.reset()}
          state={copySession.state}
          onPause={copySession.pause}
          onResume={copySession.resume}
          onAbort={copySession.abort}
          onResolveConflict={copySession.resolveConflict}
        />
      )}

      <div className="col-span-2">
        <CartPanel
          open={cartExpanded}
          items={cart.items}
          onRemove={cart.remove}
          onClearAll={cart.clear}
        />
        <CartBar
          itemCount={cart.items.length}
          totalSizeBytes={games.data?.total_bytes ?? 0}
          bulkAddTotal={activeTileId !== null ? total : null}
          expanded={cartExpanded}
          onBulkAdd={handleBulkAdd}
          onToggleExpand={() => setCartExpanded((x) => !x)}
          onDryRun={handleDryRun}
          onCopy={handleCopy}
        />
      </div>
    </div>
  )
}

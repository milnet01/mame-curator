import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'
import { useQueries } from '@tanstack/react-query'
import { AlternativesDrawer } from '@/components/alternatives/AlternativesDrawer'
import { LibraryErrorPanel } from '@/components/library/LibraryErrorPanel'
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
import { ConfirmationDialog } from '@/components/ConfirmationDialog'
import { ErrorBoundary } from '@/components/layout/ErrorBoundary'
import { useAlternatives, useLaunchGame, useOverride } from '@/hooks/useAlternatives'
import { MAX_CART_SIZE, type UseCartResult } from '@/hooks/useCart'
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
import { apiRequest } from '@/api/client'
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
//
// FP24-U: routed through apiRequest (typed errors, schema validation,
// envelope decoding) per coding-standards § 4 "no raw fetch in
// components."
//
// FP24-HH: page_size=1 (not the spec's "0") because the backend caps
// page_size at `Query(50, ge=1, le=500)`. Only the envelope's `total`
// field matters here; the 1-row payload is acceptable overhead. A
// future "?count_only=true" parameter would let us drop the items
// payload entirely.
async function fetchTileCount(tile: (typeof strings.library.featured.tiles)[number]): Promise<GamesPage> {
  const p = new URLSearchParams({ page: '1', page_size: '1' })
  if (tile.query.publisher) p.set('publisher', tile.query.publisher)
  if (tile.query.developer) p.set('developer', tile.query.developer)
  if (tile.query.genre) p.set('genre', tile.query.genre)
  if (tile.query.yearFrom) p.set('year_min', String(tile.query.yearFrom))
  if (tile.query.yearTo) p.set('year_max', String(tile.query.yearTo))
  return apiRequest<GamesPage>(`/api/games?${p}`, GamesPageSchema)
}

interface LibraryPageProps {
  cart: UseCartResult
  // FP24-C: cart panel state is owned by ShellWithPalette so the navbar
  // Cart button can open the panel from any route.
  cartExpanded: boolean
  onCartExpandedChange: (next: boolean) => void
}

export function LibraryPage({ cart, cartExpanded, onCartExpandedChange }: LibraryPageProps) {
  const [filters, setFilters] = useState<FilterSidebarState>(DEFAULT_FILTERS)
  const [openedShortName, setOpenedShortName] = useState<string | null>(null)
  const [dryRunReport, setDryRunReport] = useState<DryRunReport | null>(null)
  const [activeTileId, setActiveTileId] = useState<string | null>(null)
  // FP24-O: Clear-all is destructive (cart has no undo) — coding-
  // standards § 4 mandates AlertDialog confirm for destructive ops.
  const [clearAllOpen, setClearAllOpen] = useState(false)

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
  // FP24-V: stable refs so downstream useMemo/useEffect deps don't
  // re-run on every render. games.data flips reference on each fetch
  // resolution; the inner items/total references are already stable
  // per react-query's cached result.
  const cards: GameCard[] = useMemo(
    () => games.data?.items ?? [],
    [games.data],
  )
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
  // FP24-Z: omit `?? 0` so still-loading tiles surface as `undefined`
  // and FeaturedTilesRow's `count !== undefined` guard suppresses the
  // count label until the query lands. Otherwise tiles flash a
  // misleading "0 games" before the real number paints.
  const tileCounts: Record<string, number | undefined> = Object.fromEntries(
    strings.library.featured.tiles.map((tile, idx) => [
      tile.id,
      (tileQueries[idx].data as GamesPage | undefined)?.total,
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

  // FP24-LL: toggling a tile off must NOT wipe non-tile-driven filter
  // state (search box, letter, the various "only X" toggles). Reset
  // only the fields the tile owns (publisher / developer / genre /
  // yearRange) — everything else stays put.
  const handleTileSelect = (tileId: string) => {
    const tile = strings.library.featured.tiles.find((t) => t.id === tileId)
    if (!tile) return
    if (activeTileId === tileId) {
      setActiveTileId(null)
      setFilters((prev) => ({
        ...prev,
        publisher: null,
        developer: null,
        genre: null,
        yearRange: DEFAULT_FILTERS.yearRange,
      }))
      return
    }
    setActiveTileId(tileId)
    setFilters((prev) => ({
      ...prev,
      publisher: tile.query.publisher ?? null,
      developer: tile.query.developer ?? null,
      genre: tile.query.genre ?? null,
      yearRange: [
        tile.query.yearFrom ?? DEFAULT_FILTERS.yearRange[0],
        tile.query.yearTo ?? DEFAULT_FILTERS.yearRange[1],
      ],
    }))
  }

  // FP24-M + S: handleBulkAdd promises "Add all N" where N is the
  // filter-result total — but the loaded `cards` slice is at most one
  // page (pageSize=200). Iterate the same filter at the backend's
  // page_size=500 cap until we've covered `total`, then `addAll`.
  // Surfaces MAX_CART_SIZE truncation as a toast so the user knows
  // some items didn't fit.
  const handleBulkAdd = async () => {
    const PAGE_SIZE = 500
    const collected: string[] = []
    const targetTotal = Math.min(total, MAX_CART_SIZE)
    let page = 1
    while (collected.length < targetTotal) {
      const pageQuery: GamesQuery = { ...query, page, pageSize: PAGE_SIZE }
      const params = new URLSearchParams()
      params.set('page', String(pageQuery.page))
      params.set('page_size', String(pageQuery.pageSize))
      if (pageQuery.search) params.set('q', pageQuery.search)
      if (pageQuery.yearFrom) params.set('year_min', String(pageQuery.yearFrom))
      if (pageQuery.yearTo) params.set('year_max', String(pageQuery.yearTo))
      if (pageQuery.letter) params.set('letter', pageQuery.letter)
      if (pageQuery.genre) params.set('genre', pageQuery.genre)
      if (pageQuery.publisher) params.set('publisher', pageQuery.publisher)
      if (pageQuery.developer) params.set('developer', pageQuery.developer)
      if (pageQuery.onlyContested) params.set('only_contested', '1')
      if (pageQuery.onlyOverridden) params.set('only_overridden', '1')
      if (pageQuery.onlyChdMissing) params.set('only_chd_missing', '1')
      if (pageQuery.onlyBiosMissing) params.set('only_bios_missing', '1')
      let pageData: GamesPage
      try {
        pageData = await apiRequest<GamesPage>(`/api/games?${params}`, GamesPageSchema)
      } catch (err) {
        toastApiError(err)
        return
      }
      collected.push(...pageData.items.map((c) => c.short_name))
      if (pageData.items.length === 0) break
      page += 1
    }
    const { truncated } = cart.addAll(collected)
    if (truncated > 0) {
      toast.warning(strings.library.cart.maxCartReachedToast(MAX_CART_SIZE))
    }
  }

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
  // FP24-T: cart and copySession.reset are stable useCallback refs out of
  // useCart / useCopySession, so omitting them from the dep array is
  // intentional — including them would re-run this effect on every cart
  // mutation (cart.clear changes identity if cart re-renders) and the
  // policy logic only wants to react to copy-state and policy changes.
  useEffect(() => {
    const policy = config.data?.ui.cart_clear_on_copy ?? 'on_success'
    const st = copySession.state?.state
    if (st === 'finished' && policy !== 'never') { cart.clear(); copySession.reset() }
    else if (st === 'aborted' && policy === 'always') { cart.clear(); copySession.reset() }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [copySession.state?.state, config.data?.ui.cart_clear_on_copy])

  // FP24-G: surface the localStorage-unavailable state as a toast so
  // the user knows their cart won't persist. Toast fires once on the
  // false → true edge; the hook keeps the flag latched for the rest
  // of the session so subsequent cart edits don't re-toast.
  useEffect(() => {
    if (cart.isStorageBroken) {
      toast.warning(strings.library.cart.storageUnavailableToast)
    }
  }, [cart.isStorageBroken])

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
      <aside aria-label={strings.a11y.filtersLandmark} className="row-span-2 overflow-y-auto">
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
          {(() => {
            // FP20-I: query failure surfaces as an inline alert with a
            // Retry affordance; the FP20-G global toast already flashed
            // at error time, but it dismisses — this panel keeps the
            // failure visible until the user retries.
            //
            // FP26-V: keep the panel mounted while a refetch FROM an
            // errored state is in flight. React Query v5 resets
            // `isError` to false during refetch (so the prior `{games.
            // isError ? ...}` ternary unmounted the panel mid-retry —
            // FP25-H's `disabled={isFetching}` / "Retrying…" affordance
            // never reached the user's screen). `errorUpdatedAt >
            // dataUpdatedAt` tells us the last completed settle was an
            // error, so we sticky-render the panel through the refetch
            // window; once the refetch resolves successfully,
            // dataUpdatedAt moves ahead and the grid takes over.
            const lastSettleWasError =
              (games.errorUpdatedAt ?? 0) > (games.dataUpdatedAt ?? 0)
            const showErrorPanel =
              games.isError || (games.isFetching && lastSettleWasError)
            return showErrorPanel ? (
              <LibraryErrorPanel
                onRetry={() => games.refetch()}
                isFetching={games.isFetching}
              />
            ) : (
              <LibraryGrid
                cards={cards}
                layout={layout}
                cardsPerRowHint={config.data?.ui.cards_per_row_hint}
                isInCart={(s) => cart.has(s)}
                onAdd={(s) => cart.add(s)}
                onOpen={(card) => setOpenedShortName(card.short_name)}
              />
            )
          })()}
        </ErrorBoundary>
      </div>

      {openedWinner && (
        <ErrorBoundary
          resetKey={openedShortName}
          fallback={(error, retry) => (
            <div
              role="alert"
              className="flex flex-col items-center gap-2 rounded border border-destructive/40 bg-destructive/10 p-4 text-sm"
            >
              <p className="font-semibold">{strings.errors.alternativesFailed}</p>
              <p className="text-xs text-muted-foreground">{error.message}</p>
              <button
                type="button"
                onClick={retry}
                className="rounded border bg-background px-3 py-1 text-xs hover:bg-muted"
              >
                {strings.common.retry}
              </button>
            </div>
          )}
        >
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
            retroarchConfigured={setupCheck.data?.retroarch_configured}
          />
        </ErrorBoundary>
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
        <ErrorBoundary
          fallback={(error, retry) => (
            <div
              role="alert"
              className="flex flex-col items-center gap-2 rounded border border-destructive/40 bg-destructive/10 p-4 text-sm"
            >
              <p className="font-semibold">{strings.errors.copyModalFailed}</p>
              <p className="text-xs text-muted-foreground">{error.message}</p>
              <button
                type="button"
                onClick={retry}
                className="rounded border bg-background px-3 py-1 text-xs hover:bg-muted"
              >
                {strings.common.retry}
              </button>
            </div>
          )}
        >
          <CopyModal
            open={true}
            onOpenChange={(open) => !open && copySession.reset()}
            state={copySession.state}
            onPause={copySession.pause}
            onResume={copySession.resume}
            onAbort={copySession.abort}
          />
        </ErrorBoundary>
      )}

      <div className="col-span-2">
        <CartPanel
          open={cartExpanded}
          items={cart.items}
          onRemove={cart.remove}
          onClearAll={() => setClearAllOpen(true)}
        />
        <ConfirmationDialog
          open={clearAllOpen}
          onOpenChange={setClearAllOpen}
          title={strings.library.cart.clearAllConfirm.title}
          description={strings.library.cart.clearAllConfirm.description(cart.items.length)}
          actionLabel={strings.library.cart.clearAllConfirm.action(cart.items.length)}
          onConfirm={() => cart.clear()}
          destructive
        />
        <CartBar
          itemCount={cart.items.length}
          bulkAddTotal={activeTileId !== null ? total : null}
          expanded={cartExpanded}
          onBulkAdd={handleBulkAdd}
          onToggleExpand={() => onCartExpandedChange(!cartExpanded)}
          onDryRun={handleDryRun}
          onCopy={handleCopy}
          // FP24-N: lock Copy + Dry-run while a copy is queued so a
          // double-click can't fire validate+start twice.
          copyDisabled={validateCart.isPending || copySession.state !== null}
        />
      </div>
    </div>
  )
}

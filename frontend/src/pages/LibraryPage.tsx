import { Link } from 'react-router'
import { toast } from 'sonner'
import { AlternativesDrawer } from '@/components/alternatives/AlternativesDrawer'
import { LibraryErrorPanel } from '@/components/library/LibraryErrorPanel'
import { LibraryGrid } from '@/components/library/LibraryGrid'
import { LayoutSwitcher } from '@/components/library/LayoutSwitcher'
import { ListxmlBanner } from '@/components/library/ListxmlBanner'
import { ThemeSwitcher } from '@/components/library/ThemeSwitcher'
import { FiltersSidebar } from '@/components/library/FiltersSidebar'
import { CartBar } from '@/components/library/CartBar'
import { CartPanel } from '@/components/library/CartPanel'
import { CopyModal } from '@/components/library/CopyModal'
import { DryRunModal } from '@/components/library/DryRunModal'
import { OnboardingBanner } from '@/components/library/OnboardingBanner'
import { FeaturedTilesRow } from '@/components/library/FeaturedTilesRow'
import { ConfirmationDialog } from '@/components/ConfirmationDialog'
import { ErrorBoundary } from '@/components/layout/ErrorBoundary'
import { type UseCartResult } from '@/hooks/useCart'
import { toastApiError } from '@/lib/apiErrorToast'
import { strings } from '@/strings'
import { WALKTHROUGH_KEY } from './libraryPageHelpers'
import { useLibraryController } from './useLibraryController'

interface LibraryPageProps {
  cart: UseCartResult
  // FP24-C: cart panel state is owned by ShellWithPalette so the navbar
  // Cart button can open the panel from any route.
  cartExpanded: boolean
  onCartExpandedChange: (next: boolean) => void
}

export function LibraryPage({ cart, cartExpanded, onCartExpandedChange }: LibraryPageProps) {
  // mame-curator-1077: all non-render logic lives in useLibraryController
  // (state, data hooks, derived values, handlers, effects). The JSX
  // below is intentionally kept in this file so the source-text
  // structural tests keep asserting against the page's rendered shape.
  const {
    filters,
    setFilters,
    openedShortName,
    setOpenedShortName,
    dryRunReport,
    setDryRunReport,
    activeTileId,
    walkthrough,
    setWalkthrough,
    reviewState,
    setReviewState,
    clearReviewState,
    clearAllOpen,
    setClearAllOpen,
    config,
    facets,
    activeSession,
    alternatives,
    override,
    launch,
    setupCheck,
    validateCart,
    copySession,
    layout,
    theme,
    cards,
    total,
    tileCounts,
    openedWinner,
    games,
    handleLayout,
    handleTheme,
    handleTileSelect,
    handleBulkAdd,
    handleDryRun,
    handleCopy,
    handleSaveSession,
  } = useLibraryController(cart)

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
        {/* P14 — progress chip + walkthrough toggle. */}
        {(() => {
          const totalSlice = cards.length
          const entries = reviewState.data?.entries ?? {}
          const handled = cards.reduce(
            (n, c) => n + (c.short_name in entries ? 1 : 0),
            0,
          )
          const pct = totalSlice === 0 ? '0' : ((handled / totalSlice) * 100).toFixed(1)
          return (
            <span
              data-testid="library-progress-chip"
              className="rounded border bg-muted/50 px-2 py-1 text-xs text-muted-foreground"
            >
              {strings.library.progressChip(handled, totalSlice, pct)}
            </span>
          )
        })()}
        <label className="flex items-center gap-1 rounded border bg-muted/50 px-2 py-1 text-xs text-muted-foreground">
          <input
            type="checkbox"
            data-testid="library-walkthrough-toggle"
            checked={walkthrough}
            onChange={(e) => {
              setWalkthrough(e.target.checked)
              try {
                localStorage.setItem(WALKTHROUGH_KEY, String(e.target.checked))
              } catch {
                /* localStorage unavailable; in-memory state still updates. */
              }
            }}
          />
          {strings.library.walkthroughToggle}
        </label>
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
                reviewState={reviewState.data}
                walkthrough={walkthrough}
                onSetReviewState={(shortName, state) =>
                  setReviewState.mutate({ short_name: shortName, state })
                }
                onClearReviewState={(shortName) => clearReviewState.mutate(shortName)}
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
            reviewState={reviewState.data}
            onSetReviewState={(shortName, state) =>
              setReviewState.mutate({ short_name: shortName, state })
            }
            onClearReviewState={(shortName) => clearReviewState.mutate(shortName)}
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

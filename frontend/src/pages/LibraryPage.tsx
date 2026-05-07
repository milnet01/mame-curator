import { useMemo, useState } from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'
import { AlternativesDrawer } from '@/components/alternatives/AlternativesDrawer'
import { LibraryGrid } from '@/components/library/LibraryGrid'
import { LayoutSwitcher } from '@/components/library/LayoutSwitcher'
import { ListxmlBanner } from '@/components/library/ListxmlBanner'
import { ThemeSwitcher } from '@/components/library/ThemeSwitcher'
import {
  FiltersSidebar,
  type FilterSidebarState,
} from '@/components/library/FiltersSidebar'
import { ActionBar } from '@/components/library/ActionBar'
import { DryRunModal } from '@/components/library/DryRunModal'
import { ErrorBoundary } from '@/components/layout/ErrorBoundary'
import { useAlternatives, useLaunchGame, useOverride } from '@/hooks/useAlternatives'
import { useDryRun } from '@/hooks/useDryRun'
import { useFacets } from '@/hooks/useFacets'
import { useGames, type GamesQuery } from '@/hooks/useGames'
import { useConfig, useConfigPatch } from '@/hooks/useConfig'
import { useSessions, useSessionUpsert } from '@/hooks/useSessions'
import { useSetupCheck } from '@/hooks/useSetupCheck'
import { toastApiError } from '@/lib/apiErrorToast'
import { strings } from '@/strings'
import type {
  DryRunReport,
  GameCard,
  LayoutName,
  Session,
  ThemeName,
} from '@/api/types'

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

export function LibraryPage() {
  const [filters, setFilters] = useState<FilterSidebarState>(DEFAULT_FILTERS)
  const [openedShortName, setOpenedShortName] = useState<string | null>(null)
  // FP23: stash the dry-run report so the modal renders against it; cleared
  // on close. Null = modal closed.
  const [dryRunReport, setDryRunReport] = useState<DryRunReport | null>(null)
  const config = useConfig()
  const patch = useConfigPatch()
  const sessions = useSessions()
  const upsertSession = useSessionUpsert()
  const alternatives = useAlternatives(openedShortName)
  const override = useOverride()
  const launch = useLaunchGame()
  const facets = useFacets()
  // FP23: surface listxml-availability so the banner above the grid can warn
  // the user when parent/clone collapse can't run (per ADR-0002 fallback).
  const setupCheck = useSetupCheck()
  const dryRun = useDryRun()

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
  const totalBytes = 0 // wired in a follow-up via useStats

  // FP16 § B: AlternativesDrawer needs the *winner* card (the one the user
  // clicked) plus the alternatives list. We resolve `winner` from the
  // current page of cards by short_name; if the click target left the page
  // (filters changed in the meantime) the drawer falls back to the first
  // alternative as the displayed winner so it never shows null.
  const openedWinner = useMemo<GameCard | null>(() => {
    if (openedShortName === null) return null
    return cards.find((c) => c.short_name === openedShortName) ?? null
  }, [openedShortName, cards])

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

  // FP23: wire the previously no-op onDryRun handler. Sends the current
  // filter result (cards' short_names) to /api/copy/dry-run; on success,
  // opens DryRunModal with the returned report. P15 will swap the
  // selected_names source from `cards` to `cart.items` — modal contract
  // unchanged so this hook keeps working.
  const handleDryRun = () => {
    dryRun.mutate(
      {
        selected_names: cards.map((c) => c.short_name),
        conflict_strategy: 'CANCEL',
        append_decisions: {},
      },
      {
        onSuccess: setDryRunReport,
        onError: toastApiError,
      },
    )
  }

  // FP15 § A: fix LibraryPage:65's `onSaveSession` no-op stub.
  // A session captures: the visible year range from the sidebar +
  // the "preferred" picker chip-lists configured in Settings → Picker.
  // Empty preferred_* lists save as empty arrays (valid Session shape;
  // session focuses on year range only).
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
      {
        onSuccess: () => toast.success(strings.library.sessionSaved(name)),
        onError: toastApiError,
      },
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
        {/* FP15 § B: active-session pill — visible answer to "am I in
            a session right now?". Click navigates to /sessions for
            switch / deactivate / delete. The "No active session" link
            tells first-time users where saved sessions live. */}
        <Link
          to="/sessions"
          className="rounded border bg-muted/50 px-2 py-1 text-xs text-muted-foreground hover:bg-muted"
          title={
            activeSession
              ? strings.library.activeSessionTitle(activeSession)
              : strings.library.noActiveSessionTitle
          }
        >
          {activeSession
            ? strings.library.activeSessionPill(activeSession)
            : strings.library.noActiveSessionPill}
        </Link>
        <LayoutSwitcher value={layout} onChange={handleLayout} />
        <ThemeSwitcher value={theme} onChange={handleTheme} />
      </header>

      <div className="flex flex-col overflow-hidden">
        {/* FP23: banner only renders when listxml is missing (exists=false);
            loading and present-state both suppress it. */}
        <ListxmlBanner exists={setupCheck.data?.reference_files.listxml.exists} />
        <ErrorBoundary>
          <LibraryGrid
            cards={cards}
            layout={layout}
            cardsPerRowHint={config.data?.ui.cards_per_row_hint}
            onOpen={(card) => setOpenedShortName(card.short_name)}
          />
        </ErrorBoundary>
      </div>

      {/* FP16 § B: AlternativesDrawer wiring (FP11 § B6 stub never landed).
          The drawer mounts only when a game is selected — keeps the
          alternatives query disabled in the common closed state.
          FP19: onLaunch spawns RetroArch via POST /api/games/{name}/launch. */}
      {openedWinner && (
        <AlternativesDrawer
          open={openedShortName !== null}
          onOpenChange={(o) => !o && setOpenedShortName(null)}
          winner={openedWinner}
          alternatives={alternatives.data?.items ?? []}
          onOverride={(req) => {
            override.mutate(req, {
              onSuccess: () => {
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

      {/* FP23: DryRunModal shows the report returned from /api/copy/dry-run.
          onConfirm is intentionally a no-op + close for FP23 — full Copy
          lifecycle wiring (SSE, conflict resolution) lands in P15 alongside
          the cart-driven input swap. */}
      {dryRunReport && (
        <DryRunModal
          open={true}
          onOpenChange={(open) => !open && setDryRunReport(null)}
          report={dryRunReport}
          onConfirm={() => {
            toast.message(strings.library.dryRunConfirmDeferred)
            setDryRunReport(null)
          }}
        />
      )}

      <div className="col-span-2">
        <ActionBar
          gameCount={total}
          totalSizeBytes={totalBytes}
          biosDepCount={0}
          onDryRun={handleDryRun}
          onCopy={() => {
            /* P15: full Copy lifecycle wiring with cart input. */
          }}
        />
      </div>
    </div>
  )
}

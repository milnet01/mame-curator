import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useSearchParams,
} from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Toaster } from '@/components/ui/sonner'
import { AppShell } from '@/components/layout/AppShell'
import { ThemeProvider } from '@/components/layout/ThemeProvider'
import { ErrorBoundary } from '@/components/layout/ErrorBoundary'
import { CmdKPalette, type CmdKItem } from '@/components/CmdKPalette'
import { ConfirmationDialog } from '@/components/ConfirmationDialog'
import {
  useConfig,
  useConfigExport,
  useConfigImport,
  useConfigPatch,
  useSnapshotRestore,
  useSnapshots,
} from '@/hooks/useConfig'
import {
  useSessions,
  useSessionActivate,
  useSessionDeactivate,
  useSessionDelete,
} from '@/hooks/useSessions'
import { useActivity } from '@/hooks/useActivity'
import { useStats } from '@/hooks/useStats'
import { useHelpIndex, useHelpTopic } from '@/hooks/useHelp'
import { useKeyboard } from '@/hooks/useKeyboard'
import { useSetupCheck } from '@/hooks/useSetupCheck'
import { strings } from '@/strings'
import { ApiError } from '@/api/client'
import type { ConfigExportBundle, ThemeName } from '@/api/types'

const LibraryPage = lazy(() =>
  import('@/pages/LibraryPage').then((m) => ({ default: m.LibraryPage })),
)
const SessionsPage = lazy(() =>
  import('@/pages/SessionsPage').then((m) => ({ default: m.SessionsPage })),
)
const ActivityPage = lazy(() =>
  import('@/pages/ActivityPage').then((m) => ({ default: m.ActivityPage })),
)
const StatsPage = lazy(() =>
  import('@/pages/StatsPage').then((m) => ({ default: m.StatsPage })),
)
const SettingsPage = lazy(() =>
  import('@/pages/SettingsPage').then((m) => ({ default: m.SettingsPage })),
)
const HelpPage = lazy(() =>
  import('@/pages/HelpPage').then((m) => ({ default: m.HelpPage })),
)

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1 },
  },
})

const PALETTE_ITEMS: CmdKItem[] = [
  { id: 'go-library', section: 'actions', label: 'Go to Library', value: 'nav:/' },
  { id: 'go-sessions', section: 'actions', label: 'Go to Sessions', value: 'nav:/sessions' },
  { id: 'go-activity', section: 'actions', label: 'Go to Activity', value: 'nav:/activity' },
  { id: 'go-stats', section: 'actions', label: 'Go to Stats', value: 'nav:/stats' },
  { id: 'go-settings', section: 'actions', label: 'Go to Settings', value: 'nav:/settings' },
  { id: 'go-help', section: 'actions', label: 'Go to Help', value: 'nav:/help' },
]

/**
 * Map a project theme to a Sonner theme variant. Sonner only knows
 * `light` / `dark` / `system`; the four arcade palettes (double_dragon,
 * pacman, sf2, neogeo) are all dark-flavoured so they map to `dark`.
 */
function sonnerThemeFor(theme: ThemeName | undefined): 'light' | 'dark' | 'system' {
  if (theme === 'light') return 'light'
  if (theme === undefined) return 'system'
  return 'dark'
}

// FP11 § B8: thin route containers own the data-fetching hooks so the
// route shell stays pure JSX. Each container reads its hook(s), threads
// the result into the page's prop contract, and surfaces errors via the
// shared toaster.

function SessionsRoute() {
  const navigate = useNavigate()
  const sessions = useSessions()
  const activate = useSessionActivate()
  const deactivate = useSessionDeactivate()
  const del = useSessionDelete()
  const [pendingDelete, setPendingDelete] = useState<string | null>(null)

  if (sessions.isLoading) {
    return <div className="p-4 text-sm text-muted-foreground">Loading sessions…</div>
  }
  if (sessions.error) {
    return <div className="p-4 text-sm text-destructive">{strings.sessions.loadError}</div>
  }

  const data = sessions.data ?? { active: null, sessions: {} }

  return (
    <>
      <SessionsPage
        sessions={data.sessions}
        active={data.active}
        onActivate={(name) => activate.mutate(name)}
        onDeactivate={() => deactivate.mutate()}
        onDelete={(name) => setPendingDelete(name)}
        onCreate={() => {
          toast.message(strings.sessions.newSessionHint)
          navigate('/')
        }}
      />
      <ConfirmationDialog
        open={pendingDelete !== null}
        onOpenChange={(open) => !open && setPendingDelete(null)}
        title={strings.sessions.confirmDelete.title}
        description={
          pendingDelete ? strings.sessions.confirmDelete.description(pendingDelete) : ''
        }
        actionLabel={
          pendingDelete ? strings.destructive.deleteSession(pendingDelete) : 'Delete'
        }
        onConfirm={() => {
          if (pendingDelete) del.mutate(pendingDelete)
        }}
      />
    </>
  )
}

const ACTIVITY_PAGE_SIZE = 50

function ActivityRoute() {
  const [searchParams] = useSearchParams()
  const parsedPage = Number(searchParams.get('page'))
  const page =
    Number.isInteger(parsedPage) && parsedPage > 0 ? parsedPage : 1
  const activity = useActivity(page, ACTIVITY_PAGE_SIZE)

  if (activity.isLoading) {
    return <div className="p-4 text-sm text-muted-foreground">Loading activity…</div>
  }
  if (activity.error) {
    return <div className="p-4 text-sm text-destructive">{strings.activity.loadError}</div>
  }

  const data = activity.data ?? { items: [], page, page_size: ACTIVITY_PAGE_SIZE, total: 0 }
  return (
    <ActivityPage
      pageSize={data.page_size}
      total={data.total}
      items={data.items}
    />
  )
}

function StatsRoute() {
  const stats = useStats()
  if (stats.isLoading) {
    return <div className="p-4 text-sm text-muted-foreground">Loading stats…</div>
  }
  if (stats.error || !stats.data) {
    return <div className="p-4 text-sm text-destructive">{strings.stats.loadError}</div>
  }
  return <StatsPage stats={stats.data} />
}

function HelpRoute() {
  const index = useHelpIndex()
  const [searchParams] = useSearchParams()
  // P07 § E: Cmd-K palette navigates to /help?topic=<slug>; HelpRoute
  // honours that query param so the picked topic is pre-selected after
  // the route mounts. useEffect (not useState initialiser) so a second
  // Cmd-K pick while already on /help re-syncs.
  const topicParam = searchParams.get('topic')
  const [selectedSlug, setSelectedSlug] = useState<string | null>(topicParam)
  useEffect(() => {
    if (topicParam) setSelectedSlug(topicParam)
  }, [topicParam])
  const topic = useHelpTopic(selectedSlug)

  if (index.isLoading) {
    return <div className="p-4 text-sm text-muted-foreground">Loading help…</div>
  }
  if (index.error) {
    return <div className="p-4 text-sm text-destructive">{strings.help.loadError}</div>
  }

  const topics = index.data?.topics ?? []
  return (
    <HelpPage
      topics={topics}
      selectedSlug={selectedSlug}
      topicHtml={topic.data?.html ?? ''}
      topicLoading={topic.isLoading}
      onSelect={setSelectedSlug}
    />
  )
}

// FP12 § I + § J: SettingsRoute owns the settings-page hooks (config +
// snapshots + restore + export + import) so the SettingsPage stays
// pure-prop. Mirrors the FP11 § B8 container pattern used by Sessions /
// Activity / Stats / Help.
function SettingsRoute() {
  const config = useConfig()
  const configPatch = useConfigPatch()
  const snapshots = useSnapshots()
  const restore = useSnapshotRestore()
  const exportConfig = useConfigExport()
  const importConfig = useConfigImport()
  // FP16 § C: surface SetupCheck so the Setup banner can show per-INI
  // status (the user has no other way to tell whether refresh-inis
  // ever ran successfully).
  const setupCheck = useSetupCheck()
  const [backupError, setBackupError] = useState<string | null>(null)

  const handleExport = async () => {
    setBackupError(null)
    try {
      const bundle = await exportConfig.mutateAsync()
      const blob = new Blob([JSON.stringify(bundle, null, 2)], {
        type: 'application/json',
      })
      const url = URL.createObjectURL(blob)
      // FP13 § E3: drop millisecond noise from the export filename — second
      // resolution is plenty for a human-shaped backup name.
      const ts = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
      const a = document.createElement('a')
      a.href = url
      a.download = `mame-curator-config-${ts}.json`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch {
      setBackupError(strings.settings.backupExportError)
    }
  }

  // FP13 § B1: BackupTab now pre-validates (size + JSON parse + schema) and
  // hands us a typed bundle, so this handler is the mutate-only step.
  const handleImport = async (bundle: ConfigExportBundle) => {
    setBackupError(null)
    try {
      await importConfig.mutateAsync(bundle)
    } catch (err) {
      // FP13 § E6: prefer the server's structured `detail` over the generic
      // import-error string so the user sees what specifically rejected.
      setBackupError(
        err instanceof ApiError ? err.detail : strings.settings.backupImportError,
      )
    }
  }

  if (!config.data) {
    return (
      <div className="p-4 text-sm text-muted-foreground">Loading settings…</div>
    )
  }

  return (
    <SettingsPage
      config={config.data}
      onPatch={(patch) => configPatch.mutate(patch)}
      snapshots={snapshots.data?.items ?? []}
      snapshotsLoading={snapshots.isLoading}
      snapshotsError={
        snapshots.error ? strings.settings.snapshotsLoadError : null
      }
      onSnapshotRestore={(id) => restore.mutate(id)}
      onBackupExport={handleExport}
      onBackupImport={handleImport}
      backupError={backupError}
      setupInfo={setupCheck.data}
    />
  )
}

function ShellWithPalette() {
  const [paletteOpen, setPaletteOpen] = useState(false)
  const config = useConfig()
  const navigate = useNavigate()
  const location = useLocation()

  useKeyboard([
    {
      combo: 'k',
      meta: true,
      handler: (e) => {
        e.preventDefault()
        setPaletteOpen((o) => !o)
      },
    },
  ])

  // P07 § E: merge bundled help-topic items into the palette so users
  // can search by topic title (e.g. "playlist conflicts") and jump
  // straight to that page. Topics arrive from /api/help/index — the
  // palette stays usable without them.
  const helpIndex = useHelpIndex()
  const paletteItems = useMemo<CmdKItem[]>(() => {
    const helpItems: CmdKItem[] = (helpIndex.data?.topics ?? []).map((t) => ({
      id: `help-${t.slug}`,
      section: 'help',
      label: t.title,
      value: `nav:/help?topic=${encodeURIComponent(t.slug)}`,
      hint: strings.cmdK.sections.help,
    }))
    return [...PALETTE_ITEMS, ...helpItems]
  }, [helpIndex.data])

  const handleSelect = (value: string) => {
    if (value.startsWith('nav:')) {
      // FP11 § A1: SPA navigation via react-router's `useNavigate`.
      navigate(value.slice(4))
    }
  }

  const theme = config.data?.ui.theme

  return (
    <ThemeProvider theme={theme ?? 'dark'}>
      <AppShell onCmdK={() => setPaletteOpen(true)}>
        {/* FP11 § B12: route-level ErrorBoundary, resets on pathname
            change so a per-page crash doesn't survive a navigation
            recovery click. Drawer- and modal-level boundaries live at
            their consumer sites (LibraryPage's drawer, CopyModal). */}
        <ErrorBoundary resetKey={location.pathname}>
          <Suspense
            fallback={<div className="p-8 text-sm text-muted-foreground">Loading…</div>}
          >
            <Routes>
              <Route path="/" element={<LibraryPage />} />
              <Route path="/sessions" element={<SessionsRoute />} />
              <Route path="/activity" element={<ActivityRoute />} />
              <Route path="/stats" element={<StatsRoute />} />
              <Route path="/settings" element={<SettingsRoute />} />
              <Route path="/help" element={<HelpRoute />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </ErrorBoundary>
      </AppShell>

      {/* CmdKPalette + Toaster run as siblings to the shell so a
          route crash doesn't lock out the keyboard nav. Their own
          ErrorBoundary catches palette/toast crashes independently
          (third nesting depth per spec § 13). */}
      <ErrorBoundary>
        <CmdKPalette
          open={paletteOpen}
          onOpenChange={setPaletteOpen}
          items={paletteItems}
          onSelect={handleSelect}
        />
      </ErrorBoundary>

      <Toaster theme={sonnerThemeFor(theme)} />
    </ThemeProvider>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ShellWithPalette />
      </BrowserRouter>
    </QueryClientProvider>
  )
}

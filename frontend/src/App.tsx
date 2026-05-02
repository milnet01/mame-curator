import { lazy, Suspense, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from '@/components/ui/sonner'
import { AppShell } from '@/components/layout/AppShell'
import { ThemeProvider } from '@/components/layout/ThemeProvider'
import { ErrorBoundary } from '@/components/layout/ErrorBoundary'
import { CmdKPalette, type CmdKItem } from '@/components/CmdKPalette'
import { useConfig } from '@/hooks/useConfig'
import { useKeyboard } from '@/hooks/useKeyboard'

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
    queries: { staleTime: 30_000, retry: 1 },
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

function ShellWithPalette() {
  const [paletteOpen, setPaletteOpen] = useState(false)
  const config = useConfig()

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

  const handleSelect = (value: string) => {
    if (value.startsWith('nav:')) {
      window.location.hash = ''
      window.location.pathname = value.slice(4)
    }
  }

  const theme = config.data?.ui.theme ?? 'dark'

  return (
    <ThemeProvider theme={theme}>
      <AppShell onCmdK={() => setPaletteOpen(true)}>
        <ErrorBoundary>
          <Suspense
            fallback={<div className="p-8 text-sm text-muted-foreground">Loading…</div>}
          >
            <Routes>
              <Route path="/" element={<LibraryPage />} />
              <Route
                path="/sessions"
                element={
                  <SessionsPage
                    sessions={{}}
                    active={null}
                    onActivate={() => {}}
                    onDeactivate={() => {}}
                    onDelete={() => {}}
                    onCreate={() => {}}
                  />
                }
              />
              <Route
                path="/activity"
                element={
                  <ActivityPage
                    page={1}
                    pageSize={50}
                    total={0}
                    items={[]}
                    onPageChange={() => {}}
                  />
                }
              />
              <Route
                path="/stats"
                element={
                  <StatsPage
                    stats={{
                      by_genre: {},
                      by_decade: {},
                      by_publisher: {},
                      by_driver_status: {},
                      total_bytes: 0,
                    }}
                  />
                }
              />
              <Route
                path="/settings"
                element={
                  config.data ? (
                    <SettingsPage
                      config={config.data}
                      onPatch={() => {}}
                      onSnapshotRestore={() => {}}
                    />
                  ) : (
                    <div className="p-4 text-sm text-muted-foreground">Loading settings…</div>
                  )
                }
              />
              <Route
                path="/help"
                element={
                  <HelpPage
                    topics={[]}
                    selectedSlug={null}
                    topicHtml=""
                    onSelect={() => {}}
                  />
                }
              />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </ErrorBoundary>
      </AppShell>

      <CmdKPalette
        open={paletteOpen}
        onOpenChange={setPaletteOpen}
        items={PALETTE_ITEMS}
        onSelect={handleSelect}
      />

      <Toaster />
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

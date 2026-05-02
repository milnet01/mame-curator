import { lazy, Suspense, useState } from 'react'
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from '@/components/ui/sonner'
import { AppShell } from '@/components/layout/AppShell'
import { ThemeProvider } from '@/components/layout/ThemeProvider'
import { ErrorBoundary } from '@/components/layout/ErrorBoundary'
import { CmdKPalette, type CmdKItem } from '@/components/CmdKPalette'
import { useConfig, useConfigPatch } from '@/hooks/useConfig'
import { useKeyboard } from '@/hooks/useKeyboard'
import type { ThemeName } from '@/api/types'

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

function ShellWithPalette() {
  const [paletteOpen, setPaletteOpen] = useState(false)
  const config = useConfig()
  const configPatch = useConfigPatch()
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
                      // FP11 § B9: real PATCH wiring via useConfigPatch
                      // (was a no-op `() => {}`).
                      onPatch={(patch) => configPatch.mutate(patch)}
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

      {/* CmdKPalette + Toaster run as siblings to the shell so a
          route crash doesn't lock out the keyboard nav. Their own
          ErrorBoundary catches palette/toast crashes independently
          (third nesting depth per spec § 13). */}
      <ErrorBoundary>
        <CmdKPalette
          open={paletteOpen}
          onOpenChange={setPaletteOpen}
          items={PALETTE_ITEMS}
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

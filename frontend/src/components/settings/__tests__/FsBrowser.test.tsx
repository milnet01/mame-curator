import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { FsBrowser } from '../FsBrowser'
import { strings } from '@/strings'
import { server, http, HttpResponse, makeSandboxedListHandler } from '@/test/handlers'

// DS04 T3.1: removed redundant `afterEach(() => cleanup())` — vitest
// `globals: true` enables RTL's auto-cleanup.

const HOME = '/home/test'
const SUB = '/home/test/projects'

const homeListing = {
  path: HOME,
  parent: null,
  entries: [
    {
      name: 'projects',
      path: SUB,
      is_dir: true,
      size: null,
      mtime: '2026-05-01T00:00:00Z',
    },
    {
      name: 'notes.txt',
      path: '/home/test/notes.txt',
      is_dir: false,
      size: 42,
      mtime: '2026-05-01T00:00:00Z',
    },
  ],
}

const subListing = {
  path: SUB,
  parent: HOME,
  entries: [
    {
      name: 'mame',
      path: '/home/test/projects/mame',
      is_dir: true,
      size: null,
      mtime: '2026-05-01T00:00:00Z',
    },
  ],
}

beforeEach(() => {
  server.use(
    http.get('/api/fs/home', () => HttpResponse.json({ path: HOME })),
    http.get('/api/fs/roots', () => HttpResponse.json({ roots: ['/'] })),
    http.get('/api/fs/allowed-roots', () =>
      HttpResponse.json({
        roots: [{ id: 'r1', path: HOME, source: 'config' }],
      }),
    ),
    http.get('/api/fs/list', ({ request }) => {
      const path = new URL(request.url).searchParams.get('path')
      if (path === HOME) return HttpResponse.json(homeListing)
      if (path === SUB) return HttpResponse.json(subListing)
      return HttpResponse.json(
        {
          code: 'fs_sandboxed',
          detail: `${path} is outside the allowlist`,
          fields: [],
        },
        { status: 403 },
      )
    }),
  )
})

function renderWithClient(ui: React.ReactElement) {
  // Disable retry for BOTH queries and mutations — the grant test fires a
  // POST mutation that would otherwise inherit the 3× default retry and
  // mask a failing handler behind a retry-success.
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

describe('FsBrowser (FP12 § G)', () => {
  it('does not render when open=false', () => {
    // FP31 follow-up: an attempt to spy on `request:start` here surfaced
    // that the component fires its useQuery handlers on mount regardless
    // of `open`. That's a SUT design question (prefetch on close vs gate
    // via `enabled: open`), not a test-only fix — deferred to a separate
    // ROADMAP item for the FsBrowser prefetch policy.
    renderWithClient(
      <FsBrowser open={false} onOpenChange={() => {}} onPick={() => {}} />,
    )
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('lists the home directory on first open', async () => {
    renderWithClient(
      <FsBrowser open onOpenChange={() => {}} onPick={() => {}} />,
    )
    expect(await screen.findByText('projects')).toBeInTheDocument()
  })

  it('navigates into a directory when clicked', async () => {
    const user = userEvent.setup()
    renderWithClient(
      <FsBrowser open onOpenChange={() => {}} onPick={() => {}} />,
    )
    await user.click(await screen.findByText('projects'))
    expect(await screen.findByText('mame')).toBeInTheDocument()
  })

  it('returns to the parent via Up', async () => {
    const user = userEvent.setup()
    renderWithClient(
      <FsBrowser open onOpenChange={() => {}} onPick={() => {}} />,
    )
    await user.click(await screen.findByText('projects'))
    await screen.findByText('mame')
    await user.click(screen.getByRole('button', { name: /up/i }))
    expect(await screen.findByText('projects')).toBeInTheDocument()
  })

  it('calls onPick with the current path when Use this directory is clicked', async () => {
    const user = userEvent.setup()
    const onPick = vi.fn()
    renderWithClient(
      <FsBrowser open onOpenChange={() => {}} onPick={onPick} />,
    )
    await screen.findByText('projects')
    await user.click(
      screen.getByRole('button', { name: /use this directory/i }),
    )
    expect(onPick).toHaveBeenCalledExactlyOnceWith(HOME)
  })

  it('hides files in directory mode (default)', async () => {
    renderWithClient(
      <FsBrowser open onOpenChange={() => {}} onPick={() => {}} />,
    )
    await screen.findByText('projects')
    expect(screen.queryByText('notes.txt')).not.toBeInTheDocument()
  })

  it('shows and selects files in file mode', async () => {
    const user = userEvent.setup()
    const onPick = vi.fn()
    renderWithClient(
      <FsBrowser open onOpenChange={() => {}} onPick={onPick} mode="file" />,
    )
    const fileEntry = await screen.findByText('notes.txt')
    await user.click(fileEntry)
    expect(onPick).toHaveBeenCalledExactlyOnceWith('/home/test/notes.txt')
  })

  it('closes via the Cancel button', async () => {
    const user = userEvent.setup()
    const onOpenChange = vi.fn()
    renderWithClient(
      <FsBrowser open onOpenChange={onOpenChange} onPick={() => {}} />,
    )
    await screen.findByText('projects')
    await user.click(screen.getByRole('button', { name: /cancel/i }))
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('surfaces a grant prompt when listing returns fs_sandboxed', async () => {
    server.use(makeSandboxedListHandler(HOME, homeListing))
    renderWithClient(
      <FsBrowser
        open
        onOpenChange={() => {}}
        onPick={() => {}}
        initialPath="/etc"
      />,
    )
    await waitFor(() =>
      expect(
        screen.getByRole('alertdialog', { name: /grant filesystem access/i }),
      ).toBeInTheDocument(),
    )
    expect(
      screen.getByRole('button', { name: 'Grant access to /etc' }),
    ).toBeInTheDocument()
  })

  it('hides the "Use this directory" footer button in file mode (FP13 § C3)', async () => {
    renderWithClient(
      <FsBrowser open onOpenChange={() => {}} onPick={() => {}} mode="file" />,
    )
    await screen.findByText('projects')
    expect(
      screen.queryByRole('button', { name: /use this directory/i }),
    ).not.toBeInTheDocument()
  })

  it('does not render a drive-root button that duplicates an allowed root (FP13 § C4)', async () => {
    server.use(
      http.get('/api/fs/roots', () =>
        HttpResponse.json({ roots: ['/', HOME] }),
      ),
    )
    renderWithClient(
      <FsBrowser open onOpenChange={() => {}} onPick={() => {}} />,
    )
    await screen.findByText('projects')
    // HOME is in allowed-roots; only one quick-jump button for HOME exists.
    const homeButtons = screen.getAllByRole('button', { name: HOME })
    expect(homeButtons).toHaveLength(1)
    // The other drive root '/' still renders.
    expect(screen.getByRole('button', { name: '/' })).toBeInTheDocument()
  })

  it('renders ONLY the grant prompt when sandbox-blocked (not co-mounted with browse Dialog)', async () => {
    /**
     * FP20-K: previously both the outer "Pick a path" Dialog and the
     * grant ConfirmationDialog were rendered as siblings of a fragment.
     * ``Esc`` in the grant prompt then fired BOTH dialogs' onOpenChange
     * handlers — the outer Dialog's handler calls the parent's
     * onOpenChange(false) directly, unmounting FsBrowser even though
     * the user only intended to dismiss the grant prompt.
     *
     * Fix: render only one layer at a time. When ``sandboxBlocked`` is
     * truthy, the browse Dialog is unmounted and the AlertDialog is the
     * sole open layer; Esc routes cleanly to a single handler. The
     * FP13 § C2 behaviour (cancelling the grant closes FsBrowser) is
     * preserved by the AlertDialog's own onOpenChange.
     */
    server.use(makeSandboxedListHandler(HOME, homeListing))
    renderWithClient(
      <FsBrowser
        open
        onOpenChange={() => {}}
        onPick={() => {}}
        initialPath="/etc"
      />,
    )
    await screen.findByRole('alertdialog', { name: /grant filesystem access/i })
    // The outer browse Dialog's title is the canonical signal that it
    // is in the DOM. If both dialogs were co-mounted (pre-FP20-K), the
    // text would be present on the queryable surface.
    expect(
      screen.queryByText(strings.settings.fsBrowserTitle),
    ).not.toBeInTheDocument()
    // And only one dialog/alertdialog should be in the DOM.
    expect(screen.queryAllByRole('dialog')).toHaveLength(0)
    expect(screen.queryAllByRole('alertdialog')).toHaveLength(1)
  })

  it('closes the modal when the grant prompt is cancelled (FP13 § C2)', async () => {
    const user = userEvent.setup()
    const onOpenChange = vi.fn()
    server.use(makeSandboxedListHandler(HOME, homeListing))
    renderWithClient(
      <FsBrowser
        open
        onOpenChange={onOpenChange}
        onPick={() => {}}
        initialPath="/etc"
      />,
    )
    await screen.findByRole('alertdialog', { name: /grant filesystem access/i })
    // The grant prompt offers Cancel + the "Grant access to /etc" affirm.
    // Clicking Cancel must close FsBrowser entirely, not silently reset to
    // home (which would re-open the prompt if home hadn't loaded).
    await user.click(screen.getByRole('button', { name: /^cancel$/i }))
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('surfaces an inline error when home detection fails (FP13 § C7)', async () => {
    server.use(
      http.get('/api/fs/home', () =>
        HttpResponse.json(
          { code: 'fs_path_invalid', detail: 'no home', fields: [] },
          { status: 500 },
        ),
      ),
    )
    renderWithClient(
      <FsBrowser open onOpenChange={() => {}} onPick={() => {}} />,
    )
    expect(
      await screen.findByText(/could not detect home directory/i),
    ).toBeInTheDocument()
  })

  it('POSTs a grant when the prompt is confirmed', async () => {
    const user = userEvent.setup()
    let granted: string | null = null
    server.use(
      makeSandboxedListHandler(HOME, homeListing),
      http.post('/api/fs/allowed-roots', async ({ request }) => {
        const body = (await request.json()) as { path: string }
        granted = body.path
        return HttpResponse.json({
          roots: [
            { id: 'r1', path: HOME, source: 'config' },
            { id: 'r2', path: body.path, source: 'granted' },
          ],
        })
      }),
    )
    renderWithClient(
      <FsBrowser
        open
        onOpenChange={() => {}}
        onPick={() => {}}
        initialPath="/etc"
      />,
    )
    const grantBtn = await screen.findByRole('button', {
      name: 'Grant access to /etc',
    })
    await user.click(grantBtn)
    await waitFor(() => expect(granted).toBe('/etc'))
  })
})

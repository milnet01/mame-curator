import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, cleanup, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { FsBrowser } from '../FsBrowser'
import { server, http, HttpResponse } from '@/test/handlers'

afterEach(() => cleanup())

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
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

describe('FsBrowser (FP12 § G)', () => {
  it('does not render when open=false', () => {
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
    renderWithClient(
      <FsBrowser open onOpenChange={() => {}} onPick={() => {}} />,
    )
    await userEvent.click(await screen.findByText('projects'))
    expect(await screen.findByText('mame')).toBeInTheDocument()
  })

  it('returns to the parent via Up', async () => {
    renderWithClient(
      <FsBrowser open onOpenChange={() => {}} onPick={() => {}} />,
    )
    await userEvent.click(await screen.findByText('projects'))
    await screen.findByText('mame')
    await userEvent.click(screen.getByRole('button', { name: /up/i }))
    expect(await screen.findByText('projects')).toBeInTheDocument()
  })

  it('calls onPick with the current path when Use this directory is clicked', async () => {
    const onPick = vi.fn()
    renderWithClient(
      <FsBrowser open onOpenChange={() => {}} onPick={onPick} />,
    )
    await screen.findByText('projects')
    await userEvent.click(
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
    const onPick = vi.fn()
    renderWithClient(
      <FsBrowser open onOpenChange={() => {}} onPick={onPick} mode="file" />,
    )
    const fileEntry = await screen.findByText('notes.txt')
    await userEvent.click(fileEntry)
    expect(onPick).toHaveBeenCalledExactlyOnceWith('/home/test/notes.txt')
  })

  it('closes via the Cancel button', async () => {
    const onOpenChange = vi.fn()
    renderWithClient(
      <FsBrowser open onOpenChange={onOpenChange} onPick={() => {}} />,
    )
    await screen.findByText('projects')
    await userEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('surfaces a grant prompt when listing returns fs_sandboxed', async () => {
    server.use(
      http.get('/api/fs/list', ({ request }) => {
        const path = new URL(request.url).searchParams.get('path')
        if (path === HOME) return HttpResponse.json(homeListing)
        return HttpResponse.json(
          {
            code: 'fs_sandboxed',
            detail: `${path} outside allowlist`,
            fields: [],
          },
          { status: 403 },
        )
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

  it('closes the modal when the grant prompt is cancelled (FP13 § C2)', async () => {
    const onOpenChange = vi.fn()
    server.use(
      http.get('/api/fs/list', ({ request }) => {
        const path = new URL(request.url).searchParams.get('path')
        if (path === HOME) return HttpResponse.json(homeListing)
        return HttpResponse.json(
          {
            code: 'fs_sandboxed',
            detail: `${path} outside allowlist`,
            fields: [],
          },
          { status: 403 },
        )
      }),
    )
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
    await userEvent.click(screen.getByRole('button', { name: /^cancel$/i }))
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
    let granted: string | null = null
    server.use(
      http.get('/api/fs/list', ({ request }) => {
        const path = new URL(request.url).searchParams.get('path')
        if (path === HOME) return HttpResponse.json(homeListing)
        return HttpResponse.json(
          {
            code: 'fs_sandboxed',
            detail: `${path} outside allowlist`,
            fields: [],
          },
          { status: 403 },
        )
      }),
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
    await userEvent.click(grantBtn)
    await waitFor(() => expect(granted).toBe('/etc'))
  })
})

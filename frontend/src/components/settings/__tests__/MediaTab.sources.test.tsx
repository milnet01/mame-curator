import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { http, HttpResponse, server } from '@/test/handlers'
import { MediaTab } from '../MediaTab'
import type { AppConfigResponse, SourceReadinessRow } from '@/api/types'

function readinessRow(over: Partial<SourceReadinessRow> = {}): SourceReadinessRow {
  return {
    name: 'libretro',
    enabled: true,
    in_chain: true,
    kinds: ['boxart'],
    license_compatible: true,
    disabled_reason: null,
    needs_config: false,
    ...over,
  }
}

function media(over: Partial<AppConfigResponse['media']> = {}): AppConfigResponse['media'] {
  return {
    fetch_videos: false,
    cache_dir: '/x',
    snaps_dir: '/x/snaps',
    arcadedb_rate_limit_per_min: 30,
    mobygames_rate_limit_per_min: 5,
    sources: ['libretro', 'arcadeDB'],
    ...over,
  }
}

function renderTab(onChange = vi.fn()) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={qc}>
      <MediaTab media={media()} onChange={onChange} />
    </QueryClientProvider>,
  )
  return { onChange }
}

describe('MediaTab — source list', () => {
  it('fetches readiness once on mount', async () => {
    let calls = 0
    server.use(
      http.get('/api/media/sources', () => {
        calls += 1
        return HttpResponse.json({ sources: [] })
      }),
    )
    renderTab()
    await waitFor(() => expect(calls).toBe(1))
  })

  it('persists the reordered media.sources via onChange', async () => {
    server.use(http.get('/api/media/sources', () => HttpResponse.json({ sources: [] })))
    const user = userEvent.setup()
    const { onChange } = renderTab()
    // Move libretro (first) down → arcadeDB then libretro.
    await user.click(screen.getByRole('button', { name: /move libretro down/i }))
    expect(onChange).toHaveBeenCalledWith('sources', ['arcadeDB', 'libretro'])
  })

  // mame-curator-1084 — enable/disable sources via per-row toggle. The readiness
  // endpoint returns every known source (in_chain=false for the unconfigured
  // ones); MediaTab renders those below the reorderable list.
  function serveReadiness() {
    server.use(
      http.get('/api/media/sources', () =>
        HttpResponse.json({
          sources: [
            readinessRow({ name: 'libretro', in_chain: true }),
            readinessRow({ name: 'arcadeDB', in_chain: true }),
            readinessRow({ name: 'mobyGames', in_chain: false }),
            readinessRow({ name: 'wikipediaImage', in_chain: false }),
          ],
        }),
      ),
    )
  }

  it('renders unconfigured known sources below the reorderable list', async () => {
    serveReadiness()
    renderTab()
    // Only libretro + arcadeDB are in media.sources, so mobyGames/wikipediaImage
    // can only appear via the unconfigured section.
    expect(await screen.findByRole('switch', { name: /mobyGames/i })).toBeInTheDocument()
    expect(screen.getByRole('switch', { name: /wikipediaImage/i })).toBeInTheDocument()
    expect(screen.getByRole('switch', { name: /mobyGames/i })).not.toBeChecked()
  })

  it('removes an in-chain source from media.sources when toggled off', async () => {
    serveReadiness()
    const user = userEvent.setup()
    const { onChange } = renderTab()
    await user.click(await screen.findByRole('switch', { name: /arcadeDB/i }))
    expect(onChange).toHaveBeenCalledWith('sources', ['libretro'])
  })

  it('appends an unconfigured source to media.sources when toggled on', async () => {
    serveReadiness()
    const user = userEvent.setup()
    const { onChange } = renderTab()
    await user.click(await screen.findByRole('switch', { name: /mobyGames/i }))
    expect(onChange).toHaveBeenCalledWith('sources', ['libretro', 'arcadeDB', 'mobyGames'])
  })

  it('locks the libretro toggle on (cannot be removed from the chain)', async () => {
    serveReadiness()
    renderTab()
    const toggle = await screen.findByRole('switch', { name: /libretro/i })
    expect(toggle).toBeChecked()
    expect(toggle).toBeDisabled()
  })
})

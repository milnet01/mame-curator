import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { http, HttpResponse, server } from '@/test/handlers'
import { MediaTab } from '../MediaTab'
import type { AppConfigResponse } from '@/api/types'

function media(over: Partial<AppConfigResponse['media']> = {}): AppConfigResponse['media'] {
  return {
    fetch_videos: false,
    cache_dir: '/x',
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
})

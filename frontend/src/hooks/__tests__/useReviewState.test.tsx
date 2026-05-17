import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { server, http, HttpResponse } from '@/test/handlers'
import { useReviewStateClear, useReviewStateSet } from '../useReviewState'

vi.mock('sonner', () => ({
  toast: { error: vi.fn() },
}))

import { toast } from 'sonner'

afterEach(() => {
  vi.mocked(toast.error).mockClear()
})

const renderWithClient = () => {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  // Seed the cache so onMutate can capture `prev`.
  qc.setQueryData(['reviewState'], { entries: {} })
  return {
    qc,
    wrapper: ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    ),
  }
}

describe('useReviewStateSet — optimistic update', () => {
  it('updates the cache synchronously in onMutate', async () => {
    server.use(
      http.post('/api/state', () =>
        HttpResponse.json({ entries: { pacman: 'reviewed' } }, { status: 200 }),
      ),
    )
    const { qc, wrapper } = renderWithClient()
    const { result } = renderHook(() => useReviewStateSet(), { wrapper })

    result.current.mutate({ short_name: 'pacman', state: 'reviewed' })

    // onMutate runs synchronously; assertion shouldn't need to wait for the
    // network round-trip.
    await waitFor(() =>
      expect(qc.getQueryData(['reviewState'])).toEqual({
        entries: { pacman: 'reviewed' },
      }),
    )
  })

  it('rolls back the cache on error and toasts', async () => {
    server.use(
      http.post('/api/state', () =>
        HttpResponse.json(
          { code: 'game_not_found', detail: 'no', fields: [] },
          { status: 404 },
        ),
      ),
    )
    const { qc, wrapper } = renderWithClient()
    const { result } = renderHook(() => useReviewStateSet(), { wrapper })

    result.current.mutate({ short_name: 'no_such_game', state: 'reviewed' })

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(qc.getQueryData(['reviewState'])).toEqual({ entries: {} })
    expect(vi.mocked(toast.error)).toHaveBeenCalled()
  })
})

describe('useReviewStateClear — optimistic update', () => {
  it('removes the entry from the cache in onMutate', async () => {
    server.use(
      http.delete('/api/state/:shortName', () =>
        HttpResponse.json({ entries: {} }, { status: 200 }),
      ),
    )
    const { qc, wrapper } = renderWithClient()
    qc.setQueryData(['reviewState'], { entries: { pacman: 'reviewed' } })

    const { result } = renderHook(() => useReviewStateClear(), { wrapper })
    result.current.mutate('pacman')

    await waitFor(() =>
      expect(qc.getQueryData(['reviewState'])).toEqual({ entries: {} }),
    )
  })
})

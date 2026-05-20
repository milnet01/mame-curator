import { renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { server, http, HttpResponse } from '@/test/handlers'
import { renderWithClient as _renderWithClient } from '@/test/renderWithClient'
import { useReviewStateClear, useReviewStateSet } from '../useReviewState'

vi.mock('sonner', () => ({
  toast: { error: vi.fn() },
}))

import { toast } from 'sonner'

afterEach(() => {
  vi.mocked(toast.error).mockClear()
})

const renderWithClient = () => {
  const { qc, wrapper } = _renderWithClient()
  // Seed the cache so onMutate can capture `prev`.
  qc.setQueryData(['reviewState'], { entries: {} })
  return { qc, wrapper }
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

    // onMutate updates the cache on the next microtask (before the network
    // round-trip resolves); waitFor settles that tick without waiting on the
    // server response.
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

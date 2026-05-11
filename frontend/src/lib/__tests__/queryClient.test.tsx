import type { ReactNode } from 'react'

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider, useQuery } from '@tanstack/react-query'

vi.mock('sonner', () => ({
  toast: { error: vi.fn() },
}))

import { toast } from 'sonner'

import { ApiError } from '@/api/client'
import { createAppQueryClient } from '../queryClient'

beforeEach(() => {
  vi.mocked(toast.error).mockClear()
})

describe('createAppQueryClient', () => {
  /**
   * FP20-G: ``useApiQuery`` and other react-query call sites had no
   * shared error funnel — every R-route's query dropped silently to
   * the user when the backend returned 4xx/5xx or the network failed.
   * The fix installs a ``queryCache.onError`` hook that routes every
   * failure through ``toastApiError``, so cache misses (R01 games,
   * R03 alternatives, R07 stats, R10 sessions, R28 activity, R37 help,
   * R29 fs, R35 setup, R14 config) all surface user-visible toasts.
   */
  it('routes failing queries through toastApiError (queryCache onError)', async () => {
    const qc = createAppQueryClient()
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    )

    renderHook(
      () =>
        useQuery({
          queryKey: ['fp20g-boom'],
          queryFn: async () => {
            throw new ApiError(
              { code: 'unmapped_for_test', detail: 'boom', fields: [] },
              500,
            )
          },
          retry: false,
        }),
      { wrapper },
    )

    await waitFor(() => expect(vi.mocked(toast.error)).toHaveBeenCalled())
  })

  it('routes ApiError with code "network" through the network toast', async () => {
    const qc = createAppQueryClient()
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    )

    renderHook(
      () =>
        useQuery({
          queryKey: ['fp20g-network'],
          queryFn: async () => {
            throw new ApiError(
              { code: 'network', detail: 'fetch failed', fields: [] },
              -1,
            )
          },
          retry: false,
        }),
      { wrapper },
    )

    await waitFor(() =>
      expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
        expect.stringContaining('Connection problem'),
        expect.objectContaining({ description: expect.any(String) }),
      ),
    )
  })
})

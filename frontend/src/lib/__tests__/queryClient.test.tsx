import type { ReactNode } from 'react'

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider, useQuery } from '@tanstack/react-query'

vi.mock('sonner', () => ({
  toast: { error: vi.fn() },
}))

import { toast } from 'sonner'

import { ApiError } from '@/api/client'
import { _resetApiErrorToastDedupForTests } from '../apiErrorToast'
import { createAppQueryClient } from '../queryClient'

beforeEach(() => {
  vi.mocked(toast.error).mockClear()
  // FP26-I: reset the FP25-G dedup Map between tests. The dedup state
  // is module-level — without this, two tests that happen to reuse
  // the same `(code, detail)` key within 1.5 s would silently
  // collapse the second toast and the `toHaveBeenCalledTimes(1)`
  // assertion below would flip to 0 with a non-obvious cause.
  _resetApiErrorToastDedupForTests()
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

    await waitFor(() => expect(vi.mocked(toast.error)).toHaveBeenCalled(), { timeout: 3000 })
    // FP25-K(8): lock the once-per-failure contract. The pre-FP25-K
    // assertion (`toHaveBeenCalled`) would pass even if a regression
    // re-emitted the same failure on every retry / refetch tick;
    // `toHaveBeenCalledTimes(1)` pins the cache invariant.
    expect(vi.mocked(toast.error)).toHaveBeenCalledTimes(1)
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

    await waitFor(
      () =>
        expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
          expect.stringContaining('Connection problem'),
          expect.objectContaining({ description: expect.any(String) }),
        ),
      { timeout: 3000 },
    )
    // Symmetry with the first test: pin the once-per-failure contract so a
    // regression that re-emits the toast on each retry/refetch tick is caught.
    expect(vi.mocked(toast.error)).toHaveBeenCalledTimes(1)
  })
})

import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'

import { server, http, HttpResponse } from '@/test/handlers'
import { useFsGrantRoot } from '../useFs'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
  },
}))

import { toast } from 'sonner'

afterEach(() => {
  cleanup()
  vi.mocked(toast.error).mockClear()
})

const renderWithClient = () => {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
}

describe('useFsGrantRoot onError → toast (FP13 § A3)', () => {
  it('toasts byCode-friendly copy when grant POST returns 422 fs_path_invalid', async () => {
    server.use(
      http.post('/api/fs/allowed-roots', () =>
        HttpResponse.json(
          { code: 'fs_path_invalid', detail: 'not a directory', fields: [] },
          { status: 422 },
        ),
      ),
    )
    const { result } = renderHook(() => useFsGrantRoot(), {
      wrapper: renderWithClient(),
    })
    result.current.mutate('/tmp/not-a-dir')
    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
      expect.stringContaining('not a valid directory'),
    )
  })
})

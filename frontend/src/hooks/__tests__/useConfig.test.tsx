import { afterEach, describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'

import { server, http, HttpResponse } from '@/test/handlers'
import { makeClientWrapper } from '@/test/renderWithClient'
import { useConfigPatch, useSnapshotRestore } from '../useConfig'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
  },
}))

import { toast } from 'sonner'

// DS04 T3.1: vitest `globals: true` auto-cleanup handles RTL teardown;
// only the mock-clear is load-bearing here.
afterEach(() => {
  vi.mocked(toast.error).mockClear()
})

const renderWithClient = makeClientWrapper

describe('useConfigPatch onError → toast (FP13 § A1)', () => {
  it('toasts byCode-friendly copy when PATCH /api/config returns 422', async () => {
    server.use(
      http.patch('/api/config', () =>
        HttpResponse.json(
          { code: 'fs_path_invalid', detail: 'bad path', fields: [] },
          { status: 422 },
        ),
      ),
    )
    const { result } = renderHook(() => useConfigPatch(), {
      wrapper: renderWithClient(),
    })
    result.current.mutate({ paths: { source_roms: 'x' } } as never)
    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
      expect.stringContaining('not a valid directory'),
    )
  })
})

describe('useSnapshotRestore onError → toast (FP13 § A2)', () => {
  it('toasts byCode-friendly copy when restore returns 404 snapshot_not_found', async () => {
    server.use(
      http.post('/api/config/snapshots/missing/restore', () =>
        HttpResponse.json(
          { code: 'snapshot_not_found', detail: 'no such snapshot', fields: [] },
          { status: 404 },
        ),
      ),
    )
    const { result } = renderHook(() => useSnapshotRestore(), {
      wrapper: renderWithClient(),
    })
    result.current.mutate('missing')
    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
      expect.stringContaining('No configuration snapshot'),
    )
  })
})

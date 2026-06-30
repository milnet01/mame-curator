import { afterEach, describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'

import { server, http, HttpResponse } from '@/test/handlers'
import {
  makeClientWrapper,
  renderWithClient as makeClientWithQc,
} from '@/test/renderWithClient'
import { useFsGrantRoot } from '../useFs'

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

describe('useFsGrantRoot onSuccess → cache (FP31 mame-curator-1053)', () => {
  it('writes the granted roots into the allowed-roots cache and invalidates listings', async () => {
    // Only the error→toast path was covered before; the success path
    // (seed the allowed-roots cache + invalidate the listing prefix) was not.
    const nextRoots = {
      roots: [
        { id: 'r1', path: '/home/test', source: 'config' },
        { id: 'r2', path: '/etc', source: 'granted' },
      ],
    }
    server.use(
      http.post('/api/fs/allowed-roots', () => HttpResponse.json(nextRoots)),
    )
    const { qc, wrapper } = makeClientWithQc()
    // Seed a stale listing entry so the prefix invalidation has a target.
    qc.setQueryData(['fs', 'list', '/etc'], { sentinel: 'stale' })
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries')

    const { result } = renderHook(() => useFsGrantRoot(), { wrapper })
    result.current.mutate('/etc')

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    // onSuccess pushes the server response straight into the allowed-roots cache.
    expect(qc.getQueryData(['fs', 'allowed-roots'])).toEqual(nextRoots)
    // ...and invalidates every fs listing so a freshly-granted root refetches.
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['fs', 'list'] })
  })
})

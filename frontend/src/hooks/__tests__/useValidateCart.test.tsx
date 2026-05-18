import { beforeEach, describe, expect, it } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'

import { server, http, HttpResponse } from '@/test/handlers'
import { makeClientWrapper } from '@/test/renderWithClient'
import { useValidateCart } from '@/hooks/useValidateCart'

// DS04 T3.1: removed redundant `afterEach(() => cleanup())` — vitest
// `globals: true` enables RTL's auto-cleanup.

const REAL = new Set(['pacman', 'pacmanf', '1942'])

describe('useValidateCart', () => {
  // FP31: handler hoisted out of every `it` — three byte-for-byte copies
  // before. The same MSW reflection-server applies to every case; only the
  // mutate() input + assertion differ per test.
  beforeEach(() => {
    server.use(
      http.post('/api/games/validate', async ({ request }) => {
        const body = (await request.json()) as { short_names: string[] }
        return HttpResponse.json({
          existing: body.short_names.filter((n) => REAL.has(n)),
          missing: body.short_names.filter((n) => !REAL.has(n)),
        })
      }),
    )
  })

  it('returns existing+missing split for the input', async () => {
    const { result } = renderHook(() => useValidateCart(), {
      wrapper: makeClientWrapper(),
    })
    result.current.mutate({ short_names: ['pacman', 'ghost', '1942'] })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual({
      existing: ['pacman', '1942'],
      missing: ['ghost'],
    })
  })

  it('handles all-existing input', async () => {
    const { result } = renderHook(() => useValidateCart(), {
      wrapper: makeClientWrapper(),
    })
    result.current.mutate({ short_names: ['pacman', 'pacmanf'] })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.missing).toEqual([])
  })

  it('handles all-missing input', async () => {
    const { result } = renderHook(() => useValidateCart(), {
      wrapper: makeClientWrapper(),
    })
    result.current.mutate({ short_names: ['ghost1', 'ghost2'] })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.existing).toEqual([])
  })

  it('isError flips true when the server returns 500', async () => {
    // FP31 (chunk fc-002 coverage gap): if `/api/games/validate` returns
    // an error the caller needs `isError` so the cart UI can fall back to
    // a "skip validation" path. Previously untested.
    server.use(
      http.post('/api/games/validate', () =>
        HttpResponse.json({ code: 'unexpected', message: 'boom' }, { status: 500 }),
      ),
    )
    const { result } = renderHook(() => useValidateCart(), {
      wrapper: makeClientWrapper(),
    })
    result.current.mutate({ short_names: ['pacman'] })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

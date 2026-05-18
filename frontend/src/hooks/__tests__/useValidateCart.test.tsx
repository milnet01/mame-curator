import { describe, expect, it } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'

import { server, http, HttpResponse } from '@/test/handlers'
import { makeClientWrapper } from '@/test/renderWithClient'
import { useValidateCart } from '@/hooks/useValidateCart'

// DS04 T3.1: removed redundant `afterEach(() => cleanup())` — vitest
// `globals: true` enables RTL's auto-cleanup.

const renderWithClient = makeClientWrapper

const REAL = new Set(['pacman', 'pacmanf', '1942'])

describe('useValidateCart', () => {
  it('returns existing+missing split for the input', async () => {
    server.use(
      http.post('/api/games/validate', async ({ request }) => {
        const body = (await request.json()) as { short_names: string[] }
        return HttpResponse.json({
          existing: body.short_names.filter((n) => REAL.has(n)),
          missing: body.short_names.filter((n) => !REAL.has(n)),
        })
      }),
    )
    const { result } = renderHook(() => useValidateCart(), {
      wrapper: renderWithClient(),
    })
    result.current.mutate({ short_names: ['pacman', 'ghost', '1942'] })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual({
      existing: ['pacman', '1942'],
      missing: ['ghost'],
    })
  })

  it('handles all-existing input', async () => {
    server.use(
      http.post('/api/games/validate', async ({ request }) => {
        const body = (await request.json()) as { short_names: string[] }
        return HttpResponse.json({
          existing: body.short_names.filter((n) => REAL.has(n)),
          missing: body.short_names.filter((n) => !REAL.has(n)),
        })
      }),
    )
    const { result } = renderHook(() => useValidateCart(), {
      wrapper: renderWithClient(),
    })
    result.current.mutate({ short_names: ['pacman', 'pacmanf'] })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.missing).toEqual([])
  })

  it('handles all-missing input', async () => {
    server.use(
      http.post('/api/games/validate', async ({ request }) => {
        const body = (await request.json()) as { short_names: string[] }
        return HttpResponse.json({
          existing: body.short_names.filter((n) => REAL.has(n)),
          missing: body.short_names.filter((n) => !REAL.has(n)),
        })
      }),
    )
    const { result } = renderHook(() => useValidateCart(), {
      wrapper: renderWithClient(),
    })
    result.current.mutate({ short_names: ['ghost1', 'ghost2'] })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.existing).toEqual([])
  })
})

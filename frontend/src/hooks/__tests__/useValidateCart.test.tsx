import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'

import { server, http, HttpResponse } from '@/test/handlers'
import { useValidateCart } from '@/hooks/useValidateCart'

afterEach(() => cleanup())

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

/**
 * Shared QueryClient wrapper factory for hook + page tests.
 *
 * Previously duplicated across five hook test files (useConfig, useFs,
 * useValidateCart, useCopySession, useReviewState) — extracted by the
 * 2026-05-18 test-audit. Every consumer wants the same defaults:
 * ``retry: false`` for both queries and mutations so test failures
 * don't get rebrand from "broken handler" to "took N retries to fail".
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactElement, ReactNode } from 'react'

export interface RenderWithClientResult {
  /** A wrapper component to pass to ``renderHook`` / ``render``. */
  wrapper: (props: { children: ReactNode }) => ReactElement
  /** The underlying ``QueryClient`` — useful for tests that need to
   * seed cache entries via ``qc.setQueryData(...)`` before rendering. */
  qc: QueryClient
}

/**
 * Build a ``QueryClient`` + wrapper pair for a single test.
 *
 * Each call returns a fresh ``QueryClient`` so cache state cannot leak
 * across tests — see DS04 T3.1 isolation discipline.
 */
export function renderWithClient(): RenderWithClientResult {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
  return { qc, wrapper }
}

/**
 * Wrapper-only variant used when the test doesn't need to touch the
 * underlying ``QueryClient`` — keeps the call-site short for the
 * common case where the hook itself owns its cache interactions.
 */
export function makeClientWrapper(): (props: { children: ReactNode }) => ReactElement {
  return renderWithClient().wrapper
}

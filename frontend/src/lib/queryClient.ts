import { QueryCache, QueryClient } from '@tanstack/react-query'

import { toastApiError } from './apiErrorToast'

/**
 * FP20-G: shared QueryClient factory. The ``queryCache.onError`` hook
 * funnels every failed read-query through ``toastApiError`` so cache
 * misses across the R-route surface (R01 games, R03 alternatives,
 * R07 stats, R10 sessions, R28 activity, R37 help, R29 fs, R35 setup,
 * R14 config) stop dropping to per-route silence. Mutations retain
 * their existing per-site ``onError: toastApiError`` plumbing — adding
 * a ``mutationCache.onError`` here without removing those would
 * double-fire the toast. The boilerplate sweep is deferred to FP21.
 */
export function createAppQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: 1 },
    },
    queryCache: new QueryCache({ onError: toastApiError }),
  })
}

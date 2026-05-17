import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { apiRequest } from '@/api/client'
import {
  StatePostRequestSchema,
  StateViewSchema,
  type ReviewStateValue,
  type StatePostRequest,
  type StateView,
} from '@/api/types'
import { strings } from '@/strings'
import { useApiQuery } from './useApi'

const KEY = ['reviewState'] as const

/**
 * P14 — hydrate the per-game review-state map for the current world.
 *
 * Cache key is `['reviewState']` to align with the project's existing
 * `['games']` / `['sessions']` / `['facets']` namespace, NOT the overloaded
 * `['state']` (which would shadow generic React-Query state-shaped reads).
 */
export function useReviewState() {
  return useApiQuery<StateView>(KEY, '/api/state', StateViewSchema)
}

/**
 * Optimistic POST /api/state. The cache is updated synchronously in
 * `onMutate` so the badge appears in the same frame as the keypress;
 * `onError` rolls back; `onSettled` invalidates to reconcile with the
 * server's view.
 */
export function useReviewStateSet() {
  const qc = useQueryClient()
  return useMutation<StateView, Error, StatePostRequest, { prev: StateView | undefined }>({
    mutationFn: (body) =>
      apiRequest<StateView>('/api/state', StateViewSchema, {
        method: 'POST',
        body: StatePostRequestSchema.parse(body),
      }),
    onMutate: async (body) => {
      await qc.cancelQueries({ queryKey: KEY })
      const prev = qc.getQueryData<StateView>(KEY)
      qc.setQueryData<StateView>(KEY, (old) => ({
        entries: { ...(old?.entries ?? {}), [body.short_name]: body.state },
      }))
      return { prev }
    },
    onError: (_err, _body, ctx) => {
      if (ctx?.prev) qc.setQueryData(KEY, ctx.prev)
      toast.error(strings.library.stateUpdateFailed)
    },
    onSettled: () => qc.invalidateQueries({ queryKey: KEY }),
  })
}

/**
 * Optimistic DELETE /api/state/{short_name}. Same onMutate/onError/onSettled
 * shape as the setter; mutation arg is the short_name to clear back to pending.
 */
export function useReviewStateClear() {
  const qc = useQueryClient()
  return useMutation<StateView, Error, string, { prev: StateView | undefined }>({
    mutationFn: (shortName) =>
      apiRequest<StateView>(
        `/api/state/${encodeURIComponent(shortName)}`,
        StateViewSchema,
        { method: 'DELETE' },
      ),
    onMutate: async (shortName) => {
      await qc.cancelQueries({ queryKey: KEY })
      const prev = qc.getQueryData<StateView>(KEY)
      qc.setQueryData<StateView>(KEY, (old) => {
        const next = { ...(old?.entries ?? {}) }
        delete next[shortName]
        return { entries: next }
      })
      return { prev }
    },
    onError: (_err, _shortName, ctx) => {
      if (ctx?.prev) qc.setQueryData(KEY, ctx.prev)
      toast.error(strings.library.stateUpdateFailed)
    },
    onSettled: () => qc.invalidateQueries({ queryKey: KEY }),
  })
}

/** Re-export the value type so consumers don't dual-import from `@/api/types`. */
export type { ReviewStateValue }

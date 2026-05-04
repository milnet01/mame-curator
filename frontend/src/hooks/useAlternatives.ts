import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiRequest } from '@/api/client'
import {
  AlternativesSchema,
  OverridesViewSchema,
  type Alternatives,
  type OverridePostRequest,
  type OverridesView,
} from '@/api/types'
import { useApiQuery } from './useApi'

const KEY = (shortName: string) => ['alternatives', shortName] as const

/**
 * Fetch the parent + clones group for ``shortName``. The endpoint returns
 * an empty ``items`` array when the game has no alternative versions —
 * the Drawer renders a single-row state in that case.
 *
 * Keyed by short_name so switching between games invalidates correctly.
 */
export function useAlternatives(shortName: string | null) {
  return useApiQuery<Alternatives>(
    KEY(shortName ?? ''),
    `/api/games/${encodeURIComponent(shortName ?? '')}/alternatives`,
    AlternativesSchema,
    { enabled: shortName !== null },
  )
}

/**
 * POST a manual override (parent → winner). Invalidates the games listing
 * + the affected alternatives query so the UI re-renders with the picked
 * winner. Caller surfaces success / failure via the standard
 * ``toastApiError`` helper from ``lib/apiErrorToast``.
 */
export function useOverride() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (req: OverridePostRequest) =>
      apiRequest<OverridesView>('/api/overrides', OverridesViewSchema, {
        method: 'POST',
        body: req,
      }),
    onSuccess: (_data, req) => {
      qc.invalidateQueries({ queryKey: ['games'] })
      qc.invalidateQueries({ queryKey: KEY(req.winner) })
      qc.invalidateQueries({ queryKey: KEY(req.parent) })
    },
  })
}

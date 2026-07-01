import { useMutation, useQueryClient } from '@tanstack/react-query'

import { apiRequestVoid } from '@/api/client'
import { SourceReadinessSchema, type SourceReadiness } from '@/api/types'
import { useApiQuery } from './useApi'

// P10 chunk 10 — Settings → Media source readiness + key-paste.
// Tuple key (house style, matches useFs's ['fs', …]); the mutation invalidates
// the SAME key so a successful PUT refetches readiness (the dot flips green).
const MEDIA_SOURCES_KEY = ['media', 'sources'] as const

export function useMediaSources(enabled = true) {
  return useApiQuery<SourceReadiness>(
    MEDIA_SOURCES_KEY,
    '/api/media/sources',
    SourceReadinessSchema,
    // Brief staleTime: readiness can flip server-side mid-process (a 401 from
    // MobyGames, or a PUT /secret from another tab). Gated on `enabled` so a
    // closed Settings dialog doesn't prefetch.
    { enabled, staleTime: 5_000 },
  )
}

export function useSaveSourceSecret() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ name, secret }: { name: string; secret: string }) =>
      apiRequestVoid(`/api/media/sources/${encodeURIComponent(name)}/secret`, {
        method: 'PUT',
        body: { secret },
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: MEDIA_SOURCES_KEY }),
    // No toastApiError: the Configure modal surfaces the error inline and
    // stays open so the user can correct the key.
  })
}

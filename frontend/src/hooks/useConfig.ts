import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiRequest } from '@/api/client'
import { AppConfigResponseSchema, type AppConfigResponse } from '@/api/types'
import { useApiQuery } from './useApi'

const KEY = ['config'] as const

export function useConfig() {
  return useApiQuery<AppConfigResponse>(KEY, '/api/config', AppConfigResponseSchema)
}

export function useConfigPatch() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (patch: Partial<AppConfigResponse>) =>
      apiRequest<AppConfigResponse>('/api/config', AppConfigResponseSchema, {
        method: 'PATCH',
        body: patch,
      }),
    onSuccess: (next) => qc.setQueryData(KEY, next),
  })
}

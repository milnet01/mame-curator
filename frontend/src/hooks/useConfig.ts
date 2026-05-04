import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiRequest } from '@/api/client'
import {
  AppConfigResponseSchema,
  ConfigExportBundleSchema,
  SnapshotsListingSchema,
  type AppConfigResponse,
  type ConfigExportBundle,
  type SnapshotsListing,
} from '@/api/types'
import { useApiQuery } from './useApi'

const KEY = ['config'] as const
const SNAPSHOTS_KEY = ['config', 'snapshots'] as const

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
    onSuccess: (next) => {
      qc.setQueryData(KEY, next)
      // Each PATCH writes a fresh snapshot server-side (R15 contract);
      // invalidate so the Snapshots tab reflects the new entry on next read.
      qc.invalidateQueries({ queryKey: SNAPSHOTS_KEY })
    },
  })
}

export function useSnapshots() {
  return useApiQuery<SnapshotsListing>(
    SNAPSHOTS_KEY,
    '/api/config/snapshots',
    SnapshotsListingSchema,
  )
}

export function useSnapshotRestore() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiRequest<AppConfigResponse>(
        `/api/config/snapshots/${encodeURIComponent(id)}/restore`,
        AppConfigResponseSchema,
        { method: 'POST' },
      ),
    onSuccess: (next) => {
      qc.setQueryData(KEY, next)
      qc.invalidateQueries({ queryKey: SNAPSHOTS_KEY })
    },
  })
}

// FP12 § J — R18 export + R19 import. Backend takes / returns the full
// `ConfigExportBundle` JSON (config.py:170 + 186); the multipart hint in
// the roadmap entry is stale.
export function useConfigExport() {
  return useMutation({
    mutationFn: () =>
      apiRequest<ConfigExportBundle>(
        '/api/config/export',
        ConfigExportBundleSchema,
        { method: 'POST' },
      ),
  })
}

export function useConfigImport() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (bundle: ConfigExportBundle) =>
      apiRequest<AppConfigResponse>(
        '/api/config/import',
        AppConfigResponseSchema,
        { method: 'POST', body: bundle },
      ),
    onSuccess: (next) => {
      qc.setQueryData(KEY, next)
      qc.invalidateQueries({ queryKey: SNAPSHOTS_KEY })
    },
  })
}

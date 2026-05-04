import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiRequest } from '@/api/client'
import {
  FsAllowedRootsSchema,
  FsDriveRootsSchema,
  FsListingSchema,
  FsPathSchema,
  type FsAllowedRoots,
  type FsDriveRoots,
  type FsListing,
  type FsPath,
} from '@/api/types'
import { toastApiError } from '@/lib/apiErrorToast'
import { useApiQuery } from './useApi'

const FS_HOME_KEY = ['fs', 'home'] as const
const FS_ROOTS_KEY = ['fs', 'roots'] as const
const FS_ALLOWED_KEY = ['fs', 'allowed-roots'] as const
const fsListKey = (path: string) => ['fs', 'list', path] as const

export function useFsHome() {
  return useApiQuery<FsPath>(FS_HOME_KEY, '/api/fs/home', FsPathSchema)
}

export function useFsDriveRoots() {
  return useApiQuery<FsDriveRoots>(FS_ROOTS_KEY, '/api/fs/roots', FsDriveRootsSchema)
}

export function useFsAllowedRoots() {
  return useApiQuery<FsAllowedRoots>(
    FS_ALLOWED_KEY,
    '/api/fs/allowed-roots',
    FsAllowedRootsSchema,
  )
}

export function useFsListing(path: string | null) {
  return useApiQuery<FsListing>(
    fsListKey(path ?? ''),
    `/api/fs/list?path=${encodeURIComponent(path ?? '')}`,
    FsListingSchema,
    { enabled: path !== null },
  )
}

export function useFsGrantRoot() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (path: string) =>
      apiRequest<FsAllowedRoots>(
        '/api/fs/allowed-roots',
        FsAllowedRootsSchema,
        { method: 'POST', body: { path } },
      ),
    onSuccess: (next) => {
      qc.setQueryData(FS_ALLOWED_KEY, next)
    },
    onError: toastApiError,
  })
}

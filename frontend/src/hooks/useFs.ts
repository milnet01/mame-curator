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

// mame-curator-1047: every fs query takes an `enabled` flag (default true)
// so a mounted-but-closed FsBrowser can gate them on `open` and avoid
// prefetching home / roots / allowed-roots for a dialog the user hasn't
// opened. Default-true keeps the hooks drop-in for any always-on caller.
export function useFsHome(enabled = true) {
  return useApiQuery<FsPath>(FS_HOME_KEY, '/api/fs/home', FsPathSchema, { enabled })
}

export function useFsDriveRoots(enabled = true) {
  return useApiQuery<FsDriveRoots>(FS_ROOTS_KEY, '/api/fs/roots', FsDriveRootsSchema, {
    enabled,
  })
}

export function useFsAllowedRoots(enabled = true) {
  return useApiQuery<FsAllowedRoots>(
    FS_ALLOWED_KEY,
    '/api/fs/allowed-roots',
    FsAllowedRootsSchema,
    { enabled },
  )
}

// FP13 § C1: when `path` is null the query is disabled, but its cache slot
// must NOT collide with a real `path === ''` listing. The sentinel can never
// appear in a legitimate path string, so the disabled state and any future
// empty-path call sit on independent keys.
const DISABLED_PATH_SENTINEL = '__fs_listing_disabled__'

export function useFsListing(path: string | null, enabled = true) {
  return useApiQuery<FsListing>(
    fsListKey(path ?? DISABLED_PATH_SENTINEL),
    path !== null ? `/api/fs/list?path=${encodeURIComponent(path)}` : '',
    FsListingSchema,
    // Gated on BOTH `enabled` (open) and a real path: an `initialPath` makes
    // `path` non-null even while closed, so `enabled` is the load-bearing gate.
    { enabled: enabled && path !== null },
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
      // FP13 § C6: a freshly-granted root may unblock listings in any open
      // FsBrowser instance. Invalidate the prefix so they refetch.
      qc.invalidateQueries({ queryKey: ['fs', 'list'] })
    },
    onError: toastApiError,
  })
}

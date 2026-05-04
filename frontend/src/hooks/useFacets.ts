import { LibraryFacetsSchema, type LibraryFacets } from '@/api/types'
import { useApiQuery } from './useApi'

/**
 * GET /api/library/facets — discrete genres / publishers / developers /
 * letters drawn from the winners set, for FiltersSidebar dropdowns
 * (FP17). Cached aggressively because it only changes when the
 * underlying world is rebuilt (e.g. config reload).
 */
export function useFacets() {
  return useApiQuery<LibraryFacets>(
    ['library', 'facets'],
    '/api/library/facets',
    LibraryFacetsSchema,
    { staleTime: 60_000 },
  )
}

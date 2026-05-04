import { GamesPageSchema, type GamesPage } from '@/api/types'
import { useApiQuery } from './useApi'

export interface GamesQuery {
  page: number
  pageSize: number
  search?: string
  yearFrom?: number
  yearTo?: number
  onlyContested?: boolean
  onlyOverridden?: boolean
  onlyChdMissing?: boolean
  onlyBiosMissing?: boolean
}

function toQueryString(q: GamesQuery): string {
  // FP16 § A: backend (api/routes/games.py:60) accepts `q`, `year_min`,
  // `year_max` — the frontend was silently sending `search`, `year_from`,
  // `year_to`, so search + year-range filtering both no-op'd in production.
  const params = new URLSearchParams()
  params.set('page', String(q.page))
  params.set('page_size', String(q.pageSize))
  if (q.search) params.set('q', q.search)
  if (q.yearFrom) params.set('year_min', String(q.yearFrom))
  if (q.yearTo) params.set('year_max', String(q.yearTo))
  if (q.onlyContested) params.set('only_contested', '1')
  if (q.onlyOverridden) params.set('only_overridden', '1')
  if (q.onlyChdMissing) params.set('only_chd_missing', '1')
  if (q.onlyBiosMissing) params.set('only_bios_missing', '1')
  return params.toString()
}

export function useGames(query: GamesQuery) {
  const qs = toQueryString(query)
  return useApiQuery<GamesPage>(
    ['games', qs],
    `/api/games?${qs}`,
    GamesPageSchema,
    { staleTime: 5_000 },
  )
}

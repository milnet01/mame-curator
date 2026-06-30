/**
 * Pure, non-React helpers extracted from `LibraryPage.tsx`
 * (mame-curator-1077 — split the page under the §2 frontend file-size
 * hard cap of 350 lines). No component state lives here; the page's
 * stateful logic is in `useLibraryController.ts`.
 */
import type { FilterSidebarState } from '@/components/library/FiltersSidebar'
import { apiRequest } from '@/api/client'
import { GamesPageSchema, type GamesPage } from '@/api/types'
import { strings } from '@/strings'

export const DEFAULT_FILTERS: FilterSidebarState = {
  search: '',
  yearRange: [1975, 2025],
  letter: null,
  genre: null,
  publisher: null,
  developer: null,
  onlyContested: false,
  onlyOverridden: false,
  onlyChdMissing: false,
  onlyBiosMissing: false,
  reviewState: 'all',
}

// P14 — walkthrough-mode toggle persists across reloads.
export const WALKTHROUGH_KEY = 'mame-curator:walkthrough-mode'

export function readWalkthroughPref(): boolean {
  try {
    const raw = localStorage.getItem(WALKTHROUGH_KEY)
    if (raw === null) return true
    return raw === 'true'
  } catch {
    return true
  }
}

// Module-level helper so useQueries queryFn doesn't close over any reactive
// deps — tile objects are `as const` so they're stable references.
//
// FP24-U: routed through apiRequest (typed errors, schema validation,
// envelope decoding) per coding-standards § 4 "no raw fetch in
// components."
//
// FP24-HH: page_size=1 (not the spec's "0") because the backend caps
// page_size at `Query(50, ge=1, le=500)`. Only the envelope's `total`
// field matters here; the 1-row payload is acceptable overhead. A
// future "?count_only=true" parameter would let us drop the items
// payload entirely.
export async function fetchTileCount(
  tile: (typeof strings.library.featured.tiles)[number],
): Promise<GamesPage> {
  const p = new URLSearchParams({ page: '1', page_size: '1' })
  if (tile.query.publisher) p.set('publisher', tile.query.publisher)
  if (tile.query.developer) p.set('developer', tile.query.developer)
  if (tile.query.genre) p.set('genre', tile.query.genre)
  if (tile.query.yearFrom) p.set('year_min', String(tile.query.yearFrom))
  if (tile.query.yearTo) p.set('year_max', String(tile.query.yearTo))
  return apiRequest<GamesPage>(`/api/games?${p}`, GamesPageSchema)
}

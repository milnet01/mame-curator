import { WikipediaExtractSchema, type WikipediaExtract } from '@/api/types'
import { useApiQuery } from './useApi'

/**
 * P10 chunk 11 — the Wikipedia "About" paragraph for the Alternatives drawer.
 * `GET /media/{name}/wiki` returns a WikipediaExtract or JSON `null` (no page),
 * so the schema is `.nullable()` — a null body parses to `null` (the section
 * hides) rather than throwing. `staleTime: Infinity` because a game's Wikipedia
 * summary doesn't change on curation-session timescales.
 */
export function useWikipediaExtract(shortName: string, enabled = true) {
  return useApiQuery<WikipediaExtract | null>(
    ['wikipedia', shortName],
    `/media/${encodeURIComponent(shortName)}/wiki`,
    WikipediaExtractSchema.nullable(),
    { enabled, staleTime: Infinity },
  )
}

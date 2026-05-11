import { toast } from 'sonner'

import { ApiError } from '@/api/client'
import { strings } from '@/strings'

/**
 * Render a thrown error from a react-query mutation as a user-visible toast.
 * FP13 § A wires every project mutation through this so 422/404/500/network
 * failures stop being silent. ApiError → byCode lookup → detail fallback;
 * code === 'network' uses the connection-problem strings; non-ApiError →
 * generic.
 *
 * FP25-G: 1500 ms dedup window keyed on `(code, detail)`. Cold-start outages
 * fire 9+ near-simultaneous query failures (six tile counts via the
 * LibraryPage `useQueries` fan-out + games + facets + config + sessions +
 * setupCheck), and `queryCache.onError` would emit one toast per failure.
 * Sonner doesn't dedup. The window collapses bursts of the same
 * `(code, detail)` into a single toast while still surfacing distinct
 * errors and lets a *later* identical failure (>1.5 s later) toast again.
 */
const DEDUP_WINDOW_MS = 1500
const lastSeen = new Map<string, number>()

function shouldSkipDuplicate(key: string): boolean {
  const now = Date.now()
  const last = lastSeen.get(key)
  if (last !== undefined && now - last < DEDUP_WINDOW_MS) {
    return true
  }
  lastSeen.set(key, now)
  return false
}

/**
 * Test-only: clear the dedup state so cases that exercise the burst-
 * suppression don't bleed across tests. Production code never imports
 * this — there's no UI path that needs to reset the window.
 */
export function _resetApiErrorToastDedupForTests(): void {
  lastSeen.clear()
}

export function toastApiError(err: unknown): void {
  if (err instanceof ApiError) {
    if (err.code === 'network') {
      if (shouldSkipDuplicate(`network::${err.detail}`)) return
      toast.error(strings.errors.networkTitle, {
        description: strings.errors.networkBody,
      })
      return
    }
    if (shouldSkipDuplicate(`${err.code}::${err.detail}`)) return
    const friendly =
      strings.errors.byCode[err.code as keyof typeof strings.errors.byCode]
    toast.error(friendly ?? err.detail)
    return
  }
  // Non-ApiError: dedup on the generic key — same title for every
  // unmapped throw, so collapse the whole class to one toast per window.
  if (shouldSkipDuplicate('generic')) return
  toast.error(strings.errors.genericTitle)
}

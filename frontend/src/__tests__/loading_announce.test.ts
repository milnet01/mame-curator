/**
 * DS02 C3 — route-level loading fallbacks announce via `aria-live`.
 *
 * Five route containers in `App.tsx` (`SessionsRoute`, `ActivityRoute`,
 * `StatsRoute`, `HelpRoute`, `SettingsRoute`) render an inline
 * "Loading …" div while their data fetch is in flight. Screen readers
 * do not announce silent DOM swaps; the route transition therefore
 * passes without auditory feedback for AT users.
 *
 * Contract: each of the five loading-state branches renders a wrapper
 * with `role="status"` and `aria-live="polite"`. The sixth (the
 * Suspense fallback at the bottom of the file) is exempt per spec —
 * but if it ever picks up the role too, that's fine.
 *
 * Tested as source-text rather than render-based: the route containers
 * pull in React Query hooks, would require a full QueryClientProvider
 * setup, and the actual `aria-live` attribute is a static prop on the
 * JSX node. A regex over the source is sufficient and orders of
 * magnitude cheaper.
 *
 * Pre-fix: zero `aria-live` attrs on the Loading divs.
 * Post-fix: each `Loading <route>…` text node sits inside a wrapper
 * carrying `role="status"` and `aria-live="polite"`.
 */
import { describe, expect, it } from 'vitest'

import appTsxSource from '../App.tsx?raw'

// Five route-level loading variants. The exact wording lives in
// `strings.loading.*` post-B2, but the spec is "one fallback per
// route container", so the test counts wrappers rather than text
// content. Pattern: a `<div role="status" aria-live="polite">` that
// contains a JSX expression / literal naming the loading state.
const EXPECTED_LIVE_REGIONS = 5

describe('DS02 C3 — route-level loading fallbacks announce', () => {
  it('App.tsx exposes ≥5 role=status + aria-live=polite wrappers for route fallbacks', () => {
    // Match any opening JSX tag carrying BOTH attrs; order-insensitive.
    const re =
      /<[A-Za-z][\w.]*\b[^>]*\brole\s*=\s*["']status["'][^>]*\baria-live\s*=\s*["']polite["'][^>]*>|<[A-Za-z][\w.]*\b[^>]*\baria-live\s*=\s*["']polite["'][^>]*\brole\s*=\s*["']status["'][^>]*>/g
    const matches = appTsxSource.match(re) ?? []
    expect(
      matches.length,
      `expected ≥${EXPECTED_LIVE_REGIONS} role=status+aria-live=polite wrappers in App.tsx, found ${matches.length}`,
    ).toBeGreaterThanOrEqual(EXPECTED_LIVE_REGIONS)
  })
})

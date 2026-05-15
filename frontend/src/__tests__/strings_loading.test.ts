/**
 * DS02 B1/B2 — `strings.loading.*` namespace + App.tsx literal scrub.
 *
 * Six hardcoded `Loading …` JSX strings live in `App.tsx` at the
 * route-level Suspense fallbacks (sessions / activity / stats / help /
 * settings) plus one generic fallback. Every other user-facing string
 * already routes through `strings.ts`; B1 introduces
 * `strings.loading.{sessions,activity,stats,help,settings,generic}`
 * and B2 replaces the literals with `{strings.loading.*}`.
 *
 * Pre-fix: `strings.loading` is undefined; `App.tsx` contains six
 * `>Loading …<` literal substrings.
 * Post-fix: every key exists + is non-empty; `App.tsx` has zero
 * literal `>Loading` JSX text nodes.
 */
import { describe, expect, it } from 'vitest'

import { strings } from '../strings'
import appTsxSource from '../App.tsx?raw'

const LOADING_KEYS = [
  'sessions',
  'activity',
  'stats',
  'help',
  'settings',
  'generic',
] as const

type StringsCatalogue = Record<string, unknown>
type LoadingCatalogue = Record<string, unknown>

describe('DS02 B1 — strings.loading.* keys exist and are non-empty', () => {
  it.each(LOADING_KEYS)('strings.loading.%s is a non-empty string', (key) => {
    const root = strings as unknown as StringsCatalogue
    const loading = root.loading as LoadingCatalogue | undefined
    expect(loading, `strings.loading missing`).toBeDefined()
    const value = loading?.[key]
    expect(typeof value, `strings.loading.${key} type`).toBe('string')
    expect((value as string).length).toBeGreaterThan(0)
  })
})

describe('DS02 B2 — App.tsx has no literal Loading JSX text', () => {
  it('no `>Loading …<` substrings remain', () => {
    // Match `>Loading sessions…<`, `>Loading…<`, etc. — the JSX text
    // form. Whitespace-tolerant; case-sensitive on `Loading` since the
    // post-fix catalogue still capitalises it (it's the literal source
    // that's the violation, not the rendered text).
    const offenders: string[] = []
    const re = />\s*Loading[^<]*</g
    let m: RegExpExecArray | null
    while ((m = re.exec(appTsxSource)) !== null) {
      offenders.push(m[0])
    }
    expect(
      offenders,
      `App.tsx still contains literal Loading JSX text:\n${offenders.join('\n')}`,
    ).toEqual([])
  })
})

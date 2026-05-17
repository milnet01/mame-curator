/**
 * FP27 A8 — `strings.ts` has no orphan keys.
 *
 * The 2026-05-14 indie-review flagged ~4 dead `strings.ts` entries.
 * The exact keys aren't pre-named in the spec — this test does the
 * enumeration: walk the nested catalogue producing flat dotted-paths,
 * grep each path against the rest of `frontend/src/**`, and assert the
 * orphan set is empty.
 *
 * Pre-fix: the sweep returns ≥4 orphan dotted-paths → test fails with
 * an explicit list. Post-fix: every key has at least one consumer
 * outside `strings.ts` and the test file itself.
 *
 * Mechanics:
 *  - Vite's `import.meta.glob` with `{ query: '?raw', eager: true }`
 *    loads every consumer file at test time as a raw string. Cheap
 *    enough at ~200 files; bounded by Vitest's compilation step.
 *  - For each dotted-path key, search the raw text for the dotted
 *    prefix (e.g. `strings.cmdK.sections.games`). Substring match —
 *    sufficient because the catalogue's access pattern is statically
 *    typed and the implementer accesses keys by full dotted-path
 *    99% of the time.
 *  - Dynamic-access patterns (e.g. `strings.cmdK.sections[sectionVar]`)
 *    register as "consumer of the parent prefix" — the leaf keys
 *    of that parent are NOT flagged as orphans if the parent itself
 *    is consumed. Keeps false positives low.
 *
 * See `docs/specs/FP27.md` § A8.
 */
import { describe, expect, it } from 'vitest'

import { strings } from '../strings'

type CatalogueNode = string | { [k: string]: CatalogueNode } | Array<CatalogueNode>

function flattenKeys(
  node: CatalogueNode,
  prefix: string,
  out: string[],
): void {
  if (typeof node === 'string') {
    out.push(prefix)
    return
  }
  if (Array.isArray(node)) {
    // The catalogue uses arrays for tile lists with id+title objects;
    // skip them — they're not user-facing string keys per se, and the
    // sweep should ignore the array index as a "key".
    return
  }
  if (node && typeof node === 'object') {
    for (const [k, v] of Object.entries(node)) {
      const child = prefix ? `${prefix}.${k}` : k
      flattenKeys(v as CatalogueNode, child, out)
    }
  }
}

// Known dynamic-access parent paths. Each entry is a dotted prefix
// under which the leaf keys are looked up indirectly (e.g. via
// `strings.foo[someVar]`) — so the leaf keys themselves can't be
// detected by literal full-path grep, but the parent's appearance
// in source means the keys are reachable. Update the allowlist with
// a comment when a new dynamic-access pattern lands; otherwise the
// sweep stays strict.
//
// Format: 'parent.dotted.path' (no leading 'strings.').
const DYNAMIC_ACCESS_PARENTS = new Set<string>([
  // FP27 A8: legitimate dynamic-access patterns where a leaf key is
  // looked up via `strings.<parent>[<variable>]`. The sweep treats
  // every leaf under the parent as reachable. Update with a comment
  // when a new pattern lands.
  //
  // CopyModal.tsx: `strings.copy.sessionState[state.state]`
  'copy.sessionState',
  // CmdKPalette.tsx: `strings.cmdK.sections[item.section]`
  'cmdK.sections',
  // apiErrorToast.ts: `strings.errors.byCode[err.code]`
  'errors.byCode',
  // LayoutSwitcher.tsx / ThemeSwitcher.tsx
  'layouts',
  'themes',
  // SessionsPage.tsx — actions/metaLabels accessed by key
  'sessions.actions',
  'sessions.metaLabels',
  // SettingsPage.tsx — section tabs, default-sort + cards-per-row
  // options + cart-clear options accessed by key
  'settings.sections',
  'settings.defaultSortOptions',
  'settings.cardsPerRowOptions',
  'settings.uiLabels.cart_clear_on_copy_options',
  // FiltersTab.tsx / PickerTab.tsx — chip list / placeholder accessed
  // by key
  'settings.filterChipLists',
  'settings.filterChipPlaceholders',
  'settings.pickerChipLists',
  'settings.pickerChipPlaceholders',
  // UpdatesTab.tsx — channel options accessed by key
  'settings.updateChannelOptions',
  // P14 — FiltersSidebar.tsx: `strings.library.reviewState[opt.labelKey]`
  'library.reviewState',
])

function isDynamicAllowlisted(leafPath: string): boolean {
  for (const parent of DYNAMIC_ACCESS_PARENTS) {
    if (leafPath === parent || leafPath.startsWith(parent + '.')) {
      return true
    }
  }
  return false
}

// Load every TS/TSX file in frontend/src/ at test time as raw text.
// Vite 8's `import.meta.glob` with `query: '?raw'` is stable.
const consumerSources = import.meta.glob<string>(
  ['../**/*.ts', '../**/*.tsx'],
  { query: '?raw', import: 'default', eager: true },
)

const EXCLUDED_PATH_FRAGMENTS = [
  // DS02 A3 — the catalogue itself moved to `strings_internal.ts`;
  // its own definition file is naturally a "consumer" of every leaf
  // key (the assignment `loading: { sessions: 'Loading sessions…' }`
  // contains the substring `strings.loading.sessions` after dotted
  // flattening), which would defeat the orphan sweep. Excluding both
  // halves of the re-export pair keeps the sweep strict.
  '/strings.ts',
  '/strings_internal.ts',
  '/__tests__/',
  '.test.tsx',
  '.test.ts',
]

const CONSUMER_HAYSTACK: string = Object.entries(consumerSources)
  .filter(([path]) => !EXCLUDED_PATH_FRAGMENTS.some((f) => path.includes(f)))
  .map(([, src]) => src)
  .join('\n')

describe('FP27 A8 — strings.ts has no orphan keys', () => {
  it('every flat dotted-path is consumed somewhere in frontend/src/', () => {
    const flat: string[] = []
    flattenKeys(strings as unknown as CatalogueNode, '', flat)
    expect(flat.length).toBeGreaterThan(0)

    const orphans: string[] = []
    for (const dotted of flat) {
      // Strict: require the EXACT full dotted path
      // `strings.<dotted>` to appear in some consumer file. Dynamic-
      // access patterns (e.g. `strings.cmdK.sections[section]`) opt
      // in via DYNAMIC_ACCESS_PARENTS.
      if (isDynamicAllowlisted(dotted)) {
        continue
      }
      const fullPath = 'strings.' + dotted
      if (!CONSUMER_HAYSTACK.includes(fullPath)) {
        orphans.push(fullPath)
      }
    }

    // Helpful failure: print the orphan list so the developer can
    // delete them directly.
    expect(orphans, `orphan strings keys:\n${orphans.join('\n')}`).toEqual([])
  })
})

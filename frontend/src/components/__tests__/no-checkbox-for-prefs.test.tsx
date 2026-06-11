/**
 * Invariant: every prefs surface uses shadcn `<Switch>`, NEVER `<Checkbox>`.
 *
 * Per design §8 + spec § "Tests to write first": multi-select cases (e.g.
 * picking 5 games for a bulk action) may legitimately use Checkbox; this
 * test renders the prefs-area surfaces with a representative state and
 * asserts that `screen.queryAllByRole('checkbox')` returns `[]`.
 *
 * The complementary grep gate runs at PR time:
 *   git grep -l "Checkbox" frontend/src/ | grep -v src/components/ui
 */
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'

// DS04 T3.1 pattern: vitest `globals: true` enables RTL's auto-cleanup;
// no need for manual `cleanup()` calls in this file.

import { FiltersSidebar } from '../library/FiltersSidebar'
import { LayoutSwitcher } from '../library/LayoutSwitcher'
import { ThemeSwitcher } from '../library/ThemeSwitcher'
import { SettingsPage } from '@/pages/SettingsPage'
import type { AppConfigResponse } from '@/api/types'
import { baseFiltersValue } from '@/test/fixtures'

const config: AppConfigResponse = {
  paths: {
    source_roms: '/x',
    source_dat: '/x',
    dest_roms: '/x',
    retroarch_playlist: '/x',
    catver: null,
    languages: null,
    bestgames: null,
    mature: null,
    series: null,
    listxml: null,
    retroarch: null,
    retroarch_core: null,
  },
  server: { host: '127.0.0.1', port: 8080, open_browser_on_start: true },
  filters: {
    drop_bios_devices_mechanical: true,
    drop_categories: [],
    drop_genres: [],
    drop_publishers: [],
    drop_developers: [],
    drop_year_before: null,
    drop_year_after: null,
    drop_japanese_only_text: true,
    drop_preliminary_emulation: true,
    drop_chd_required: true,
    drop_mature: true,
    region_priority: [],
    preferred_genres: [],
    preferred_publishers: [],
    preferred_developers: [],
    prefer_parent_over_clone: true,
    prefer_good_driver: true,
  },
  media: { fetch_videos: false, cache_dir: '/x', arcadedb_rate_limit_per_min: 30 },
  ui: {
    theme: 'dark',
    layout: 'masonry',
    default_sort: 'name',
    show_alternatives_indicator: true,
    cards_per_row_hint: 'auto',
    cart_clear_on_copy: 'on_success',
  },
  updates: { channel: 'stable', check_on_startup: true, ini_check_on_startup: true },
  fs: { granted_roots: [] },
  restart_required: false,
}

describe('no-checkbox-for-prefs invariant', () => {
  it('FiltersSidebar prefs surface uses Switch, never Checkbox', () => {
    render(
      <FiltersSidebar
        value={baseFiltersValue}
        onChange={() => {}}
        onSaveSession={() => {}}
      />,
    )
    expect(screen.queryAllByRole('checkbox')).toHaveLength(0)
  })

  it('LayoutSwitcher uses no Checkbox', () => {
    render(<LayoutSwitcher value="masonry" onChange={() => {}} />)
    expect(screen.queryAllByRole('checkbox')).toHaveLength(0)
  })

  it('ThemeSwitcher uses no Checkbox', () => {
    render(<ThemeSwitcher value="dark" onChange={() => {}} />)
    expect(screen.queryAllByRole('checkbox')).toHaveLength(0)
  })

  it('SettingsPage prefs tabs use Switch, never Checkbox', async () => {
    const user = userEvent.setup()
    // DS02 D1: SettingsPage now reads its active tab via
    // `useSearchParams`, so it must render inside a Router.
    render(
      <MemoryRouter>
        <SettingsPage
          config={config}
          onPatch={() => {}}
          onSnapshotRestore={() => {}}
        />
      </MemoryRouter>,
    )
    // Visit EVERY tab the page renders, not a hardcoded subset — test-audit
    // FP03 (2026-05-18) flagged that the 5-tab subset would let a future
    // checkbox-shaped preference landing on Paths/Snapshots/Backup/About
    // slip past this invariant. Enumerating `role="tab"` at runtime keeps
    // the test in lockstep with `SECTION_KEYS` in SettingsPage.tsx without
    // a hand-maintained mirror.
    const tabs = screen.getAllByRole('tab')
    expect(tabs.length, 'SettingsPage rendered zero tabs').toBeGreaterThan(0)
    for (const tab of tabs) {
      const label = tab.textContent ?? '<no label>'
      await user.click(tab)
      expect(
        screen.queryAllByRole('checkbox'),
        `Tab "${label}" leaked a Checkbox`,
      ).toHaveLength(0)
    }
  })
})

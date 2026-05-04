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
import { render, screen, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { FiltersSidebar } from '../library/FiltersSidebar'
import { LayoutSwitcher } from '../library/LayoutSwitcher'
import { ThemeSwitcher } from '../library/ThemeSwitcher'
import { SettingsPage } from '@/pages/SettingsPage'
import type { AppConfigResponse } from '@/api/types'

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
  media: { fetch_videos: false, cache_dir: '/x' },
  ui: {
    theme: 'dark',
    layout: 'masonry',
    default_sort: 'name',
    show_alternatives_indicator: true,
    cards_per_row_hint: 'auto',
  },
  updates: { channel: 'stable', check_on_startup: true, ini_check_on_startup: true },
  fs: { granted_roots: [] },
  restart_required: false,
}

describe('no-checkbox-for-prefs invariant', () => {
  it('FiltersSidebar prefs surface uses Switch, never Checkbox', () => {
    render(
      <FiltersSidebar
        value={{
          search: '',
          yearRange: [1980, 2010],
          letter: null,
          genre: null,
          publisher: null,
          developer: null,
          onlyContested: false,
          onlyOverridden: false,
          onlyChdMissing: false,
          onlyBiosMissing: false,
        }}
        onChange={() => {}}
        onSaveSession={() => {}}
      />,
    )
    expect(screen.queryAllByRole('checkbox')).toHaveLength(0)
    cleanup()
  })

  it('LayoutSwitcher uses no Checkbox', () => {
    render(<LayoutSwitcher value="masonry" onChange={() => {}} />)
    expect(screen.queryAllByRole('checkbox')).toHaveLength(0)
    cleanup()
  })

  it('ThemeSwitcher uses no Checkbox', () => {
    render(<ThemeSwitcher value="dark" onChange={() => {}} />)
    expect(screen.queryAllByRole('checkbox')).toHaveLength(0)
    cleanup()
  })

  it('SettingsPage prefs tabs use Switch, never Checkbox', async () => {
    render(
      <SettingsPage
        config={config}
        onPatch={() => {}}
        onSnapshotRestore={() => {}}
      />,
    )
    // Visit each prefs tab and verify no Checkbox shows.
    for (const tab of ['Filters', 'Picker', 'Interface', 'Updates', 'Media']) {
      await userEvent.click(screen.getByRole('tab', { name: tab }))
      expect(
        screen.queryAllByRole('checkbox'),
        `Tab "${tab}" leaked a Checkbox`,
      ).toHaveLength(0)
    }
    cleanup()
  })
})

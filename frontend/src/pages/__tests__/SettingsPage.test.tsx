import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { SettingsPage } from '../SettingsPage'
import type { AppConfigResponse } from '@/api/types'

const config: AppConfigResponse = {
  paths: {
    source_roms: '/mnt/roms',
    source_dat: '/mnt/dat.xml',
    dest_roms: '/mnt/dest',
    retroarch_playlist: '/mnt/mame.lpl',
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
    region_priority: ['World'],
    preferred_genres: [],
    preferred_publishers: [],
    preferred_developers: [],
    prefer_parent_over_clone: true,
    prefer_good_driver: true,
  },
  media: { fetch_videos: false, cache_dir: './data/media-cache' },
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

describe('SettingsPage', () => {
  it('renders every section header (FP11 § B3 — 8 tabs incl. snapshots + about)', () => {
    render(
      <SettingsPage
        config={config}
        onPatch={() => {}}
        onSnapshotRestore={() => {}}
      />,
    )
    expect(screen.getByText(/^Paths$/)).toBeInTheDocument()
    expect(screen.getByText(/^Filters$/)).toBeInTheDocument()
    expect(screen.getByText(/^Picker$/)).toBeInTheDocument()
    expect(screen.getByText(/^Interface$/)).toBeInTheDocument()
    expect(screen.getByText(/^Updates$/)).toBeInTheDocument()
    expect(screen.getByText(/^Media$/)).toBeInTheDocument()
    expect(screen.getByText(/^Snapshots$/)).toBeInTheDocument()
    expect(screen.getByText(/^About$/)).toBeInTheDocument()
  })

  it('renders the R36 update banner when updateInfo is provided (FP11 § B3)', async () => {
    render(
      <SettingsPage
        config={config}
        onPatch={() => {}}
        onSnapshotRestore={() => {}}
        updateInfo={{
          current_version: '0.0.1',
          latest_version: '0.0.2',
          update_available: true,
        }}
      />,
    )
    await userEvent.click(screen.getByRole('tab', { name: /^Updates$/ }))
    expect(screen.getByText(/0\.0\.1.*0\.0\.2/)).toBeInTheDocument()
  })

  it('uses Switch (not Checkbox) on the Filters tab', async () => {
    render(
      <SettingsPage
        config={config}
        onPatch={() => {}}
        onSnapshotRestore={() => {}}
      />,
    )
    await userEvent.click(screen.getByRole('tab', { name: /^Filters$/ }))
    expect(screen.queryAllByRole('checkbox')).toHaveLength(0)
    expect(screen.getAllByRole('switch').length).toBeGreaterThan(0)
  })

  it('calls onPatch when a Filters Switch is toggled', async () => {
    const onPatch = vi.fn()
    render(
      <SettingsPage
        config={config}
        onPatch={onPatch}
        onSnapshotRestore={() => {}}
      />,
    )
    await userEvent.click(screen.getByRole('tab', { name: /^Filters$/ }))
    const firstSwitch = screen.getAllByRole('switch')[0]!
    await userEvent.click(firstSwitch)
    expect(onPatch).toHaveBeenCalled()
  })
})

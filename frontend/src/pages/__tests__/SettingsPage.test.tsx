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

  it('renders 4 chip-list editors on the Filters tab (FP12 § A)', async () => {
    render(
      <SettingsPage
        config={config}
        onPatch={() => {}}
        onSnapshotRestore={() => {}}
      />,
    )
    await userEvent.click(screen.getByRole('tab', { name: /^Filters$/ }))
    expect(screen.getByPlaceholderText('Add category…')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Add genre…')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Add publisher…')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Add developer…')).toBeInTheDocument()
  })

  it('renders 3 chip-list editors on the Picker tab (FP12 § A)', async () => {
    const pickerConfig = {
      ...config,
      filters: {
        ...config.filters,
        preferred_genres: ['shooter'],
        preferred_publishers: ['capcom'],
      },
    }
    render(
      <SettingsPage
        config={pickerConfig}
        onPatch={() => {}}
        onSnapshotRestore={() => {}}
      />,
    )
    await userEvent.click(screen.getByRole('tab', { name: /^Picker$/ }))
    // 3 placeholders, one per chip-list field (preferred_*).
    expect(
      screen.getAllByPlaceholderText(/^Add (genre|publisher|developer)…$/),
    ).toHaveLength(3)
    // Existing values render as chips with remove buttons.
    expect(screen.getByRole('button', { name: 'Remove shooter' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Remove capcom' })).toBeInTheDocument()
  })

  it('patches the filters list when a chip is added via Enter (FP12 § A)', async () => {
    const onPatch = vi.fn()
    render(
      <SettingsPage
        config={config}
        onPatch={onPatch}
        onSnapshotRestore={() => {}}
      />,
    )
    await userEvent.click(screen.getByRole('tab', { name: /^Filters$/ }))
    const input = screen.getByPlaceholderText('Add genre…')
    await userEvent.type(input, 'shooter{Enter}')
    expect(onPatch).toHaveBeenCalledWith(
      expect.objectContaining({
        filters: expect.objectContaining({ drop_genres: ['shooter'] }),
      }),
    )
  })

  it('patches drop_year_before when the year-range switch is toggled on (FP12 § C)', async () => {
    const onPatch = vi.fn()
    render(
      <SettingsPage
        config={config}
        onPatch={onPatch}
        onSnapshotRestore={() => {}}
      />,
    )
    await userEvent.click(screen.getByRole('tab', { name: /^Filters$/ }))
    await userEvent.click(
      screen.getByRole('switch', {
        name: 'Apply Drop games before year filter',
      }),
    )
    expect(onPatch).toHaveBeenCalledWith(
      expect.objectContaining({
        filters: expect.objectContaining({ drop_year_before: 1971 }),
      }),
    )
  })

  it('patches region_priority when reordered on the Picker tab (FP12 § B)', async () => {
    const onPatch = vi.fn()
    const cfg: AppConfigResponse = {
      ...config,
      filters: { ...config.filters, region_priority: ['us', 'eu', 'jp'] },
    }
    render(
      <SettingsPage
        config={cfg}
        onPatch={onPatch}
        onSnapshotRestore={() => {}}
      />,
    )
    await userEvent.click(screen.getByRole('tab', { name: /^Picker$/ }))
    expect(
      screen.getByRole('list', { name: 'Region priority' }),
    ).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Move us down' }))
    expect(onPatch).toHaveBeenCalledWith(
      expect.objectContaining({
        filters: expect.objectContaining({
          region_priority: ['eu', 'us', 'jp'],
        }),
      }),
    )
  })
})

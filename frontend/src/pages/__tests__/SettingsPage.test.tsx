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
  it('renders every section header (FP12 § J — 9 tabs incl. backup)', () => {
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
    expect(screen.getByText(/^Backup & restore$/)).toBeInTheDocument()
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

  it('renders the updates.channel dropdown with the current value (FP12 § E)', async () => {
    render(
      <SettingsPage
        config={config}
        onPatch={() => {}}
        onSnapshotRestore={() => {}}
      />,
    )
    await userEvent.click(screen.getByRole('tab', { name: /^Updates$/ }))
    const trigger = screen.getByRole('combobox', { name: 'Update channel' })
    expect(trigger).toHaveTextContent('Stable')
  })

  it('patches updates.channel when a new option is picked (FP12 § E)', async () => {
    const onPatch = vi.fn()
    render(
      <SettingsPage
        config={config}
        onPatch={onPatch}
        onSnapshotRestore={() => {}}
      />,
    )
    await userEvent.click(screen.getByRole('tab', { name: /^Updates$/ }))
    await userEvent.click(
      screen.getByRole('combobox', { name: 'Update channel' }),
    )
    await userEvent.click(screen.getByRole('option', { name: 'Dev' }))
    expect(onPatch).toHaveBeenCalledWith(
      expect.objectContaining({
        updates: expect.objectContaining({ channel: 'dev' }),
      }),
    )
  })

  it('renders the default_sort dropdown with the current value (FP12 § D)', async () => {
    render(
      <SettingsPage
        config={config}
        onPatch={() => {}}
        onSnapshotRestore={() => {}}
      />,
    )
    await userEvent.click(screen.getByRole('tab', { name: /^Interface$/ }))
    const trigger = screen.getByRole('combobox', { name: 'Default sort order' })
    expect(trigger).toHaveTextContent('By name')
  })

  it('patches ui.default_sort when a new option is picked (FP12 § D)', async () => {
    const onPatch = vi.fn()
    render(
      <SettingsPage
        config={config}
        onPatch={onPatch}
        onSnapshotRestore={() => {}}
      />,
    )
    await userEvent.click(screen.getByRole('tab', { name: /^Interface$/ }))
    await userEvent.click(
      screen.getByRole('combobox', { name: 'Default sort order' }),
    )
    await userEvent.click(screen.getByRole('option', { name: 'By year' }))
    expect(onPatch).toHaveBeenCalledWith(
      expect.objectContaining({
        ui: expect.objectContaining({ default_sort: 'year' }),
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

  it('renders the snapshot list when given snapshots (FP12 § I)', async () => {
    render(
      <SettingsPage
        config={config}
        onPatch={() => {}}
        onSnapshotRestore={() => {}}
        snapshots={[
          {
            id: '20260502T164321Z-abc',
            ts: new Date('2026-05-02T16:43:21Z'),
            files: ['config.yaml', 'overrides.yaml'],
          },
        ]}
      />,
    )
    await userEvent.click(screen.getByRole('tab', { name: /^Snapshots$/ }))
    expect(
      screen.getByRole('button', { name: /^Restore$/ }),
    ).toBeInTheDocument()
    expect(screen.getByText(/2 files/)).toBeInTheDocument()
  })

  it('propagates the snapshot id to onSnapshotRestore on confirm (FP12 § I)', async () => {
    const onSnapshotRestore = vi.fn()
    render(
      <SettingsPage
        config={config}
        onPatch={() => {}}
        onSnapshotRestore={onSnapshotRestore}
        snapshots={[
          {
            id: '20260502T164321Z-abc',
            ts: new Date('2026-05-02T16:43:21Z'),
            files: ['config.yaml', 'overrides.yaml'],
          },
        ]}
      />,
    )
    await userEvent.click(screen.getByRole('tab', { name: /^Snapshots$/ }))
    await userEvent.click(screen.getByRole('button', { name: /^Restore$/ }))
    await userEvent.click(
      screen.getByRole('button', { name: 'Restore 2 files' }),
    )
    expect(onSnapshotRestore).toHaveBeenCalledExactlyOnceWith(
      '20260502T164321Z-abc',
    )
  })

  it('renders an editable media.cache_dir input on the Media tab (FP12 § F)', async () => {
    render(
      <SettingsPage
        config={config}
        onPatch={() => {}}
        onSnapshotRestore={() => {}}
      />,
    )
    await userEvent.click(screen.getByRole('tab', { name: /^Media$/ }))
    const input = screen.getByLabelText(
      /^Media cache directory$/,
    ) as HTMLInputElement
    expect(input.value).toBe('./data/media-cache')
  })

  it('patches media.cache_dir on blur when the value changes (FP12 § F)', async () => {
    const onPatch = vi.fn()
    render(
      <SettingsPage
        config={config}
        onPatch={onPatch}
        onSnapshotRestore={() => {}}
      />,
    )
    await userEvent.click(screen.getByRole('tab', { name: /^Media$/ }))
    const input = screen.getByLabelText(/^Media cache directory$/)
    await userEvent.clear(input)
    await userEvent.type(input, '/tmp/new-cache')
    await userEvent.tab()
    expect(onPatch).toHaveBeenCalledWith(
      expect.objectContaining({
        media: expect.objectContaining({ cache_dir: '/tmp/new-cache' }),
      }),
    )
  })

  it('renders 4 editable path rows on the Paths tab (FP12 § H)', () => {
    render(
      <SettingsPage
        config={config}
        onPatch={() => {}}
        onSnapshotRestore={() => {}}
      />,
    )
    expect(screen.getByLabelText(/^Source ROMs$/)).toHaveValue('/mnt/roms')
    expect(screen.getByLabelText(/^Destination$/)).toHaveValue('/mnt/dest')
    expect(screen.getByLabelText(/^DAT$/)).toHaveValue('/mnt/dat.xml')
    expect(screen.getByLabelText(/^RetroArch playlist$/)).toHaveValue(
      '/mnt/mame.lpl',
    )
  })

  it('patches paths.source_roms on blur (FP12 § H)', async () => {
    const onPatch = vi.fn()
    render(
      <SettingsPage
        config={config}
        onPatch={onPatch}
        onSnapshotRestore={() => {}}
      />,
    )
    const input = screen.getByLabelText(/^Source ROMs$/)
    await userEvent.clear(input)
    await userEvent.type(input, '/new/roms')
    await userEvent.tab()
    expect(onPatch).toHaveBeenCalledWith(
      expect.objectContaining({
        paths: expect.objectContaining({ source_roms: '/new/roms' }),
      }),
    )
  })

  it('does not patch the DAT immediately — surfaces a destructive confirm (FP12 § H)', async () => {
    const onPatch = vi.fn()
    render(
      <SettingsPage
        config={config}
        onPatch={onPatch}
        onSnapshotRestore={() => {}}
      />,
    )
    const input = screen.getByLabelText(/^DAT$/)
    await userEvent.clear(input)
    await userEvent.type(input, '/new/dat.xml')
    await userEvent.tab()
    expect(onPatch).not.toHaveBeenCalled()
    expect(
      screen.getByRole('alertdialog', { name: /swap dat/i }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Swap DAT to /new/dat.xml' }),
    ).toBeInTheDocument()
  })

  it('patches the DAT only after the confirm dialog is accepted (FP12 § H)', async () => {
    const onPatch = vi.fn()
    render(
      <SettingsPage
        config={config}
        onPatch={onPatch}
        onSnapshotRestore={() => {}}
      />,
    )
    const input = screen.getByLabelText(/^DAT$/)
    await userEvent.clear(input)
    await userEvent.type(input, '/new/dat.xml')
    await userEvent.tab()
    await userEvent.click(
      screen.getByRole('button', { name: 'Swap DAT to /new/dat.xml' }),
    )
    expect(onPatch).toHaveBeenCalledWith(
      expect.objectContaining({
        paths: expect.objectContaining({ source_dat: '/new/dat.xml' }),
      }),
    )
  })

  it('does not patch the DAT if the confirm is cancelled (FP12 § H)', async () => {
    const onPatch = vi.fn()
    render(
      <SettingsPage
        config={config}
        onPatch={onPatch}
        onSnapshotRestore={() => {}}
      />,
    )
    const input = screen.getByLabelText(/^DAT$/)
    await userEvent.clear(input)
    await userEvent.type(input, '/new/dat.xml')
    await userEvent.tab()
    await userEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(onPatch).not.toHaveBeenCalled()
  })

  it('fires onBackupExport when Export is clicked on the Backup tab (FP12 § J)', async () => {
    const onBackupExport = vi.fn()
    render(
      <SettingsPage
        config={config}
        onPatch={() => {}}
        onSnapshotRestore={() => {}}
        onBackupExport={onBackupExport}
      />,
    )
    await userEvent.click(
      screen.getByRole('tab', { name: /^Backup & restore$/ }),
    )
    await userEvent.click(screen.getByRole('button', { name: /^Export/ }))
    expect(onBackupExport).toHaveBeenCalledOnce()
  })

  it('renders the restart-required banner when config.restart_required is true (FP13 § A4)', () => {
    render(
      <SettingsPage
        config={{ ...config, restart_required: true }}
        onPatch={() => {}}
        onSnapshotRestore={() => {}}
      />,
    )
    expect(
      screen.getByText(/restart `mame-curator serve`/i),
    ).toBeInTheDocument()
  })

  it('omits the restart-required banner when config.restart_required is false (FP13 § A4)', () => {
    render(
      <SettingsPage
        config={config}
        onPatch={() => {}}
        onSnapshotRestore={() => {}}
      />,
    )
    expect(
      screen.queryByText(/restart `mame-curator serve`/i),
    ).not.toBeInTheDocument()
  })
})

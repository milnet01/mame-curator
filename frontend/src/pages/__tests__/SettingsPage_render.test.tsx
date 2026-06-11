import { describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { SettingsPage } from '../SettingsPage'

import { config, render } from './_settingsPageFixtures'

/**
 * DS05 Cluster A1 — upper-file tab-rendering tests for SettingsPage.
 *
 * Extracted from `SettingsPage.test.tsx` (was L72-L349) so both files
 * stay under the 500-line hard cap. Covers: 9-tab header render
 * assertion + RetroArch Setup-banner parameter table + Updates R36
 * banner + Filters/Picker chip-list render-and-patch + Updates,
 * Interface dropdown render-and-patch pairs through cards_per_row_hint
 * integer-cast. The `render` wrapper + `config` AppConfig literal are
 * imported from `_settingsPageFixtures.ts` (sibling, leading-underscore =
 * not a test file).
 */

describe('SettingsPage — render', () => {
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

  // DS04 T2.12: collapsed two near-identical 70-line tests for
  // `retroarch_configured` true / false into one `it.each` table over
  // `(configured, expected)`. The full `setupInfo` shape lives in a
  // local helper so both branches share one literal.
  function makeSetupInfo(retroarch_configured: boolean) {
    return {
      config_present: true,
      paths: {
        source_roms: { path: '/mnt/roms', exists: true, readable: true, writable: true, dat_parses: null },
        source_dat: {
          path: '/mnt/dat.xml',
          exists: true,
          readable: true,
          writable: false,
          dat_parses: true,
        },
        dest_roms: { path: '/mnt/dest', exists: true, readable: true, writable: true, dat_parses: null },
      },
      reference_files: {
        catver: { path: '', exists: false },
        languages: { path: '', exists: false },
        bestgames: { path: '', exists: false },
        mature: { path: '', exists: false },
        series: { path: '', exists: false },
        listxml: { path: '', exists: false },
      },
      cloneof_map_size: 0,
      retroarch_configured,
    }
  }

  it.each<[boolean, RegExp]>([
    [false, /RetroArch: not configured/i],
    [true, /RetroArch: configured/i],
  ])(
    'shows the RetroArch Setup-banner line for retroarch_configured=%s (FP22-C)',
    (configured, expectedText) => {
      render(
        <SettingsPage
          config={config}
          onPatch={() => {}}
          onSnapshotRestore={() => {}}
          setupInfo={makeSetupInfo(configured)}
        />,
      )
      expect(screen.getByText(expectedText)).toBeInTheDocument()
    },
  )

  it('renders the R36 update banner when updateInfo is provided (FP11 § B3)', async () => {
    const user = userEvent.setup()
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
    await user.click(screen.getByRole('tab', { name: /^Updates$/ }))
    expect(screen.getByText(/0\.0\.1.*0\.0\.2/)).toBeInTheDocument()
  })

  it('uses Switch (not Checkbox) on the Filters tab', async () => {
    const user = userEvent.setup()
    render(
      <SettingsPage
        config={config}
        onPatch={() => {}}
        onSnapshotRestore={() => {}}
      />,
    )
    await user.click(screen.getByRole('tab', { name: /^Filters$/ }))
    expect(screen.queryAllByRole('checkbox')).toHaveLength(0)
    expect(screen.getAllByRole('switch').length).toBeGreaterThan(0)
  })

  it('calls onPatch when a Filters Switch is toggled', async () => {
    const user = userEvent.setup()
    const onPatch = vi.fn()
    render(
      <SettingsPage
        config={config}
        onPatch={onPatch}
        onSnapshotRestore={() => {}}
      />,
    )
    await user.click(screen.getByRole('tab', { name: /^Filters$/ }))
    const firstSwitch = screen.getAllByRole('switch')[0]!
    await user.click(firstSwitch)
    expect(onPatch).toHaveBeenCalled()
  })

  it('renders 4 chip-list editors on the Filters tab (FP12 § A)', async () => {
    const user = userEvent.setup()
    render(
      <SettingsPage
        config={config}
        onPatch={() => {}}
        onSnapshotRestore={() => {}}
      />,
    )
    await user.click(screen.getByRole('tab', { name: /^Filters$/ }))
    expect(screen.getByPlaceholderText('Add category…')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Add genre…')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Add publisher…')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Add developer…')).toBeInTheDocument()
  })

  it('renders 3 chip-list editors on the Picker tab (FP12 § A)', async () => {
    const user = userEvent.setup()
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
    await user.click(screen.getByRole('tab', { name: /^Picker$/ }))
    // 3 placeholders, one per chip-list field (preferred_*).
    expect(
      screen.getAllByPlaceholderText(/^Add (genre|publisher|developer)…$/),
    ).toHaveLength(3)
    // Existing values render as chips with remove buttons.
    expect(
      screen.getByRole('button', { name: 'Remove shooter from Preferred genres' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Remove capcom from Preferred publishers' }),
    ).toBeInTheDocument()
  })

  it('patches the filters list when a chip is added via Enter (FP12 § A)', async () => {
    const user = userEvent.setup()
    const onPatch = vi.fn()
    render(
      <SettingsPage
        config={config}
        onPatch={onPatch}
        onSnapshotRestore={() => {}}
      />,
    )
    await user.click(screen.getByRole('tab', { name: /^Filters$/ }))
    const input = screen.getByPlaceholderText('Add genre…')
    await user.type(input, 'shooter{Enter}')
    expect(onPatch).toHaveBeenCalledWith(
      expect.objectContaining({
        filters: expect.objectContaining({ drop_genres: ['shooter'] }),
      }),
    )
  })

  it('renders the updates.channel dropdown with the current value (FP12 § E)', async () => {
    const user = userEvent.setup()
    render(
      <SettingsPage
        config={config}
        onPatch={() => {}}
        onSnapshotRestore={() => {}}
      />,
    )
    await user.click(screen.getByRole('tab', { name: /^Updates$/ }))
    const trigger = screen.getByRole('combobox', { name: 'Update channel' })
    expect(trigger).toHaveTextContent('Stable')
  })

  it('patches updates.channel when a new option is picked (FP12 § E)', async () => {
    const user = userEvent.setup()
    const onPatch = vi.fn()
    render(
      <SettingsPage
        config={config}
        onPatch={onPatch}
        onSnapshotRestore={() => {}}
      />,
    )
    await user.click(screen.getByRole('tab', { name: /^Updates$/ }))
    await user.click(
      screen.getByRole('combobox', { name: 'Update channel' }),
    )
    await user.click(screen.getByRole('option', { name: 'Dev' }))
    expect(onPatch).toHaveBeenCalledWith(
      expect.objectContaining({
        updates: expect.objectContaining({ channel: 'dev' }),
      }),
    )
  })

  it('renders the default_sort dropdown with the current value (FP12 § D)', async () => {
    const user = userEvent.setup()
    render(
      <SettingsPage
        config={config}
        onPatch={() => {}}
        onSnapshotRestore={() => {}}
      />,
    )
    await user.click(screen.getByRole('tab', { name: /^Interface$/ }))
    const trigger = screen.getByRole('combobox', { name: 'Default sort order' })
    expect(trigger).toHaveTextContent('By name')
  })

  it('patches ui.default_sort when a new option is picked (FP12 § D)', async () => {
    const user = userEvent.setup()
    const onPatch = vi.fn()
    render(
      <SettingsPage
        config={config}
        onPatch={onPatch}
        onSnapshotRestore={() => {}}
      />,
    )
    await user.click(screen.getByRole('tab', { name: /^Interface$/ }))
    await user.click(
      screen.getByRole('combobox', { name: 'Default sort order' }),
    )
    await user.click(screen.getByRole('option', { name: 'By year' }))
    expect(onPatch).toHaveBeenCalledWith(
      expect.objectContaining({
        ui: expect.objectContaining({ default_sort: 'year' }),
      }),
    )
  })

  it('renders the cards_per_row_hint dropdown with the current value (P07 § C)', async () => {
    const user = userEvent.setup()
    render(
      <SettingsPage
        config={config}
        onPatch={() => {}}
        onSnapshotRestore={() => {}}
      />,
    )
    await user.click(screen.getByRole('tab', { name: /^Interface$/ }))
    const trigger = screen.getByRole('combobox', { name: 'Cards per row' })
    expect(trigger).toHaveTextContent('Automatic')
  })

  it('patches ui.cards_per_row_hint as a number when an integer option is picked (P07 § C)', async () => {
    const user = userEvent.setup()
    const onPatch = vi.fn()
    render(
      <SettingsPage
        config={config}
        onPatch={onPatch}
        onSnapshotRestore={() => {}}
      />,
    )
    await user.click(screen.getByRole('tab', { name: /^Interface$/ }))
    await user.click(
      screen.getByRole('combobox', { name: 'Cards per row' }),
    )
    await user.click(screen.getByRole('option', { name: '6 columns' }))
    expect(onPatch).toHaveBeenCalledWith(
      expect.objectContaining({
        ui: expect.objectContaining({ cards_per_row_hint: 6 }),
      }),
    )
  })

  // FP29 — the FP22-C setup banner directs users to "set paths.retroarch
  // and paths.retroarch_core in the Paths tab to enable launching", but
  // the tab shipped without inputs for either field — leaving the
  // Launch-in-RetroArch button (FP19) gated behind a config.yaml hand-
  // edit. These four tests pin the inputs on the Paths tab and the
  // nullable round-trip: empty string round-trips to `null` so the
  // backend schema (`retroarch: str | None`) stays clean.
  it('renders the RetroArch executable + core PathRows on the Paths tab (FP29)', () => {
    render(
      <SettingsPage
        config={config}
        onPatch={() => {}}
        onSnapshotRestore={() => {}}
      />,
    )
    expect(screen.getByLabelText('RetroArch executable')).toBeInTheDocument()
    expect(screen.getByLabelText('RetroArch core')).toBeInTheDocument()
  })

  it('patches paths.retroarch when the executable PathRow blurs (FP29)', async () => {
    const user = userEvent.setup()
    const onPatch = vi.fn()
    render(
      <SettingsPage
        config={config}
        onPatch={onPatch}
        onSnapshotRestore={() => {}}
      />,
    )
    const input = screen.getByLabelText('RetroArch executable')
    await user.type(input, '/usr/bin/retroarch')
    await user.tab()
    expect(onPatch).toHaveBeenCalledWith(
      expect.objectContaining({
        paths: expect.objectContaining({ retroarch: '/usr/bin/retroarch' }),
      }),
    )
  })

  it('patches paths.retroarch_core when the core PathRow blurs (FP29)', async () => {
    const user = userEvent.setup()
    const onPatch = vi.fn()
    render(
      <SettingsPage
        config={config}
        onPatch={onPatch}
        onSnapshotRestore={() => {}}
      />,
    )
    const input = screen.getByLabelText('RetroArch core')
    await user.type(input, '/path/to/mame_libretro.so')
    await user.tab()
    expect(onPatch).toHaveBeenCalledWith(
      expect.objectContaining({
        paths: expect.objectContaining({
          retroarch_core: '/path/to/mame_libretro.so',
        }),
      }),
    )
  })

  it('saves an empty RetroArch executable as null (FP29 nullable round-trip)', async () => {
    const user = userEvent.setup()
    const onPatch = vi.fn()
    const seededConfig = {
      ...config,
      paths: { ...config.paths, retroarch: '/old/retroarch' },
    }
    render(
      <SettingsPage
        config={seededConfig}
        onPatch={onPatch}
        onSnapshotRestore={() => {}}
      />,
    )
    const input = screen.getByLabelText('RetroArch executable')
    await user.clear(input)
    await user.tab()
    expect(onPatch).toHaveBeenCalledWith(
      expect.objectContaining({
        paths: expect.objectContaining({ retroarch: null }),
      }),
    )
  })
})

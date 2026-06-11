import { describe, expect, it, vi } from 'vitest'
import { render as rtlRender, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route, useLocation } from 'react-router'

import { SettingsPage } from '../SettingsPage'
import type { AppConfigResponse } from '@/api/types'

import { config, render } from './_settingsPageFixtures'

/**
 * DS05 Cluster A — main SettingsPage test file.
 *
 * Two seam-splits extracted to siblings:
 *   - `SettingsPage_render.test.tsx` covers the upper-file tab-rendering
 *     tests (was L72-L349).
 *   - `SettingsPage_destructive_confirm.test.tsx` covers the FP12 § H +
 *     FP13 § B2 destructive-DAT-confirm cluster (was L520-L602).
 *
 * This file retains the year-range / region-priority / snapshot /
 * media-cache / paths / backup-export / restart-banner /
 * cart_clear_on_copy tests + the DS02 D1 `?tab=` URL-state nested
 * describe. The `render` wrapper + `config` AppConfig literal moved to
 * `_settingsPageFixtures.ts` so all three test files share one source.
 */

describe('SettingsPage', () => {
  it('patches drop_year_before when the year-range switch is toggled on (FP12 § C)', async () => {
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
    await user.click(
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
    const user = userEvent.setup()
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
    await user.click(screen.getByRole('tab', { name: /^Picker$/ }))
    expect(
      screen.getByRole('list', { name: 'Region priority' }),
    ).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Move us down' }))
    expect(onPatch).toHaveBeenCalledWith(
      expect.objectContaining({
        filters: expect.objectContaining({
          region_priority: ['eu', 'us', 'jp'],
        }),
      }),
    )
  })

  it('renders the snapshot list when given snapshots (FP12 § I)', async () => {
    const user = userEvent.setup()
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
    await user.click(screen.getByRole('tab', { name: /^Snapshots$/ }))
    expect(
      screen.getByRole('button', { name: /^Restore$/ }),
    ).toBeInTheDocument()
    expect(screen.getByText(/2 files/)).toBeInTheDocument()
  })

  it('propagates the snapshot id to onSnapshotRestore on confirm (FP12 § I)', async () => {
    const user = userEvent.setup()
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
    await user.click(screen.getByRole('tab', { name: /^Snapshots$/ }))
    await user.click(screen.getByRole('button', { name: /^Restore$/ }))
    await user.click(
      screen.getByRole('button', { name: 'Restore 2 files' }),
    )
    expect(onSnapshotRestore).toHaveBeenCalledExactlyOnceWith(
      '20260502T164321Z-abc',
    )
  })

  it('renders an editable media.cache_dir input on the Media tab (FP12 § F)', async () => {
    const user = userEvent.setup()
    render(
      <SettingsPage
        config={config}
        onPatch={() => {}}
        onSnapshotRestore={() => {}}
      />,
    )
    await user.click(screen.getByRole('tab', { name: /^Media$/ }))
    const input = screen.getByLabelText(
      /^Media cache directory$/,
    ) as HTMLInputElement
    expect(input.value).toBe('./data/media-cache')
  })

  it('patches media.cache_dir on blur when the value changes (FP12 § F)', async () => {
    const user = userEvent.setup()
    const onPatch = vi.fn()
    render(
      <SettingsPage
        config={config}
        onPatch={onPatch}
        onSnapshotRestore={() => {}}
      />,
    )
    await user.click(screen.getByRole('tab', { name: /^Media$/ }))
    const input = screen.getByLabelText(/^Media cache directory$/)
    await user.clear(input)
    await user.type(input, '/tmp/new-cache')
    await user.tab()
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
    const user = userEvent.setup()
    const onPatch = vi.fn()
    render(
      <SettingsPage
        config={config}
        onPatch={onPatch}
        onSnapshotRestore={() => {}}
      />,
    )
    const input = screen.getByLabelText(/^Source ROMs$/)
    await user.clear(input)
    await user.type(input, '/new/roms')
    await user.tab()
    expect(onPatch).toHaveBeenCalledWith(
      expect.objectContaining({
        paths: expect.objectContaining({ source_roms: '/new/roms' }),
      }),
    )
  })

  it('fires onBackupExport when Export is clicked on the Backup tab (FP12 § J)', async () => {
    const user = userEvent.setup()
    const onBackupExport = vi.fn()
    render(
      <SettingsPage
        config={config}
        onPatch={() => {}}
        onSnapshotRestore={() => {}}
        onBackupExport={onBackupExport}
      />,
    )
    await user.click(
      screen.getByRole('tab', { name: /^Backup & restore$/ }),
    )
    await user.click(screen.getByRole('button', { name: /^Export/ }))
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

  it('renders the cart_clear_on_copy dropdown with the current value (P15 § F13)', async () => {
    const user = userEvent.setup()
    render(
      <SettingsPage
        config={config}
        onPatch={() => {}}
        onSnapshotRestore={() => {}}
      />,
    )
    await user.click(screen.getByRole('tab', { name: /^Interface$/ }))
    const trigger = screen.getByRole('combobox', { name: 'Clear cart after copy' })
    expect(trigger).toHaveTextContent('On success only')
  })

  it('patches ui.cart_clear_on_copy when a new option is picked (P15 § F13)', async () => {
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
      screen.getByRole('combobox', { name: 'Clear cart after copy' }),
    )
    await user.click(screen.getByRole('option', { name: 'Never' }))
    expect(onPatch).toHaveBeenCalledWith(
      expect.objectContaining({
        ui: expect.objectContaining({ cart_clear_on_copy: 'never' }),
      }),
    )
  })

  // DS02 D1 — Settings active-tab persists in the URL `?tab=…`.
  //
  // Pre-fix: the active tab lives in `useState` (or Radix
  // `defaultValue`), so reloading drops back to the default tab and
  // copy-paste-share of a deep-link to a non-default tab is
  // impossible. The Settings page should route the active tab
  // through `useSearchParams` so `?tab=backup` reloads on the
  // Backup & restore tab and clicking another tab rewrites the URL.
  describe('DS02 D1 — tab state lives in URL ?tab=', () => {
    function LocationSpy({ onLocation }: { onLocation: (s: string) => void }) {
      const loc = useLocation()
      onLocation(loc.pathname + loc.search)
      return null
    }

    function renderWithSpy(initialPath: string, onLocation: (s: string) => void = () => {}) {
      return rtlRender(
        <MemoryRouter initialEntries={[initialPath]}>
          <Routes>
            <Route
              path="/settings"
              element={
                <>
                  <LocationSpy onLocation={onLocation} />
                  <SettingsPage
                    config={config}
                    onPatch={() => {}}
                    onSnapshotRestore={() => {}}
                  />
                </>
              }
            />
          </Routes>
        </MemoryRouter>,
      )
    }

    it('?tab=backup activates the Backup & restore tab on load', () => {
      renderWithSpy('/settings?tab=backup')
      const tab = screen.getByRole('tab', { name: /^Backup & restore$/ })
      // Radix Tabs sets data-state="active" on the selected trigger.
      expect(tab.getAttribute('data-state')).toBe('active')
    })

    it('clicking a different tab rewrites the URL search param', async () => {
      const user = userEvent.setup()
      const seen: string[] = []
      renderWithSpy('/settings', (s) => seen.push(s))
      await user.click(screen.getByRole('tab', { name: /^Filters$/ }))
      // After click, the URL must include ?tab=filters (or equivalent
      // canonical encoding). Assert via the captured location stream.
      const last = seen[seen.length - 1]
      expect(last).toMatch(/[?&]tab=filters\b/i)
    })

    it('default tab loads when ?tab= is absent', () => {
      renderWithSpy('/settings')
      // Pre-existing default is `paths`. Lock that behaviour so the
      // useSearchParams wiring doesn't accidentally change defaults.
      const tab = screen.getByRole('tab', { name: /^Paths$/ })
      expect(tab.getAttribute('data-state')).toBe('active')
    })
  })
})

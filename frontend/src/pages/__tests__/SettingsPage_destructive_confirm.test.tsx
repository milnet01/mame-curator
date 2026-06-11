import { describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { SettingsPage } from '../SettingsPage'

import { config, render } from './_settingsPageFixtures'

/**
 * DS05 Cluster A2 — destructive-DAT-confirm cluster for SettingsPage.
 *
 * Extracted from `SettingsPage.test.tsx` (was L520-L602) so both files
 * stay under the 500-line hard cap. Covers the FP12 § H + FP13 § B2
 * confirm-dialog wiring around the source_dat path field: changing the
 * DAT immediately must not patch; the AlertDialog must surface a
 * specific Swap button; accept patches; cancel reverts the input;
 * cancel-after-revert doesn't fire onPatch. The `render` wrapper +
 * `config` literal come from `_settingsPageFixtures.ts`.
 */

describe('SettingsPage — destructive DAT confirm', () => {
  it('does not patch the DAT immediately — surfaces a destructive confirm (FP12 § H)', async () => {
    const user = userEvent.setup()
    const onPatch = vi.fn()
    render(
      <SettingsPage
        config={config}
        onPatch={onPatch}
        onSnapshotRestore={() => {}}
      />,
    )
    const input = screen.getByLabelText(/^DAT$/)
    await user.clear(input)
    await user.type(input, '/new/dat.xml')
    await user.tab()
    expect(onPatch).not.toHaveBeenCalled()
    expect(
      screen.getByRole('alertdialog', { name: /swap dat/i }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Swap DAT to /new/dat.xml' }),
    ).toBeInTheDocument()
  })

  it('patches the DAT only after the confirm dialog is accepted (FP12 § H)', async () => {
    const user = userEvent.setup()
    const onPatch = vi.fn()
    render(
      <SettingsPage
        config={config}
        onPatch={onPatch}
        onSnapshotRestore={() => {}}
      />,
    )
    const input = screen.getByLabelText(/^DAT$/)
    await user.clear(input)
    await user.type(input, '/new/dat.xml')
    await user.tab()
    await user.click(
      screen.getByRole('button', { name: 'Swap DAT to /new/dat.xml' }),
    )
    expect(onPatch).toHaveBeenCalledWith(
      expect.objectContaining({
        paths: expect.objectContaining({ source_dat: '/new/dat.xml' }),
      }),
    )
  })

  it('reverts the DAT input back to the prior value when the confirm is cancelled (FP13 § B2)', async () => {
    const user = userEvent.setup()
    render(
      <SettingsPage
        config={config}
        onPatch={() => {}}
        onSnapshotRestore={() => {}}
      />,
    )
    const input = screen.getByLabelText(/^DAT$/) as HTMLInputElement
    await user.clear(input)
    await user.type(input, '/new/dat.xml')
    await user.tab()
    await user.click(screen.getByRole('button', { name: /cancel/i }))
    // After cancel, the input should re-mount and re-seed from the unchanged
    // `value` prop. Without the FP13 § B2 reset-tick this assertion fails —
    // the old `draft` state retains '/new/dat.xml'.
    expect((screen.getByLabelText(/^DAT$/) as HTMLInputElement).value).toBe(
      config.paths.source_dat,
    )
  })

  it('does not patch the DAT if the confirm is cancelled (FP12 § H)', async () => {
    const user = userEvent.setup()
    const onPatch = vi.fn()
    render(
      <SettingsPage
        config={config}
        onPatch={onPatch}
        onSnapshotRestore={() => {}}
      />,
    )
    const input = screen.getByLabelText(/^DAT$/)
    await user.clear(input)
    await user.type(input, '/new/dat.xml')
    await user.tab()
    await user.click(screen.getByRole('button', { name: /cancel/i }))
    expect(onPatch).not.toHaveBeenCalled()
  })
})

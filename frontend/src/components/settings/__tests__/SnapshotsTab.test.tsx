import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { SnapshotsTab } from '../SnapshotsTab'
import type { Snapshot } from '@/api/types'

// DS04 T3.1: removed redundant `afterEach(() => cleanup())` — vitest
// `globals: true` enables RTL's auto-cleanup.

const sample: readonly Snapshot[] = [
  {
    id: '20260502T164321Z-abc123',
    ts: new Date('2026-05-02T16:43:21Z'),
    files: ['config.yaml', 'overrides.yaml', 'sessions.yaml', 'notes.json'],
  },
  {
    id: '20260501T091500Z-def456',
    ts: new Date('2026-05-01T09:15:00Z'),
    files: ['config.yaml'],
  },
]

describe('SnapshotsTab (FP12 § I)', () => {
  it('renders loading state when loading', () => {
    render(<SnapshotsTab snapshots={[]} loading onRestore={() => {}} />)
    expect(screen.getByText(/loading snapshots/i)).toBeInTheDocument()
  })

  it('renders error state when error is set', () => {
    render(
      <SnapshotsTab
        snapshots={[]}
        error="Could not load snapshots."
        onRestore={() => {}}
      />,
    )
    expect(screen.getByRole('alert')).toHaveTextContent(/could not load/i)
  })

  it('renders empty state when there are no snapshots', () => {
    render(<SnapshotsTab snapshots={[]} onRestore={() => {}} />)
    expect(screen.getByText(/no snapshots yet/i)).toBeInTheDocument()
  })

  it('renders one row per snapshot with file count + restore button', () => {
    render(<SnapshotsTab snapshots={sample} onRestore={() => {}} />)
    expect(screen.getAllByRole('button', { name: /^Restore/ })).toHaveLength(2)
    expect(screen.getByText(/4 files/)).toBeInTheDocument()
    expect(screen.getByText(/^1 file$/)).toBeInTheDocument()
  })

  it('opens a confirmation dialog when Restore is clicked', async () => {
    const user = userEvent.setup()
    render(<SnapshotsTab snapshots={sample} onRestore={() => {}} />)
    const buttons = screen.getAllByRole('button', { name: /^Restore/ })
    await user.click(buttons[0]!)
    expect(
      screen.getByRole('alertdialog', { name: /restore configuration/i }),
    ).toBeInTheDocument()
  })

  it('uses a concrete action label including file count (design §8)', async () => {
    const user = userEvent.setup()
    render(<SnapshotsTab snapshots={sample} onRestore={() => {}} />)
    const buttons = screen.getAllByRole('button', { name: /^Restore/ })
    await user.click(buttons[0]!)
    expect(
      screen.getByRole('button', { name: 'Restore 4 files' }),
    ).toBeInTheDocument()
  })

  it('calls onRestore with the snapshot id only after confirming', async () => {
    const user = userEvent.setup()
    const onRestore = vi.fn()
    render(<SnapshotsTab snapshots={sample} onRestore={onRestore} />)
    const buttons = screen.getAllByRole('button', { name: /^Restore/ })
    await user.click(buttons[0]!)
    expect(onRestore).not.toHaveBeenCalled()
    await user.click(
      screen.getByRole('button', { name: 'Restore 4 files' }),
    )
    expect(onRestore).toHaveBeenCalledExactlyOnceWith(
      '20260502T164321Z-abc123',
    )
  })

  it('does not call onRestore when the dialog is cancelled', async () => {
    const user = userEvent.setup()
    const onRestore = vi.fn()
    render(<SnapshotsTab snapshots={sample} onRestore={onRestore} />)
    await user.click(
      screen.getAllByRole('button', { name: /^Restore/ })[0]!,
    )
    await user.click(screen.getByRole('button', { name: /cancel/i }))
    expect(onRestore).not.toHaveBeenCalled()
  })

  // ---- FP20-J: restoreError surfaces above the snapshot list -------------

  it('renders restoreError as an inline alert above the snapshot list', () => {
    /**
     * FP20-J: a restore-mutation failure used to surface only as a
     * dismissible toast — the confirmation dialog auto-closed and
     * the user was left looking at an unchanged list with no signal
     * that anything went wrong. The fix mirrors ``BackupTab.error``:
     * a persistent ``<p role="alert">`` above the list so the user
     * can read the failure reason after the toast has gone.
     */
    render(
      <SnapshotsTab
        snapshots={sample}
        restoreError="Could not restore snapshot: server returned 500."
        onRestore={() => {}}
      />,
    )
    expect(screen.getByRole('alert')).toHaveTextContent(/could not restore/i)
    // Critical: the list still renders below the alert. Earlier
    // load-time ``error`` early-returns and hides the list, but a
    // restoreError must not — the user needs the list visible to
    // try a different snapshot.
    expect(screen.getAllByRole('button', { name: /^Restore/ })).toHaveLength(2)
  })

  it('does not render an alert when restoreError is null', () => {
    render(
      <SnapshotsTab snapshots={sample} restoreError={null} onRestore={() => {}} />,
    )
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('restoreError still allows opening the restore dialog (user can try another)', async () => {
    const user = userEvent.setup()
    render(
      <SnapshotsTab
        snapshots={sample}
        restoreError="Last restore failed."
        onRestore={() => {}}
      />,
    )
    const buttons = screen.getAllByRole('button', { name: /^Restore/ })
    await user.click(buttons[1]!)
    expect(
      screen.getByRole('alertdialog', { name: /restore configuration/i }),
    ).toBeInTheDocument()
  })
})

import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { SnapshotsTab } from '../SnapshotsTab'
import type { Snapshot } from '@/api/types'

afterEach(() => cleanup())

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
    render(<SnapshotsTab snapshots={sample} onRestore={() => {}} />)
    const buttons = screen.getAllByRole('button', { name: /^Restore/ })
    await userEvent.click(buttons[0]!)
    expect(
      screen.getByRole('alertdialog', { name: /restore configuration/i }),
    ).toBeInTheDocument()
  })

  it('uses a concrete action label including file count (design §8)', async () => {
    render(<SnapshotsTab snapshots={sample} onRestore={() => {}} />)
    const buttons = screen.getAllByRole('button', { name: /^Restore/ })
    await userEvent.click(buttons[0]!)
    expect(
      screen.getByRole('button', { name: 'Restore 4 files' }),
    ).toBeInTheDocument()
  })

  it('calls onRestore with the snapshot id only after confirming', async () => {
    const onRestore = vi.fn()
    render(<SnapshotsTab snapshots={sample} onRestore={onRestore} />)
    const buttons = screen.getAllByRole('button', { name: /^Restore/ })
    await userEvent.click(buttons[0]!)
    expect(onRestore).not.toHaveBeenCalled()
    await userEvent.click(
      screen.getByRole('button', { name: 'Restore 4 files' }),
    )
    expect(onRestore).toHaveBeenCalledExactlyOnceWith(
      '20260502T164321Z-abc123',
    )
  })

  it('does not call onRestore when the dialog is cancelled', async () => {
    const onRestore = vi.fn()
    render(<SnapshotsTab snapshots={sample} onRestore={onRestore} />)
    await userEvent.click(
      screen.getAllByRole('button', { name: /^Restore/ })[0]!,
    )
    await userEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(onRestore).not.toHaveBeenCalled()
  })
})

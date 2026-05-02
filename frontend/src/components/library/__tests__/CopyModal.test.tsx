import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { CopyModal, type CopyModalState } from '../CopyModal'

const baseState: CopyModalState = {
  jobId: 'job-1',
  state: 'running',
  filesDone: 1,
  filesTotal: 3,
  bytesDone: 100,
  bytesTotal: 300,
  currentFile: 'pacman.zip',
  warnings: [],
  conflict: null,
}

describe('CopyModal', () => {
  it('renders the progress line and current file', () => {
    render(
      <CopyModal
        open
        onOpenChange={() => {}}
        state={baseState}
        onPause={() => {}}
        onResume={() => {}}
        onAbort={() => {}}
        onResolveConflict={() => {}}
      />,
    )
    expect(screen.getByText(/1 \/ 3/)).toBeInTheDocument()
    expect(screen.getByText(/pacman\.zip/)).toBeInTheDocument()
  })

  it('shows pause when running and resume when paused', async () => {
    const onPause = vi.fn()
    const onResume = vi.fn()
    const { rerender } = render(
      <CopyModal
        open
        onOpenChange={() => {}}
        state={baseState}
        onPause={onPause}
        onResume={onResume}
        onAbort={() => {}}
        onResolveConflict={() => {}}
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: /pause/i }))
    expect(onPause).toHaveBeenCalled()

    rerender(
      <CopyModal
        open
        onOpenChange={() => {}}
        state={{ ...baseState, state: 'paused' }}
        onPause={onPause}
        onResume={onResume}
        onAbort={() => {}}
        onResolveConflict={() => {}}
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: /resume/i }))
    expect(onResume).toHaveBeenCalled()
  })

  it('opens the abort prompt offering BOTH keep + recycle paths (FP11 § A3)', async () => {
    const onAbort = vi.fn()
    render(
      <CopyModal
        open
        onOpenChange={() => {}}
        state={baseState}
        onPause={() => {}}
        onResume={() => {}}
        onAbort={onAbort}
        onResolveConflict={() => {}}
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: /cancel/i }))
    // Spec / design §9: "Cancel asks whether to keep already-copied
    // files or remove them." Both paths must be reachable.
    expect(
      await screen.findByRole('button', { name: /keep files/i }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /move to recycle bin/i }),
    ).toBeInTheDocument()
  })

  it('aborts with recycle_partial=true when user picks recycle', async () => {
    const onAbort = vi.fn()
    render(
      <CopyModal
        open
        onOpenChange={() => {}}
        state={baseState}
        onPause={() => {}}
        onResume={() => {}}
        onAbort={onAbort}
        onResolveConflict={() => {}}
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: /cancel/i }))
    await userEvent.click(
      await screen.findByRole('button', { name: /move to recycle bin/i }),
    )
    expect(onAbort).toHaveBeenCalledWith({ recycle_partial: true })
  })

  it('aborts with recycle_partial=false when user picks keep', async () => {
    const onAbort = vi.fn()
    render(
      <CopyModal
        open
        onOpenChange={() => {}}
        state={baseState}
        onPause={() => {}}
        onResume={() => {}}
        onAbort={onAbort}
        onResolveConflict={() => {}}
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: /cancel/i }))
    await userEvent.click(
      await screen.findByRole('button', { name: /keep files/i }),
    )
    expect(onAbort).toHaveBeenCalledWith({ recycle_partial: false })
  })

  it('shows a Done button in terminal states (FP11 § D8)', async () => {
    const onOpenChange = vi.fn()
    const { rerender } = render(
      <CopyModal
        open
        onOpenChange={onOpenChange}
        state={{ ...baseState, state: 'finished' }}
        onPause={() => {}}
        onResume={() => {}}
        onAbort={() => {}}
        onResolveConflict={() => {}}
      />,
    )
    const done = screen.getByRole('button', { name: /^done$/i })
    expect(done).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /pause/i })).toBeNull()
    expect(screen.queryByRole('button', { name: /^cancel$/i })).toBeNull()
    await userEvent.click(done)
    expect(onOpenChange).toHaveBeenCalledWith(false)

    rerender(
      <CopyModal
        open
        onOpenChange={onOpenChange}
        state={{ ...baseState, state: 'aborted' }}
        onPause={() => {}}
        onResume={() => {}}
        onAbort={() => {}}
        onResolveConflict={() => {}}
      />,
    )
    expect(screen.getByRole('button', { name: /^done$/i })).toBeInTheDocument()
  })

  it('renders the conflict prompt when the state carries one', () => {
    render(
      <CopyModal
        open
        onOpenChange={() => {}}
        state={{
          ...baseState,
          state: 'paused',
          conflict: {
            short_name: 'pacman',
            existing: 'pacmanf',
          },
        }}
        onPause={() => {}}
        onResume={() => {}}
        onAbort={() => {}}
        onResolveConflict={() => {}}
      />,
    )
    expect(
      screen.getByText(/Existing playlist detected/i),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /keep existing/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^replace$/i })).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /replace and recycle/i }),
    ).toBeInTheDocument()
  })
})

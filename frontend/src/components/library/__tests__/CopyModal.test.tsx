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

  it('opens the abort confirmation and forwards onAbort', async () => {
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
    // ConfirmationDialog action label is concrete per design rules.
    const confirm = await screen.findByRole('button', {
      name: /move to recycle bin/i,
    })
    await userEvent.click(confirm)
    expect(onAbort).toHaveBeenCalledWith({ recycle_partial: true })
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

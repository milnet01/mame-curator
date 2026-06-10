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

// Render the modal in its default running state and click Cancel to open
// the keep/recycle abort prompt; returns the onAbort spy so the caller can
// assert which path the user picks.
async function openAbortPrompt() {
  const onAbort = vi.fn()
  render(
    <CopyModal
      open
      onOpenChange={() => {}}
      state={baseState}
      onPause={() => {}}
      onResume={() => {}}
      onAbort={onAbort}
    />,
  )
  await userEvent.click(screen.getByRole('button', { name: /cancel/i }))
  return onAbort
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
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: /pause/i }))
    expect(onPause).toHaveBeenCalledOnce()

    rerender(
      <CopyModal
        open
        onOpenChange={() => {}}
        state={{ ...baseState, state: 'paused' }}
        onPause={onPause}
        onResume={onResume}
        onAbort={() => {}}
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: /resume/i }))
    expect(onResume).toHaveBeenCalledOnce()
  })

  it('opens the abort prompt offering BOTH keep + recycle paths (FP11 § A3)', async () => {
    await openAbortPrompt()
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
    const onAbort = await openAbortPrompt()
    await userEvent.click(
      await screen.findByRole('button', { name: /move to recycle bin/i }),
    )
    expect(onAbort).toHaveBeenCalledWith({ recycle_partial: true })
  })

  it('aborts with recycle_partial=false when user picks keep', async () => {
    const onAbort = await openAbortPrompt()
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
      />,
    )
    expect(screen.getByRole('button', { name: /^done$/i })).toBeInTheDocument()
  })

  it('renders the conflict prompt as a read-only banner (FP27 A4)', () => {
    // The prior three Keep/Replace/Replace-and-recycle buttons were
    // removed because there is no /api/copy/resolve-conflict endpoint
    // — they silently dropped the user's choice. The banner now
    // points at the only real resolution path: abort + restart with
    // an updated append_decisions payload.
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
      />,
    )
    expect(screen.getByText(/Existing playlist detected/i)).toBeInTheDocument()
    expect(
      screen.getByText(/Restart the copy with updated append_decisions/i),
    ).toBeInTheDocument()
    // The prior three buttons are gone.
    expect(screen.queryByRole('button', { name: /keep existing/i })).toBeNull()
    expect(screen.queryByRole('button', { name: /^replace$/i })).toBeNull()
    expect(
      screen.queryByRole('button', { name: /replace and recycle/i }),
    ).toBeNull()
  })
})

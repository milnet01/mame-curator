import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { LibraryErrorPanel } from '../LibraryErrorPanel'
import { strings } from '@/strings'

describe('LibraryErrorPanel', () => {
  /**
   * FP20-I: the LibraryPage previously read ``games.data`` without
   * checking ``games.isError``; a backend outage surfaced as
   * "No games match your filters" with the action bar disabled — no
   * signal the failure was network-side. This panel is the inline
   * surface that replaces the grid on error, giving the user a clear
   * retry affordance even after the global toast (FP20-G) dismisses.
   */
  it('renders an alert role so screen readers announce assertively', () => {
    render(<LibraryErrorPanel onRetry={() => {}} />)
    const panel = screen.getByRole('alert')
    expect(panel).toBeInTheDocument()
  })

  it('shows the load-failed title and hint copy', () => {
    render(<LibraryErrorPanel onRetry={() => {}} />)
    expect(screen.getByText(strings.library.loadFailedTitle)).toBeInTheDocument()
    expect(screen.getByText(strings.library.loadFailedHint)).toBeInTheDocument()
  })

  it('renders a Retry button that invokes onRetry on click', async () => {
    const onRetry = vi.fn()
    render(<LibraryErrorPanel onRetry={onRetry} />)
    const button = screen.getByRole('button', { name: strings.common.retry })
    await userEvent.click(button)
    expect(onRetry).toHaveBeenCalledTimes(1)
  })
})

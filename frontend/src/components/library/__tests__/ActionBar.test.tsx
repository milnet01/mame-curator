import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { ActionBar } from '../ActionBar'

describe('ActionBar', () => {
  it('renders the count summary', () => {
    render(
      <ActionBar
        gameCount={2847}
        totalSizeBytes={18.2 * 1024 * 1024 * 1024}
        biosDepCount={47}
        onDryRun={() => {}}
        onCopy={() => {}}
      />,
    )
    expect(screen.getByText(/2,847 games/)).toBeInTheDocument()
    expect(screen.getByText(/18\.2.*GB/)).toBeInTheDocument()
    expect(screen.getByText(/47 BIOS deps/)).toBeInTheDocument()
  })

  it('calls onDryRun and onCopy when the matching buttons are clicked', async () => {
    const onDryRun = vi.fn()
    const onCopy = vi.fn()
    render(
      <ActionBar
        gameCount={1}
        totalSizeBytes={1024}
        biosDepCount={0}
        onDryRun={onDryRun}
        onCopy={onCopy}
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: /dry-run/i }))
    expect(onDryRun).toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button', { name: /^copy$/i }))
    expect(onCopy).toHaveBeenCalled()
  })

  it('disables both buttons when gameCount is zero', () => {
    render(
      <ActionBar
        gameCount={0}
        totalSizeBytes={0}
        biosDepCount={0}
        onDryRun={() => {}}
        onCopy={() => {}}
      />,
    )
    expect(screen.getByRole('button', { name: /dry-run/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /^copy$/i })).toBeDisabled()
  })
})

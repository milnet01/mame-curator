import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { ConfirmationDialog } from '../ConfirmationDialog'

describe('ConfirmationDialog', () => {
  it('renders the concrete action label and target description', () => {
    render(
      <ConfirmationDialog
        open
        onOpenChange={() => {}}
        title="Delete files"
        description="Delete 3 files from drive"
        actionLabel="Delete 3 files from drive"
        onConfirm={() => {}}
      />,
    )
    // The action label must NOT be a generic "OK".
    expect(screen.queryByRole('button', { name: /^OK$/ })).toBeNull()
    expect(
      screen.getByRole('button', { name: 'Delete 3 files from drive' }),
    ).toBeInTheDocument()
    // Both the AlertDialog description and the action button carry the
    // concrete target text.
    expect(screen.getAllByText('Delete 3 files from drive').length).toBeGreaterThanOrEqual(2)
  })

  it('throws if the action label is "OK"', () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() =>
      render(
        <ConfirmationDialog
          open
          onOpenChange={() => {}}
          title="x"
          description="x"
          actionLabel="OK"
          onConfirm={() => {}}
        />,
      ),
    ).toThrow(/concrete/i)
    errorSpy.mockRestore()
  })

  it('calls onConfirm and closes when the action button is clicked', async () => {
    const onConfirm = vi.fn()
    const onOpenChange = vi.fn()
    render(
      <ConfirmationDialog
        open
        onOpenChange={onOpenChange}
        title="Reset"
        description="Reset the configuration to defaults"
        actionLabel="Reset configuration"
        onConfirm={onConfirm}
      />,
    )
    await userEvent.click(
      screen.getByRole('button', { name: 'Reset configuration' }),
    )
    expect(onConfirm).toHaveBeenCalled()
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })
})

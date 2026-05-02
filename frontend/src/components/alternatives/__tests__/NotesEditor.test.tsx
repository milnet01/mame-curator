import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { NotesEditor } from '../NotesEditor'
import { strings } from '@/strings'

describe('NotesEditor', () => {
  it('hydrates the textarea from the initial note', () => {
    render(
      <NotesEditor initial="hard rom set" onSave={() => Promise.resolve()} />,
    )
    expect(screen.getByRole('textbox')).toHaveValue('hard rom set')
  })

  it('calls onSave when the textarea blurs with new content', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined)
    render(<NotesEditor initial="" onSave={onSave} />)
    const textarea = screen.getByRole('textbox')
    await userEvent.type(textarea, 'updated note')
    textarea.blur()
    // Wait one microtask for the blur handler.
    await Promise.resolve()
    expect(onSave).toHaveBeenCalledWith('updated note')
  })

  it('does not save when the content has not changed', () => {
    const onSave = vi.fn().mockResolvedValue(undefined)
    render(<NotesEditor initial="static" onSave={onSave} />)
    screen.getByRole('textbox').blur()
    expect(onSave).not.toHaveBeenCalled()
  })

  it('flips to the saved badge after a successful save', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined)
    render(<NotesEditor initial="" onSave={onSave} />)
    const textarea = screen.getByRole('textbox')
    await userEvent.type(textarea, 'changed')
    textarea.blur()
    await waitFor(() =>
      expect(screen.getByText(strings.notes.saved)).toBeInTheDocument(),
    )
  })

  it('shows the error badge with role="alert" when onSave rejects', async () => {
    const onSave = vi.fn().mockRejectedValue(new Error('boom'))
    render(<NotesEditor initial="" onSave={onSave} />)
    const textarea = screen.getByRole('textbox')
    await userEvent.type(textarea, 'changed')
    textarea.blur()
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(strings.notes.saveError)
  })

  // FP11 § D2: the "stuck error" guard. When a save fails, the error
  // badge stays put until the next save attempt — but the *moment* a
  // retry begins, the badge MUST flip to `saving` so the user doesn't
  // see a stale "Could not save" while a fresh request is in flight.
  it('clears a prior error to "saving" while a retry is in flight', async () => {
    const retry: { resolve?: () => void } = {}
    const onSave = vi
      .fn()
      .mockRejectedValueOnce(new Error('boom'))
      .mockImplementationOnce(
        () => new Promise<void>((res) => { retry.resolve = res }),
      )

    render(<NotesEditor initial="" onSave={onSave} />)
    const textarea = screen.getByRole('textbox')

    // First attempt — fails, error badge sticks.
    await userEvent.type(textarea, 'first')
    textarea.blur()
    await screen.findByRole('alert')

    // Second attempt — type more, blur. Before the promise resolves,
    // the badge must read "Saving…", NOT "Could not save".
    await userEvent.type(textarea, ' second')
    textarea.blur()
    await waitFor(() =>
      expect(screen.getByText(strings.notes.saving)).toBeInTheDocument(),
    )
    expect(screen.queryByText(strings.notes.saveError)).not.toBeInTheDocument()

    // Let the retry resolve so the test cleans up cleanly.
    retry.resolve?.()
  })
})

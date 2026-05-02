import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { NotesEditor } from '../NotesEditor'

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
})

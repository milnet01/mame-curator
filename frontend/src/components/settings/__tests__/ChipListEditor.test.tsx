import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, cleanup, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { ChipListEditor } from '../ChipListEditor'

afterEach(() => cleanup())

describe('ChipListEditor', () => {
  it('renders one chip per value with a remove-button accessible name', () => {
    render(
      <ChipListEditor
        ariaLabel="Drop genres"
        value={['shooter', 'puzzle', 'racing']}
        onChange={() => {}}
        addPlaceholder="Add genre…"
      />,
    )

    expect(
      screen.getByRole('list', { name: 'Drop genres' }),
    ).toBeInTheDocument()
    // One remove button per chip.
    expect(screen.getByRole('button', { name: 'Remove shooter' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Remove puzzle' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Remove racing' })).toBeInTheDocument()
  })

  it('renders the supplied placeholder on the trailing input', () => {
    render(
      <ChipListEditor
        ariaLabel="Drop genres"
        value={[]}
        onChange={() => {}}
        addPlaceholder="Add genre…"
      />,
    )
    expect(
      screen.getByPlaceholderText('Add genre…'),
    ).toBeInTheDocument()
  })

  it('adds a chip on Enter and clears the input', async () => {
    const onChange = vi.fn()
    render(
      <ChipListEditor
        ariaLabel="Drop genres"
        value={['shooter']}
        onChange={onChange}
        addPlaceholder="Add genre…"
      />,
    )

    const input = screen.getByPlaceholderText('Add genre…')
    await userEvent.type(input, 'puzzle{Enter}')

    expect(onChange).toHaveBeenCalledWith(['shooter', 'puzzle'])
    expect(input).toHaveValue('')
  })

  it('removes the clicked chip via its remove button', async () => {
    const onChange = vi.fn()
    render(
      <ChipListEditor
        ariaLabel="Drop genres"
        value={['shooter', 'puzzle', 'racing']}
        onChange={onChange}
        addPlaceholder="Add genre…"
      />,
    )

    await userEvent.click(
      screen.getByRole('button', { name: 'Remove puzzle' }),
    )

    expect(onChange).toHaveBeenCalledWith(['shooter', 'racing'])
  })

  it('removes the last chip on Backspace when the input is empty', async () => {
    const onChange = vi.fn()
    render(
      <ChipListEditor
        ariaLabel="Drop genres"
        value={['shooter', 'puzzle']}
        onChange={onChange}
        addPlaceholder="Add genre…"
      />,
    )

    const input = screen.getByPlaceholderText('Add genre…')
    input.focus()
    await userEvent.keyboard('{Backspace}')

    expect(onChange).toHaveBeenCalledWith(['shooter'])
  })

  it('does NOT remove on Backspace when the input has text', async () => {
    const onChange = vi.fn()
    render(
      <ChipListEditor
        ariaLabel="Drop genres"
        value={['shooter']}
        onChange={onChange}
        addPlaceholder="Add genre…"
      />,
    )

    const input = screen.getByPlaceholderText('Add genre…')
    await userEvent.type(input, 'p{Backspace}')

    expect(onChange).not.toHaveBeenCalled()
  })

  it('splits a comma-separated paste into multiple chips', async () => {
    const onChange = vi.fn()
    render(
      <ChipListEditor
        ariaLabel="Drop genres"
        value={['shooter']}
        onChange={onChange}
        addPlaceholder="Add genre…"
      />,
    )

    const input = screen.getByPlaceholderText('Add genre…')
    input.focus()
    await userEvent.paste('puzzle, racing,  fighting')

    expect(onChange).toHaveBeenCalledWith([
      'shooter',
      'puzzle',
      'racing',
      'fighting',
    ])
  })

  it('trims whitespace and ignores empty add attempts', async () => {
    const onChange = vi.fn()
    render(
      <ChipListEditor
        ariaLabel="Drop genres"
        value={[]}
        onChange={onChange}
        addPlaceholder="Add genre…"
      />,
    )

    const input = screen.getByPlaceholderText('Add genre…')
    await userEvent.type(input, '   {Enter}')
    expect(onChange).not.toHaveBeenCalled()

    await userEvent.type(input, '  shooter  {Enter}')
    expect(onChange).toHaveBeenLastCalledWith(['shooter'])
  })

  it('dedupes — adding an existing value is a no-op', async () => {
    const onChange = vi.fn()
    render(
      <ChipListEditor
        ariaLabel="Drop genres"
        value={['shooter']}
        onChange={onChange}
        addPlaceholder="Add genre…"
      />,
    )

    const input = screen.getByPlaceholderText('Add genre…')
    await userEvent.type(input, 'shooter{Enter}')

    expect(onChange).not.toHaveBeenCalled()
    expect(input).toHaveValue('')
  })

  it('renders chips in the listitem role', () => {
    render(
      <ChipListEditor
        ariaLabel="Drop genres"
        value={['shooter', 'puzzle']}
        onChange={() => {}}
        addPlaceholder="Add genre…"
      />,
    )

    const list = screen.getByRole('list', { name: 'Drop genres' })
    expect(within(list).getAllByRole('listitem')).toHaveLength(2)
  })
})

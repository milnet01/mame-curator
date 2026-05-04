import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, cleanup, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { DragReorderList } from '../DragReorderList'

afterEach(() => cleanup())

describe('DragReorderList', () => {
  it('exposes the list with the supplied ariaLabel and renders items in order', () => {
    render(
      <DragReorderList
        ariaLabel="Region priority"
        items={['us', 'eu', 'jp']}
        onChange={() => {}}
      />,
    )
    const list = screen.getByRole('list', { name: 'Region priority' })
    const items = within(list).getAllByRole('listitem')
    expect(items).toHaveLength(3)
    expect(within(items[0]).getByText('us')).toBeInTheDocument()
    expect(within(items[1]).getByText('eu')).toBeInTheDocument()
    expect(within(items[2]).getByText('jp')).toBeInTheDocument()
  })

  it('moves an item down when its Down button is clicked', async () => {
    const onChange = vi.fn()
    render(
      <DragReorderList
        ariaLabel="Region priority"
        items={['us', 'eu', 'jp']}
        onChange={onChange}
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: 'Move us down' }))
    expect(onChange).toHaveBeenCalledWith(['eu', 'us', 'jp'])
  })

  it('moves an item up when its Up button is clicked', async () => {
    const onChange = vi.fn()
    render(
      <DragReorderList
        ariaLabel="Region priority"
        items={['us', 'eu', 'jp']}
        onChange={onChange}
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: 'Move jp up' }))
    expect(onChange).toHaveBeenCalledWith(['us', 'jp', 'eu'])
  })

  it('disables the Up button on the first item', () => {
    render(
      <DragReorderList
        ariaLabel="Region priority"
        items={['us', 'eu', 'jp']}
        onChange={() => {}}
      />,
    )
    expect(screen.getByRole('button', { name: 'Move us up' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Move eu up' })).not.toBeDisabled()
  })

  it('disables the Down button on the last item', () => {
    render(
      <DragReorderList
        ariaLabel="Region priority"
        items={['us', 'eu', 'jp']}
        onChange={() => {}}
      />,
    )
    expect(screen.getByRole('button', { name: 'Move jp down' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Move eu down' })).not.toBeDisabled()
  })

  it('reorders downward via ArrowDown when an item is focused', async () => {
    const onChange = vi.fn()
    render(
      <DragReorderList
        ariaLabel="Region priority"
        items={['us', 'eu', 'jp']}
        onChange={onChange}
      />,
    )
    const items = screen.getAllByRole('listitem')
    items[0].focus()
    await userEvent.keyboard('{ArrowDown}')
    expect(onChange).toHaveBeenCalledWith(['eu', 'us', 'jp'])
  })

  it('reorders upward via ArrowUp when an item is focused', async () => {
    const onChange = vi.fn()
    render(
      <DragReorderList
        ariaLabel="Region priority"
        items={['us', 'eu', 'jp']}
        onChange={onChange}
      />,
    )
    const items = screen.getAllByRole('listitem')
    items[2].focus()
    await userEvent.keyboard('{ArrowUp}')
    expect(onChange).toHaveBeenCalledWith(['us', 'jp', 'eu'])
  })

  it('ignores ArrowUp on the first item (no onChange)', async () => {
    const onChange = vi.fn()
    render(
      <DragReorderList
        ariaLabel="Region priority"
        items={['us', 'eu', 'jp']}
        onChange={onChange}
      />,
    )
    const items = screen.getAllByRole('listitem')
    items[0].focus()
    await userEvent.keyboard('{ArrowUp}')
    expect(onChange).not.toHaveBeenCalled()
  })

  it('ignores ArrowDown on the last item (no onChange)', async () => {
    const onChange = vi.fn()
    render(
      <DragReorderList
        ariaLabel="Region priority"
        items={['us', 'eu', 'jp']}
        onChange={onChange}
      />,
    )
    const items = screen.getAllByRole('listitem')
    items[2].focus()
    await userEvent.keyboard('{ArrowDown}')
    expect(onChange).not.toHaveBeenCalled()
  })

  it('renders an empty list without crashing', () => {
    render(
      <DragReorderList
        ariaLabel="Region priority"
        items={[]}
        onChange={() => {}}
      />,
    )
    expect(screen.getByRole('list', { name: 'Region priority' })).toBeInTheDocument()
    expect(screen.queryAllByRole('listitem')).toHaveLength(0)
  })
})

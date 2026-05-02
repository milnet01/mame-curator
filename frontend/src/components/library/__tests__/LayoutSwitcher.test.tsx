import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { LayoutSwitcher } from '../LayoutSwitcher'
import type { LayoutName } from '@/api/types'

describe('LayoutSwitcher', () => {
  it('shows the current layout label', () => {
    render(<LayoutSwitcher value="masonry" onChange={() => {}} />)
    expect(screen.getByRole('button', { name: /masonry/i })).toBeInTheDocument()
  })

  it('lists every layout option in the menu', async () => {
    render(<LayoutSwitcher value="masonry" onChange={() => {}} />)
    await userEvent.click(screen.getByRole('button', { name: /masonry/i }))
    for (const layout of ['Masonry', 'List', 'Covers', 'Grouped']) {
      expect(await screen.findByRole('menuitemradio', { name: layout })).toBeInTheDocument()
    }
  })

  it('calls onChange with the picked layout', async () => {
    const onChange = vi.fn<(name: LayoutName) => void>()
    render(<LayoutSwitcher value="masonry" onChange={onChange} />)
    await userEvent.click(screen.getByRole('button', { name: /masonry/i }))
    await userEvent.click(await screen.findByRole('menuitemradio', { name: 'List' }))
    expect(onChange).toHaveBeenCalledWith('list')
  })
})

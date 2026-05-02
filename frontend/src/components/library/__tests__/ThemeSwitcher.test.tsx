import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { ThemeSwitcher } from '../ThemeSwitcher'
import type { ThemeName } from '@/api/types'

afterEach(() => {
  document.documentElement.removeAttribute('data-theme')
})

describe('ThemeSwitcher', () => {
  it('shows the current theme', () => {
    render(<ThemeSwitcher value="dark" onChange={() => {}} />)
    expect(screen.getByRole('button', { name: /dark/i })).toBeInTheDocument()
  })

  it('lists every theme option', async () => {
    render(<ThemeSwitcher value="dark" onChange={() => {}} />)
    await userEvent.click(screen.getByRole('button', { name: /dark/i }))
    for (const theme of ['Dark', 'Light', 'Double Dragon', 'Pac-Man', 'SF2', 'Neo Geo']) {
      expect(await screen.findByRole('menuitemradio', { name: theme })).toBeInTheDocument()
    }
  })

  it('sets data-theme on the document root and calls onChange', async () => {
    const onChange = vi.fn<(name: ThemeName) => void>()
    render(<ThemeSwitcher value="dark" onChange={onChange} />)
    await userEvent.click(screen.getByRole('button', { name: /dark/i }))
    await userEvent.click(await screen.findByRole('menuitemradio', { name: 'Pac-Man' }))
    expect(onChange).toHaveBeenCalledWith('pacman')
    expect(document.documentElement.getAttribute('data-theme')).toBe('pacman')
  })
})

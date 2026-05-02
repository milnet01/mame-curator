import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { ThemeSwitcher } from '../ThemeSwitcher'
import type { ThemeName } from '@/api/types'

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

  it('calls onChange with the picked theme name', async () => {
    // FP11 § D3: ThemeSwitcher delegates the DOM mutation to ThemeProvider
    // (single writer). The click handler ONLY fires onChange; the provider's
    // useEffect mirrors the config value into `data-theme`.
    const onChange = vi.fn<(name: ThemeName) => void>()
    render(<ThemeSwitcher value="dark" onChange={onChange} />)
    await userEvent.click(screen.getByRole('button', { name: /dark/i }))
    await userEvent.click(await screen.findByRole('menuitemradio', { name: 'Pac-Man' }))
    expect(onChange).toHaveBeenCalledWith('pacman')
  })
})

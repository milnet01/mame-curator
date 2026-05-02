import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { GameCard } from '../GameCard'
import { strings } from '@/strings'
import type { GameCard as GameCardType } from '@/api/types'

const baseCard: GameCardType = {
  short_name: 'pacman',
  description: 'Pac-Man (Midway)',
  year: 1980,
  manufacturer: 'Namco (Midway license)',
  publisher: 'Midway',
  developer: 'Namco',
  badges: [],
}

describe('GameCard', () => {
  it('renders title, year and publisher', () => {
    render(<GameCard card={baseCard} onOpen={() => {}} />)
    expect(screen.getByRole('heading', { name: 'Pac-Man (Midway)' })).toBeInTheDocument()
    // Year and publisher render together as "1980 · Midway".
    expect(screen.getByText(/1980 · Midway/)).toBeInTheDocument()
  })

  it('renders the box-art image with a media URL and accessible name', () => {
    render(<GameCard card={baseCard} onOpen={() => {}} />)
    const img = screen.getByAltText(strings.library.flyerAlt('Pac-Man (Midway)'))
    expect(img).toHaveAttribute('src', '/media/pacman/boxart')
  })

  it('falls back to a placeholder when the image fails to load', async () => {
    render(<GameCard card={baseCard} onOpen={() => {}} />)
    const img = screen.getByAltText(strings.library.flyerAlt('Pac-Man (Midway)'))
    img.dispatchEvent(new Event('error'))
    expect(
      await screen.findByText(strings.library.placeholderFlyer),
    ).toBeInTheDocument()
  })

  it('exposes every badge as an accessible label', () => {
    const card: GameCardType = {
      ...baseCard,
      badges: ['contested', 'overridden', 'chd_missing', 'bios_missing', 'has_notes'],
    }
    render(<GameCard card={card} onOpen={() => {}} />)
    expect(
      screen.getByLabelText(strings.library.badges.contested),
    ).toBeInTheDocument()
    expect(
      screen.getByLabelText(strings.library.badges.overridden),
    ).toBeInTheDocument()
    expect(
      screen.getByLabelText(strings.library.badges.chd_missing),
    ).toBeInTheDocument()
    expect(
      screen.getByLabelText(strings.library.badges.bios_missing),
    ).toBeInTheDocument()
    expect(
      screen.getByLabelText(strings.library.badges.has_notes),
    ).toBeInTheDocument()
  })

  it('calls onOpen when the user clicks the card', async () => {
    const onOpen = vi.fn()
    render(<GameCard card={baseCard} onOpen={onOpen} />)
    await userEvent.click(screen.getByRole('button', { name: /Pac-Man/ }))
    expect(onOpen).toHaveBeenCalledTimes(1)
  })

  it('calls onOpen when the user activates the card with Enter', async () => {
    const onOpen = vi.fn()
    render(<GameCard card={baseCard} onOpen={onOpen} />)
    const card = screen.getByRole('button', { name: /Pac-Man/ })
    card.focus()
    await userEvent.keyboard('{Enter}')
    expect(onOpen).toHaveBeenCalledTimes(1)
  })
})

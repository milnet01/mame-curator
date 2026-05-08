import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
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
    render(<GameCard card={baseCard} inCart={false} onOpen={() => {}} onAdd={() => {}} />)
    expect(screen.getByRole('heading', { name: 'Pac-Man (Midway)' })).toBeInTheDocument()
    // Year and publisher render together as "1980 · Midway".
    expect(screen.getByText(/1980 · Midway/)).toBeInTheDocument()
  })

  it('renders the short name so users can identify games without art', () => {
    render(<GameCard card={baseCard} inCart={false} onOpen={() => {}} onAdd={() => {}} />)
    expect(screen.getByText('pacman')).toBeInTheDocument()
  })

  it('renders the box-art image with a media URL and accessible name', () => {
    render(<GameCard card={baseCard} inCart={false} onOpen={() => {}} onAdd={() => {}} />)
    const img = screen.getByAltText(strings.library.flyerAlt('Pac-Man (Midway)'))
    expect(img).toHaveAttribute('src', '/media/pacman/boxart')
  })

  it('shows the description in the art area when the image fails (so the game is still identifiable)', () => {
    render(<GameCard card={baseCard} inCart={false} onOpen={() => {}} onAdd={() => {}} />)
    const img = screen.getByAltText(strings.library.flyerAlt('Pac-Man (Midway)'))
    fireEvent.error(img)
    // Description appears once in the heading and once as the art-area placeholder.
    const matches = screen.getAllByText('Pac-Man (Midway)')
    expect(matches.length).toBeGreaterThanOrEqual(2)
  })

  it('exposes every badge as an accessible label', () => {
    const card: GameCardType = {
      ...baseCard,
      badges: ['contested', 'overridden', 'chd_missing', 'bios_missing', 'has_notes'],
    }
    render(<GameCard card={card} inCart={false} onOpen={() => {}} onAdd={() => {}} />)
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
    render(<GameCard card={baseCard} inCart={false} onOpen={onOpen} onAdd={() => {}} />)
    await userEvent.click(screen.getByRole('button', { name: 'Pac-Man (Midway)' }))
    expect(onOpen).toHaveBeenCalledTimes(1)
  })

  it('calls onOpen when the user activates the card with Enter', async () => {
    const onOpen = vi.fn()
    render(<GameCard card={baseCard} inCart={false} onOpen={onOpen} onAdd={() => {}} />)
    const card = screen.getByRole('button', { name: 'Pac-Man (Midway)' })
    card.focus()
    await userEvent.keyboard('{Enter}')
    expect(onOpen).toHaveBeenCalledTimes(1)
  })

  // FP24-E + Q: outer card is a role="button" div (not a native button)
  // because the +Add control inside is itself a real button — nested
  // <button> is invalid HTML5. WAI-ARIA composite button still requires
  // both Enter and Space activation.
  it('calls onOpen when the user activates the card with Space', async () => {
    const onOpen = vi.fn()
    render(<GameCard card={baseCard} inCart={false} onOpen={onOpen} onAdd={() => {}} />)
    const card = screen.getByRole('button', { name: 'Pac-Man (Midway)' })
    card.focus()
    await userEvent.keyboard(' ')
    expect(onOpen).toHaveBeenCalledTimes(1)
  })

  it('outer card is not a native button (avoids nested-button HTML5 violation)', () => {
    render(<GameCard card={baseCard} inCart={false} onOpen={() => {}} onAdd={() => {}} />)
    const card = screen.getByRole('button', { name: 'Pac-Man (Midway)' })
    expect(card.tagName).not.toBe('BUTTON')
  })
})

describe('GameCard +Add', () => {
  it('renders an Add button when not in cart', () => {
    render(
      <GameCard card={baseCard} inCart={false} onOpen={() => {}} onAdd={() => {}} />,
    )
    expect(
      screen.getByRole('button', { name: /add pac-man \(midway\) to cart/i }),
    ).toBeInTheDocument()
  })

  it('renders ✓ Added when in cart', () => {
    render(
      <GameCard card={baseCard} inCart={true} onOpen={() => {}} onAdd={() => {}} />,
    )
    expect(screen.getByText(/✓ added/i)).toBeInTheDocument()
  })

  it('emits onAdd when Add button clicked, does not bubble to onOpen', () => {
    const onAdd = vi.fn()
    const onOpen = vi.fn()
    render(<GameCard card={baseCard} inCart={false} onOpen={onOpen} onAdd={onAdd} />)
    fireEvent.click(
      screen.getByRole('button', { name: /add pac-man \(midway\) to cart/i }),
    )
    expect(onAdd).toHaveBeenCalledWith('pacman')
    expect(onOpen).not.toHaveBeenCalled()
  })

  it('emits onOpen when card body clicked', () => {
    const onAdd = vi.fn()
    const onOpen = vi.fn()
    render(<GameCard card={baseCard} inCart={false} onOpen={onOpen} onAdd={onAdd} />)
    // Outer card button has aria-label === card.description
    fireEvent.click(screen.getByRole('button', { name: 'Pac-Man (Midway)' }))
    expect(onOpen).toHaveBeenCalled()
  })
})

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

  it('renders the box-art image with a media URL', () => {
    // FP20-H: img is decorative (alt=""), so queries by alt-text no
    // longer find it; the testid carries through. Decoration is the
    // right semantic — the heading already names the card via
    // aria-labelledby, so a duplicate alt would double-announce.
    render(<GameCard card={baseCard} inCart={false} onOpen={() => {}} onAdd={() => {}} />)
    const img = screen.getByTestId('gamecard-img-pacman')
    expect(img).toHaveAttribute('src', '/media/pacman/boxart')
  })

  it('shows the description in the art area when the image fails (so the game is still identifiable)', () => {
    render(<GameCard card={baseCard} inCart={false} onOpen={() => {}} onAdd={() => {}} />)
    const img = screen.getByTestId('gamecard-img-pacman')
    fireEvent.error(img)
    // Description appears once in the heading and once as the art-area placeholder.
    const matches = screen.getAllByText('Pac-Man (Midway)')
    expect(matches.length).toBeGreaterThanOrEqual(2)
  })

  // ---- FP20-H: accessible-name + decorative-image hardening ---------------

  it('outer card has no aria-label (avoids clobbering accessible name)', () => {
    render(<GameCard card={baseCard} inCart={false} onOpen={() => {}} onAdd={() => {}} />)
    const card = screen.getByRole('button', { name: 'Pac-Man (Midway)' })
    expect(card).not.toHaveAttribute('aria-label')
  })

  it('outer card delegates accessible name to the <h3> via aria-labelledby', () => {
    render(<GameCard card={baseCard} inCart={false} onOpen={() => {}} onAdd={() => {}} />)
    const card = screen.getByRole('button', { name: 'Pac-Man (Midway)' })
    const labelledBy = card.getAttribute('aria-labelledby')
    expect(labelledBy).toBe('gamecard-title-pacman')
    const heading = screen.getByRole('heading', { name: 'Pac-Man (Midway)' })
    expect(heading.id).toBe('gamecard-title-pacman')
  })

  it('box-art image is marked decorative (alt="") so the heading is the sole name source', () => {
    render(<GameCard card={baseCard} inCart={false} onOpen={() => {}} onAdd={() => {}} />)
    const img = screen.getByTestId('gamecard-img-pacman')
    expect(img).toHaveAttribute('alt', '')
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
    // FP20-H: outer card's accessible name now comes from the <h3> via
    // aria-labelledby — no aria-label on the wrapper.
    fireEvent.click(screen.getByRole('button', { name: 'Pac-Man (Midway)' }))
    expect(onOpen).toHaveBeenCalled()
  })

  // ---- P14 — review-state badge (chunk 10) -------------------------------

  it('renders no review-state badge when prop is undefined (pending)', () => {
    render(
      <GameCard
        card={baseCard}
        inCart={false}
        onOpen={() => {}}
        onAdd={() => {}}
      />,
    )
    expect(screen.queryByTestId('review-badge-reviewed')).not.toBeInTheDocument()
    expect(screen.queryByTestId('review-badge-skipped')).not.toBeInTheDocument()
    expect(screen.queryByTestId('review-badge-needs-decision')).not.toBeInTheDocument()
  })

  it.each([
    ['reviewed', strings.library.badges.reviewed, 'text-emerald-500'],
    ['skipped', strings.library.badges.skipped, 'text-rose-500'],
    ['needs-decision', strings.library.badges.needsDecision, 'text-amber-500'],
  ] as const)(
    'renders the %s badge with the correct label + tint',
    (state, label, tint) => {
      render(
        <GameCard
          card={baseCard}
          inCart={false}
          onOpen={() => {}}
          onAdd={() => {}}
          reviewState={state}
        />,
      )
      const badge = screen.getByTestId(`review-badge-${state}`)
      expect(badge).toHaveAttribute('aria-label', label)
      // tint is applied to the inner icon (svg child).
      expect(badge.querySelector('svg')).toHaveClass(tint)
    },
  )
})

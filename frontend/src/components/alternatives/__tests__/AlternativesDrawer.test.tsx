import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import type { ReactElement } from 'react'

import { AlternativesDrawer } from '../AlternativesDrawer'
import type { GameCard } from '@/api/types'

// FP22-B introduced a <Link> in the disabled-Launch hint, so any render
// that exercises the Launch path needs a router context. Wrapping every
// render keeps the existing tests untouched while supporting the new
// ones.
function renderWithRouter(ui: ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>)
}

// `short_name` + `description` are required per fixture; the rest default
// to the Namco/Midway/1980 shape these tests share (mame-curator-1055n).
function makeGameCard(
  overrides: Partial<GameCard> & Pick<GameCard, 'short_name' | 'description'>,
): GameCard {
  return {
    year: 1980,
    manufacturer: 'Namco',
    publisher: 'Midway',
    developer: 'Namco',
    badges: [],
    ...overrides,
  }
}

const winner: GameCard = makeGameCard({ short_name: 'pacman', description: 'Pac-Man' })
const clones: GameCard[] = [
  makeGameCard({ short_name: 'pacmanf', description: 'Pac-Man (fast hack)' }),
  makeGameCard({ short_name: 'pacmanjr', description: 'Pac-Man Jr.', year: 1981 }),
]

describe('AlternativesDrawer', () => {
  it('renders parent + clones when open', () => {
    renderWithRouter(
      <AlternativesDrawer
        open
        onOpenChange={() => {}}
        winner={winner}
        alternatives={[winner, ...clones]}
        onOverride={() => {}}
      />,
    )
    expect(screen.getByText('Pac-Man')).toBeInTheDocument()
    expect(screen.getByText('Pac-Man (fast hack)')).toBeInTheDocument()
    expect(screen.getByText('Pac-Man Jr.')).toBeInTheDocument()
  })

  it('calls onOverride with parent + chosen winner and closes', async () => {
    const onOverride = vi.fn()
    const onOpenChange = vi.fn()
    renderWithRouter(
      <AlternativesDrawer
        open
        onOpenChange={onOpenChange}
        winner={winner}
        alternatives={[winner, ...clones]}
        onOverride={onOverride}
      />,
    )
    await userEvent.click(
      screen.getByRole('button', { name: /Use Pac-Man Jr\./i }),
    )
    expect(onOverride).toHaveBeenCalledWith({
      parent: 'pacman',
      winner: 'pacmanjr',
    })
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('disables the use-this-version button on the current winner', () => {
    renderWithRouter(
      <AlternativesDrawer
        open
        onOpenChange={() => {}}
        winner={winner}
        alternatives={[winner, ...clones]}
        onOverride={() => {}}
      />,
    )
    const winnerButton = screen.getByRole('button', { name: /Pac-Man.*selected/i })
    expect(winnerButton).toBeDisabled()
  })

  it('shows "only version" hint and no rows when alternatives.length === 1 (FP11 § B5)', () => {
    renderWithRouter(
      <AlternativesDrawer
        open
        onOpenChange={() => {}}
        winner={winner}
        alternatives={[winner]}
        onOverride={() => {}}
      />,
    )
    expect(
      screen.getByText(/only version in the library/i),
    ).toBeInTheDocument()
    // No rows = no Use buttons rendered.
    expect(screen.queryByRole('button', { name: /^Use /i })).not.toBeInTheDocument()
  })

  it('renders boxart media on every row (FP11 § B6)', () => {
    renderWithRouter(
      <AlternativesDrawer
        open
        onOpenChange={() => {}}
        winner={winner}
        alternatives={[winner, ...clones]}
        onOverride={() => {}}
      />,
    )
    expect(screen.getByAltText(/Box art for Pac-Man$/)).toHaveAttribute(
      'src',
      '/media/pacman/boxart',
    )
    expect(screen.getByAltText(/Box art for Pac-Man Jr\./)).toHaveAttribute(
      'src',
      '/media/pacmanjr/boxart',
    )
  })

  it('disables Launch and shows the configure hint when RetroArch is not configured (FP22-B)', () => {
    renderWithRouter(
      <AlternativesDrawer
        open
        onOpenChange={() => {}}
        winner={winner}
        alternatives={[winner, ...clones]}
        onOverride={() => {}}
        onLaunch={() => {}}
        retroarchConfigured={false}
      />,
    )
    const launchButton = screen.getByRole('button', { name: /Launch in RetroArch/i })
    expect(launchButton).toBeDisabled()
    // The hint text spans a <Link> in the middle, so assert against the
    // combined textContent of the status element rather than getByText.
    const hint = screen.getByRole('status')
    expect(hint.textContent).toMatch(/Configure RetroArch in Settings.*to enable launching/i)
    // Hint links to Settings → Paths so the user can fix it in one click.
    const link = screen.getByRole('link', { name: /Settings.*Paths/i })
    expect(link).toHaveAttribute('href', '/settings?tab=paths')
  })

  it('does not call onLaunch when the button is gated (FP22-B)', async () => {
    const onLaunch = vi.fn()
    renderWithRouter(
      <AlternativesDrawer
        open
        onOpenChange={() => {}}
        winner={winner}
        alternatives={[winner, ...clones]}
        onOverride={() => {}}
        onLaunch={onLaunch}
        retroarchConfigured={false}
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: /Launch in RetroArch/i }))
    expect(onLaunch).not.toHaveBeenCalled()
  })

  it('enables Launch when retroarchConfigured is true (FP22-B)', async () => {
    const onLaunch = vi.fn()
    renderWithRouter(
      <AlternativesDrawer
        open
        onOpenChange={() => {}}
        winner={winner}
        alternatives={[winner, ...clones]}
        onOverride={() => {}}
        onLaunch={onLaunch}
        retroarchConfigured
      />,
    )
    const launchButton = screen.getByRole('button', { name: /Launch in RetroArch/i })
    expect(launchButton).toBeEnabled()
    await userEvent.click(launchButton)
    expect(onLaunch).toHaveBeenCalledWith('pacman')
  })

  it('treats undefined retroarchConfigured as not-yet-known and disables Launch (FP22-B)', () => {
    // setupCheck.data is undefined while the query is loading; the button
    // should not be clickable until we have a definitive answer, otherwise
    // the user can race the query and trigger a 422.
    renderWithRouter(
      <AlternativesDrawer
        open
        onOpenChange={() => {}}
        winner={winner}
        alternatives={[winner, ...clones]}
        onOverride={() => {}}
        onLaunch={() => {}}
      />,
    )
    expect(screen.getByRole('button', { name: /Launch in RetroArch/i })).toBeDisabled()
  })
})

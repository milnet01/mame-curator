import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { AlternativesDrawer } from '../AlternativesDrawer'
import type { GameCard } from '@/api/types'

const winner: GameCard = {
  short_name: 'pacman',
  description: 'Pac-Man',
  year: 1980,
  manufacturer: 'Namco',
  publisher: 'Midway',
  developer: 'Namco',
  badges: [],
}
const clones: GameCard[] = [
  {
    short_name: 'pacmanf',
    description: 'Pac-Man (fast hack)',
    year: 1980,
    manufacturer: 'Namco',
    publisher: 'Midway',
    developer: 'Namco',
    badges: [],
  },
  {
    short_name: 'pacmanjr',
    description: 'Pac-Man Jr.',
    year: 1981,
    manufacturer: 'Namco',
    publisher: 'Midway',
    developer: 'Namco',
    badges: [],
  },
]

describe('AlternativesDrawer', () => {
  it('renders parent + clones when open', () => {
    render(
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
    render(
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
    render(
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
})

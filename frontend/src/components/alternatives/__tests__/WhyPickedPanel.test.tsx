import { describe, expect, it } from 'vitest'
import { render, screen, within } from '@testing-library/react'

import { WhyPickedPanel } from '../WhyPickedPanel'
import type { Explanation } from '@/api/types'

const explanation: Explanation = {
  short_name: 'pacman',
  parent: 'pacman',
  candidates: ['pacman', 'pacmanf', 'pacmanjr'],
  hits: [
    { name: 'region_priority', detail: 'World > USA' },
    { name: 'driver_status', detail: 'good > imperfect' },
    { name: 'parent_over_clone', detail: 'parent wins' },
  ],
}

describe('WhyPickedPanel', () => {
  it('renders the hits chain in order', () => {
    render(<WhyPickedPanel explanation={explanation} />)
    const items = screen.getAllByRole('listitem')
    expect(items).toHaveLength(3)
    expect(within(items[0]!).getByText(/region_priority/)).toBeInTheDocument()
    expect(within(items[0]!).getByText(/World > USA/)).toBeInTheDocument()
    expect(within(items[1]!).getByText(/driver_status/)).toBeInTheDocument()
    expect(within(items[2]!).getByText(/parent_over_clone/)).toBeInTheDocument()
  })

  it('renders the candidate list and highlights the parent', () => {
    render(<WhyPickedPanel explanation={explanation} />)
    expect(screen.getByText(/pacmanf/)).toBeInTheDocument()
    expect(screen.getByText(/pacmanjr/)).toBeInTheDocument()
  })

  it('renders an empty hint when no hits are present', () => {
    render(
      <WhyPickedPanel
        explanation={{ ...explanation, hits: [] }}
      />,
    )
    expect(screen.getByText(/no tiebreaker chain/i)).toBeInTheDocument()
  })
})

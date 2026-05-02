import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'

import { StatsPage } from '../StatsPage'
import type { Stats } from '@/api/types'

const stats: Stats = {
  by_genre: { Fighting: 120, Shooter: 200, Platformer: 60 },
  by_decade: { '1980s': 50, '1990s': 250, '2000s': 80 },
  by_publisher: { Capcom: 180, Konami: 60, SNK: 90 },
  by_driver_status: { good: 350, imperfect: 25, preliminary: 5 },
  total_bytes: 15.4 * 1024 ** 3,
}

describe('StatsPage', () => {
  it('renders every section header from the fixture', () => {
    render(<StatsPage stats={stats} />)
    expect(screen.getByText(/by genre/i)).toBeInTheDocument()
    expect(screen.getByText(/by decade/i)).toBeInTheDocument()
    expect(screen.getByText(/top publishers/i)).toBeInTheDocument()
    expect(screen.getByText(/driver status/i)).toBeInTheDocument()
  })

  it('renders the per-bucket counts', () => {
    render(<StatsPage stats={stats} />)
    expect(screen.getByText('Fighting')).toBeInTheDocument()
    expect(screen.getByText('120')).toBeInTheDocument()
    expect(screen.getByText('1990s')).toBeInTheDocument()
    expect(screen.getByText('Capcom')).toBeInTheDocument()
  })

  it('renders the total library size', () => {
    render(<StatsPage stats={stats} />)
    expect(screen.getByText(/15\.4 GB/)).toBeInTheDocument()
  })
})

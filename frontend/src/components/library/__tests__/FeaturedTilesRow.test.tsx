import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { FeaturedTilesRow } from '@/components/library/FeaturedTilesRow'
import { strings } from '@/strings'

describe('FeaturedTilesRow', () => {
  it('renders each tile from strings.library.featured.tiles', () => {
    render(
      <FeaturedTilesRow counts={{}} activeTileId={null} onTileSelect={() => {}} />,
    )
    for (const tile of strings.library.featured.tiles) {
      expect(screen.getByText(tile.title)).toBeInTheDocument()
    }
  })

  it('shows count when provided', () => {
    render(
      <FeaturedTilesRow
        counts={{ 'beat-em-ups': 51 }}
        activeTileId={null}
        onTileSelect={() => {}}
      />,
    )
    expect(screen.getByText(/51 games/i)).toBeInTheDocument()
  })

  it('emits onTileSelect with the tile id on click', () => {
    const onTileSelect = vi.fn()
    render(
      <FeaturedTilesRow counts={{}} activeTileId={null} onTileSelect={onTileSelect} />,
    )
    // DS04 T3.2: query by accessible role + name rather than
    // `.closest('button')` from a label text node — RTL idiom that
    // also surfaces an a11y regression if the tile stops being a
    // proper button.
    const button = screen.getByRole('button', { name: 'Capcom Classics' })
    fireEvent.click(button)
    expect(onTileSelect).toHaveBeenCalledWith('capcom-classics')
  })

  it('marks the active tile with aria-pressed=true', () => {
    render(
      <FeaturedTilesRow
        counts={{}}
        activeTileId="beat-em-ups"
        onTileSelect={() => {}}
      />,
    )
    const active = screen.getByText("Beat 'em Ups").closest('button')!
    expect(active).toHaveAttribute('aria-pressed', 'true')
  })
})

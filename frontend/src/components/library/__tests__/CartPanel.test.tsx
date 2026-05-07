import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { CartPanel } from '@/components/library/CartPanel'

const items = [
  { shortName: 'pacman' },
  { shortName: '1942', chosenVariant: '1942j' },
]

describe('CartPanel', () => {
  it('does not render when open=false', () => {
    render(
      <CartPanel
        open={false}
        items={items}
        onRemove={() => {}}
        onClearAll={() => {}}
      />,
    )
    expect(screen.queryByText(/pacman/)).not.toBeInTheDocument()
  })

  it('renders one row per cart item when open=true', () => {
    render(
      <CartPanel
        open={true}
        items={items}
        onRemove={() => {}}
        onClearAll={() => {}}
      />,
    )
    expect(screen.getByText('pacman')).toBeInTheDocument()
    expect(screen.getByText('1942')).toBeInTheDocument()
  })

  it('shows variant badge when chosenVariant is set', () => {
    render(
      <CartPanel
        open={true}
        items={items}
        onRemove={() => {}}
        onClearAll={() => {}}
      />,
    )
    expect(screen.getByText('⇄ 1942j')).toBeInTheDocument()
  })

  it('emits onRemove(shortName) when ✕ is clicked', () => {
    const onRemove = vi.fn()
    render(
      <CartPanel
        open={true}
        items={items}
        onRemove={onRemove}
        onClearAll={() => {}}
      />,
    )
    fireEvent.click(screen.getByRole('button', { name: /remove pacman/i }))
    expect(onRemove).toHaveBeenCalledWith('pacman')
  })

  it('emits onClearAll when Clear all is clicked', () => {
    const onClearAll = vi.fn()
    render(
      <CartPanel
        open={true}
        items={items}
        onRemove={() => {}}
        onClearAll={onClearAll}
      />,
    )
    fireEvent.click(screen.getByRole('button', { name: /clear all/i }))
    expect(onClearAll).toHaveBeenCalled()
  })
})

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import type { ComponentProps } from 'react'
import { CartBar } from '@/components/library/CartBar'

const noop = () => {}

type CartBarProps = ComponentProps<typeof CartBar>

function cartBarProps(overrides: Partial<CartBarProps> = {}): CartBarProps {
  return {
    itemCount: 0,
    bulkAddTotal: null,
    expanded: false,
    onBulkAdd: noop,
    onToggleExpand: noop,
    onDryRun: noop,
    onCopy: noop,
    ...overrides,
  }
}

function renderCartBar(overrides: Partial<CartBarProps> = {}) {
  return render(<CartBar {...cartBarProps(overrides)} />)
}

describe('CartBar', () => {
  it('renders empty-cart summary when items=0', () => {
    renderCartBar()
    expect(screen.getByText(/cart empty/i)).toBeInTheDocument()
  })

  it('disables Copy and Dry-run when cart empty', () => {
    renderCartBar()
    expect(screen.getByRole('button', { name: /copy/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /dry-run/i })).toBeDisabled()
  })

  it('shows summary when itemCount > 0', () => {
    renderCartBar({ itemCount: 51 })
    // FP24-B: GB figure removed from CartBar — useCart.totalBytes is
    // a v1-deferred concept (see useCart.ts § 4.1 docstring), and showing
    // the filtered-library byte total here misled users about copy size.
    expect(screen.getByText(/51 games/)).toBeInTheDocument()
    expect(screen.queryByText(/GB/i)).not.toBeInTheDocument()
  })

  it('shows bulk-add button only when bulkAddTotal is non-null', () => {
    const { rerender } = renderCartBar()
    expect(screen.queryByRole('button', { name: /add all/i })).not.toBeInTheDocument()

    rerender(<CartBar {...cartBarProps({ bulkAddTotal: 51 })} />)
    expect(screen.getByRole('button', { name: /add all 51/i })).toBeInTheDocument()
  })

  it('emits callbacks on click', () => {
    const onBulkAdd = vi.fn()
    const onToggleExpand = vi.fn()
    const onDryRun = vi.fn()
    const onCopy = vi.fn()
    renderCartBar({ itemCount: 3, bulkAddTotal: 51, onBulkAdd, onToggleExpand, onDryRun, onCopy })
    fireEvent.click(screen.getByRole('button', { name: /add all 51/i }))
    fireEvent.click(screen.getByRole('button', { name: /expand cart/i }))
    fireEvent.click(screen.getByRole('button', { name: /dry-run/i }))
    fireEvent.click(screen.getByRole('button', { name: /^copy$/i }))
    expect(onBulkAdd).toHaveBeenCalled()
    expect(onToggleExpand).toHaveBeenCalled()
    expect(onDryRun).toHaveBeenCalled()
    expect(onCopy).toHaveBeenCalled()
  })

  it('expand button uses Collapse aria-label when expanded=true', () => {
    renderCartBar({ itemCount: 3, expanded: true })
    expect(screen.getByRole('button', { name: /collapse cart/i })).toBeInTheDocument()
  })
})

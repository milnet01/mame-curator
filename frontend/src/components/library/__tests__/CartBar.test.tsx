import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { CartBar } from '@/components/library/CartBar'

const noop = () => {}

describe('CartBar', () => {
  it('renders empty-cart summary when items=0', () => {
    render(
      <CartBar
        itemCount={0}
        totalSizeBytes={0}
        bulkAddTotal={null}
        expanded={false}
        onBulkAdd={noop}
        onToggleExpand={noop}
        onDryRun={noop}
        onCopy={noop}
      />,
    )
    expect(screen.getByText(/cart empty/i)).toBeInTheDocument()
  })

  it('disables Copy and Dry-run when cart empty', () => {
    render(
      <CartBar
        itemCount={0}
        totalSizeBytes={0}
        bulkAddTotal={null}
        expanded={false}
        onBulkAdd={noop}
        onToggleExpand={noop}
        onDryRun={noop}
        onCopy={noop}
      />,
    )
    expect(screen.getByRole('button', { name: /copy/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /dry-run/i })).toBeDisabled()
  })

  it('shows summary when itemCount > 0', () => {
    render(
      <CartBar
        itemCount={51}
        totalSizeBytes={1024 ** 3 * 2.5}
        bulkAddTotal={null}
        expanded={false}
        onBulkAdd={noop}
        onToggleExpand={noop}
        onDryRun={noop}
        onCopy={noop}
      />,
    )
    expect(screen.getByText(/51 games · 2\.5 GB/)).toBeInTheDocument()
  })

  it('shows bulk-add button only when bulkAddTotal is non-null', () => {
    const { rerender } = render(
      <CartBar
        itemCount={0}
        totalSizeBytes={0}
        bulkAddTotal={null}
        expanded={false}
        onBulkAdd={noop}
        onToggleExpand={noop}
        onDryRun={noop}
        onCopy={noop}
      />,
    )
    expect(screen.queryByRole('button', { name: /add all/i })).not.toBeInTheDocument()

    rerender(
      <CartBar
        itemCount={0}
        totalSizeBytes={0}
        bulkAddTotal={51}
        expanded={false}
        onBulkAdd={noop}
        onToggleExpand={noop}
        onDryRun={noop}
        onCopy={noop}
      />,
    )
    expect(screen.getByRole('button', { name: /add all 51/i })).toBeInTheDocument()
  })

  it('emits callbacks on click', () => {
    const onBulkAdd = vi.fn()
    const onToggleExpand = vi.fn()
    const onDryRun = vi.fn()
    const onCopy = vi.fn()
    render(
      <CartBar
        itemCount={3}
        totalSizeBytes={0}
        bulkAddTotal={51}
        expanded={false}
        onBulkAdd={onBulkAdd}
        onToggleExpand={onToggleExpand}
        onDryRun={onDryRun}
        onCopy={onCopy}
      />,
    )
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
    render(
      <CartBar
        itemCount={3}
        totalSizeBytes={0}
        bulkAddTotal={null}
        expanded={true}
        onBulkAdd={noop}
        onToggleExpand={noop}
        onDryRun={noop}
        onCopy={noop}
      />,
    )
    expect(screen.getByRole('button', { name: /collapse cart/i })).toBeInTheDocument()
  })
})

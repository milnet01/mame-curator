import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

import { ErrorBoundary } from '../ErrorBoundary'

function Boom({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) throw new Error('kaboom')
  return <p>safe</p>
}

describe('ErrorBoundary', () => {
  // Restore the console.error spies even if an assertion throws first,
  // so a leaked silencer can't mask real errors in later tests.
  afterEach(() => vi.restoreAllMocks())

  it('renders children when no error is thrown', () => {
    render(
      <ErrorBoundary>
        <Boom shouldThrow={false} />
      </ErrorBoundary>,
    )
    expect(screen.getByText('safe')).toBeInTheDocument()
  })

  it('renders the fallback panel when a child throws', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    render(
      <ErrorBoundary>
        <Boom shouldThrow />
      </ErrorBoundary>,
    )
    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByText('kaboom')).toBeInTheDocument()  })

  it('clears the error when resetKey changes', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const { rerender } = render(
      <ErrorBoundary resetKey="a">
        <Boom shouldThrow />
      </ErrorBoundary>,
    )
    expect(screen.getByRole('alert')).toBeInTheDocument()
    rerender(
      <ErrorBoundary resetKey="b">
        <Boom shouldThrow={false} />
      </ErrorBoundary>,
    )
    expect(screen.getByText('safe')).toBeInTheDocument()  })

  it('exposes a Try again button in the fallback panel', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    render(
      <ErrorBoundary>
        <Boom shouldThrow />
      </ErrorBoundary>,
    )
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()  })
})
